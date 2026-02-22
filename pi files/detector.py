# ─────────────────────────────────────────────
# detector.py  —  Stage 1: Find faces in a frame
#
# Uses MediaPipe FaceMesh which gives us:
#   • Bounding boxes  → where to crop
#   • 468 landmarks   → eye positions for alignment
#
# MediaPipe is chosen over YOLOv8 here because it runs
# well on Pi CPU without needing a GPU.  YOLOv8 would
# need the Coral USB Accelerator to be fast enough.
# ─────────────────────────────────────────────

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import List, Optional, Tuple
from loguru import logger

import config


@dataclass
class DetectedFace:
    """
    Everything we know about one face found in a frame.
    Passed down the pipeline to aligner → recogniser → liveness.
    """
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2) in pixels
    crop: np.ndarray                   # raw BGR crop of the face region
    landmarks: np.ndarray              # shape (5, 2) — the 5 key landmarks
                                       # [left_eye, right_eye, nose, mouth_left, mouth_right]
    confidence: float


class FaceDetector:
    """
    Wraps MediaPipe FaceMesh.

    Usage:
        detector = FaceDetector()
        faces = detector.detect(frame)   # frame is a BGR numpy array from cv2
    """

    # MediaPipe FaceMesh landmark indices for the 5 key points
    # We extract these specifically because ArcFace alignment uses exactly 5 points
    _LEFT_EYE_IDX   = 33
    _RIGHT_EYE_IDX  = 263
    _NOSE_IDX       = 1
    _MOUTH_L_IDX    = 61
    _MOUTH_R_IDX    = 291

    def __init__(self):
        mp_face_mesh = mp.solutions.face_mesh
        self._mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,          # video mode — reuses tracking between frames
            max_num_faces=5,                  # detect up to 5 faces per frame
            refine_landmarks=True,            # more accurate eye/lip landmarks
            min_detection_confidence=config.MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MP_MIN_TRACKING_CONFIDENCE,
        )
        logger.info("FaceDetector initialised (MediaPipe FaceMesh)")

    def detect(self, frame_bgr: np.ndarray) -> List[DetectedFace]:
        """
        Detect all faces in a BGR frame.

        Returns a list of DetectedFace objects.
        Empty list if no faces found or frame is bad.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w = frame_bgr.shape[:2]

        # MediaPipe expects RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return []

        detected = []
        for face_landmarks in results.multi_face_landmarks:
            # ── Extract bounding box from all 468 landmarks ───────────────────
            xs = [lm.x * w for lm in face_landmarks.landmark]
            ys = [lm.y * h for lm in face_landmarks.landmark]

            x1 = max(0, int(min(xs)) - 10)
            y1 = max(0, int(min(ys)) - 10)
            x2 = min(w, int(max(xs)) + 10)
            y2 = min(h, int(max(ys)) + 10)

            face_w = x2 - x1
            face_h = y2 - y1

            # Skip faces that are too small — likely background noise
            if face_w < config.MIN_FACE_SIZE_PX or face_h < config.MIN_FACE_SIZE_PX:
                continue

            # ── Extract the 5 key landmark positions ─────────────────────────
            def lm_xy(idx):
                lm = face_landmarks.landmark[idx]
                return [lm.x * w, lm.y * h]

            key_landmarks = np.array([
                lm_xy(self._LEFT_EYE_IDX),
                lm_xy(self._RIGHT_EYE_IDX),
                lm_xy(self._NOSE_IDX),
                lm_xy(self._MOUTH_L_IDX),
                lm_xy(self._MOUTH_R_IDX),
            ], dtype=np.float32)

            # ── Crop the face region ──────────────────────────────────────────
            crop = frame_bgr[y1:y2, x1:x2].copy()

            detected.append(DetectedFace(
                bbox=(x1, y1, x2, y2),
                crop=crop,
                landmarks=key_landmarks,
                confidence=config.MP_MIN_DETECTION_CONFIDENCE,  # MediaPipe doesn't expose raw score
            ))

        return detected

    def draw_debug(self, frame: np.ndarray, faces: List[DetectedFace]) -> np.ndarray:
        """Draw bounding boxes and landmarks — useful during development / tuning."""
        out = frame.copy()
        for face in faces:
            x1, y1, x2, y2 = face.bbox
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            for (lx, ly) in face.landmarks:
                cv2.circle(out, (int(lx), int(ly)), 3, (255, 0, 0), -1)
        return out

    def close(self):
        self._mesh.close()
