"""Heavy CV library detection — the only module that imports the CV stack.

Import cost lives here and nowhere else. Every import is guarded so the CV
system degrades gracefully when a library is missing, and so importing
``cv_analysis`` never hard-fails a deployment that has not installed
``requirements-cv.txt``.

The stakeholder/auth service must never import this module.
"""
from __future__ import annotations

import logging
import warnings

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None
    logger.warning("OpenCV not available - video analysis disabled")

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is a hard CV requirement
    np = None
    logger.warning("NumPy not available - CV pipeline disabled")

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except Exception:
    DeepFace = None
    DEEPFACE_AVAILABLE = False
    logger.warning("DeepFace not available - emotion analysis uses fallback")

try:
    import mediapipe as mp
    mp_pose      = mp.solutions.pose
    mp_face_mesh = mp.solutions.face_mesh
    MEDIAPIPE_AVAILABLE = True
except Exception:
    mp = None
    mp_pose = None
    mp_face_mesh = None
    MEDIAPIPE_AVAILABLE = False
    logger.warning("MediaPipe not available - posture/gaze analysis disabled")

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except Exception:
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition not available - using fallback detection")

try:
    from mtcnn import MTCNN as _MTCNNClass
    _MTCNN_GLOBAL = _MTCNNClass()
    MTCNN_AVAILABLE = True
    logger.info("MTCNN available - enhanced low-res detection enabled")
except Exception:
    MTCNN_AVAILABLE = False
    _MTCNN_GLOBAL = None
    logger.warning("MTCNN not available (pip install mtcnn) - detection uses ensemble fallback")

OPENCV_AVAILABLE = cv2 is not None

_clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)) if cv2 else None


def library_status() -> dict:
    """Availability map served by GET /system_info."""
    return {
        "deepface": DEEPFACE_AVAILABLE,
        "mediapipe": MEDIAPIPE_AVAILABLE,
        "face_recognition": FACE_RECOGNITION_AVAILABLE,
        "mtcnn": MTCNN_AVAILABLE,
    }
