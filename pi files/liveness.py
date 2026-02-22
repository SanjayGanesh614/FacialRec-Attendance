# ─────────────────────────────────────────────
# liveness.py  —  Anti-spoofing check
#
# Uses the Silent-Face-Anti-Spoofing MiniFASNet model.
# This detects whether the face is:
#   • A real 3D face (liveness score HIGH → allow)
#   • A printed photo or phone screen (liveness score LOW → reject)
#
# Model download:
#   The ONNX model file is not included in this repo due to size.
#   Download from:
#     https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
#   Place the file at:
#     models/liveness/2.7_80x80_MiniFASNetV2.onnx
#
# If model file is missing, liveness check is SKIPPED with a warning.
# Set LIVENESS_THRESHOLD in config.py to tune sensitivity.
# ─────────────────────────────────────────────

import cv2
import numpy as np
from pathlib import Path
from loguru import logger

import config


class LivenessDetector:
    """
    Runs the MiniFASNetV2 ONNX model on a face crop.

    Returns a score 0.0–1.0 where:
        > config.LIVENESS_THRESHOLD  →  real face  (PASS)
        ≤ config.LIVENESS_THRESHOLD  →  spoof      (FAIL)
    """

    def __init__(self):
        self._session = None
        self._enabled = False
        self._load_model()

    def _load_model(self):
        model_path = config.LIVENESS_MODEL

        if not Path(model_path).exists():
            logger.warning(
                f"Liveness model not found at {model_path}. "
                "Liveness check DISABLED. "
                "Download from: https://github.com/minivision-ai/Silent-Face-Anti-Spoofing"
            )
            return

        try:
            import onnxruntime as ort
            # Force CPU — Pi has no CUDA
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 2   # 2 threads is sweet spot on Pi 4
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            self._input_name  = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            self._enabled = True
            logger.info("LivenessDetector loaded MiniFASNetV2")
        except Exception as exc:
            logger.error(f"Failed to load liveness model: {exc}")

    def check(self, aligned_face_bgr: np.ndarray) -> tuple[bool, float]:
        """
        Check if the face is real.

        Parameters
        ----------
        aligned_face_bgr : np.ndarray
            112×112 BGR image from the aligner.

        Returns
        -------
        (is_real: bool, score: float)
            is_real — True if the face passes the liveness check
            score   — raw model score (higher = more likely real)
        """
        if not self._enabled:
            # Model not loaded → pass-through (don't block legitimate users)
            return True, 1.0

        if aligned_face_bgr is None:
            return False, 0.0

        try:
            # ── Preprocess ────────────────────────────────────────────────────
            img = cv2.resize(aligned_face_bgr, config.LIVENESS_INPUT_SIZE)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0

            # Normalise with ImageNet mean/std — matches training preprocessing
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img = (img - mean) / std

            # HWC → NCHW (batch=1, channels=3, H, W)
            img = img.transpose(2, 0, 1)[np.newaxis, ...]

            # ── Inference ─────────────────────────────────────────────────────
            output = self._session.run(
                [self._output_name],
                {self._input_name: img}
            )[0]

            # Model outputs [spoof_prob, real_prob]
            # Apply softmax just in case model doesn't
            exp_out  = np.exp(output[0] - np.max(output[0]))
            probs    = exp_out / exp_out.sum()
            real_score = float(probs[1])   # index 1 = real

            is_real = real_score > config.LIVENESS_THRESHOLD

            if not is_real:
                logger.warning(f"Liveness FAILED — score: {real_score:.3f} (threshold: {config.LIVENESS_THRESHOLD})")

            return is_real, real_score

        except Exception as exc:
            logger.error(f"Liveness check error: {exc}")
            return True, 1.0   # fail-open rather than blocking everyone if model crashes
