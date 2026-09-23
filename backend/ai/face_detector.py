"""Face detection using OpenCV's YuNet (ONNX) detector.

YuNet returns bounding boxes plus 5 facial keypoints per face, which is
sufficient to run the standard ArcFace alignment step.
"""
import logging
import os
import threading

import cv2

from .config import DETECTOR_MODEL_PATH, model_missing_message

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_detector = None
_detector_meta = {"dim": None}


def _ensure_detector():
    """Lazily load the YuNet detector once (thread-safe)."""
    global _detector
    with _lock:
        if _detector is not None:
            return _detector
        if not os.path.exists(DETECTOR_MODEL_PATH):
            raise FileNotFoundError(model_missing_message())
        try:
            _detector = cv2.FaceDetectorYN_create(
                DETECTOR_MODEL_PATH, "", (320, 320), score_threshold=0.5
            )
            logger.info("YuNet face detector loaded from %s", DETECTOR_MODEL_PATH)
        except Exception as exc:
            logger.exception("Failed to load YuNet detector")
            raise RuntimeError(f"Could not load the face detection model: {exc}") from exc
        return _detector


def is_available():
    return os.path.exists(DETECTOR_MODEL_PATH)


def detect_faces(image):
    """Detect faces in a BGR image.

    Returns a list of dicts:
        {bbox: (x, y, w, h), kps: [(x, y) * 5], score: float}
    Faces are sorted by area (largest first).
    """
    detector = _ensure_detector()
    h, w = image.shape[:2]
    # YuNet keeps the input size on the shared detector instance, so sizing and
    # detection must happen atomically - otherwise two concurrent requests with
    # different image sizes corrupt each other's results.
    with _lock:
        if _detector_meta["dim"] != (w, h):
            detector.setInputSize((w, h))
            _detector_meta["dim"] = (w, h)
        _, faces = detector.detect(image)

    results = []
    if faces is None:
        return results
    for face in faces:
        # YuNet output layout (15 values): x, y, w, h, 5 * (x, y) landmarks,
        # score - so landmarks start at index 4. (Reading them from index 5
        # shifts every landmark pair onto the wrong axis and feeds the score
        # in as the last "landmark", producing a misaligned face crop: the
        # same photo still matched itself, but any other photo of that person
        # failed to match.)
        x, y, fw, fh = float(face[0]), float(face[1]), float(face[2]), float(face[3])
        kps = [(float(face[4 + i * 2]), float(face[4 + i * 2 + 1])) for i in range(5)]
        score = float(face[-1])
        results.append({"bbox": (x, y, fw, fh), "kps": kps, "score": score})
    results.sort(key=lambda f: f["bbox"][2] * f["bbox"][3], reverse=True)
    return results