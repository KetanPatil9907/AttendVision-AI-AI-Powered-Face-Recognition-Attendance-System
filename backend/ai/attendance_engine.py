"""High-level attendance recognition engine.

Takes a raw image (from webcam frame or uploaded classroom photo), detects
faces, and processes EVERY detected face independently: quality gate ->
alignment -> ArcFace embedding -> cosine match against the enrolled gallery.

Faces that fail the configurable quality gate are reported as LOW_QUALITY
(no embedding is attempted) instead of being silently dropped, so the UI
can show exactly why a face was not considered. Every other detection
either matches a real enrolled student above the configured threshold, or
is reported as unknown (or ambiguous when the margin rule cannot separate
look-alikes). The engine never invents results.
"""
import logging
import os

import cv2
import numpy as np

from .face_detector import detect_faces, is_available as detector_available
from .face_encoder import generate_embedding, is_available as encoder_available
from .face_matcher import best_match
from .preprocessing import align_face, assess_face_quality, decode_image

logger = logging.getLogger(__name__)


def models_ready():
    return detector_available() and encoder_available()


class RecognitionResult:
    """One recognized (or unknown / low-quality) face in an image."""

    def __init__(self, bbox, confidence, score):
        self.bbox = bbox  # (x, y, w, h)
        self.confidence = confidence  # cosine similarity
        self.score = score  # detector confidence
        self.student_id = None
        self.student_name = None
        self.roll_number = None
        self.matched = False
        self.ambiguous = False
        self.low_quality = False
        self.quality_issues = []
        self.face_index = None
        self.size = (int(bbox[2]), int(bbox[3]))
        self.sharpness = None

    @property
    def quality(self):
        return "LOW_QUALITY" if self.low_quality else "GOOD"

    def as_dict(self):
        if self.matched:
            status = "MATCHED"
        elif self.low_quality:
            status = "LOW_QUALITY"
        elif self.ambiguous:
            status = "AMBIGUOUS"
        else:
            status = "UNKNOWN"
        return {
            "bbox": [float(v) for v in self.bbox],
            "confidence": float(self.confidence),
            "confidence_pct": round(float(self.confidence) * 100, 1),
            "detector_score": float(self.score),
            "student_id": self.student_id,
            "student_name": self.student_name,
            "roll_number": self.roll_number,
            "matched": self.matched,
            "ambiguous": self.ambiguous,
            "low_quality": self.low_quality,
            "status": status,
            # Structured debug info (section 11) - never raw embeddings.
            "face_index": self.face_index,
            "face_width": self.size[0],
            "face_height": self.size[1],
            "quality": self.quality,
            "quality_issues": list(self.quality_issues),
            "sharpness": round(self.sharpness, 1) if self.sharpness is not None else None,
        }


def _crop_margin(image, bbox, margin=0.25):
    """Expand the detected box by a margin (out-of-bounds clipping)."""
    x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    img_h, img_w = image.shape[:2]
    mx = int(w * margin)
    my = int(h * margin)
    x = max(0, x - mx)
    y = max(0, y - my)
    x2 = min(img_w, x + w + 2 * mx)
    y2 = min(img_h, y + h + 2 * my)
    return (x, y, x2 - x, y2 - y)


def recognize_faces(image_bytes, gallery, threshold=0.70, min_face_ratio=None, margin=0.0):
    """Recognize every face in the provided image bytes.

    gallery: list of dicts {student_id, roll_number, name, embedding}.
        Multiple entries may belong to the same student (one per
        registration photo); best_match groups them per student.
    threshold: cosine-similarity threshold for a confident match.
    min_face_ratio: optional extra size gate (fraction of image width) on
        top of the configured quality gate.
    margin: required top1-vs-runner-up student gap (see face_matcher);
        rejects ambiguous look-alike matches instead of guessing.

    Every detected face is processed independently and ALWAYS appears in
    the results with a status: MATCHED / AMBIGUOUS / UNKNOWN / LOW_QUALITY.

    Returns (results, inner_error_message). When the AI pipeline cannot run
    (missing models, bad image) results is None and inner_error_message is set.
    """
    image, err = decode_image(image_bytes)
    if image is None:
        return None, err

    results = []
    faces = detect_faces(image)
    img_w = image.shape[1]

    for i, face in enumerate(faces):
        bbox = face["bbox"]
        res = RecognitionResult(bbox, 0.0, face["score"])
        res.face_index = i

        # Quality gate FIRST - a face that is too small / blurry / weakly
        # detected is reported as LOW_QUALITY and never matched.
        ok, metrics, issues = assess_face_quality(image, face)
        res.sharpness = metrics["sharpness"]
        if ok and min_face_ratio is not None and (bbox[2] / img_w) < min_face_ratio:
            ok = False
            issues.append(f"face too small relative to image (caller gate {min_face_ratio})")
        if not ok:
            res.low_quality = True
            res.quality_issues = issues
            results.append(res)
            continue

        try:
            aligned = align_face(image, face["kps"])
            embedding = generate_embedding(aligned)
            idx, sim = best_match(embedding, gallery, threshold, margin=margin)
            res.confidence = sim
            if idx is not None:
                entry = gallery[idx]
                res.matched = True
                res.student_id = entry["student_id"]
                res.student_name = entry["name"]
                res.roll_number = entry["roll_number"]
            elif sim >= threshold:
                # Passed the absolute threshold but not the margin rule: the
                # top candidate is too close to the runner-up to be trusted
                # (classic look-alike / degraded-probe situation).
                res.ambiguous = True
            results.append(res)
        except Exception as exc:  # alignment/embedding failure for one face
            logger.warning("Face %d processing failed: %s", i, exc)
            res.low_quality = True
            res.quality_issues = [f"could not process face ({exc})"]
            results.append(res)
    return results, None