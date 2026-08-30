"""CCTV analysis pipeline: frames -> faces -> emotion / posture / gaze -> traits.

Pure CV/behavioural logic. It knows nothing about authentication, roles or
scope; the CV routes apply those before calling in here.
"""
from __future__ import annotations

import base64
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from cv_analysis.config import (
    ANALYSIS_DIR,
    FRAME_DIFFERENCE_THRESHOLD,
    INPUT_VIDEOS_DIR,
    PROFILES_DIR,
    SIMILARITY_THRESHOLD,
)
from cv_analysis.db import (
    db_insert_analysis_with_traits,
    db_insert_frame,
    db_insert_video,
    db_upsert_person,
)
from cv_analysis.libraries import (
    DEEPFACE_AVAILABLE,
    FACE_RECOGNITION_AVAILABLE,
    MEDIAPIPE_AVAILABLE,
    MTCNN_AVAILABLE,
    DeepFace,
    _clahe,
    _MTCNN_GLOBAL,
    cv2,
    face_recognition,
    mp_face_mesh,
    mp_pose,
    np,
)
from cv_analysis.state import _db_lock, analysis_cache, person_database, pinned_profiles

_posture_call_counter = 0

# ─── FRAME UTILITIES ──────────────────────────────────────────────────────────

def enhance_frame_for_cctv(frame):
    """CLAHE + bilateral filter for low-res CCTV footage."""
    try:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = _clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        return cv2.bilateralFilter(enhanced, 5, 45, 45)
    except:
        return frame


def enhance_face_crop(face_image):
    """CLAHE + unsharp mask for face crops."""
    if face_image is None or face_image.size == 0:
        return face_image
    try:
        lab = cv2.cvtColor(face_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = _clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.2)
        return cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    except:
        return face_image


def upscale_for_detection(image, target_min_side=640):
    """Upscale image to at least target_min_side on the short side for better detection."""
    h, w = image.shape[:2]
    short_side = min(h, w)
    if short_side >= target_min_side:
        return image, 1.0
    scale = target_min_side / short_side
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    upscaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    # Apply sharpening after upscale
    blur = cv2.GaussianBlur(upscaled, (0, 0), 0.8)
    upscaled = cv2.addWeighted(upscaled, 1.4, blur, -0.4, 0)
    return upscaled, scale


def calculate_frame_difference(frame1, frame2):
    if frame1 is None or frame2 is None:
        return 1.0
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    diff  = cv2.absdiff(gray1, gray2)
    return np.sum(diff) / (gray1.shape[0] * gray1.shape[1] * 255)


def extract_intelligent_frames(video_path, max_frames=12):
    print(f"Processing video: {video_path}")
    cap         = cv2.VideoCapture(str(video_path))
    total       = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps         = cap.get(cv2.CAP_PROP_FPS) or 25.0

    if total == 0 or fps == 0:
        cap.release()
        return []

    interval       = max(1, total // (max_frames * 2))
    selected       = []
    prev_frame     = None
    frame_idx      = 0

    while len(selected) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        # Cap maximum resolution to keep speed reasonable
        if frame.shape[0] > 720:
            scale  = 720 / frame.shape[0]
            frame  = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        # Enhance each frame for detection
        frame = enhance_frame_for_cctv(frame)

        if prev_frame is None:
            selected.append((frame_idx, frame))
            prev_frame = frame
        else:
            if calculate_frame_difference(prev_frame, frame) > FRAME_DIFFERENCE_THRESHOLD:
                selected.append((frame_idx, frame))
                prev_frame = frame

        frame_idx += interval
        if frame_idx >= total:
            break

    cap.release()
    print(f"  Extracted {len(selected)} keyframes from {total} total frames")
    return selected

# ─── FACE ENCODING HELPER ─────────────────────────────────────────────────────

def get_face_encoding_from_crop(face_roi):
    """Get 128-d face encoding from a cropped face image."""
    if face_roi is None or face_roi.size == 0:
        return [0.0] * 128
    if FACE_RECOGNITION_AVAILABLE:
        try:
            rgb  = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, number_of_times_to_upsample=1, model='hog')
            encs = face_recognition.face_encodings(rgb, locs, num_jitters=1)
            if encs:
                return encs[0].tolist()
        except:
            pass
    # Fallback: pixel histogram as pseudo-encoding
    try:
        resized = cv2.resize(face_roi, (32, 32))
        gray    = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        hist    = cv2.calcHist([gray], [0], None, [128], [0, 256]).flatten()
        norm    = np.linalg.norm(hist)
        return (hist / (norm + 1e-6)).tolist()
    except:
        return [0.0] * 128


# ─── IMPROVED FACE DETECTION ──────────────────────────────────────────────────

def detect_all_faces_in_frame(image):
    """
    Multi-model, multi-scale face detection ensemble.
    Order: MTCNN → face_recognition HOG → MediaPipe → Haar cascade.
    Upscales low-res frames for dramatically better detection of distant/small faces.
    """
    h_orig, w_orig = image.shape[:2]
    all_detections = []
    seen_boxes     = []

    # ── IoU helpers ────────────────────────────────────────────────────────
    def box_iou(b1, b2):
        x1 = max(b1[0], b2[0]);  y1 = max(b1[1], b2[1])
        x2 = min(b1[0]+b1[2], b2[0]+b2[2]);  y2 = min(b1[1]+b1[3], b2[1]+b2[3])
        inter = max(0, x2-x1) * max(0, y2-y1)
        union = b1[2]*b1[3] + b2[2]*b2[3] - inter
        return inter / (union + 1e-6)

    def already_seen(bbox, threshold=0.30):
        for sb in seen_boxes:
            if box_iou(bbox, sb) > threshold:
                return True
        return False

    def add_detection(orig_image, ox, oy, ow, oh, enc, quality, source):
        """Clip to image bounds, skip if duplicate, add to list."""
        ox  = max(0, ox);  oy  = max(0, oy)
        ow  = min(w_orig - ox, ow);  oh  = min(h_orig - oy, oh)
        if ow < 12 or oh < 12:
            return
        bbox     = (ox, oy, ow, oh)
        if already_seen(bbox):
            return
        face_roi = orig_image[oy:oy+oh, ox:ox+ow].copy()
        if face_roi.size == 0:
            return
        if enc is None:
            enc = get_face_encoding_from_crop(face_roi)
        all_detections.append({
            'bbox':          bbox,
            'encoding':      enc,
            'face_image':    face_roi,
            'quality_score': quality,
            'source':        source
        })
        seen_boxes.append(bbox)

    # ── Upscaled version for small/low-res frames ───────────────────────
    upscaled, up_scale = upscale_for_detection(image, target_min_side=480)
    uh, uw = upscaled.shape[:2]

    def map_back(x, y, bw, bh, scale):
        """Map detected coordinates back to original image space."""
        return (
            max(0, int(x  / scale)),
            max(0, int(y  / scale)),
            max(1, int(bw / scale)),
            max(1, int(bh / scale))
        )

    # ══ 1. MTCNN — best for low-res, occluded, varied-angle faces ════════
    if MTCNN_AVAILABLE and _MTCNN_GLOBAL is not None:
        for img, scale in [(image, 1.0), (upscaled, up_scale)]:
            try:
                rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                dets = _MTCNN_GLOBAL.detect_faces(rgb)
                for d in dets:
                    if d['confidence'] < 0.70:
                        continue
                    x, y, bw, bh = d['box']
                    x, y = max(0, x), max(0, y)
                    ox, oy, ow, oh = map_back(x, y, bw, bh, scale)
                    face_roi = image[oy:oy+oh, ox:ox+ow].copy() if oh > 0 and ow > 0 else None
                    enc = get_face_encoding_from_crop(face_roi) if face_roi is not None else None
                    add_detection(image, ox, oy, ow, oh, enc, float(d['confidence']), 'mtcnn')
            except Exception as e:
                print(f"  MTCNN error: {e}")

    # ══ 2. face_recognition HOG — fast, reliable for frontal faces ═══════
    if FACE_RECOGNITION_AVAILABLE:
        for img, scale in [(image, 1.0), (upscaled, up_scale)]:
            for upsample in [1, 2]:
                try:
                    rgb  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    locs = face_recognition.face_locations(rgb, number_of_times_to_upsample=upsample, model='hog')
                    encs = face_recognition.face_encodings(rgb, locs, num_jitters=1)
                    for (top, right, bottom, left), enc in zip(locs, encs):
                        ox, oy, ow, oh = map_back(left, top, right-left, bottom-top, scale)
                        # Slight padding
                        pad_x = int(ow * 0.12);  pad_y = int(oh * 0.18)
                        add_detection(image, ox-pad_x, oy-pad_y, ow+pad_x*2, oh+pad_y*2, enc.tolist(),
                                      (ow*oh)/(w_orig*h_orig+1e-6), 'face_recognition')
                except Exception as e:
                    pass  # silently skip failed upsamples

    # ══ 3. MediaPipe — good at full-frontal, medium distance ═════════════
    if MEDIAPIPE_AVAILABLE:
        for img, scale in [(image, 1.0), (upscaled, up_scale)]:
            ph, pw = img.shape[:2]
            for model_sel, min_conf in [(1, 0.30), (0, 0.30)]:
                try:
                    fd  = mp.solutions.face_detection.FaceDetection(
                            model_selection=model_sel,
                            min_detection_confidence=min_conf)
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    res = fd.process(rgb)
                    fd.close()
                    if not res.detections:
                        continue
                    for det in res.detections:
                        bb   = det.location_data.relative_bounding_box
                        x    = max(0, int(bb.xmin * pw))
                        y    = max(0, int(bb.ymin * ph))
                        bw2  = min(pw-x, int(bb.width  * pw))
                        bh2  = min(ph-y, int(bb.height * ph))
                        if bw2 < 10 or bh2 < 10:
                            continue
                        ox, oy, ow, oh = map_back(x, y, bw2, bh2, scale)
                        face_roi = image[oy:oy+oh, ox:ox+ow].copy() if oh>0 and ow>0 else None
                        enc = get_face_encoding_from_crop(face_roi) if face_roi is not None else None
                        score = float(det.score[0]) if det.score else 0.5
                        add_detection(image, ox, oy, ow, oh, enc, score, 'mediapipe')
                except Exception as e:
                    print(f"  MediaPipe fd error: {e}")

    # ══ 4. Haar cascade fallback (always runs as safety net) ═════════════
    if len(all_detections) == 0 or True:   # always supplement with Haar
        cascade_configs = [
            (cv2.data.haarcascades + 'haarcascade_frontalface_default.xml', 1.05, 3),
            (cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',    1.04, 2),
            (cv2.data.haarcascades + 'haarcascade_profileface.xml',         1.05, 2),
        ]
        for img, scale in [(image, 1.0), (upscaled, up_scale)]:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.equalizeHist(gray, gray)
            for cpath, sf, mn in cascade_configs:
                try:
                    cascade = cv2.CascadeClassifier(cpath)
                    if cascade.empty():
                        continue
                    dets = cascade.detectMultiScale(
                        gray, scaleFactor=sf, minNeighbors=mn,
                        minSize=(15, 15), flags=cv2.CASCADE_SCALE_IMAGE)
                    if len(dets) == 0:
                        continue
                    for (x, y, fw, fh) in dets:
                        ox, oy, ow, oh = map_back(x, y, fw, fh, scale)
                        face_roi = image[oy:oy+oh, ox:ox+ow].copy() if oh>0 and ow>0 else None
                        enc = get_face_encoding_from_crop(face_roi) if face_roi is not None else None
                        add_detection(image, ox, oy, ow, oh, enc,
                                      (ow*oh)/(w_orig*h_orig+1e-6), 'haar')
                except:
                    pass

    # ── Final NMS: remove any remaining heavy overlaps ──────────────────
    if len(all_detections) > 1:
        all_detections.sort(key=lambda d: d['quality_score'], reverse=True)
        kept  = []
        kboxes = []
        for det in all_detections:
            if not any(box_iou(det['bbox'], kb) > 0.40 for kb in kboxes):
                kept.append(det)
                kboxes.append(det['bbox'])
        all_detections = kept

    print(f"  Detected {len(all_detections)} faces in frame")
    return all_detections


# ─── GAZE & ATTENTION ANALYSIS ────────────────────────────────────────────────

def analyze_gaze_and_attention(face_image):
    """
    Analyze gaze direction and attention using MediaPipe Face Mesh iris landmarks.
    Returns direction, attention score, head pose, and eye-contact flag.
    """
    result = {
        'gaze_direction':  'forward',   # forward/left/right/up/down
        'gaze_horizontal': 0.0,         # -1 (left) … +1 (right)
        'gaze_vertical':   0.0,         # -1 (up)   … +1 (down)
        'head_yaw':        0.0,         # degrees, negative=turned left
        'head_pitch':      0.0,         # degrees, negative=tilted up
        'attention_score': 50,          # 0-100
        'focus_zone':      'ahead',     # ahead/camera/left/right/up/down/distracted
        'eye_contact':     False,
        'eye_openness':    50,
    }

    if face_image is None or face_image.size == 0 or not MEDIAPIPE_AVAILABLE:
        return result

    try:
        h, w = face_image.shape[:2]
        # Upscale tiny faces for mesh quality
        scale_up = 1.0
        if h < 80 or w < 80:
            scale_up = max(80 / h, 80 / w, 2.0)
            face_image = cv2.resize(face_image,
                                    (int(w * scale_up), int(h * scale_up)),
                                    interpolation=cv2.INTER_LANCZOS4)

        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,          # enables iris landmarks 468-477
            min_detection_confidence=0.35,
            min_tracking_confidence=0.35
        )
        rgb          = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        mesh_result  = face_mesh.process(rgb)
        face_mesh.close()

        if not mesh_result.multi_face_landmarks:
            return result

        lm = mesh_result.multi_face_landmarks[0].landmark

        # ── Iris landmarks (refine_landmarks required) ──
        # Left iris:  474-477  |  Right iris:  469-472
        L_IRIS = [474, 475, 476, 477]
        R_IRIS = [469, 470, 471, 472]

        # Eye boundary landmarks
        L_EYE_IN  = 362;  L_EYE_OUT = 263
        R_EYE_IN  = 133;  R_EYE_OUT = 33
        L_EYE_TOP = 386;  L_EYE_BOT = 374
        R_EYE_TOP = 159;  R_EYE_BOT = 145

        # Iris centres
        l_iris = np.mean([[lm[i].x, lm[i].y] for i in L_IRIS], axis=0)
        r_iris = np.mean([[lm[i].x, lm[i].y] for i in R_IRIS], axis=0)

        # Eye centres & dimensions
        l_cx = (lm[L_EYE_IN].x + lm[L_EYE_OUT].x) / 2
        l_cy = (lm[L_EYE_TOP].y + lm[L_EYE_BOT].y) / 2
        r_cx = (lm[R_EYE_IN].x + lm[R_EYE_OUT].x) / 2
        r_cy = (lm[R_EYE_TOP].y + lm[R_EYE_BOT].y) / 2
        l_ew = abs(lm[L_EYE_OUT].x - lm[L_EYE_IN].x)
        r_ew = abs(lm[R_EYE_OUT].x - lm[R_EYE_IN].x)
        l_eh = abs(lm[L_EYE_TOP].y - lm[L_EYE_BOT].y)
        r_eh = abs(lm[R_EYE_TOP].y - lm[R_EYE_BOT].y)

        # Gaze offset (normalised to eye size)
        l_gx = (l_iris[0] - l_cx) / (l_ew + 1e-6)
        r_gx = (r_iris[0] - r_cx) / (r_ew + 1e-6)
        l_gy = (l_iris[1] - l_cy) / (l_eh + 1e-6)
        r_gy = (r_iris[1] - r_cy) / (r_eh + 1e-6)

        gaze_x = float(np.clip(np.mean([l_gx, r_gx]) * 3, -1, 1))
        gaze_y = float(np.clip(np.mean([l_gy, r_gy]) * 3, -1, 1))

        # Eye openness (mean of both eyes ear-ratio)
        eye_open_l = l_eh / (l_ew + 1e-6)
        eye_open_r = r_eh / (r_ew + 1e-6)
        eye_openness = int(np.clip(np.mean([eye_open_l, eye_open_r]) * 500, 0, 100))

        # ── Head pose via facial landmark geometry ──────────────────────
        NOSE_TIP  = 1
        CHIN      = 152
        L_TEMPLE  = 234
        R_TEMPLE  = 454
        L_EYE_C   = 468 if len(lm) > 468 else 159   # iris centre if available
        R_EYE_C   = 473 if len(lm) > 473 else 386

        face_width = abs(lm[L_TEMPLE].x - lm[R_TEMPLE].x) + 1e-6
        # Head yaw: nose deviates left/right from face midline
        mid_x      = (lm[L_TEMPLE].x + lm[R_TEMPLE].x) / 2
        yaw_norm   = (lm[NOSE_TIP].x - mid_x) / face_width
        head_yaw   = float(np.clip(yaw_norm * 80, -45, 45))

        # Head pitch: nose relative to eye-to-chin centre
        mid_y      = (lm[R_EYE_TOP].y + lm[L_EYE_TOP].y) / 2
        chin_y     = lm[CHIN].y
        nose_y     = lm[NOSE_TIP].y
        pitch_norm = (nose_y - (mid_y + chin_y) / 2) / (abs(chin_y - mid_y) + 1e-6)
        head_pitch = float(np.clip(pitch_norm * 60 - 10, -30, 30))

        # ── Direction classification ──────────────────────────────────
        H_THRESH = 0.10;  V_THRESH = 0.10
        if abs(gaze_x) < H_THRESH and abs(gaze_y) < V_THRESH:
            direction = 'forward'
        elif abs(gaze_x) >= abs(gaze_y):
            direction = 'right' if gaze_x > 0 else 'left'
        else:
            direction = 'down' if gaze_y > 0 else 'up'

        # Eye contact: gaze forward + head roughly facing camera
        eye_contact = (direction == 'forward'
                       and abs(head_yaw) < 15
                       and abs(head_pitch) < 12)

        # Focus zone for display
        if eye_contact:
            focus_zone = 'camera'
        elif direction == 'forward':
            focus_zone = 'ahead'
        elif direction in ('left', 'right'):
            focus_zone = 'side'
        else:
            focus_zone = direction

        # ── Attention score ──────────────────────────────────────────
        forward_bonus  = 40 if direction == 'forward' else 5
        head_bonus     = max(0, 30 - abs(head_yaw) * 0.8 - abs(head_pitch) * 0.6)
        eye_bonus      = min(30, eye_openness * 0.3)
        attention      = int(np.clip(forward_bonus + head_bonus + eye_bonus, 0, 100))

        result.update({
            'gaze_direction':  direction,
            'gaze_horizontal': round(gaze_x, 3),
            'gaze_vertical':   round(gaze_y, 3),
            'head_yaw':        round(head_yaw, 1),
            'head_pitch':      round(head_pitch, 1),
            'attention_score': attention,
            'focus_zone':      focus_zone,
            'eye_contact':     bool(eye_contact),
            'eye_openness':    eye_openness,
        })

    except Exception as e:
        print(f"  Gaze analysis error: {e}")

    return result


# ─── POSTURE ANALYSIS ─────────────────────────────────────────────────────────

def analyze_posture_for_person(full_frame, face_bbox):
    h, w = full_frame.shape[:2]
    fx, fy, fw, fh = face_bbox

    body_x1 = max(0, fx - int(fw * 0.8))
    body_y1 = max(0, fy)
    body_x2 = min(w, fx + fw + int(fw * 0.8))
    body_y2 = min(h, fy + fh * 5)
    person_crop = full_frame[body_y1:body_y2, body_x1:body_x2]

    default = {
        'shoulder_symmetry': 50, 'head_forward_tilt': 50,
        'spine_alignment':   50, 'body_openness': 50,
        'movement_energy':   50, 'posture_quality': 'unknown',
        'posture_score':     50, 'energy_level': 50, 'landmarks': None
    }

    if (not MEDIAPIPE_AVAILABLE or person_crop.size == 0
            or person_crop.shape[0] < 40 or person_crop.shape[1] < 20):
        return default

    try:
        pose = mp_pose.Pose(static_image_mode=True, model_complexity=0,
                            min_detection_confidence=0.35, min_tracking_confidence=0.35)
        enhanced = enhance_face_crop(person_crop)
        rgb      = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        results  = pose.process(rgb)
        pose.close()

        if not results.pose_landmarks:
            return default

        lm  = results.pose_landmarks.landmark
        L   = mp_pose.PoseLandmark

        ls  = lm[L.LEFT_SHOULDER.value];   rs  = lm[L.RIGHT_SHOULDER.value]
        lh  = lm[L.LEFT_HIP.value];        rh  = lm[L.RIGHT_HIP.value]
        nose = lm[L.NOSE.value]
        lw  = lm[L.LEFT_WRIST.value];      rw  = lm[L.RIGHT_WRIST.value]
        le_elbow = lm[L.LEFT_ELBOW.value]; re_elbow = lm[L.RIGHT_ELBOW.value]

        shoulder_diff     = abs(ls.y - rs.y)
        shoulder_symmetry = max(0, 100 - shoulder_diff * 400)

        mid_shoulder_x    = (ls.x + rs.x) / 2
        head_forward_tilt = max(0, 100 - abs(nose.x - mid_shoulder_x) * 300)

        mid_hip_x         = (lh.x + rh.x) / 2
        spine_alignment   = max(0, 100 - abs(mid_shoulder_x - mid_hip_x) * 350)

        shoulder_width    = abs(ls.x - rs.x)
        hip_width         = abs(lh.x - rh.x)
        body_openness     = min(100, max(0, shoulder_width / (hip_width + 1e-6) * 60))

        arm_activity      = np.mean([(1-lw.y), (1-rw.y), (1-le_elbow.y), (1-re_elbow.y)]) * 100
        movement_energy   = min(100, max(0, arm_activity * 1.4))

        posture_score = float(np.clip(
            shoulder_symmetry * 0.25 + head_forward_tilt * 0.20 +
            spine_alignment   * 0.25 + body_openness    * 0.15 +
            movement_energy   * 0.15, 0, 100))

        if   posture_score >= 78: posture_quality = 'excellent'; el_base = 75
        elif posture_score >= 60: posture_quality = 'good';      el_base = 60
        elif posture_score >= 42: posture_quality = 'fair';      el_base = 45
        else:                     posture_quality = 'poor';      el_base = 25

        energy_level = min(100, int(el_base + movement_energy * 0.20))

        return {
            'shoulder_symmetry': int(shoulder_symmetry),
            'head_forward_tilt': int(head_forward_tilt),
            'spine_alignment':   int(spine_alignment),
            'body_openness':     int(body_openness),
            'movement_energy':   int(movement_energy),
            'posture_quality':   posture_quality,
            'posture_score':     round(posture_score, 1),
            'energy_level':      energy_level,
            'landmarks':         [(l.x, l.y, l.z) for l in lm]
        }
    except Exception as e:
        print(f"  Per-person posture error: {e}")
        return default


# ─── FACE TEXTURE TRAITS ──────────────────────────────────────────────────────

def analyze_face_texture_traits(face_image):
    traits = {
        'face_brightness':      50,
        'facial_tension':       50,
        'eye_openness':         50,
        'skin_tone_uniformity': 50
    }
    if face_image is None or face_image.size == 0:
        return traits
    try:
        gray    = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(face_image, (96, 96))
        gray_r  = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        traits['face_brightness']      = int(np.clip(np.mean(gray) / 2.55, 0, 100))
        lap                            = cv2.Laplacian(gray_r, cv2.CV_64F)
        traits['facial_tension']       = int(np.clip(float(np.std(lap)) / 3, 0, 100))
        h, w                           = gray_r.shape
        eye_region                     = gray_r[int(h*0.2):int(h*0.55), :]
        traits['eye_openness']         = int(np.clip(float(np.mean(eye_region)) / 2.55, 0, 100))
        hsv                            = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        traits['skin_tone_uniformity'] = 100 - int(np.clip(float(np.std(hsv[:,:,1])) / 1.28, 0, 100))
    except Exception as e:
        print(f"  Texture analysis error: {e}")
    return traits


# ─── EMOTION ANALYSIS ─────────────────────────────────────────────────────────

def analyze_emotion_full(face_image):
    emotion_data = {
        'dominant_emotion':    'neutral',
        'emotion_scores':      {'happy':0,'neutral':60,'sad':0,'angry':0,'fear':0,'surprise':0,'disgust':0},
        'engagement':          50,
        'stress_level':        'low',
        'emotional_positivity':50,
        'emotional_stability': 60,
        'social_confidence':   50,
    }
    if face_image is None or face_image.size == 0:
        return emotion_data

    if DEEPFACE_AVAILABLE:
        try:
            enhanced = enhance_face_crop(face_image) if face_image.shape[0] >= 40 else face_image
            result   = DeepFace.analyze(enhanced, actions=['emotion'],
                                         enforce_detection=False, silent=True)
            if isinstance(result, list):
                result = result[0]
            em = result['emotion']
            emotion_data['dominant_emotion'] = result['dominant_emotion']
            emotion_data['emotion_scores']   = {k: round(float(v), 2) for k, v in em.items()}

            happy   = em.get('happy',   0);  neutral = em.get('neutral', 0)
            sad     = em.get('sad',     0);  angry   = em.get('angry',   0)
            fear    = em.get('fear',    0);  surprise= em.get('surprise', 0)
            disgust = em.get('disgust', 0)

            positive = happy + neutral*0.5 + surprise*0.3
            negative = sad*1.2 + angry*1.4 + fear*1.3 + disgust*1.1
            stress_raw = (angry*1.5 + fear*1.4 + sad*0.9 + disgust*0.8) / 100

            emotion_data.update({
                'emotional_positivity': int(np.clip(50 + (positive-negative)*0.45, 0, 100)),
                'engagement':           int(np.clip((happy*1.3 + surprise*0.9 + neutral*0.6)*0.6, 0, 100)),
                'stress_level':         'high' if stress_raw>0.35 else 'moderate' if stress_raw>0.15 else 'low',
                'emotional_stability':  int(np.clip(100 - stress_raw*120, 0, 100)),
                'social_confidence':    int(np.clip((happy*1.1+neutral*0.7-sad*0.8-fear*0.9)*0.5+40, 0, 100)),
            })
        except Exception as e:
            print(f"  DeepFace error: {e}")
    else:
        # Texture-based fallback
        try:
            texture  = analyze_face_texture_traits(face_image)
            bright   = texture['face_brightness']
            tension  = texture['facial_tension']
            emotion_data.update({
                'emotional_positivity': int(np.clip(bright*0.7 + (100-tension)*0.3, 0, 100)),
                'emotional_stability':  int(np.clip((100-tension)*0.8 + bright*0.2, 0, 100)),
                'engagement':           int(np.clip(bright*0.6 + texture['eye_openness']*0.4, 0, 100)),
                'social_confidence':    int(np.clip(bright*0.8*0.8, 0, 100)),
                'stress_level':         'high' if tension>65 else 'moderate' if tension>40 else 'low',
            })
        except Exception as e:
            print(f"  Fallback emotion error: {e}")

    return emotion_data


# ─── WELLBEING TRAITS ─────────────────────────────────────────────────────────

def compute_10_trait_wellbeing(emotion_data, posture_data, texture_traits, gaze_data=None):
    if gaze_data is None:
        gaze_data = {}

    gaze_attention = gaze_data.get('attention_score', 50)
    eye_openness   = gaze_data.get('eye_openness',   texture_traits.get('eye_openness', 50))

    traits = {
        'emotional_positivity': int(np.clip(emotion_data.get('emotional_positivity', 50), 0, 100)),
        'stress_resilience':    int(np.clip(emotion_data.get('emotional_stability',  60), 0, 100)),
        'social_engagement':    int(np.clip(emotion_data.get('engagement',           50), 0, 100)),
        'social_confidence':    int(np.clip(emotion_data.get('social_confidence',    50), 0, 100)),
        'physical_energy':      int(np.clip(posture_data.get('energy_level',         50), 0, 100)),
        'posture_health':       int(np.clip(posture_data.get('posture_score',        50), 0, 100)),
        'body_openness':        int(np.clip(posture_data.get('body_openness',        50), 0, 100)),
        'focus_alertness':      int(np.clip(
            eye_openness   * 0.30 +
            posture_data.get('head_forward_tilt', 50) * 0.25 +
            gaze_attention * 0.45,
            0, 100)),
        'facial_relaxation':    int(np.clip(100 - texture_traits.get('facial_tension', 50), 0, 100)),
        'vitality_glow':        int(np.clip(
            texture_traits.get('face_brightness',      50) * 0.5 +
            texture_traits.get('skin_tone_uniformity', 50) * 0.5,
            0, 100)),
    }

    weights = {
        'emotional_positivity': 0.18, 'stress_resilience':  0.14,
        'social_engagement':    0.10, 'social_confidence':  0.08,
        'physical_energy':      0.14, 'posture_health':     0.12,
        'body_openness':        0.06, 'focus_alertness':    0.10,
        'facial_relaxation':    0.04, 'vitality_glow':      0.04,
    }

    overall      = sum(traits[k] * weights[k] for k in weights)
    stress_pen   = {'high': 8, 'moderate': 3, 'low': 0}.get(emotion_data.get('stress_level', 'low'), 0)
    overall      = max(0, int(np.clip(overall, 0, 100)) - stress_pen)
    return traits, overall


# ─── PROFILE IMAGE — FACE-CENTRED ZOOM ────────────────────────────────────────

_blank_b64 = None
def _get_blank_b64():
    global _blank_b64
    if _blank_b64 is None:
        blank = np.ones((240, 200, 3), dtype=np.uint8) * 228
        _, buf = cv2.imencode('.jpg', blank)
        _blank_b64 = base64.b64encode(buf).decode('utf-8')
    return _blank_b64


def create_profile_image(frame, face_bbox):
    """
    Creates a face-centred, zoomed profile photo from the ORIGINAL frame.
    • Crops face + 55 % padding on all sides
    • Upscales to 240 × 240 (2-step Lanczos for very small faces)
    • CLAHE + unsharp mask to recover CCTV detail
    """
    if frame is None or frame.size == 0 or face_bbox is None:
        return _get_blank_b64()
    try:
        fh_img, fw_img = frame.shape[:2]
        fx, fy, fw, fh = face_bbox

        # Ensure minimum face size
        if fw < 8 or fh < 8:
            return _get_blank_b64()

        # Generous padding so hair / chin are visible
        pad   = int(max(fw, fh) * 0.60)
        x1    = max(0, fx - pad)
        y1    = max(0, fy - pad)
        x2    = min(fw_img, fx + fw + pad)
        y2    = min(fh_img, fy + fh + pad)

        crop  = frame[y1:y2, x1:x2].copy()
        if crop.size == 0:
            return _get_blank_b64()

        h_c, w_c = crop.shape[:2]
        TARGET   = 240

        # CLAHE contrast boost
        lab  = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l    = _clahe.apply(l)
        crop = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # 2-step upscale for very small CCTV faces
        scale = min(TARGET / h_c, TARGET / w_c)
        if scale > 2.0:
            crop = cv2.resize(crop, (w_c*2, h_c*2), interpolation=cv2.INTER_LANCZOS4)
            h_c, w_c = crop.shape[:2]
            scale    = min(TARGET / h_c, TARGET / w_c)

        new_h = max(1, int(h_c * scale))
        new_w = max(1, int(w_c * scale))
        crop  = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Unsharp mask — sharpens CCTV blur
        blur  = cv2.GaussianBlur(crop, (0, 0), sigmaX=1.0)
        crop  = cv2.addWeighted(crop, 1.55, blur, -0.55, 0)

        # Centre on square canvas
        canvas = np.ones((TARGET, TARGET, 3), dtype=np.uint8) * 228
        y_off  = (TARGET - new_h) // 2
        x_off  = (TARGET - new_w) // 2
        canvas[y_off:y_off+new_h, x_off:x_off+new_w] = crop

        _, buf = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return base64.b64encode(buf).decode('utf-8')
    except:
        return _get_blank_b64()


def score_frame_quality(frame, face_bbox):
    if frame is None or frame.size == 0:
        return 0.0
    try:
        fx, fy, fw, fh = face_bbox
        fh_img, fw_img = frame.shape[:2]
        face_roi       = frame[fy:fy+fh, fx:fx+fw]
        if face_roi.size == 0:
            return 0.0
        gray           = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        sharpness      = min(100.0, float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 4.0)
        size_score     = min(100.0, (fw * fh) / (fw_img * fh_img + 1e-6) * 2000.0)
        brightness     = max(0.0, 100.0 - abs(float(np.mean(gray)) - 120) * 1.3)
        contrast       = min(100.0, float(np.std(gray)) * 2.2)
        h_f, w_f       = gray.shape
        if w_f > 10:
            left_h  = gray[:, :w_f//2]
            right_h = cv2.flip(gray[:, w_f-w_f//2:], 1)
            mw      = min(left_h.shape[1], right_h.shape[1])
            sym     = max(0.0, 100.0 - np.mean(np.abs(left_h[:,:mw].astype(float) - right_h[:,:mw].astype(float))) * 2.5)
        else:
            sym = 40.0
        return float(sharpness*0.35 + size_score*0.25 + sym*0.20 + brightness*0.12 + contrast*0.08)
    except:
        return 0.0


# ─── PERSON MATCHING ──────────────────────────────────────────────────────────

def calculate_person_similarity(enc1, enc2):
    if enc1 is None or enc2 is None:
        return 0.0
    try:
        a = np.array(enc1, dtype=np.float64)
        b = np.array(enc2, dtype=np.float64)
        if len(a) == 128 and len(b) == 128:
            return float(max(0.0, 1.0 - np.linalg.norm(a - b) / 0.80))
        min_len = min(len(a), len(b))
        a = a[:min_len];  b = b[:min_len]
        n1 = np.linalg.norm(a);  n2 = np.linalg.norm(b)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.clip(np.dot(a, b) / (n1 * n2 + 1e-6), 0.0, 1.0))
    except:
        return 0.0


_NAMES_LIST = [
    "Alex Chen", "Jordan Blake", "Morgan Silva", "Taylor Reed",
    "Casey Wright", "Riley Storm", "Drew Patel", "Quinn Davis",
    "Avery Stone", "Parker Lane", "Skyler Fox", "Cameron Wells",
    "Bailey Ross", "Rowan Hart", "Finley Nash", "Sage Kumar",
    "Noel Sharma", "River Das", "Emery Nair", "Phoenix Iyer",
    "Arjun Mehta", "Priya Rajan", "Kiran Bose", "Ananya Pillai",
    "Rohan Verma", "Diya Kapoor", "Vikram Singh", "Tara Rao",
    "Aditya Joshi", "Meera Nair"
]


def match_or_create_person(face_data, frame_image, timestamp, date_str, school_name='Unknown School'):
    encoding  = face_data['encoding']
    face_bbox = face_data['bbox']
    quality   = score_frame_quality(frame_image, face_bbox)

    best_match = None;  best_sim = 0

    with _db_lock:
        for pid, pinfo in person_database.items():
            if pinfo.get('school') != school_name:
                continue
            for stored_enc in pinfo.get('all_encodings', [pinfo.get('encoding')]):
                if stored_enc is None:
                    continue
                sim = calculate_person_similarity(encoding, stored_enc)
                if sim > best_sim and sim > SIMILARITY_THRESHOLD:
                    best_sim   = sim
                    best_match = pid

        if best_match:
            pid = best_match
            person_database[pid]['last_seen']        = timestamp
            person_database[pid]['appearance_count'] += 1
            if date_str not in person_database[pid]['dates_seen']:
                person_database[pid]['dates_seen'].append(date_str)

            all_encs = person_database[pid].get('all_encodings', [])
            if len(all_encs) < 10:
                all_encs.append(encoding)
                person_database[pid]['all_encodings'] = all_encs

            # Update profile photo if this frame is sharper
            if quality > person_database[pid].get('best_quality', 0):
                profile_img = create_profile_image(frame_image, face_bbox)
                if profile_img != _get_blank_b64():
                    person_database[pid]['best_quality']  = quality
                    person_database[pid]['profile_image'] = profile_img
                    print(f"  ↑ Profile photo updated for {pid} (q={quality:.1f})")
            # Persist updated person to DB
            db_upsert_person(pid, person_database[pid])
            return pid

        # ── New person ──────────────────────────────────────────────────
        school_count = sum(1 for p in person_database.values() if p.get('school') == school_name)
        person_id    = f"{school_name.replace(' ','_').upper()}_P{school_count+1:04d}"
        auto_name    = _NAMES_LIST[len(person_database) % len(_NAMES_LIST)]
        profile_img  = create_profile_image(frame_image, face_bbox)

        person_database[person_id] = {
            'person_id':        person_id,
            'name':             auto_name,
            'school':           school_name,
            'encoding':         encoding,
            'all_encodings':    [encoding],
            'first_seen':       timestamp,
            'last_seen':        timestamp,
            'dates_seen':       [date_str],
            'appearance_count': 1,
            'profile_image':    profile_img,
            'best_quality':     quality,
            'is_name_editable': True,
        }
        print(f"  + New person: {auto_name} ({person_id}) @ {school_name}")
        # Persist new person to DB
        db_upsert_person(person_id, person_database[person_id])
        return person_id


# ─── FRAME ANALYSIS ───────────────────────────────────────────────────────────

def _analyse_one_face(face_data, frame, timestamp, date_str, school_name):
    """Stateless analysis for one face — safe to run in a thread pool."""
    person_id = match_or_create_person(face_data, frame, timestamp, date_str, school_name)
    face_img  = face_data['face_image']
    bbox      = face_data['bbox']

    emotion  = analyze_emotion_full(face_img)
    texture  = analyze_face_texture_traits(face_img)
    gaze     = analyze_gaze_and_attention(face_img)

    return person_id, emotion, texture, gaze, bbox


def analyze_frame(frame, frame_idx, timestamp, date_str, school_name='Unknown School'):
    global _posture_call_counter
    frame_analysis = {'frame_idx': frame_idx, 'timestamp': timestamp, 'persons': []}

    faces = detect_all_faces_in_frame(frame)
    if not faces:
        print(f"  Frame {frame_idx}: no faces detected")
        return frame_analysis

    print(f"  Frame {frame_idx}: {len(faces)} face(s) found")

    # Run emotion + gaze in parallel, then merge sequentially for person matching
    results = []
    with ThreadPoolExecutor(max_workers=min(4, len(faces))) as pool:
        futures = [
            pool.submit(_analyse_one_face, fd, frame, timestamp, date_str, school_name)
            for fd in faces
        ]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                print(f"  Face analysis error: {e}")

    for person_id, emotion, texture, gaze, bbox in results:
        _posture_call_counter += 1
        if _posture_call_counter % 3 == 1:
            posture = analyze_posture_for_person(frame, bbox)
            analyze_frame._last_posture = posture
        else:
            posture = getattr(analyze_frame, '_last_posture', None) or \
                      analyze_posture_for_person(frame, bbox)

        traits, overall = compute_10_trait_wellbeing(emotion, posture, texture, gaze)
                # ── Write to DB ──────────────────────────────────────────────
        # frame_id is passed down from analyze_video_file (Step 6 below)
        _db_frame_id = getattr(analyze_frame, '_current_db_frame_id', None)
        db_insert_analysis_with_traits(
            frame_id        = _db_frame_id,
            person_id       = person_id,
            emotion         = emotion.get('dominant_emotion', 'neutral'),
            wellbeing_score = overall,
            attention_score = gaze.get('attention_score', 50),
            posture_score   = int(posture.get('posture_score', 50)),
            traits          = traits,
        )
        # ─────────────────────────────────────────────────────────────
        frame_analysis['persons'].append({
            'person_id':       person_id,
            'has_face':        True,
            'emotion':         emotion,
            'posture':         posture,
            'texture':         texture,
            'gaze':            gaze,
            'traits':          traits,
            'overall_wellbeing': overall,
        })

    return frame_analysis


analyze_frame._last_posture = None


# ─── VIDEO & DATE PIPELINE ────────────────────────────────────────────────────

def analyze_video_file(video_path, date_str, school_name='Unknown School'):
    print(f"Analyzing: {video_path.name}")
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()

    frames = extract_intelligent_frames(video_path)
    video_analysis = {
        'video_name':            video_path.name,
        'date':                  date_str,
        'school':                school_name,
        'total_frames_analyzed': len(frames),
        'fps':                   fps,
        'frames':                []
    }
    db_video_id = db_insert_video(video_path.name, school_name, date_str)
    for frame_idx, frame in frames:
      frame_time_sec = round(frame_idx / fps, 2)

      # Insert frame record and make its id available to analyze_frame
      db_frame_id = db_insert_frame(db_video_id, frame_idx, frame_time_sec)
      analyze_frame._current_db_frame_id = db_frame_id

      result = analyze_frame(frame, frame_idx, datetime.now().isoformat(), date_str, school_name)
      result['frame_time_sec'] = frame_time_sec
      video_analysis['frames'].append(result)

    return video_analysis


def analyze_date_folder(date_folder, school_name='Unknown School'):
    date_str    = date_folder.name
    print(f"  Date: {date_str} | School: {school_name}")

    video_exts  = ["*.mp4","*.avi","*.mov","*.mkv","*.MP4","*.MOV","*.AVI","*.MKV","*.webm","*.flv"]
    video_files = []
    for pat in video_exts:
        video_files.extend(date_folder.glob(pat))
    video_files = list(set(video_files))

    if not video_files:
        print(f"  No videos in {date_str}")
        return None

    date_analysis = {'date': date_str, 'school': school_name, 'videos': [], 'summary': {}}
    for vf in video_files:
        date_analysis['videos'].append(analyze_video_file(vf, date_str, school_name))

    all_persons   = set()
    all_wellbeing = []
    for video in date_analysis['videos']:
        for frame in video['frames']:
            for person in frame['persons']:
                all_persons.add(person['person_id'])
                all_wellbeing.append(person['overall_wellbeing'])

    date_analysis['summary'] = {
        'unique_persons':    len(all_persons),
        'average_wellbeing': int(np.mean(all_wellbeing)) if all_wellbeing else 0,
        'total_detections':  len(all_wellbeing)
    }

    safe_school = school_name.replace(' ', '_').replace('/', '-')
    out_file    = ANALYSIS_DIR / f"analysis_{safe_school}_{date_str}.json"
    with open(out_file, 'w') as f:
        json.dump(date_analysis, f, indent=2)
    print(f"  Saved: {out_file.name}")
    return date_analysis


def analyze_all_dates():
    print("Starting Sentio Mind analysis pipeline")
    school_folders = sorted([d for d in INPUT_VIDEOS_DIR.iterdir() if d.is_dir()])

    if not school_folders:
        print("No school folders in input_videos/")
        return {}

    all_results = {}
    for school_folder in school_folders:
        school_name  = school_folder.name
        print(f"\nSchool: {school_name}")
        date_folders = sorted([d for d in school_folder.iterdir() if d.is_dir()])[-5:]
        for date_folder in date_folders:
            result = analyze_date_folder(date_folder, school_name)
            if result:
                all_results[f"{school_name}|{result['date']}"] = result

    profiles_file = PROFILES_DIR / "person_database.json"
    with open(profiles_file, 'w') as f:
        json.dump({
            pid: {
                'person_id':        d['person_id'],
                'name':             d['name'],
                'school':           d.get('school', ''),
                'first_seen':       d['first_seen'],
                'last_seen':        d['last_seen'],
                'dates_seen':       d['dates_seen'],
                'appearance_count': d['appearance_count'],
                'profile_image':    d['profile_image'],
                'is_name_editable': d.get('is_name_editable', True)
            }
            for pid, d in person_database.items()
        }, f, indent=2)

    print(f"\nTotal unique persons: {len(person_database)}")
    return all_results


# ─── REPORT GENERATION ────────────────────────────────────────────────────────

TRAIT_KEYS = [
    'emotional_positivity', 'stress_resilience', 'social_engagement',
    'social_confidence',    'physical_energy',   'posture_health',
    'body_openness',        'focus_alertness',   'facial_relaxation', 'vitality_glow'
]


def generate_multi_day_report():
    date_results = {}
    for af in ANALYSIS_DIR.glob("analysis_*.json"):
        with open(af) as f:
            data = json.load(f)
        date_results[f"{data.get('school','')}|{data.get('date','')}"] = data

    person_timeline = defaultdict(lambda: {
        'dates': [], 'wellbeing_scores': [], 'engagement_scores': [],
        'detections': 0,
        'trait_sums': {k: [] for k in TRAIT_KEYS},
        'gaze_directions': [],
        'temporal_series': []
    })

    all_schools = set();  all_dates = set()

    for key, dd in date_results.items():
        school = dd.get('school', '');  date = dd.get('date', '')
        all_schools.add(school);  all_dates.add(date)

        for video in dd['videos']:
            vname = video.get('video_name', '')
            for frame in video['frames']:
                ft = frame.get('frame_time_sec', frame.get('frame_idx', 0))
                for person in frame['persons']:
                    pid = person['person_id']
                    if pid.startswith('NOBODYFACE'):
                        continue
                    wb  = person['overall_wellbeing']
                    tr  = person.get('traits', {})
                    gz  = person.get('gaze', {})
                    tl  = person_timeline[pid]
                    tl['dates'].append(date)
                    tl['wellbeing_scores'].append(wb)
                    tl['engagement_scores'].append(person.get('emotion', {}).get('engagement', 50))
                    tl['detections'] += 1
                    tl['gaze_directions'].append(gz.get('gaze_direction', 'forward'))
                    for tk in TRAIT_KEYS:
                        v = tr.get(tk)
                        if v is not None:
                            tl['trait_sums'][tk].append(v)
                    tl['temporal_series'].append({
                        't':        float(ft),
                        'date':     date,
                        'video':    vname,
                        'label':    f"{date} {ft}s",
                        'wellbeing':wb,
                        'traits':   {tk: tr.get(tk, 50) for tk in TRAIT_KEYS},
                        'gaze':     gz.get('gaze_direction', 'forward'),
                        'attention':gz.get('attention_score', 50),
                        'focus_zone': gz.get('focus_zone', 'ahead'),
                    })

    for pid in person_timeline:
        person_timeline[pid]['temporal_series'].sort(key=lambda x: (x['date'], x['t']))

    report = {
        'date_summaries':  date_results,
        'person_profiles': {},
        'pinned_profiles': list(pinned_profiles),
        'overall_stats':   {
            'total_dates_analyzed': len(all_dates),
            'total_unique_persons': len(person_timeline),
            'total_schools':        len(all_schools),
            'schools':              sorted(all_schools),
            'date_range':           sorted(all_dates)
        }
    }

    for pid, tl in person_timeline.items():
        pinfo       = person_database.get(pid, {})
        days_present = len(set(tl['dates']))
        avg_w        = int(np.mean(tl['wellbeing_scores'])) if tl['wellbeing_scores'] else 0
        avg_e        = int(np.mean(tl['engagement_scores'])) if tl['engagement_scores'] else 0
        avg_traits   = {tk: int(np.mean(v)) if v else 50 for tk, v in tl['trait_sums'].items()}

        # Dominant gaze direction
        from collections import Counter
        gaze_counter = Counter(tl['gaze_directions'])
        dominant_gaze = gaze_counter.most_common(1)[0][0] if gaze_counter else 'forward'

        report['person_profiles'][pid] = {
            'person_id':       pid,
            'name':            pinfo.get('name', f'Person {pid}'),
            'school':          pinfo.get('school', ''),
            'profile_image':   pinfo.get('profile_image', _get_blank_b64()),
            'days_present':    days_present,
            'total_detections': tl['detections'],
            'average_wellbeing': avg_w,
            'average_engagement': avg_e,
            'avg_traits':      avg_traits,
            'dominant_gaze':   dominant_gaze,
            'dates_seen':      sorted(set(tl['dates'])),
            'wellbeing_trend': tl['wellbeing_scores'],
            'temporal_series': tl['temporal_series'],
            'is_name_editable': pinfo.get('is_name_editable', True),
            'pinned':          pid in pinned_profiles,
        }

    rf = ANALYSIS_DIR / "multi_day_report.json"
    with open(rf, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Multi-day report: {rf}")
    return report


# ─── HTML TEMPLATE ────────────────────────────────────────────────────────────
