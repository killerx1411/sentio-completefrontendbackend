# test_db.py
import os
import sys
import cv2
import numpy as np
import json
import base64
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from flask import Flask, render_template_string, jsonify, request, send_file, send_from_directory
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask_cors import CORS
# ─── LIBRARY DETECTION ────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

CORS(app, resources={
    r"/*": {
        "origins": ["https://product.sentiomind.in"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
}, supports_credentials=True)

load_dotenv()
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except:
    DEEPFACE_AVAILABLE = False
    print("DeepFace not available - emotion analysis uses fallback")

try:
    import mediapipe as mp
    mp_pose      = mp.solutions.pose
    mp_face_mesh = mp.solutions.face_mesh
    MEDIAPIPE_AVAILABLE = True
except:
    MEDIAPIPE_AVAILABLE = False
    print("MediaPipe not available - posture/gaze analysis disabled")

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except:
    FACE_RECOGNITION_AVAILABLE = False
    print("face_recognition not available - using fallback detection")

try:
    from mtcnn import MTCNN as _MTCNNClass
    _MTCNN_GLOBAL = _MTCNNClass()
    MTCNN_AVAILABLE = True
    print("MTCNN available - enhanced low-res detection enabled")
except:
    MTCNN_AVAILABLE = False
    _MTCNN_GLOBAL  = None
    print("MTCNN not available (pip install mtcnn) - detection uses ensemble fallback")

# ─── PATHS ────────────────────────────────────────────────────────────────────

PROJECT_ROOT      = Path(__file__).parent
INPUT_VIDEOS_DIR  = PROJECT_ROOT / "input_videos"
PROFILES_DIR      = PROJECT_ROOT / "profiles"
SNAPSHOTS_DIR     = PROJECT_ROOT / "snapshots"
ANALYSIS_DIR      = PROJECT_ROOT / "analysis_results"

for _d in [INPUT_VIDEOS_DIR, PROFILES_DIR, SNAPSHOTS_DIR, ANALYSIS_DIR]:
    _d.mkdir(exist_ok=True)
_DB_URL = os.environ.get("SENTIO_DB_URL", "")

def get_db_conn():
    """Return a new psycopg2 connection. Raises if SENTIO_DB_URL is not set."""
    if not _DB_URL:
        raise RuntimeError(
            "SENTIO_DB_URL environment variable is not set.\n"
            "Example: export SENTIO_DB_URL='postgresql://user:pass@localhost:5432/sentio_mind_db'"
        )
    conn = psycopg2.connect(_DB_URL, sslmode='require')
    conn.autocommit = False
    return conn

def _db_available() -> bool:
    """Silent check — returns False if DB is unreachable so analysis still runs offline."""
    try:
        conn = get_db_conn()
        conn.close()
        return True
    except Exception as e:
        print(f"  [DB] Not available — running in file-only mode. ({e})")
        return False

_USE_DB = _db_available()   # checked once at startup
# ─── DB WRITE HELPERS ─────────────────────────────────────────────────────────

def db_upsert_person(person_id: str, data: dict):
    """Insert or update a person row."""
    if not _USE_DB:
        return
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO persons
                        (person_id, name, school, first_seen, last_seen,
                         appearance_count, profile_image)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (person_id) DO UPDATE SET
                        name             = EXCLUDED.name,
                        last_seen        = EXCLUDED.last_seen,
                        appearance_count = EXCLUDED.appearance_count,
                        profile_image    = EXCLUDED.profile_image
                """, (
                    person_id,
                    data.get('name'),
                    data.get('school'),
                    data.get('first_seen'),
                    data.get('last_seen'),
                    data.get('appearance_count', 1),
                    data.get('profile_image', '')
                ))
        conn.close()
    except Exception as e:
        print(f"  [DB] db_upsert_person error: {e}")


def db_insert_video(video_name: str, school: str, date_str: str) -> int | None:
    """Insert a video row, return its video_id (or None on failure)."""
    if not _USE_DB:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO videos (video_name, school, date)
                    VALUES (%s, %s, %s)
                    RETURNING video_id
                """, (video_name, school, date_str))
                video_id = cur.fetchone()[0]
        conn.close()
        return video_id
    except Exception as e:
        print(f"  [DB] db_insert_video error: {e}")
        return None


def db_insert_frame(video_id: int, frame_index: int, timestamp: float) -> int | None:
    """Insert a frame row, return frame_id."""
    if not _USE_DB or video_id is None:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO frames (video_id, frame_index, timestamp)
                    VALUES (%s, %s, %s)
                    RETURNING frame_id
                """, (video_id, frame_index, timestamp))
                frame_id = cur.fetchone()[0]
        conn.close()
        return frame_id
    except Exception as e:
        print(f"  [DB] db_insert_frame error: {e}")
        return None


def db_insert_analysis_with_traits(
        frame_id: int,
        person_id: str,
        emotion: str,
        wellbeing_score: int,
        attention_score: int,
        posture_score: int,
        traits: dict) -> int | None:
    """
    Insert one analysis row + one traits row in a single transaction.
    Returns the analysis id, or None on failure.
    """
    if not _USE_DB or frame_id is None:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                # ── analysis row ──
                cur.execute("""
                    INSERT INTO analysis
                        (frame_id, person_id, emotion,
                         wellbeing_score, attention_score, posture_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    frame_id, person_id, emotion,
                    wellbeing_score, attention_score, posture_score
                ))
                analysis_id = cur.fetchone()[0]

                # ── traits row ──
                cur.execute("""
                    INSERT INTO traits
                        (analysis_id,
                         emotional_positivity, stress_resilience, social_engagement,
                         social_confidence,    physical_energy,   posture_health,
                         body_openness,        focus_alertness,   facial_relaxation,
                         vitality_glow)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    analysis_id,
                    traits.get('emotional_positivity', 50),
                    traits.get('stress_resilience',    50),
                    traits.get('social_engagement',    50),
                    traits.get('social_confidence',    50),
                    traits.get('physical_energy',      50),
                    traits.get('posture_health',       50),
                    traits.get('body_openness',        50),
                    traits.get('focus_alertness',      50),
                    traits.get('facial_relaxation',    50),
                    traits.get('vitality_glow',        50),
                ))
        conn.close()
        return analysis_id
    except Exception as e:
        print(f"  [DB] db_insert_analysis_with_traits error: {e}")
        return None
# ─── APP & GLOBALS ────────────────────────────────────────────────────────────



person_database  = {}
analysis_cache   = {}
pinned_profiles  = set()       # person_ids pinned to dashboard

SIMILARITY_THRESHOLD       = 0.48   # slightly lower = more generous matching
FRAME_DIFFERENCE_THRESHOLD = 0.15

_clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
_db_lock  = threading.Lock()

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

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sentio Mind — Behavioral Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --bg:#f5f5f0;--surface:#fff;--surface2:#f0eeea;--border:#e2e0db;--border2:#d4d2cc;
  --text-primary:#1a1917;--text-secondary:#5c5b57;--text-muted:#9b9994;
  --accent:#2563eb;--accent-light:#eff6ff;--accent-mid:#bfdbfe;
  --green:#059669;--green-light:#ecfdf5;--amber:#d97706;--amber-light:#fffbeb;
  --red:#dc2626;--red-light:#fef2f2;--pin:#7c3aed;--pin-light:#f5f3ff;
  --shadow-sm:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-md:0 4px 16px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.04);
  --shadow-lg:0 12px 40px rgba(0,0,0,.10),0 4px 12px rgba(0,0,0,.05);
  --radius:12px;--radius-sm:8px;--radius-lg:20px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);line-height:1.6;-webkit-font-smoothing:antialiased}
.hero{background:rgba(255,255,255,.92);border-bottom:1px solid var(--border);padding:0 48px;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
.hero-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:68px}
.logo-wrap{display:flex;align-items:center;gap:12px}
.brain-svg{width:36px;height:36px;flex-shrink:0}
.logo-name{font-family:'Syne',sans-serif;font-weight:800;font-size:1.25rem;letter-spacing:-.02em}
.logo-sub{font-size:.7rem;color:var(--text-muted);font-weight:400;letter-spacing:.08em;text-transform:uppercase;margin-top:-2px}
.nav-links{display:flex;align-items:center;gap:2px}
.nav-link{padding:8px 16px;border-radius:var(--radius-sm);font-size:.875rem;font-weight:500;color:var(--text-secondary);cursor:pointer;transition:all .2s;border:none;background:transparent}
.nav-link:hover{background:var(--surface2);color:var(--text-primary)}
.nav-link.active{background:var(--accent-light);color:var(--accent);font-weight:600}
.nav-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;background:var(--green-light);color:var(--green);border-radius:20px;font-size:.75rem;font-weight:600}
.dot-live{width:7px;height:7px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.page-section{display:none}.page-section.active{display:block}

/* LANDING */
.landing-hero{background:var(--surface);padding:96px 48px 80px;border-bottom:1px solid var(--border);text-align:center}
.landing-hero-inner{max-width:780px;margin:0 auto}
.hero-eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;background:var(--accent-light);border:1px solid var(--accent-mid);border-radius:20px;font-size:.75rem;font-weight:600;color:var(--accent);letter-spacing:.04em;text-transform:uppercase;margin-bottom:32px}
.landing-hero h1{font-family:'Syne',sans-serif;font-size:clamp(2.5rem,5vw,4rem);font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-bottom:24px}
.landing-hero h1 em{font-style:normal;color:var(--accent)}
.landing-hero p{font-size:1.125rem;color:var(--text-secondary);font-weight:300;max-width:560px;margin:0 auto 48px;line-height:1.7}
.hero-cta{display:flex;gap:12px;justify-content:center;align-items:center;flex-wrap:wrap}
.schools-section{padding:56px 48px;background:var(--bg)}
.schools-inner{max-width:1400px;margin:0 auto}
.schools-label{font-size:.75rem;font-weight:600;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;text-align:center;margin-bottom:32px}
.schools-grid{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}
.school-chip{padding:10px 20px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.875rem;font-weight:500;color:var(--text-secondary);transition:all .2s;cursor:default}
.school-chip:hover{border-color:var(--accent-mid);color:var(--accent)}
.features-section{padding:80px 48px;background:var(--surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.features-inner{max-width:1400px;margin:0 auto}
.section-header{text-align:center;margin-bottom:56px}
.section-tag{display:inline-block;padding:4px 12px;background:var(--surface2);border-radius:4px;font-size:.7rem;font-weight:700;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:16px}
.section-header h2{font-family:'Syne',sans-serif;font-size:2.25rem;font-weight:800;letter-spacing:-.025em;line-height:1.2}
.features-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.feature-card{padding:32px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);transition:all .3s}
.feature-card:hover{box-shadow:var(--shadow-md);border-color:var(--border2);transform:translateY(-2px)}
.feature-icon{width:48px;height:48px;background:var(--accent-light);border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;margin-bottom:20px}
.feature-card h3{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:10px}
.feature-card p{font-size:.875rem;color:var(--text-secondary);line-height:1.7}

/* DASHBOARD */
.dashboard-wrap{max-width:1400px;margin:0 auto;padding:40px 48px}
.dash-topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:32px}
.dash-title{font-family:'Syne',sans-serif;font-size:1.625rem;font-weight:800;letter-spacing:-.025em}
.dash-sub{font-size:.875rem;color:var(--text-muted);margin-top:2px}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 20px;border-radius:var(--radius-sm);font-size:.875rem;font-weight:600;cursor:pointer;transition:all .2s;border:none;font-family:inherit;white-space:nowrap}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:#1d4ed8;box-shadow:0 4px 12px rgba(37,99,235,.3);transform:translateY(-1px)}.btn-primary:disabled{opacity:.55;cursor:not-allowed;transform:none}
.btn-ghost{background:var(--surface);border:1px solid var(--border);color:var(--text-secondary)}.btn-ghost:hover{border-color:var(--border2);color:var(--text-primary)}
.btn-pin{background:var(--pin-light);border:1px solid #ddd6fe;color:var(--pin)}.btn-pin:hover{background:#ede9fe;border-color:#c4b5fd}
.btn-lg{padding:14px 28px;font-size:.9375rem;border-radius:var(--radius)}
.btn-sm{padding:7px 14px;font-size:.8125rem}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:32px}
.kpi-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;transition:all .2s}.kpi-card:hover{box-shadow:var(--shadow-md)}
.kpi-label{font-size:.75rem;font-weight:600;color:var(--text-muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.kpi-num{font-family:'Syne',sans-serif;font-size:2.25rem;font-weight:800;letter-spacing:-.03em;line-height:1}
.kpi-unit{font-size:1rem;color:var(--text-muted);font-weight:400;margin-left:3px}
.kpi-meta{font-size:.8rem;color:var(--text-muted);margin-top:8px}
.kpi-good{color:var(--green)!important}.kpi-warn{color:var(--amber)!important}.kpi-bad{color:var(--red)!important}
.content-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);margin-bottom:24px;overflow:hidden}
.content-card-header{padding:24px 28px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.content-card-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;display:flex;align-items:center;gap:10px}
.content-card-body{padding:28px}

/* PINNED SECTION */
.pinned-banner{background:linear-gradient(135deg,#f5f3ff,#ede9fe);border:1px solid #c4b5fd;border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:24px}
.pinned-banner-title{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:800;color:var(--pin);display:flex;align-items:center;gap:8px;margin-bottom:14px}
.pinned-grid{display:flex;gap:12px;flex-wrap:wrap}
.pinned-chip{display:flex;align-items:center;gap:10px;padding:10px 14px;background:white;border:1px solid #c4b5fd;border-radius:10px;cursor:pointer;transition:all .2s}
.pinned-chip:hover{box-shadow:var(--shadow-sm);transform:translateY(-1px)}
.pinned-chip img{width:36px;height:36px;border-radius:6px;object-fit:cover;border:1px solid #c4b5fd}
.pinned-chip-name{font-weight:600;font-size:.8rem;color:var(--text-primary)}
.pinned-chip-wb{font-family:'Syne',sans-serif;font-size:.9rem;font-weight:800}
.unpin-btn{font-size:.65rem;color:#a78bfa;cursor:pointer;margin-left:4px}
.unpin-btn:hover{color:var(--pin)}

/* PERSON CARDS */
.person-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:20px}
.person-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);transition:all .25s;overflow:hidden}
.person-card:hover{box-shadow:var(--shadow-md);border-color:var(--border2)}
.person-card.flagged{border-color:#fca5a5;background:var(--red-light)}
.person-card.warn{border-color:#fcd34d;background:var(--amber-light)}
.person-card.pinned-card{border-color:#c4b5fd;box-shadow:0 0 0 2px #ede9fe}
.person-name{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;cursor:pointer;transition:color .2s}
.person-name:hover{color:var(--accent)}
.well-track{width:100%;height:6px;background:var(--surface2);border-radius:3px;margin:10px 0;overflow:hidden}
.well-fill{height:100%;border-radius:3px;transition:width .6s ease}
.well-high{background:linear-gradient(90deg,#10b981,#059669)}
.well-mid{background:linear-gradient(90deg,#f59e0b,#d97706)}
.well-low{background:linear-gradient(90deg,#ef4444,#dc2626)}
.tag{padding:3px 8px;border-radius:4px;font-size:.7rem;font-weight:600;letter-spacing:.03em;text-transform:uppercase}
.tag-blue{background:var(--accent-light);color:var(--accent)}
.tag-green{background:var(--green-light);color:var(--green)}
.tag-amber{background:var(--amber-light);color:var(--amber)}
.tag-red{background:var(--red-light);color:var(--red)}
.tag-pin{background:var(--pin-light);color:var(--pin)}

/* GAZE VISUALISER */
.gaze-eye-box{display:inline-flex;align-items:center;justify-content:center;width:48px;height:32px;background:#f8faff;border:1.5px solid var(--border);border-radius:20px;position:relative;overflow:hidden}
.gaze-iris{width:12px;height:12px;background:var(--accent);border-radius:50%;position:absolute;transition:all .3s;box-shadow:0 0 0 2px rgba(37,99,235,.2)}
.gaze-label-row{display:flex;align-items:center;gap:8px;margin-top:6px}
.gaze-dir-badge{padding:2px 8px;border-radius:4px;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.gaze-forward{background:#dcfce7;color:#15803d}
.gaze-left,.gaze-right{background:#fef9c3;color:#a16207}
.gaze-up,.gaze-down{background:#e0e7ff;color:#4338ca}
.gaze-camera{background:var(--green-light);color:var(--green)}
.gaze-distracted{background:var(--red-light);color:var(--red)}

/* MISC */
.date-strip{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}
.date-pill{padding:8px 16px;background:var(--surface);border:1px solid var(--border);border-radius:8px;font-size:.8125rem;font-weight:600;cursor:pointer;transition:all .2s;color:var(--text-secondary)}
.date-pill:hover{border-color:var(--accent-mid);color:var(--accent)}
.date-pill.active{background:var(--accent-light);border-color:var(--accent-mid);color:var(--accent)}
.timeline-stream{display:flex;flex-direction:column;gap:16px}
.tl-item{display:flex;gap:20px;align-items:flex-start}
.tl-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);border:2px solid var(--accent-mid);flex-shrink:0}
.tl-line{width:2px;background:var(--border);flex:1;margin-top:4px;min-height:32px}
.tl-body{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px 20px;margin-bottom:4px}
.tl-date{font-size:.75rem;font-weight:700;color:var(--accent);letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px}
.tl-person{font-size:.9375rem;font-weight:600;margin-bottom:4px}
.tl-meta{font-size:.8125rem;color:var(--text-secondary)}
.empty-state{text-align:center;padding:80px 24px;color:var(--text-muted)}
.empty-icon{font-size:3rem;margin-bottom:16px;opacity:.35}
.empty-title{font-size:1.125rem;font-weight:600;color:var(--text-secondary);margin-bottom:8px}
.empty-sub{font-size:.875rem}
.loading-overlay{display:none;position:fixed;inset:0;background:rgba(245,245,240,.88);backdrop-filter:blur(8px);z-index:999;align-items:center;justify-content:center;flex-direction:column;gap:20px}
.loading-overlay.active{display:flex}
.spinner{width:48px;height:48px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-title{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:700}
.loading-sub{font-size:.875rem;color:var(--text-secondary)}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.settings-row{padding:20px 24px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center}
.settings-key{font-size:.875rem;font-weight:600;color:var(--text-secondary)}
.settings-val{font-size:.875rem;color:var(--text-primary);font-weight:700;font-family:monospace;background:var(--surface);padding:4px 10px;border-radius:4px;border:1px solid var(--border)}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(26,25,23,.5);z-index:200;align-items:center;justify-content:center}
.modal-overlay.active{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:32px;width:480px;max-width:90vw;box-shadow:var(--shadow-lg)}
.modal h3{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:800;margin-bottom:8px}
.modal p{font-size:.875rem;color:var(--text-secondary);margin-bottom:20px}
.modal-input{width:100%;padding:12px 16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.9375rem;font-family:inherit;margin-bottom:20px;outline:none;transition:border-color .2s}
.modal-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.modal-actions{display:flex;gap:10px;justify-content:flex-end}
.metric-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--surface2);font-size:.8125rem}
.metric-item:last-child{border-bottom:none}
.metric-k{color:var(--text-muted);font-weight:500}
.metric-v{color:var(--text-primary);font-weight:700}
@media(max-width:900px){.hero,.dashboard-wrap,.landing-hero,.schools-section,.features-section{padding-left:20px;padding-right:20px}.contacts-grid,.settings-grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<nav class="hero">
  <div class="hero-inner">
    <div class="logo-wrap">
      <svg class="brain-svg" viewBox="0 0 64 64" fill="none">
        <rect width="64" height="64" rx="14" fill="#eff6ff"/>
        <path d="M22 28c0-5.523 4.477-10 10-10s10 4.477 10 10c0 1.5-.33 2.92-.918 4.194C43.012 33.36 44 35.07 44 37c0 3.314-2.686 6-6 6a5.98 5.98 0 01-3-.798A5.98 5.98 0 0132 43a5.98 5.98 0 01-3 .798A6 6 0 0120 37c0-1.93.988-3.64 2.918-4.806A9.96 9.96 0 0122 28z" fill="#dbeafe" stroke="#2563eb" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M32 18v25M22 28c3 0 5 2 5 5s-2 4-5 4M42 28c-3 0-5 2-5 5s2 4 5 4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="32" cy="28" r="3" fill="#2563eb"/>
      </svg>
      <div><div class="logo-name">Sentio Mind</div><div class="logo-sub">Behavioral Intelligence</div></div>
    </div>
    <div class="nav-links">
      <button class="nav-link active" onclick="goTo('home',this)">Home</button>
      <button class="nav-link" onclick="goTo('dashboard',this)">Dashboard</button>
      <button class="nav-link" onclick="goTo('profiles',this)">Profiles</button>
      <button class="nav-link" onclick="goTo('temporal',this)">Temporal</button>
      <button class="nav-link" onclick="goTo('daily',this)">Daily</button>
      <button class="nav-link" onclick="goTo('timeline',this)">Timeline</button>
      <button class="nav-link" onclick="goTo('settings',this)">Settings</button>
    </div>
    <div class="nav-badge"><div class="dot-live"></div>System Active</div>
  </div>
</nav>

<!-- HOME -->
<div id="page-home" class="page-section active">
  <section class="landing-hero">
    <div class="landing-hero-inner">
      <div class="hero-eyebrow">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M7 4v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        AI-Powered CCTV Analytics
      </div>
      <h1>Understand <em>behavior.</em><br>Unlock wellbeing.</h1>
      <p>Sentio Mind uses state-of-the-art computer vision — MTCNN + face_recognition + MediaPipe — to analyze CCTV footage at multiple scales, detect every individual even in low-resolution footage, and track gaze, posture, and wellbeing across days.</p>
      <div class="hero-cta">
        <button class="btn btn-primary btn-lg" onclick="goToAndAnalyze()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5,3 19,12 5,21"/></svg>
          Start Analysis
        </button>
        <button class="btn btn-ghost btn-lg" onclick="goTo('dashboard',document.querySelectorAll('.nav-link')[1])">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          Open Dashboard
        </button>
      </div>
    </div>
  </section>
  <section class="schools-section"><div class="schools-inner">
    <div class="schools-label">Trusted by institutions across the country</div>
    <div class="schools-grid">
      <div class="school-chip">Delhi Public School</div><div class="school-chip">Ryan International</div>
      <div class="school-chip">Kendriya Vidyalaya</div><div class="school-chip">Podar International</div>
      <div class="school-chip">The Heritage School</div><div class="school-chip">Amity School Network</div>
      <div class="school-chip">Greenwood High</div><div class="school-chip">National Public School</div>
    </div>
  </div></section>
  <section class="features-section"><div class="features-inner">
    <div class="section-header"><div class="section-tag">Capabilities</div><h2>Everything you need,<br>built in one platform</h2></div>
    <div class="features-grid">
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg></div><h3>MTCNN + Multi-Scale Detection</h3><p>MTCNN, face_recognition (HOG+CNN), MediaPipe, and Haar cascade run in ensemble on both original and 2× upscaled frames — maximising detection on low-pixel CCTV footage.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></div><h3>Gaze & Attention Analysis</h3><p>MediaPipe Face Mesh iris landmarks detect gaze direction (forward/left/right/up/down), head pose (yaw/pitch), eye contact, and compute a 0–100 attention score per person.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div><h3>10-Trait Wellbeing Profile</h3><p>Emotion, posture, gaze, and texture combine into 10 behavioural traits — positivity, resilience, energy, posture, focus/alertness, vitality and more — with a weighted overall score.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg></div><h3>Pin Profiles to Dashboard</h3><p>Pin any individual's profile card directly to the dashboard for at-a-glance monitoring. Pinned profiles appear in a highlighted banner above the KPIs.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div><h3>Face-Centred Profile Photos</h3><p>Profile images are tight face-centred crops with generous padding, 2-step Lanczos upscaling, CLAHE contrast enhancement, and unsharp masking — sharp even from blurry CCTV.</p></div>
      <div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg></div><h3>Longitudinal Tracking</h3><p>Re-identification across days and cameras with cosine similarity matching, building long-term profiles with trend charts and temporal gaze/attention history.</p></div>
    </div>
  </div></section>
  <div class="footer-bottom" style="padding:24px 48px;background:var(--bg);border-top:1px solid var(--border)">
    <div style="max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center">
      <div style="font-size:.8rem;color:var(--text-muted)">© 2026 Sentio Mind. All rights reserved.</div>
      <div style="display:flex;gap:20px"><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Privacy</span><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Terms</span><span style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Security</span></div>
    </div>
  </div>
</div>

<!-- DASHBOARD -->
<div id="page-dashboard" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar">
      <div><div class="dash-title">Overview Dashboard</div><div class="dash-sub" id="dashDateSub">No analysis run yet</div></div>
      <button class="btn btn-primary" id="runBtn" onclick="runAnalysis()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5,3 19,12 5,21"/></svg>
        Run Analysis
      </button>
    </div>
    <!-- PINNED PROFILES BANNER -->
    <div class="pinned-banner" id="pinnedBanner" style="display:none">
      <div class="pinned-banner-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
        📌 Pinned Profiles
      </div>
      <div class="pinned-grid" id="pinnedGrid"></div>
    </div>
    <div class="kpi-row" id="kpiRow">
      <div class="kpi-card"><div class="kpi-label">Total Persons</div><div class="kpi-num" id="kpiPersons">—</div><div class="kpi-meta" id="kpiPersonsMeta">Run analysis to populate</div></div>
      <div class="kpi-card"><div class="kpi-label">Avg Wellbeing</div><div class="kpi-num" id="kpiWell">—</div><div class="kpi-meta" id="kpiWellMeta">—</div></div>
      <div class="kpi-card"><div class="kpi-label">Avg Engagement</div><div class="kpi-num" id="kpiEng">—</div><div class="kpi-meta">Across all persons</div></div>
      <div class="kpi-card"><div class="kpi-label">Days Analyzed</div><div class="kpi-num" id="kpiDays">—</div><div class="kpi-meta" id="kpiDaysMeta">—</div></div>
      <div class="kpi-card" style="border-color:#fca5a5"><div class="kpi-label" style="color:var(--red)">⚠ Needs Monitoring</div><div class="kpi-num kpi-bad" id="kpiAtRisk">—</div><div class="kpi-meta" id="kpiAtRiskMeta">—</div></div>
    </div>
    <div class="content-card">
      <div class="content-card-header"><div class="content-card-title">Top Tracked Persons — School Analysis</div></div>
      <div class="content-card-body" id="topPersonsList">
        <div class="empty-state"><div class="empty-icon">👁️</div><div class="empty-title">No data yet</div><div class="empty-sub">Click Run Analysis to process footage</div></div>
      </div>
    </div>
  </div>
</div>

<!-- PROFILES -->
<div id="page-profiles" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar">
      <div><div class="dash-title">Person Profiles</div><div class="dash-sub">Auto-generated from detected individuals</div></div>
    </div>
    <div id="profilesGrid">
      <div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">No profiles yet</div><div class="empty-sub">Run analysis to auto-create profiles</div></div>
    </div>
  </div>
</div>

<!-- TEMPORAL -->
<div id="page-temporal" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Temporal Analysis</div><div class="dash-sub">Trait &amp; wellbeing trends over time per person</div></div></div>
    <div style="margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <label style="font-size:.82rem;font-weight:600;color:var(--text-secondary)">Person:</label>
      <select id="temporalPersonSelect" onchange="renderTemporalCharts()" style="padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:.85rem;color:var(--text-primary);min-width:220px"><option value="">— run analysis first —</option></select>
      <label style="font-size:.82rem;font-weight:600;color:var(--text-secondary);margin-left:12px">Show:</label>
      <select id="temporalTraitSelect" onchange="renderTemporalCharts()" style="padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);font-size:.85rem;color:var(--text-primary)">
        <option value="all">All Traits</option>
        <option value="wellbeing">Overall Wellbeing</option>
        <option value="emotional_positivity">Emotional Positivity</option>
        <option value="stress_resilience">Stress Resilience</option>
        <option value="social_engagement">Social Engagement</option>
        <option value="focus_alertness">Focus &amp; Alertness</option>
        <option value="physical_energy">Physical Energy</option>
        <option value="posture_health">Posture Health</option>
      </select>
    </div>
    <div id="temporalPersonCard" style="display:none;margin-bottom:20px;background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px;align-items:center;gap:20px">
      <img id="temporalAvatar" src="" style="width:80px;height:80px;border-radius:10px;object-fit:cover;border:2px solid var(--border)">
      <div><div id="temporalName" style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800"></div><div id="temporalMeta" style="font-size:.8rem;color:var(--text-muted);margin-top:4px"></div><div id="temporalWbBadge" style="margin-top:8px"></div></div>
    </div>
    <div id="temporalChartsArea"><div class="empty-state"><div class="empty-icon">📈</div><div class="empty-title">Select a person above</div></div></div>
  </div>
</div>

<!-- DAILY -->
<div id="page-daily" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Daily Analysis</div><div class="dash-sub">Date-by-date breakdown</div></div></div>
    <div class="date-strip" id="dateStrip"></div>
    <div id="dailyContent"><div class="empty-state"><div class="empty-icon">📅</div><div class="empty-title">No daily data</div></div></div>
  </div>
</div>

<!-- TIMELINE -->
<div id="page-timeline" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">Person Timeline</div><div class="dash-sub">Day-by-day appearance &amp; behavior stream</div></div></div>
    <div id="timelineContent"><div class="empty-state"><div class="empty-icon">⏱️</div><div class="empty-title">No timeline data</div></div></div>
  </div>
</div>

<!-- SETTINGS -->
<div id="page-settings" class="page-section">
  <div class="dashboard-wrap">
    <div class="dash-topbar"><div><div class="dash-title">System Settings</div><div class="dash-sub">Configuration and detection status</div></div></div>
    <div class="content-card">
      <div class="content-card-header"><div class="content-card-title">Detection Modules</div></div>
      <div class="content-card-body"><div class="settings-grid">
        <div class="settings-row"><span class="settings-key">MTCNN (best for low-res)</span><span class="settings-val" id="settingMtcnn">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">DeepFace Emotions</span><span class="settings-val" id="settingDeepface">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">MediaPipe Pose + Gaze</span><span class="settings-val" id="settingMediapipe">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">face_recognition HOG</span><span class="settings-val" id="settingFaceRec">Checking…</span></div>
        <div class="settings-row"><span class="settings-key">Haar Cascade Fallback</span><span class="settings-val">✓ Always on</span></div>
        <div class="settings-row"><span class="settings-key">Multi-scale Upscale</span><span class="settings-val">2× Lanczos ✓</span></div>
        <div class="settings-row"><span class="settings-key">Similarity Threshold</span><span class="settings-val">48%</span></div>
        <div class="settings-row"><span class="settings-key">Max Frames/Video</span><span class="settings-val">12 keyframes</span></div>
        <div class="settings-row"><span class="settings-key">Profile Image</span><span class="settings-val">Face-centred 240×240</span></div>
        <div class="settings-row"><span class="settings-key">Parallel Face Analysis</span><span class="settings-val">ThreadPoolExecutor ✓</span></div>
      </div></div>
    </div>
    <div class="content-card" style="margin-top:20px">
      <div class="content-card-header"><div class="content-card-title">Folder Structure</div></div>
      <div class="content-card-body">
        <pre style="font-size:.85rem;line-height:1.8;color:var(--text-secondary);background:var(--bg);padding:20px;border-radius:var(--radius-sm);border:1px solid var(--border);overflow-x:auto">input_videos/
  Delhi_Public_School/
    CCTV_24_02_2026/
      camera1.mp4
    CCTV_25_02_2026/
      recording.avi</pre>
      </div>
    </div>
  </div>
</div>

<div class="loading-overlay" id="loadingOverlay">
  <div class="spinner"></div>
  <div class="loading-title">Analyzing footage…</div>
  <div class="loading-sub" id="loadingSub">This may take several minutes</div>
</div>

<div class="modal-overlay" id="editModal">
  <div class="modal">
    <h3>Edit Person Name</h3>
    <p>Update the display name. Saved to the profile database.</p>
    <input class="modal-input" id="modalNameInput" type="text" placeholder="Enter new name…"/>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="saveModalName()">Save</button>
    </div>
  </div>
</div>

<script>
/* ─── STATE ─── */
let currentData = {};
let editingPersonId = null;

const TRAIT_COLORS = {
  emotional_positivity:'#f59e0b', stress_resilience:'#10b981', social_engagement:'#3b82f6',
  social_confidence:'#8b5cf6',    physical_energy:'#ef4444',   posture_health:'#06b6d4',
  body_openness:'#84cc16',        focus_alertness:'#f97316',   facial_relaxation:'#ec4899',
  vitality_glow:'#a78bfa',        wellbeing:'#2563eb'
};
const TRAIT_LABELS = {
  emotional_positivity:'😊 Emotional Positivity', stress_resilience:'🛡️ Stress Resilience',
  social_engagement:'🤝 Social Engagement',       social_confidence:'💬 Social Confidence',
  physical_energy:'⚡ Physical Energy',            posture_health:'🧍 Posture Health',
  body_openness:'🙌 Body Openness',               focus_alertness:'👁️ Focus & Alertness',
  facial_relaxation:'😌 Facial Relaxation',        vitality_glow:'✨ Vitality & Glow',
  wellbeing:'📊 Overall Wellbeing'
};
const ALL_TRAITS = Object.keys(TRAIT_COLORS).filter(k => k !== 'wellbeing');
let temporalChartInstances = {};
let dashMiniCharts = {};

/* ─── NAVIGATION ─── */
function goTo(page, el) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (el) el.classList.add('active');
}
function goToAndAnalyze() {
  goTo('dashboard', document.querySelectorAll('.nav-link')[1]);
  setTimeout(runAnalysis, 200);
}

/* ─── ANALYSIS ─── */
async function runAnalysis() {
  document.getElementById('loadingOverlay').classList.add('active');
  document.getElementById('runBtn').disabled = true;
  document.getElementById('loadingSub').textContent = 'Running multi-scale detection + gaze analysis…';
  try {
    const r = await fetch('/run_analysis', { method: 'POST' });
    const d = await r.json();
    if (d.success) {
      currentData = d.report;
      renderAll(d.report);
      document.getElementById('dashDateSub').textContent = 'Last updated: ' + new Date().toLocaleString();
    } else { alert('Error: ' + d.message); }
  } catch(e) { alert('Error: ' + e); }
  finally {
    document.getElementById('loadingOverlay').classList.remove('active');
    document.getElementById('runBtn').disabled = false;
  }
}

function renderAll(report) {
  renderKPIs(report);
  renderPinnedBanner(report);
  renderTopPersons(report);
  renderProfiles(report);
  renderTemporalSetup(report);
  renderDaily(report);
  renderTimeline(report);
}

/* ─── GAZE VISUALISER ─── */
function gazeWidget(gaze) {
  if (!gaze) return '';
  const dir  = gaze.gaze_direction || 'forward';
  const attn = gaze.attention_score || 50;
  const zone = gaze.focus_zone || 'ahead';
  const ec   = gaze.eye_contact ? '👁️ Eye contact' : '';
  // Map gaze_horizontal / gaze_vertical (-1..+1) to CSS offset in the eye box
  const gh   = Math.max(-1, Math.min(1, gaze.gaze_horizontal || 0));
  const gv   = Math.max(-1, Math.min(1, gaze.gaze_vertical   || 0));
  const irisX = 50 + gh * 30;   // % left
  const irisY = 50 + gv * 30;   // % top
  const dirCls = ['forward','left','right','up','down','camera','distracted'].includes(dir)
                  ? 'gaze-' + dir : 'gaze-forward';
  const attnColor = attn >= 70 ? '#10b981' : attn >= 45 ? '#f59e0b' : '#ef4444';
  return `<div style="margin-top:10px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px">
    <div style="font-size:.65rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:7px">👁️ Gaze & Attention</div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <div class="gaze-eye-box">
        <div class="gaze-iris" style="left:calc(${irisX}% - 6px);top:calc(${irisY}% - 6px)"></div>
      </div>
      <div>
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span class="gaze-dir-badge ${dirCls}">${dir}</span>
          <span style="font-size:.7rem;color:var(--text-muted)">zone: <b>${zone}</b></span>
          ${ec ? '<span style="font-size:.7rem;color:var(--green)">'+ec+'</span>' : ''}
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:5px">
          <span style="font-size:.68rem;color:var(--text-muted)">Attention</span>
          <div style="width:70px;height:5px;background:var(--surface2);border-radius:3px;overflow:hidden">
            <div style="width:${attn}%;height:100%;background:${attnColor};border-radius:3px"></div>
          </div>
          <span style="font-size:.7rem;font-weight:700;color:${attnColor}">${attn}%</span>
        </div>
        ${gaze.head_yaw !== undefined ? `<div style="font-size:.65rem;color:var(--text-muted);margin-top:3px">Head: yaw ${gaze.head_yaw}° pitch ${gaze.head_pitch}°</div>` : ''}
      </div>
    </div>
  </div>`;
}

/* ─── PINNED BANNER ─── */
function renderPinnedBanner(report) {
  const pinned = report.pinned_profiles || [];
  const banner = document.getElementById('pinnedBanner');
  const grid   = document.getElementById('pinnedGrid');
  if (!pinned.length) { banner.style.display = 'none'; return; }
  banner.style.display = 'block';
  grid.innerHTML = pinned.map(pid => {
    const p = report.person_profiles[pid];
    if (!p) return '';
    const wc = p.average_wellbeing >= 70 ? '#10b981' : p.average_wellbeing >= 50 ? '#f59e0b' : '#ef4444';
    return `<div class="pinned-chip" onclick="goToPersonTemporal('${pid}')">
      <img src="data:image/jpeg;base64,${p.profile_image}" alt="">
      <div><div class="pinned-chip-name">${p.name}</div>
        <div class="pinned-chip-wb" style="color:${wc}">${p.average_wellbeing}%</div></div>
      <span class="unpin-btn" onclick="event.stopPropagation();unpinProfile('${pid}')" title="Unpin">✕</span>
    </div>`;
  }).join('');
}

/* ─── KPIs ─── */
function renderKPIs(report) {
  const stats   = report.overall_stats;
  const persons = Object.values(report.person_profiles);
  const avgW    = persons.length ? Math.round(persons.reduce((a,p)=>a+p.average_wellbeing,0)/persons.length) : 0;
  const avgE    = persons.length ? Math.round(persons.reduce((a,p)=>a+p.average_engagement,0)/persons.length) : 0;
  const atRisk  = persons.filter(p=>p.average_wellbeing<50).length;
  document.getElementById('kpiPersons').textContent     = stats.total_unique_persons;
  document.getElementById('kpiPersonsMeta').textContent = `${stats.total_schools||1} school(s), ${stats.total_dates_analyzed} day(s)`;
  document.getElementById('kpiWell').innerHTML          = `${avgW}<span class="kpi-unit">%</span>`;
  document.getElementById('kpiWellMeta').innerHTML      = `<span class="${avgW>=70?'kpi-good':avgW>=50?'kpi-warn':'kpi-bad'}">${avgW>=70?'↑ Good':avgW>=50?'→ Moderate':'↓ Needs attention'}</span>`;
  document.getElementById('kpiEng').innerHTML           = `${avgE}<span class="kpi-unit">%</span>`;
  document.getElementById('kpiDays').textContent        = stats.total_dates_analyzed;
  document.getElementById('kpiDaysMeta').textContent    = `${stats.date_range[0]||''} → ${stats.date_range.at(-1)||''}`;
  document.getElementById('kpiAtRisk').textContent      = atRisk;
  document.getElementById('kpiAtRiskMeta').textContent  = 'Wellbeing below 50%';
}

/* ─── TOP PERSONS ─── */
let dashMiniChartStore = {};
function destroyDashMini() {
  Object.values(dashMiniChartStore).forEach(c=>{try{c.destroy()}catch(e){}});
  dashMiniChartStore = {};
}
function renderTopPersons(report) {
  destroyDashMini();
  const allPersons = Object.values(report.person_profiles);
  const schools    = report.overall_stats.schools || [];
  let html = '';
  schools.forEach(school => {
    const sp     = allPersons.filter(p => p.school === school);
    if (!sp.length) return;
    const avgW   = Math.round(sp.reduce((a,p)=>a+p.average_wellbeing,0)/sp.length);
    const atRisk = sp.filter(p=>p.average_wellbeing<50).sort((a,b)=>a.average_wellbeing-b.average_wellbeing);
    const top4   = [...sp].sort((a,b)=>b.total_detections-a.total_detections).slice(0,4);
    const sc     = avgW>=70?'var(--green)':avgW>=50?'var(--amber)':'var(--red)';

    html += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;margin-bottom:24px;overflow:hidden">
      <div style="padding:20px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg)">
        <div><div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800">${school}</div>
          <div style="font-size:.8rem;color:var(--text-muted)">${sp.length} persons · ${atRisk.length} monitoring</div></div>
        <div style="text-align:right"><div style="font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;color:${sc}">${avgW}%</div>
          <div style="font-size:.65rem;color:var(--text-muted);font-weight:600;letter-spacing:.05em">AVG WELLBEING</div></div>
      </div>`;

    if (atRisk.length) {
      html += `<div style="padding:14px 24px;border-bottom:1px solid var(--border);background:#fff8f8">
        <div style="font-size:.7rem;font-weight:700;color:var(--red);letter-spacing:.07em;text-transform:uppercase;margin-bottom:8px">⚠ Needs Monitoring</div>
        <div style="display:flex;flex-direction:column;gap:6px">`;
      atRisk.slice(0,5).forEach(p => {
        const lowest = p.avg_traits ? Object.entries(p.avg_traits).sort((a,b)=>a[1]-b[1])[0] : null;
        const gazeIcon = {forward:'→',left:'←',right:'→',up:'↑',down:'↓'}[p.dominant_gaze||'forward']||'→';
        html += `<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:white;border:1px solid #fca5a5;border-radius:8px">
          <img src="data:image/jpeg;base64,${p.profile_image}" style="width:38px;height:38px;border-radius:6px;object-fit:cover;flex-shrink:0">
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:.85rem">${p.name}</div>
            <div style="font-size:.7rem;color:var(--text-muted)">Lowest: ${lowest?lowest[0].replace(/_/g,' '):'—'} (${lowest?lowest[1]:'—'}%) · Gaze: ${gazeIcon} ${p.dominant_gaze||'unknown'}</div>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:var(--red)">${p.average_wellbeing}%</div>
        </div>`;
      });
      html += `</div></div>`;
    }

    html += `<div style="padding:16px 24px">
      <div style="font-size:.7rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:10px">Top Tracked — Wellbeing Over Time</div>
      <div style="display:flex;flex-direction:column;gap:12px">`;
    top4.forEach(p => {
      const wc  = p.average_wellbeing>=70?'#10b981':p.average_wellbeing>=50?'#f59e0b':'#ef4444';
      const cid = 'mini_' + p.person_id.replace(/[^a-zA-Z0-9]/g,'_');
      const isPinned = (currentData.pinned_profiles||[]).includes(p.person_id);
      html += `<div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <img src="data:image/jpeg;base64,${p.profile_image}" style="width:44px;height:44px;border-radius:8px;object-fit:cover;border:2px solid var(--border);flex-shrink:0">
          <div style="flex:1;min-width:0">
            <div style="font-weight:700;font-size:.875rem">${p.name}</div>
            <div style="font-size:.7rem;color:var(--text-muted)">${p.total_detections} det · ${p.days_present}d · Gaze: ${p.dominant_gaze||'—'} · <span style="color:${wc};font-weight:700">${p.average_wellbeing}%</span></div>
          </div>
          <button onclick="goToPersonTemporal('${p.person_id}')" style="font-size:.7rem;padding:4px 8px;border:1px solid var(--accent);border-radius:6px;background:var(--accent-light);color:var(--accent);cursor:pointer;font-weight:600">Chart →</button>
          <button onclick="togglePin('${p.person_id}')" style="font-size:.7rem;padding:4px 8px;border:1px solid #c4b5fd;border-radius:6px;background:var(--pin-light);color:var(--pin);cursor:pointer;font-weight:600" id="pinbtn_${p.person_id.replace(/[^a-zA-Z0-9]/g,'_')}">${isPinned?'📌 Unpin':'📌 Pin'}</button>
        </div>
        <div style="position:relative;height:60px"><canvas id="${cid}"></canvas></div>
        <div style="font-size:.65rem;color:var(--text-muted);text-align:center;margin-top:3px">Wellbeing over time</div>
      </div>`;
    });
    html += `</div></div></div>`;
  });

  document.getElementById('topPersonsList').innerHTML = html ||
    '<div class="empty-state"><div class="empty-icon">👁️</div><div class="empty-title">No data</div></div>';

  setTimeout(() => {
    schools.forEach(school => {
      const sp = allPersons.filter(p=>p.school===school);
      [...sp].sort((a,b)=>b.total_detections-a.total_detections).slice(0,4).forEach(p => {
        const cid = 'mini_' + p.person_id.replace(/[^a-zA-Z0-9]/g,'_');
        if (p.temporal_series?.length) buildDashMini(cid, p.temporal_series);
      });
    });
  }, 120);
}

function buildDashMini(cid, series) {
  const ctx = document.getElementById(cid);
  if (!ctx) return;
  if (dashMiniChartStore[cid]) { try { dashMiniChartStore[cid].destroy(); } catch(e){} }
  const byDate = {};
  series.forEach(pt => { if (!byDate[pt.date]) byDate[pt.date]=[]; byDate[pt.date].push(pt.wellbeing); });
  const dates = Object.keys(byDate).sort();
  const vals  = dates.map(d => Math.round(byDate[d].reduce((a,v)=>a+v,0)/byDate[d].length));
  dashMiniChartStore[cid] = new Chart(ctx.getContext('2d'), {
    type:'line',
    data:{ labels: dates.length>1?dates:series.map((_,i)=>i+1+''), datasets:[{
      data: dates.length>1?vals:series.map(pt=>pt.wellbeing),
      borderColor:'#2563eb', backgroundColor:'#2563eb22', borderWidth:2, pointRadius:3, tension:.4, fill:true
    }]},
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{display:false},y:{display:false,min:0,max:100}} }
  });
}

/* ─── PROFILES PAGE ─── */
function renderProfiles(report) {
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  if (!persons.length) { document.getElementById('profilesGrid').innerHTML='<div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">No profiles</div></div>'; return; }
  const schools = [...new Set(persons.map(p=>p.school||'Unknown'))].sort();
  let html = '';
  schools.forEach(school => {
    const sp   = persons.filter(p=>(p.school||'Unknown')===school);
    const avgW = Math.round(sp.reduce((a,p)=>a+p.average_wellbeing,0)/sp.length);
    const sc   = avgW>=70?'var(--green)':avgW>=50?'var(--amber)':'var(--red)';
    html += `<div style="margin-bottom:40px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--border)">
        <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800">${school}</div>
        <div style="display:flex;align-items:center;gap:16px">
          <span style="font-size:.8rem;color:var(--text-muted)">${sp.length} persons</span>
          <span style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:${sc}">${avgW}% avg wellbeing</span>
        </div>
      </div>
      <div class="person-grid">`;

    sp.forEach(p => {
      const isPinned = (report.pinned_profiles||[]).includes(p.person_id);
      const wc  = p.average_wellbeing>=70?'var(--green)':p.average_wellbeing>=50?'var(--amber)':'var(--red)';
      const cc  = p.average_wellbeing<40?'flagged':p.average_wellbeing<60?'warn':'';
      const pc  = isPinned ? 'pinned-card' : '';
      const wfc = p.average_wellbeing>=70?'well-high':p.average_wellbeing>=50?'well-mid':'well-low';
      const engTag = p.average_engagement>=60?'tag-green':p.average_engagement>=40?'tag-amber':'tag-red';
      const traits = p.avg_traits || {};
      const gaze   = p.temporal_series?.length ? (p.temporal_series.at(-1)||{}).gaze : p.dominant_gaze;
      const lastPt = p.temporal_series?.at(-1) || {};

      let traitsHtml = '';
      Object.keys(TRAIT_LABELS).filter(k=>k!=='wellbeing').forEach(tk => {
        const val = traits[tk] !== undefined ? traits[tk] : 50;
        const bc  = val>=70?'#10b981':val>=45?'#f59e0b':'#ef4444';
        traitsHtml += `<div style="margin-bottom:6px">
          <div style="display:flex;justify-content:space-between;margin-bottom:2px">
            <span style="font-size:.69rem;color:var(--text-secondary);font-weight:500">${TRAIT_LABELS[tk]}</span>
            <span style="font-size:.69rem;font-weight:700;color:${bc}">${val}%</span>
          </div>
          <div style="width:100%;height:4px;background:var(--surface2);border-radius:2px;overflow:hidden">
            <div style="width:${val}%;height:100%;background:${bc};border-radius:2px"></div>
          </div>
        </div>`;
      });

      html += `<div class="person-card ${cc} ${pc}" style="padding:0;overflow:hidden">
        <!-- Face-centred profile photo -->
        <div style="position:relative;width:100%;background:var(--surface2)">
          <img src="data:image/jpeg;base64,${p.profile_image}" id="avatar-${p.person_id}"
            style="width:100%;height:240px;object-fit:cover;object-position:top center;display:block;image-rendering:-webkit-optimize-contrast">
          <!-- Pin button -->
          <button onclick="togglePin('${p.person_id}')" title="${isPinned?'Unpin from dashboard':'Pin to dashboard'}"
            style="position:absolute;top:10px;left:10px;padding:5px 10px;background:${isPinned?'#7c3aed':'rgba(255,255,255,.9)'};border-radius:8px;border:${isPinned?'none':'1px solid #c4b5fd'};cursor:pointer;font-size:.68rem;font-weight:700;color:${isPinned?'white':'var(--pin)'};backdrop-filter:blur(4px);display:flex;align-items:center;gap:4px"
            id="pinbtn_card_${p.person_id.replace(/[^a-zA-Z0-9]/g,'_')}">
            📌 ${isPinned?'Pinned':'Pin'}
          </button>
          <!-- Upload photo -->
          <label style="position:absolute;top:10px;right:42px;width:30px;height:30px;background:rgba(37,99,235,.88);border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;border:2px solid white">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <input type="file" accept="image/*" style="display:none" onchange="uploadPhoto(event,'${p.person_id}')">
          </label>
          <!-- Delete -->
          <button onclick="deletePerson('${p.person_id}','${p.name.replace(/'/g,'&#39;')}')"
            style="position:absolute;top:10px;right:10px;width:30px;height:30px;background:rgba(220,38,38,.88);border-radius:8px;border:2px solid white;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
          </button>
          <!-- Wellbeing badge -->
          <div style="position:absolute;bottom:10px;left:10px;background:rgba(255,255,255,.92);border-radius:8px;padding:4px 10px;backdrop-filter:blur(4px)">
            <span style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:${wc}">${p.average_wellbeing}%</span>
            <span style="font-size:.62rem;color:var(--text-muted);font-weight:600;margin-left:3px">WELLBEING</span>
          </div>
          ${isPinned ? '<div style="position:absolute;bottom:10px;right:10px;background:#7c3aed;color:white;border-radius:6px;padding:3px 8px;font-size:.65rem;font-weight:700">📌 PINNED</div>' : ''}
        </div>
        <!-- Info section -->
        <div style="padding:14px 16px">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:6px">
            <div style="flex:1;min-width:0">
              <div class="person-name" onclick="openModal('${p.person_id}','${p.name.replace(/'/g,'&#39;')}')">
                ${p.name}
                <svg style="display:inline;vertical-align:middle;margin-left:4px" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </div>
              <div style="font-size:.7rem;color:var(--text-muted)">${p.person_id}</div>
            </div>
          </div>
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px">
            <span class="tag tag-blue">${p.days_present}d tracked</span>
            <span class="tag ${engTag}">${p.average_engagement}% eng</span>
            <span class="tag tag-blue">${p.total_detections} det</span>
            ${isPinned?'<span class="tag tag-pin">📌 Pinned</span>':''}
          </div>
          <div class="well-track"><div class="well-fill ${wfc}" style="width:${p.average_wellbeing}%"></div></div>
          <!-- GAZE WIDGET -->
          ${gazeWidget({ gaze_direction: gaze||p.dominant_gaze, attention_score: lastPt.attention||50, focus_zone: lastPt.focus_zone||'ahead', gaze_horizontal:0, gaze_vertical:0, head_yaw: 0, head_pitch: 0 })}
          <!-- 10-trait bars -->
          <div style="margin-top:12px">
            <div style="font-size:.66rem;font-weight:700;color:var(--text-muted);letter-spacing:.07em;text-transform:uppercase;margin-bottom:7px">10-Trait Behavioral Analysis</div>
            ${traitsHtml}
          </div>
          <div style="margin-top:10px">
            <div class="metric-item"><span class="metric-k">First Seen</span><span class="metric-v">${p.dates_seen[0]||'—'}</span></div>
            <div class="metric-item"><span class="metric-k">Last Seen</span><span class="metric-v">${p.dates_seen.at(-1)||'—'}</span></div>
            <div class="metric-item"><span class="metric-k">Dominant Gaze</span><span class="metric-v">${p.dominant_gaze||'—'}</span></div>
          </div>
        </div>
      </div>`;
    });
    html += `</div></div>`;
  });
  document.getElementById('profilesGrid').innerHTML = html;
}

/* ─── PIN / UNPIN ─── */
async function togglePin(personId) {
  const pinned = currentData.pinned_profiles || [];
  const isPinned = pinned.includes(personId);
  const action = isPinned ? 'unpin' : 'pin';
  try {
    const r = await fetch('/pin_profile', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ person_id: personId, action }) });
    const d = await r.json();
    if (d.success) {
      if (isPinned) { currentData.pinned_profiles = pinned.filter(p=>p!==personId); }
      else          { currentData.pinned_profiles = [...pinned, personId]; }
      if (currentData.person_profiles?.[personId]) {
        currentData.person_profiles[personId].pinned = !isPinned;
      }
      renderAll(currentData);
    }
  } catch(e) { console.error('Pin error:', e); }
}
async function unpinProfile(personId) { await togglePin(personId); }

/* ─── TEMPORAL PAGE ─── */
function renderTemporalSetup(report) {
  const sel = document.getElementById('temporalPersonSelect');
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  sel.innerHTML = '<option value="">— select a person —</option>';
  persons.forEach(p => {
    const o = document.createElement('option');
    o.value = p.person_id;
    o.textContent = `${p.name} (${p.school||''}) · ${p.total_detections} det`;
    sel.appendChild(o);
  });
}

function destroyTemporalCharts() {
  Object.values(temporalChartInstances).forEach(c=>{try{c.destroy()}catch(e){}});
  temporalChartInstances = {};
}
function makeDS(key, data, fill=false) {
  const color = TRAIT_COLORS[key]||'#64748b';
  return { label: TRAIT_LABELS[key]||key, data, borderColor:color, backgroundColor:color+'18', borderWidth:fill?3:2, pointRadius:4, pointHoverRadius:6, tension:.4, fill };
}
function buildChart(parentEl, id, title, labels, datasets) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:14px';
  wrap.innerHTML = `<div style="font-size:.88rem;font-weight:700;margin-bottom:12px">${title}</div><div style="position:relative;height:200px"><canvas id="c_${id}"></canvas></div>`;
  parentEl.appendChild(wrap);
  const ctx = document.getElementById('c_'+id);
  if (!ctx) return;
  temporalChartInstances['c_'+id] = new Chart(ctx.getContext('2d'), {
    type:'line', data:{labels, datasets},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top',labels:{font:{family:'DM Sans',size:11},boxWidth:12,padding:8}},
        tooltip:{callbacks:{label:c=>' '+(c.dataset.label||'')+': '+(c.parsed.y??'—')+'%'}}},
      scales:{x:{title:{display:true,text:'Time (s)'},ticks:{font:{size:10},maxRotation:30},grid:{color:'#f0eeea'}},
              y:{min:0,max:100,title:{display:true,text:'Score (%)'},ticks:{font:{size:10}},grid:{color:'#f0eeea'}}}}
  });
}
function renderTemporalCharts() {
  if (!currentData) return;
  const pid  = document.getElementById('temporalPersonSelect').value;
  const mode = document.getElementById('temporalTraitSelect').value;
  const area = document.getElementById('temporalChartsArea');
  if (!pid) { area.innerHTML='<div class="empty-state"><div class="empty-icon">👤</div><div class="empty-title">Select a person</div></div>'; return; }
  const p = currentData.person_profiles[pid];
  if (!p) return;

  const card = document.getElementById('temporalPersonCard');
  card.style.display = 'flex';
  document.getElementById('temporalAvatar').src = 'data:image/jpeg;base64,'+p.profile_image;
  document.getElementById('temporalName').textContent = p.name;
  document.getElementById('temporalMeta').textContent = `${p.school||''} · ${p.total_detections} detections · ${p.days_present} days`;
  const wbColor = p.average_wellbeing>=70?'#10b981':p.average_wellbeing>=50?'#f59e0b':'#ef4444';
  document.getElementById('temporalWbBadge').innerHTML = `<span style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:${wbColor}">${p.average_wellbeing}%</span><span style="font-size:.75rem;color:var(--text-muted);margin-left:6px">avg wellbeing</span>`;

  const series = p.temporal_series||[];
  if (!series.length) { area.innerHTML='<div class="empty-state"><div class="empty-icon">📉</div><div class="empty-title">No temporal data</div></div>'; return; }

  destroyTemporalCharts();
  area.innerHTML = '';

  const byDate = {};
  series.forEach(pt=>{ if (!byDate[pt.date]) byDate[pt.date]=[]; byDate[pt.date].push(pt); });
  const dates = Object.keys(byDate).sort();

  dates.forEach(date => {
    const pts  = byDate[date].sort((a,b)=>a.t-b.t);
    const xLbs = pts.map(pt=>pt.t.toFixed(1)+'s');
    const dayDiv = document.createElement('div');
    dayDiv.style.cssText = 'margin-bottom:28px';
    dayDiv.innerHTML = `<div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;padding:10px 0 8px;border-bottom:2px solid var(--border);margin-bottom:14px;display:flex;align-items:center;gap:10px">
      <span style="background:var(--accent);color:white;border-radius:6px;padding:2px 10px;font-size:.8rem">${date}</span>
      <span style="font-size:.8rem;font-weight:400;color:var(--text-muted)">${pts.length} pts · ${pts[0].video||''}</span>
    </div>`;
    area.appendChild(dayDiv);

    if (mode === 'all') {
      buildChart(dayDiv,'wb_'+date+'_'+pid,'Overall Wellbeing — '+date, xLbs, [makeDS('wellbeing',pts.map(pt=>pt.wellbeing),true)]);
      buildChart(dayDiv,'emo_'+date+'_'+pid,'Emotional & Social — '+date, xLbs,
        ['emotional_positivity','stress_resilience','social_engagement','social_confidence','focus_alertness'].map(tk=>makeDS(tk,pts.map(pt=>pt.traits[tk]??null))));
      buildChart(dayDiv,'phy_'+date+'_'+pid,'Physical & Appearance — '+date, xLbs,
        ['physical_energy','posture_health','body_openness','facial_relaxation','vitality_glow'].map(tk=>makeDS(tk,pts.map(pt=>pt.traits[tk]??null))));
      // Attention / gaze chart
      buildChart(dayDiv,'gaze_'+date+'_'+pid,'Attention Score — '+date, xLbs,
        [{ label:'Attention Score', data: pts.map(pt=>pt.attention||50), borderColor:'#7c3aed', backgroundColor:'#7c3aed18', borderWidth:2, pointRadius:4, tension:.4, fill:true }]);
    } else {
      const ds = mode==='wellbeing' ? [makeDS('wellbeing',pts.map(pt=>pt.wellbeing),true)] :
                 [makeDS(mode,pts.map(pt=>pt.traits[mode]??null))];
      buildChart(dayDiv,mode+'_'+date+'_'+pid,(TRAIT_LABELS[mode]||mode)+' — '+date, xLbs, ds);
    }
  });
}
function goToPersonTemporal(pid) {
  goTo('temporal', document.querySelectorAll('.nav-link')[3]);
  setTimeout(()=>{ const sel=document.getElementById('temporalPersonSelect'); if(sel){sel.value=pid;renderTemporalCharts();} },150);
}

/* ─── DAILY ─── */
function renderDaily(report) {
  const dates = report.overall_stats.date_range;
  if (!dates.length) return;
  document.getElementById('dateStrip').innerHTML = dates.map((d,i)=>`<div class="date-pill ${i===0?'active':''}" onclick="selectDate('${d}',this)">${d}</div>`).join('');
  showDate(dates[0], report);
}
function selectDate(date, el) {
  document.querySelectorAll('.date-pill').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  showDate(date, currentData);
}
function showDate(date, report) {
  const dd = report.date_summaries[date] || Object.values(report.date_summaries).find(d=>d.date===date);
  if (!dd) return;
  const html = `<div class="kpi-row">
    <div class="kpi-card"><div class="kpi-label">Unique Persons</div><div class="kpi-num">${dd.summary.unique_persons}</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg Wellbeing</div><div class="kpi-num">${dd.summary.average_wellbeing}<span class="kpi-unit">%</span></div></div>
    <div class="kpi-card"><div class="kpi-label">Total Detections</div><div class="kpi-num">${dd.summary.total_detections}</div></div>
    <div class="kpi-card"><div class="kpi-label">Videos</div><div class="kpi-num">${dd.videos.length}</div></div>
  </div>
  <div class="content-card"><div class="content-card-header"><div class="content-card-title">Videos on ${date}</div></div>
    <div class="content-card-body">
      ${dd.videos.map(v=>`<div style="padding:12px 16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:.875rem">${v.video_name}</span>
        <span style="font-size:.8rem;color:var(--text-muted)">${v.total_frames_analyzed} frames</span>
      </div>`).join('')}
    </div>
  </div>`;
  document.getElementById('dailyContent').innerHTML = html;
}

/* ─── TIMELINE ─── */
function renderTimeline(report) {
  const persons = Object.values(report.person_profiles).sort((a,b)=>b.total_detections-a.total_detections);
  if (!persons.length) return;
  let html = '<div class="timeline-stream">';
  persons.forEach(p => {
    p.dates_seen.forEach((date,i) => {
      const last = i===p.dates_seen.length-1;
      html += `<div class="tl-item">
        <div style="display:flex;flex-direction:column;align-items:center;padding-top:4px">
          <div class="tl-dot"></div>${!last?'<div class="tl-line"></div>':''}
        </div>
        <div class="tl-body">
          <div class="tl-date">${date}</div>
          <div class="tl-person">${p.name}${(report.pinned_profiles||[]).includes(p.person_id)?' 📌':''}</div>
          <div class="tl-meta">${p.school||''} · ${p.person_id} · Wellbeing ${p.average_wellbeing}% · Gaze: ${p.dominant_gaze||'—'}</div>
        </div>
      </div>`;
    });
  });
  html += '</div>';
  document.getElementById('timelineContent').innerHTML = html;
}

/* ─── PROFILE ACTIONS ─── */
async function deletePerson(personId, personName) {
  if (!confirm(`Delete "${personName}"? Cannot be undone.`)) return;
  const r = await fetch('/delete_person', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:personId}) });
  const d = await r.json();
  if (d.success) { delete currentData.person_profiles[personId]; currentData.pinned_profiles=(currentData.pinned_profiles||[]).filter(p=>p!==personId); renderAll(currentData); }
  else alert('Error: '+d.message);
}
async function uploadPhoto(event, personId) {
  const file = event.target.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {
    const b64 = e.target.result.split(',')[1];
    const r = await fetch('/update_person_photo', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:personId,image_b64:b64}) });
    const d = await r.json();
    if (d.success) {
      const img = document.getElementById('avatar-'+personId);
      if (img) img.src = e.target.result;
      if (currentData.person_profiles?.[personId]) currentData.person_profiles[personId].profile_image = b64;
    }
  };
  reader.readAsDataURL(file);
}
function openModal(personId, currentName) {
  editingPersonId = personId;
  document.getElementById('modalNameInput').value = currentName;
  document.getElementById('editModal').classList.add('active');
  setTimeout(()=>document.getElementById('modalNameInput').focus(),100);
}
function closeModal() { document.getElementById('editModal').classList.remove('active'); editingPersonId=null; }
async function saveModalName() {
  const name = document.getElementById('modalNameInput').value.trim();
  if (!name || !editingPersonId) return;
  const r = await fetch('/update_person_name', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({person_id:editingPersonId,name}) });
  const d = await r.json();
  if (d.success) {
    if (currentData.person_profiles?.[editingPersonId]) currentData.person_profiles[editingPersonId].name = name;
    renderAll(currentData); closeModal();
  }
}
document.getElementById('editModal').addEventListener('click', e=>{ if(e.target===document.getElementById('editModal'))closeModal(); });
document.getElementById('modalNameInput').addEventListener('keydown', e=>{ if(e.key==='Enter')saveModalName(); if(e.key==='Escape')closeModal(); });

/* ─── INIT ─── */
async function loadSystemInfo() {
  try {
    const d = await (await fetch('/system_info')).json();
    document.getElementById('settingMtcnn').textContent      = d.mtcnn          ? '✓ Available (best quality)' : '✗ pip install mtcnn';
    document.getElementById('settingDeepface').textContent   = d.deepface       ? '✓ Available' : '✗ Not installed';
    document.getElementById('settingMediapipe').textContent  = d.mediapipe      ? '✓ Available' : '✗ Not installed';
    document.getElementById('settingFaceRec').textContent    = d.face_recognition?'✓ Available' : '✗ Not installed';
  } catch(e) {}
}
async function loadExistingData() {
  try {
    const d = await (await fetch('/get_report')).json();
    if (d.success && d.report) { currentData=d.report; renderAll(d.report); document.getElementById('dashDateSub').textContent='Loaded from saved report'; }
  } catch(e) {}
}
loadSystemInfo(); loadExistingData();
</script>
</body>
</html>'''


# ─── FLASK ROUTES ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)
@app.route('/health')
def health():
    return "OK", 200
@app.route('/run_analysis', methods=['POST'])
def run_analysis_endpoint():
    try:
        analyze_all_dates()
        report = generate_multi_day_report()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get_report', methods=['GET'])
def get_report():
    try:
        rf = ANALYSIS_DIR / "multi_day_report.json"
        if rf.exists():
            with open(rf) as f:
                report = json.load(f)
            # Restore pinned_profiles to in-memory set
            pinned_profiles.clear()
            pinned_profiles.update(report.get('pinned_profiles', []))
            return jsonify({'success': True, 'report': report})
        return jsonify({'success': False, 'message': 'No report'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/pin_profile', methods=['POST'])
def pin_profile():
    try:
        data      = request.get_json()
        person_id = data.get('person_id')
        action    = data.get('action', 'pin')   # 'pin' or 'unpin'
        if not person_id:
            return jsonify({'success': False, 'message': 'Missing person_id'})

        if action == 'pin':
            pinned_profiles.add(person_id)
        else:
            pinned_profiles.discard(person_id)

        # Persist to report JSON
        rf = ANALYSIS_DIR / "multi_day_report.json"
        if rf.exists():
            with open(rf) as f: report = json.load(f)
            report['pinned_profiles'] = list(pinned_profiles)
            with open(rf, 'w') as f: json.dump(report, f, indent=2)

        return jsonify({'success': True, 'pinned': list(pinned_profiles)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_person_name', methods=['POST'])
def update_person_name():
    try:
        data = request.get_json()
        pid  = data.get('person_id')
        name = data.get('name')
        if pid in person_database:
            person_database[pid]['name'] = name

        for fpath in [PROFILES_DIR/"person_database.json", ANALYSIS_DIR/"multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f: db = json.load(f)
                target = db if fpath.name.endswith('person_database.json') else db.get('person_profiles', {})
                if pid in target:
                    target[pid]['name'] = name
                with open(fpath, 'w') as f: json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_person_photo', methods=['POST'])
def update_person_photo():
    try:
        data = request.get_json()
        pid  = data.get('person_id')
        b64  = data.get('image_b64')
        if not pid or not b64:
            return jsonify({'success': False, 'message': 'Missing fields'})

        if pid in person_database:
            person_database[pid]['profile_image'] = b64
            person_database[pid]['best_quality']  = 9999

        for fpath in [PROFILES_DIR/"person_database.json", ANALYSIS_DIR/"multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f: db = json.load(f)
                target = db if fpath.name.endswith('person_database.json') else db.get('person_profiles', {})
                if pid in target:
                    target[pid]['profile_image'] = b64
                with open(fpath, 'w') as f: json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_person', methods=['POST'])
def delete_person():
    try:
        data = request.get_json()
        pid  = data.get('person_id')
        if not pid:
            return jsonify({'success': False, 'message': 'Missing person_id'})

        person_database.pop(pid, None)
        pinned_profiles.discard(pid)

        for fpath in [PROFILES_DIR/"person_database.json", ANALYSIS_DIR/"multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f: db = json.load(f)
                if fpath.name.endswith('person_database.json'):
                    db.pop(pid, None)
                else:
                    db.get('person_profiles', {}).pop(pid, None)
                    db['pinned_profiles'] = list(pinned_profiles)
                    db['overall_stats']['total_unique_persons'] = len(db.get('person_profiles', {}))
                with open(fpath, 'w') as f: json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/system_info', methods=['GET'])
def system_info():
    return jsonify({
        'deepface':        DEEPFACE_AVAILABLE,
        'mediapipe':       MEDIAPIPE_AVAILABLE,
        'face_recognition':FACE_RECOGNITION_AVAILABLE,
        'mtcnn':           MTCNN_AVAILABLE,
    })

@app.route('/app')
@app.route('/app/<path:path>')
def serve_react(path=''):
    build_dir = '/home/ubuntu/frontend_build'
    if path and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    return send_from_directory(build_dir, 'index.html')

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print()
    print("=" * 62)
    print("  Sentio Mind — Behavioral Intelligence Platform  v2.0")
    print("=" * 62)
    print(f"  MTCNN           : {'✓ available' if MTCNN_AVAILABLE else '✗  pip install mtcnn'}")
    print(f"  DeepFace        : {'✓ available' if DEEPFACE_AVAILABLE else '✗  pip install deepface'}")
    print(f"  MediaPipe       : {'✓ available' if MEDIAPIPE_AVAILABLE else '✗  pip install mediapipe'}")
    print(f"  face_recognition: {'✓ available' if FACE_RECOGNITION_AVAILABLE else '✗  pip install face_recognition'}")
    print()
    print(f"  Input : {INPUT_VIDEOS_DIR}")
    print(f"  Output: {ANALYSIS_DIR}")
    print()
    print("  Folder: input_videos/<SCHOOL>/<DATE_FOLDER>/*.mp4")
    print()
    print("  Open:   http://localhost:5001")
    print("=" * 62)
    print()
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)

