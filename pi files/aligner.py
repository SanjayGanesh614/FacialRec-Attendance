# ─────────────────────────────────────────────
# aligner.py  —  Stage 2: Normalise face orientation
#
# WHY this step matters:
#   ArcFace was trained on aligned faces where both eyes
#   sit at fixed pixel positions.  Without alignment,
#   accuracy drops significantly — especially when someone
#   tilts their head.
#
# We use an affine warp driven by the 5 MediaPipe landmarks
# to produce a 112×112 image that matches ArcFace's
# expected input format exactly.
# ─────────────────────────────────────────────

import cv2
import numpy as np
from loguru import logger
from detector import DetectedFace


# Reference landmark positions for a 112×112 ArcFace-aligned image.
# These are the canonical coordinates ArcFace was trained on.
# Source: InsightFace / ArcFace paper reference implementation.
_ARCFACE_REFERENCE_LANDMARKS = np.array([
    [38.2946, 51.6963],   # left eye centre
    [73.5318, 51.5014],   # right eye centre
    [56.0252, 71.7366],   # nose tip
    [41.5493, 92.3655],   # mouth left corner
    [70.7299, 92.2041],   # mouth right corner
], dtype=np.float32)

_OUTPUT_SIZE = (112, 112)


class FaceAligner:
    """
    Takes a DetectedFace (with its 5 landmarks) and returns a
    112×112 BGR image that is geometrically normalised for ArcFace.

    Usage:
        aligner = FaceAligner()
        aligned_img = aligner.align(face)   # returns np.ndarray or None
    """

    def align(self, face: DetectedFace) -> np.ndarray | None:
        """
        Compute similarity transform from detected landmarks → reference
        landmarks and warp the crop accordingly.

        Returns aligned 112×112 BGR image, or None if transform fails.
        """
        if face.landmarks is None or len(face.landmarks) != 5:
            logger.warning("Aligner: missing or incomplete landmarks, skipping alignment")
            return self._resize_fallback(face.crop)

        try:
            # estimateAffinePartial2D finds the best-fit similarity transform
            # (rotation + uniform scale + translation, no shear/skew)
            # between our detected landmark positions and the reference positions.
            transform_matrix, inliers = cv2.estimateAffinePartial2D(
                face.landmarks,
                _ARCFACE_REFERENCE_LANDMARKS,
                method=cv2.LMEDS,
            )

            if transform_matrix is None:
                logger.warning("Aligner: could not estimate transform, using resize fallback")
                return self._resize_fallback(face.crop)

            # We need to apply the transform to the FULL original frame crop,
            # not just the small face crop, because the landmarks are in
            # original-frame coordinates.  We reconstruct by padding.
            # Simpler: since our landmarks are relative to the full frame,
            # we apply the warp to the face crop with an offset correction.
            #
            # Offset the transform to account for the crop's top-left corner
            x1, y1 = face.bbox[0], face.bbox[1]
            transform_matrix[0, 2] -= x1 * transform_matrix[0, 0] + y1 * transform_matrix[0, 1]
            transform_matrix[1, 2] -= x1 * transform_matrix[1, 0] + y1 * transform_matrix[1, 1]

            aligned = cv2.warpAffine(
                face.crop,
                transform_matrix,
                _OUTPUT_SIZE,
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            return aligned

        except Exception as exc:
            logger.warning(f"Aligner error: {exc}, using resize fallback")
            return self._resize_fallback(face.crop)

    def _resize_fallback(self, crop: np.ndarray) -> np.ndarray:
        """
        If alignment fails, just resize the crop.
        Accuracy will be slightly lower but the system still works.
        """
        if crop is None or crop.size == 0:
            return None
        return cv2.resize(crop, _OUTPUT_SIZE, interpolation=cv2.INTER_LINEAR)
