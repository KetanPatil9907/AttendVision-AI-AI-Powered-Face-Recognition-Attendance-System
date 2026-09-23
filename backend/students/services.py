"""Face registration service for students.

Runs the pre-trained pipeline over each uploaded photo. Registration rules:

- Image must contain exactly one usable face.
- No face / multiple faces / too-small / blurry faces are rejected by the
  shared quality gate (ai.preprocessing.assess_face_quality).
- Each student may store up to settings.MAX_STUDENT_PHOTOS photos.
- EVERY photo keeps its own normalized 512-d embedding on StudentFace -
  recognition matches against all of a student's photos and takes the
  strongest similarity (no averaging on the matching path).
- The consolidated FaceEmbedding (mean vector) is still refreshed as a
  legacy fallback for photos stored before per-photo embeddings existed.
"""
import logging

import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from ai.attendance_engine import models_ready
from ai.face_detector import detect_faces
from ai.face_encoder import generate_embedding
from ai.preprocessing import align_face, assess_face_quality, decode_image
from ai.config import MIN_FACE_RATIO

from .models import FaceEmbedding, StudentFace

logger = logging.getLogger(__name__)


class FaceRegistrationError(Exception):
    """Raised when a photo cannot be used for face registration."""


def assert_models_ready():
    if not models_ready():
        from ai.config import model_missing_message

        raise FaceRegistrationError(model_missing_message())


def process_photo(student, image_bytes) -> dict:
    """Validate, detect and embed one photo, storing the StudentFace record.

    Returns a summary dict with the stored face photo and per-photo embedding.
    """
    assert_models_ready()

    existing_count = StudentFace.objects.filter(student=student).count()
    if existing_count >= settings.MAX_STUDENT_PHOTOS:
        raise FaceRegistrationError(
            f"Face registration limit reached ({settings.MAX_STUDENT_PHOTOS} photos)."
        )

    image, err = decode_image(image_bytes)
    if image is None:
        raise FaceRegistrationError(err)

    faces = detect_faces(image)
    if not faces:
        raise FaceRegistrationError("No face detected in this image.")

    img_h, img_w = image.shape[:2]
    faces = [f for f in faces if (f["bbox"][2] / img_w) >= MIN_FACE_RATIO]
    if not faces:
        raise FaceRegistrationError(
            "The detected face is too small. Please bring the face closer to the camera."
        )
    if len(faces) > 1:
        raise FaceRegistrationError(
            "Multiple faces detected. Exactly one face is required per registration photo."
        )

    face = faces[0]
    ok, _metrics, issues = assess_face_quality(image, face)
    if not ok:
        raise FaceRegistrationError(" ".join(issues))

    # Generate embedding from the aligned face.
    aligned = align_face(image, face["kps"])
    embedding = generate_embedding(aligned)
    embedding_list = embedding.tolist()  # JSON-serializable

    # Save the photo (compressed JPEG to keep media small) with ITS OWN
    # embedding - this is the vector recognition will match against.
    photo = StudentFace(student=student, embedding=embedding_list, embedding_generated=True)
    ok, jpeg = cv2_encode_jpeg(image)
    if ok:
        photo.image.save(f"face_{student.pk}_{existing_count + 1}.jpg", ContentFile(jpeg), save=False)
    photo.save()

    _rebuild_consolidated_embedding(student)

    return {
        "photo_id": photo.pk,
        "embedding_dim": len(embedding_list),
        "photo_count": StudentFace.objects.filter(student=student).count(),
    }


def embed_stored_photo(photo):
    """(Re)compute and store the embedding of a stored registration photo.

    Returns the vector, or None when the photo yields no usable face.
    Used by the consolidated rebuild and by the backfill management command
    for photos uploaded before per-photo embeddings existed.
    """
    photo.image.open("rb")
    image, _ = decode_image(photo.image.read())
    photo.image.close()
    if image is None:
        return None
    faces = detect_faces(image)
    if not faces:
        return None
    aligned = align_face(image, faces[0]["kps"])
    vector = generate_embedding(aligned)
    photo.embedding = vector.tolist()
    photo.embedding_generated = True
    photo.save(update_fields=["embedding", "embedding_generated"])
    return vector


def cv2_encode_jpeg(image):
    """Encode a BGR image to JPEG bytes, returning (ok, bytes)."""
    import cv2

    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        return False, None
    return True, buf.tobytes()


def _rebuild_consolidated_embedding(student, force_reembed=False):
    """Refresh the legacy consolidated embedding (mean of per-photo vectors).

    Stored per-photo embeddings are reused directly; legacy photos without
    one are embedded here once and upgraded in place (lazy backfill).
    force_reembed=True recomputes EVERY photo's vector - required after a
    detector/alignment/model change that invalidates previously stored
    embeddings.
    """
    photos = list(StudentFace.objects.filter(student=student))
    vectors = []
    for photo in photos:
        if photo.embedding and not force_reembed:
            vectors.append(np.asarray(photo.embedding, dtype=np.float64))
            continue
        try:
            vector = embed_stored_photo(photo)
            if vector is not None:
                vectors.append(vector.astype(np.float64))
        except Exception as exc:
            logger.warning("Embedding rebuild skipped photo %s: %s", photo.pk, exc)

    if not vectors:
        # No usable photo -> remove any previously stored embedding.
        FaceEmbedding.objects.filter(student=student).delete()
        return

    mean = np.mean(np.stack(vectors), axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm

    with transaction.atomic():
        FaceEmbedding.objects.update_or_create(
            student=student,
            defaults={
                "embedding": mean.tolist(),
                "model_name": "arcface-w600k-r50",
                "photo_count": len(photos),
            },
        )


def remove_face_registration(student):
    """Delete all photos and the consolidated embedding for a student."""
    with transaction.atomic():
        for face_id in StudentFace.objects.filter(student=student).values_list("pk", flat=True):
            face = StudentFace.objects.get(pk=face_id)
            face.image.delete(save=False)
            face.delete()
        FaceEmbedding.objects.filter(student=student).delete()