"""Image preprocessing: decode, validate, align and quality-check faces.

The recognition model expects a canonical 112x112 aligned face produced by a
similarity transform computed from the five facial landmarks. This is the same
alignment approach InsightFace applies internally.
"""
import cv2
import numpy as np

from .config import (
    CANONICAL_FACE_SIZE,
    MIN_DETECTOR_SCORE,
    MIN_FACE_PX,
    MIN_FACE_RATIO,
    MIN_FACE_SHARPNESS,
    TARGET_LANDMARKS,
)


def decode_image(contents):
    """Decode raw bytes (JPEG/PNG/etc) into a BGR numpy array.

    Returns (image, error_message). image is None when decoding fails.
    """
    try:
        data = np.frombuffer(contents, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is None:
            return None, "Invalid image file. Please upload a valid photo (JPEG/PNG)."
        return image, None
    except Exception:
        return None, "Could not read the image file."


def image_sharpness(image):
    """Variance of the Laplacian - a simple no-reference blur estimate."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def align_face(image, keypoints):
    """Align a face to the canonical ArcFace template using a similarity
    transform estimated from the 5 detected landmarks."""
    src = np.array(keypoints, dtype=np.float32)
    dst = np.array(TARGET_LANDMARKS, dtype=np.float32)
    transform, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
    if transform is None:
        transform, _ = cv2.estimateAffinePartial2D(src, dst)
    if transform is None:
        raise ValueError("Face alignment failed - could not estimate transform.")
    aligned = cv2.warpAffine(
        image, transform, (CANONICAL_FACE_SIZE, CANONICAL_FACE_SIZE), flags=cv2.INTER_LINEAR
    )
    return aligned


def preprocess_for_recognition(aligned_112):
    """Convert a 112x112 aligned BGR face to the model input tensor.

    The ArcFace w600k_r50 model expects NCHW float32 RGB input normalized
    with: value = (value - 127.5) / 127.5.
    """
    rgb = cv2.cvtColor(aligned_112, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = (rgb - 127.5) / 127.5
    tensor = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...]
    return np.ascontiguousarray(tensor)


def assess_face_quality(image, face):
    """Quality gate for one detected face (registration AND recognition).

    A face must clear every configurable gate before an embedding is
    generated; failing faces are reported as LOW_QUALITY instead of being
    matched against the gallery. The gates were calibrated against real
    photos (see config/settings.py) so normal classroom faces pass while
    tiny or blurred faces are rejected.

    Returns (ok, metrics, issues):
      ok      - True when the face may be embedded.
      metrics - {width, height, ratio, detector_score, sharpness}.
      issues  - human-readable reasons when the face fails.
    """
    x, y, w, h = (int(v) for v in face["bbox"])
    img_h, img_w = image.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    crop = image[y0 : y0 + max(h, 1), x0 : x0 + max(w, 1)]
    sharpness = image_sharpness(crop) if crop.size else 0.0
    ratio = (w / img_w) if img_w else 0.0
    metrics = {
        "width": w,
        "height": h,
        "ratio": ratio,
        "detector_score": float(face.get("score", 0.0)),
        "sharpness": float(sharpness),
    }

    issues = []
    if w < MIN_FACE_PX or h < MIN_FACE_PX:
        issues.append(f"face too small ({w}x{h} px, min {MIN_FACE_PX} px)")
    if ratio < MIN_FACE_RATIO:
        issues.append(f"face too small relative to image ({ratio:.3f} < {MIN_FACE_RATIO})")
    if metrics["detector_score"] < MIN_DETECTOR_SCORE:
        issues.append(f"weak detection (score {metrics['detector_score']:.2f})")
    if sharpness < MIN_FACE_SHARPNESS:
        issues.append(f"face too blurry (sharpness {sharpness:.1f} < {MIN_FACE_SHARPNESS})")
    return not issues, metrics, issues