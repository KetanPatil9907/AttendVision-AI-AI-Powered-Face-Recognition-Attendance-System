"""Attendance orchestration: recognition, automatic marking, finalization.

Recognition is scope-limited to the students enrolled in the session's
division. For every matched face we create/update the unique AttendanceRecord
(student, session) - the database constraint makes duplicate marking
impossible.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ai.attendance_engine import recognize_faces
from ai.face_matcher import cosine_similarity

from .models import AttendanceRecord, AttendanceSession, RecognitionLog

logger = logging.getLogger(__name__)


def build_gallery(session):
    """Load the matching gallery for a session - one entry per (student, photo).

    Every registration photo contributes its own embedding, so a probe face
    is compared against ALL samples of each student and the strongest
    per-student similarity wins (best_match does the grouping). A student
    registered before per-photo embeddings existed falls back to their
    legacy consolidated vector.
    """
    students = list(
        session.division.students.filter(status="active")
        .select_related("face_embedding")
        .prefetch_related("faces")
    )
    gallery = []
    for student in students:
        vectors = [f.embedding for f in student.faces.all() if f.embedding]
        if not vectors:
            emb = getattr(student, "face_embedding", None)
            if emb is not None:
                vectors = [emb.embedding]
        for vec in vectors:
            gallery.append(
                {
                    "student_id": student.pk,
                    "name": student.full_name,
                    "roll_number": student.roll_number,
                    "embedding": vec,
                }
            )
    return gallery, students


def ensure_present_records(session):
    """Create AttendanceRecord rows for all enrolled students.

    Students without face registration are included (absent until matched or
    manually marked). They are not part of the AI gallery but remain in the
    roster so attendance can still be corrected manually.
    """
    with transaction.atomic():
        existing = set(
            AttendanceRecord.objects.filter(session=session).values_list("student_id", flat=True)
        )
        students = list(session.division.students.filter(status="active"))
        to_create = [
            AttendanceRecord(session=session, student=s) for s in students if s.pk not in existing
        ]
        AttendanceRecord.objects.bulk_create(to_create, ignore_conflicts=True)


def mark_present(session, student_id, confidence, matched_by="ai"):
    """Mark a student present for the session (idempotent / duplicate-safe).

    A manual correction made by the teacher is sticky: the AI never flips a
    record the teacher explicitly set to "absent" back to "present".
    """
    record, created = AttendanceRecord.objects.get_or_create(
        session=session, student_id=student_id
    )
    if (
        not created
        and matched_by == "ai"
        and record.manually_updated
        and record.status == AttendanceRecord.Status.ABSENT
    ):
        return record, "manual_lock"
    if created or record.status != AttendanceRecord.Status.PRESENT:
        record.status = AttendanceRecord.Status.PRESENT
        record.confidence = confidence
        record.marked_by_ai = matched_by == "ai"
        record.manually_updated = matched_by == "manual"
        record.recognized_at = timezone.now()
        record.save(update_fields=["status", "confidence", "marked_by_ai", "manually_updated", "recognized_at", "updated_at"])
        return record, "marked"
    if confidence > record.confidence:
        record.confidence = confidence
        record.recognized_at = timezone.now()
        record.save(update_fields=["confidence", "recognized_at", "updated_at"])
    return record, "already_present"


def process_recognition(session, image_bytes, throttle_dedup=False):
    """Run AI recognition over an image for a live session.

    Matched students (confidence >= threshold) are automatically marked
    present. Returns the raw detection list plus counters and per-result dedup
    status for the UI.
    """
    if session.status == AttendanceSession.Status.FINALIZED:
        return {
            "error": "Attendance session has already been finalized.",
            "code": "session_finalized",
        }

    # Materialise records for students enrolled after the session was created
    # so a freshly-added student can be marked the moment their face matches.
    ensure_present_records(session)

    gallery, students = build_gallery(session)
    threshold = settings.RECOGNITION_THRESHOLD
    margin = settings.RECOGNITION_MARGIN
    detections, inner_error = recognize_faces(
        image_bytes, gallery, threshold=threshold, margin=margin
    )

    if detections is None:
        return {"error": inner_error, "code": "ai_error"}

    enrolled_ids = {s.pk for s in students}
    already_present_ids = set(
        AttendanceRecord.objects.filter(
            session=session, status=AttendanceRecord.Status.PRESENT
        ).values_list("student_id", flat=True)
    )

    present_counter = 0
    unknown_counter = 0
    ambiguous_counter = 0
    low_quality_counter = 0
    new_marks = 0
    repeated = 0
    manual_locks = 0
    results = []

    for det in detections:
        entry = det.as_dict()
        matching_student_id = entry["student_id"]
        if entry["low_quality"] and not entry["matched"]:
            # Too small / too blurry / weakly detected - identification was
            # never attempted. Logged for debugging, never marked.
            RecognitionLog.objects.create(
                session=session,
                confidence=entry["confidence"],
                result=RecognitionLog.Result.REJECTED,
                message=(
                    f"LOW_QUALITY face #{entry['face_index']} "
                    f"{entry['face_width']}x{entry['face_height']} det "
                    f"{entry['detector_score']:.2f} - "
                    f"{'; '.join(entry['quality_issues'])}. Not attempted."
                ),
            )
            entry["mark_status"] = "low_quality"
            entry["already_present"] = False
            low_quality_counter += 1
            results.append(entry)
            continue
        if entry["ambiguous"] and not entry["matched"]:
            # Cleared the absolute threshold but not the margin rule: the best
            # candidate is too close to the runner-up (look-alike classmate or
            # degraded probe). Report "too close to call" and NEVER mark.
            RecognitionLog.objects.create(
                session=session,
                confidence=entry["confidence"],
                result=RecognitionLog.Result.REJECTED,
                message=(
                    f"Ambiguous face #{entry['face_index']} "
                    f"{entry['face_width']}x{entry['face_height']} at "
                    f"{entry['confidence_pct']}% - closest candidates within "
                    f"the {margin} margin rule, not marked."
                ),
            )
            entry["mark_status"] = "ambiguous"
            entry["already_present"] = False
            ambiguous_counter += 1
            results.append(entry)
            continue
        if not entry["matched"] or matching_student_id not in enrolled_ids:
            # Unknown face / not enrollable - log and report, never mark.
            RecognitionLog.objects.create(
                session=session,
                confidence=entry["confidence"],
                result=RecognitionLog.Result.UNKNOWN,
                message=(
                    f"Unknown face #{entry['face_index']} "
                    f"{entry['face_width']}x{entry['face_height']} det "
                    f"{entry['detector_score']:.2f} at confidence "
                    f"{entry['confidence_pct']}% (threshold {threshold})."
                ),
            )
            entry["mark_status"] = "unknown"
            entry["already_present"] = False
            unknown_counter += 1
            results.append(entry)
            continue

        student_id = matching_student_id
        already = student_id in already_present_ids
        if already:
            record, _ = AttendanceRecord.objects.get_or_create(session=session, student_id=student_id)
            mark_present(session, student_id, entry["confidence"])
            present_counter += 1
            repeated += 1
            entry["mark_status"] = "already_present"
            entry["already_present"] = True
            RecognitionLog.objects.create(
                session=session,
                student_id=student_id,
                confidence=entry["confidence"],
                result=RecognitionLog.Result.MATCHED,
                message="Duplicate detection - already marked present.",
            )
        else:
            record, mark_status = mark_present(session, student_id, entry["confidence"])
            if mark_status == "manual_lock":
                # Matched, but the teacher manually marked this student absent -
                # the manual correction wins over the AI.
                entry["mark_status"] = "manual_lock"
                entry["already_present"] = False
                manual_locks += 1
                RecognitionLog.objects.create(
                    session=session,
                    student_id=student_id,
                    confidence=entry["confidence"],
                    result=RecognitionLog.Result.MATCHED,
                    message="Matched, but a manual 'absent' correction was kept.",
                )
            else:
                present_counter += 1
                new_marks += 1
                entry["mark_status"] = "marked" if mark_status == "marked" else "already_present"
                entry["already_present"] = mark_status == "already_present"
                already_present_ids.add(student_id)
                RecognitionLog.objects.create(
                    session=session,
                    student_id=student_id,
                    confidence=entry["confidence"],
                    result=RecognitionLog.Result.MATCHED,
                    message=(
                        f"Matched {entry['student_name']} at "
                        f"{entry['confidence_pct']}% ({entry['face_width']}x"
                        f"{entry['face_height']}, det "
                        f"{entry['detector_score']:.2f}, quality GOOD, "
                        f"threshold {threshold})."
                    ),
                )
        results.append(entry)

    return {
        "detections": results,
        "detected": len(results),
        "present": present_counter,
        "unknown": unknown_counter,
        "ambiguous": ambiguous_counter,
        "low_quality": low_quality_counter,
        "new_marks": new_marks,
        "repeated": repeated,
        "manual_lock": manual_locks,
        "session_status": session.status,
        "threshold": threshold,
        "margin": margin,
    }


def finalize_session(session):
    """Finalize the session. No further detection/marking is allowed."""
    with transaction.atomic():
        current = AttendanceSession.objects.select_for_update().get(pk=session.pk)
        # Any remaining unmarked transfer/other-status students become absent.
        ensure_present_records(current)
        current.status = AttendanceSession.Status.FINALIZED
        current.finalized_at = timezone.now()
        current.save(update_fields=["status", "finalized_at"])
    return current


def guess_match(student, session):
    """Confidence of an existing record for display (0.0 when not present)."""
    record = AttendanceRecord.objects.filter(session=session, student=student).first()
    if record and record.status == AttendanceRecord.Status.PRESENT:
        return record.confidence
    return 0.0