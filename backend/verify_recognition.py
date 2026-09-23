"""End-to-end verification of the face-recognition pipeline (spec section 13).

Runs against the real HTTP endpoints AND the engine directly:

  TEST 1  original registration photo                -> KNOWN
  TEST 2  different photo of same student (leave-
          one-out gallery: probe photo EXCLUDED)     -> KNOWN
  TEST 3  group photo, 1 known + 2 unknown people    -> only the known
          student matched, others UNKNOWN
  TEST 4  group photo with all 3 registered students -> each recognized
          independently
  TEST 5  completely unknown person                  -> UNKNOWN/AMBIGUOUS,
          marks nobody
  TEST 6  very small face and heavily blurred face   -> LOW_QUALITY
  TEST 7  same student appears twice in one photo    -> one record only
  TEST 8  recognition run twice                       -> no duplicates
  +       manual 'absent' lock, finalize lock, audit logs, API shape
          (no raw embeddings exposed)

Everything runs in a throwaway session that is deleted at the end.
"""
import io
import os
import sys
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django

django.setup()

from django.test.utils import setup_test_environment

setup_test_environment()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from ai.attendance_engine import recognize_faces
from attendance.models import AttendanceRecord, RecognitionLog
from attendance.services import build_gallery
from classes.models import Classroom, Division, Subject
from students.models import FaceEmbedding, Student, StudentFace

THRESHOLD = settings.RECOGNITION_THRESHOLD
MARGIN = settings.RECOGNITION_MARGIN
print(f"RECOGNITION_THRESHOLD={THRESHOLD}  RECOGNITION_MARGIN={MARGIN}")
print(
    f"gates: min_face_px={settings.RECOGNITION_MIN_FACE_PX} "
    f"ratio={settings.RECOGNITION_MIN_FACE_RATIO} "
    f"det>={settings.RECOGNITION_MIN_DETECTOR_SCORE} "
    f"sharp>={settings.RECOGNITION_MIN_FACE_SHARPNESS} "
    f"max_photos={settings.MAX_STUDENT_PHOTOS}"
)

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((bool(condition), name, detail))
    print(("PASS  " if condition else "FAIL  ") + name + ("  | " + str(detail) if detail else ""))


def img_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def photo_of(student, index=0):
    faces = list(student.faces.all())
    return img_bytes(os.path.join(settings.MEDIA_ROOT, faces[index].image.name))


def strip_of(sources, height=700):
    """Paste images side by side at a common height (a classroom-photo strip)."""
    images = []
    for src in sources:
        raw = src if isinstance(src, bytes) else img_bytes(src)
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        images.append(im.resize((max(1, int(im.width * height / im.height)), height), Image.LANCZOS))
    canvas = Image.new("RGB", (sum(i.width for i in images), height), (240, 240, 240))
    x = 0
    for im in images:
        canvas.paste(im, (x, 0))
        x += im.width
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def upload(client, session_id, name, data):
    return client.post(
        f"/api/attendance/sessions/{session_id}/recognize/",
        {"image": SimpleUploadedFile(name, data, "image/jpeg")},
        format="multipart",
    )


def present_set(session_id):
    return set(
        AttendanceRecord.objects.filter(
            session_id=session_id, status="present"
        ).values_list("student_id", flat=True)
    )


def statuses(data):
    return [(d.get("face_index"), d.get("status"), d.get("student_name")) for d in data.get("detections", [])]


user = get_user_model().objects.first()
client = APIClient()
client.force_authenticate(user)

students = list(Student.objects.filter(status="active").order_by("roll_number"))
check("gallery has 3 enrolled students", len(students) == 3, [s.full_name for s in students])
s_parth, s_sammer, s_harshal = students[0], students[1], students[2]

# --- per-photo embedding storage (section 2) --------------------------------
all_photos = StudentFace.objects.filter(student__in=students)
with_emb = all_photos.filter(embedding__isnull=False).count()
check("0a. every registration photo stores its own embedding",
      with_emb == all_photos.count() and with_emb >= 3,
      f"{with_emb}/{all_photos.count()} photos")
photo_counts = {s.full_name: s.faces.count() for s in students}
print("     photo counts:", photo_counts)

# --- throwaway session -------------------------------------------------------
session_kwargs = dict(
    teacher=user,
    classroom=Classroom.objects.first(),
    division=Division.objects.filter(classroom=Classroom.objects.first()).first(),
    subject=Subject.objects.first(),
    date=date(2026, 9, 23),
    lecture_number="E2E-RECOGN",
)
from attendance.models import AttendanceSession

session = AttendanceSession.objects.create(**session_kwargs)
print("test session id:", session.pk)

UNKNOW_PATH = os.path.join(os.path.dirname(settings.BASE_DIR), "unknow.jpeg")
FACE_TEST_PATH = os.path.join(settings.BASE_DIR, "tests", "data", "face_test.jpg")

try:
    r = client.get(f"/api/attendance/sessions/{session.pk}/records/")
    check("0b. roster auto-materialised", r.status_code == 200 and len(r.data.get("records", [])) == 3,
          f"status={r.status_code} roster={len(r.data.get('records', []))}")

    gallery, _ = build_gallery(session)
    check("0c. gallery holds one entry per photo",
          len(gallery) == all_photos.count(),
          f"entries={len(gallery)} photos={all_photos.count()}")

    # ======================================================================
    # TEST 7 - same student twice in one photo (fresh session: only ONE new
    # mark from two detections). Runs first so the session is empty.
    # ======================================================================
    doubled = strip_of([photo_of(s_parth), photo_of(s_parth)])
    r = upload(client, session.pk, "double.jpg", doubled)
    d = r.data
    check("T7a. doubled photo detected both faces", d.get("detected") == 2, statuses(d))
    matched7 = [x for x in d.get("detections", []) if x.get("matched")]
    check("T7b. both detections matched the same student",
          len(matched7) == 2 and all(m["student_id"] == s_parth.pk for m in matched7),
          [(m["student_name"], m["confidence_pct"]) for m in matched7])
    check("T7c. only ONE new attendance mark", d.get("new_marks") == 1,
          {k: d.get(k) for k in ("detected", "new_marks", "repeated")})
    recs = AttendanceRecord.objects.filter(session=session, student=s_parth)
    check("T7d. exactly one record exists for the student", recs.count() == 1 and recs.first().status == "present",
          f"records={recs.count()}")

    # ======================================================================
    # TEST 1 + TEST 8 - original registration photo -> KNOWN; running the
    # recognition again never creates a duplicate record.
    # ======================================================================
    r = upload(client, session.pk, "original.jpg", photo_of(s_parth))
    d = r.data
    matched1 = [x for x in d.get("detections", []) if x.get("matched")]
    check("T1. original registration photo KNOWN",
          r.status_code == 200 and len(matched1) >= 1 and all(m["student_id"] == s_parth.pk for m in matched1),
          [(m["student_name"], m["confidence_pct"]) for m in matched1])
    check("T8. second run adds no duplicate record",
          d.get("new_marks") == 0 and d.get("repeated", 0) >= 1
          and AttendanceRecord.objects.filter(session=session, student=s_parth).count() == 1,
          {k: d.get(k) for k in ("new_marks", "repeated")})

    # ======================================================================
    # TEST 2 - DIFFERENT photo of a registered student -> KNOWN.
    # Leave-one-out: the probe photo's own embedding is EXCLUDED from the
    # gallery, so the match must come from the student's OTHER photos.
    # (Sammer's middle photo has a notably different framing/size.)
    # ======================================================================
    probe_photo = list(s_sammer.faces.all())[1]
    probe_bytes = img_bytes(os.path.join(settings.MEDIA_ROOT, probe_photo.image.name))
    loo_gallery = [
        {"student_id": f.student_id, "name": f.student.full_name,
         "roll_number": f.student.roll_number, "embedding": f.embedding}
        for f in all_photos.exclude(pk=probe_photo.pk)
        if f.embedding
    ]
    results, err = recognize_faces(probe_bytes, loo_gallery, threshold=THRESHOLD, margin=MARGIN)
    det2 = [x.as_dict() for x in results] if results else []
    m2 = [x for x in det2 if x.get("matched")]
    check("T2. different photo of known student KNOWN (leave-one-out gallery)",
          err is None and len(m2) >= 1 and m2[0]["student_id"] == s_sammer.pk,
          [(x["student_name"], x["confidence_pct"], x["status"]) for x in det2])
    # For transparency: what would the legacy MEAN vector have scored?
    legacy = FaceEmbedding.objects.filter(student=s_sammer).first()
    if legacy:
        legacy_results, _ = recognize_faces(
            probe_bytes,
            [{"student_id": s_sammer.pk, "name": s_sammer.full_name,
              "roll_number": s_sammer.roll_number, "embedding": legacy.embedding}],
            threshold=0.0,
        )
        legacy_score = max((x.confidence for x in legacy_results), default=0.0)
        per_photo_score = max((x["confidence"] for x in det2), default=0.0)
        print(f"     per-photo best={per_photo_score:.3f} vs legacy mean vector={legacy_score:.3f}")

    # ======================================================================
    # TEST 3 - group photo: Parth (known) + 2 unenrolled people.
    # ======================================================================
    group3 = strip_of([photo_of(s_parth), FACE_TEST_PATH, UNKNOW_PATH])
    before3 = present_set(session.pk)
    r = upload(client, session.pk, "group3.jpg", group3)
    d = r.data
    check("T3a. group of 3 faces detected", d.get("detected") == 3, statuses(d))
    matched3 = {x["student_id"] for x in d.get("detections", []) if x.get("matched")}
    check("T3b. ONLY the enrolled student matched", matched3 == {s_parth.pk},
          f"matched={sorted(matched3)}")
    others3 = [x for x in d.get("detections", []) if not x.get("matched")]
    check("T3c. other faces reported UNKNOWN (not marked)",
          all(x["status"] in ("UNKNOWN", "LOW_QUALITY") for x in others3),
          [(x["status"], x["confidence_pct"]) for x in others3])
    check("T3d. no extra attendance marks",
          d.get("new_marks") == 0 and present_set(session.pk) == before3 == {s_parth.pk},
          {k: d.get(k) for k in ("new_marks", "present", "unknown")})

    # ======================================================================
    # TEST 4 - group photo containing ALL registered students.
    # ======================================================================
    group_all = strip_of([photo_of(s_parth), photo_of(s_sammer), photo_of(s_harshal)])
    r = upload(client, session.pk, "group_all.jpg", group_all)
    d = r.data
    check("T4a. group of 3 enrolled faces detected", d.get("detected") == 3, statuses(d))
    matched4 = {x["student_id"] for x in d.get("detections", []) if x.get("matched")}
    check("T4b. each registered student recognized independently",
          matched4 == {s_parth.pk, s_sammer.pk, s_harshal.pk},
          f"matched={sorted(matched4)}")
    check("T4c. two NEW marks (Parth already present)",
          d.get("new_marks") == 2, {k: d.get(k) for k in ("new_marks", "repeated", "present")})
    check("T4d. whole class now present",
          present_set(session.pk) == {s_parth.pk, s_sammer.pk, s_harshal.pk},
          sorted(present_set(session.pk)))

    # ======================================================================
    # TEST 5 - completely unknown person (the incident photo) -> nobody marked.
    # ======================================================================
    before5 = present_set(session.pk)
    r = upload(client, session.pk, "unknown.jpg", img_bytes(UNKNOW_PATH))
    d5 = r.data
    after5 = present_set(session.pk)
    check("T5a. unknown photo processed with detections",
          r.status_code == 200 and d5.get("detected", 0) >= 1, statuses(d5))
    check("T5b. unknown person NOT matched (unknown or ambiguous)",
          all(x["status"] in ("UNKNOWN", "AMBIGUOUS", "LOW_QUALITY") for x in d5.get("detections", [])),
          statuses(d5))
    check("T5c. unknown person marked NOBODY",
          d5.get("new_marks", 0) == 0 and before5 == after5,
          {k: d5.get(k) for k in ("new_marks", "unknown", "ambiguous", "present")})

    # ======================================================================
    # TEST 6 - very small face and heavily blurred face -> LOW_QUALITY.
    # ======================================================================
    import cv2
    import numpy as np

    parth_img = cv2.imdecode(np.frombuffer(photo_of(s_parth), np.uint8), cv2.IMREAD_COLOR)
    # a) tiny face (~31x41 px, below RECOGNITION_MIN_FACE_PX)
    scale = 30 / 253
    tiny = cv2.resize(parth_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, tiny_jpeg = cv2.imencode(".jpg", tiny, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    r = upload(client, session.pk, "tiny.jpg", tiny_jpeg.tobytes())
    d = r.data
    dets6a = d.get("detections", [])
    tiny_ok = (d.get("detected", 0) == 0) or (
        all(x["status"] == "LOW_QUALITY" for x in dets6a) and d.get("new_marks") == 0
    )
    check("T6a. tiny face -> LOW_QUALITY (or safely not detected)",
          tiny_ok and present_set(session.pk) == before5,
          statuses(d) + [(d.get("new_marks"),)])

    # b) heavily blurred face (large enough to detect, fails the sharpness gate)
    blurred = cv2.GaussianBlur(parth_img, (15, 15), 0)
    ok, blur_jpeg = cv2.imencode(".jpg", blurred, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    r = upload(client, session.pk, "blur.jpg", blur_jpeg.tobytes())
    d = r.data
    dets6b = d.get("detections", [])
    check("T6b. blurred face detected by YuNet", len(dets6b) >= 1, statuses(d))
    check("T6c. blurred face reported LOW_QUALITY with reasons, not matched",
          all(x["status"] == "LOW_QUALITY" and x["quality_issues"] for x in dets6b)
          and d.get("new_marks") == 0,
          [(x["status"], x.get("sharpness"), x.get("quality_issues")) for x in dets6b])
    check("T6d. LOW_QUALITY decision written to the audit log",
          RecognitionLog.objects.filter(session=session, result=RecognitionLog.Result.REJECTED)
          .filter(message__contains="LOW_QUALITY").exists())

    # ======================================================================
    # API shape (section 12) - use the last response (T6c / d5 for counters).
    # ======================================================================
    d = d5
    check("API1. response carries counters + threshold/margin",
          all(k in d for k in ("detected", "present", "unknown", "ambiguous",
                               "low_quality", "new_marks", "repeated",
                               "threshold", "margin")),
          {k: d.get(k) for k in ("threshold", "margin", "low_quality", "ambiguous")})
    det0 = (d.get("detections") or [{}])[0]
    check("API2. per-face debug fields present",
          all(k in det0 for k in ("face_index", "bbox", "face_width", "face_height",
                                  "detector_score", "quality", "status", "confidence")),
          {k: det0.get(k) for k in ("face_index", "face_width", "detector_score", "quality", "status")})
    raw_vectors = [
        k for det in d.get("detections", []) for k in det
        if "embedding" in k or "vector" in k
    ]
    check("API3. no raw embeddings exposed", not raw_vectors, raw_vectors)

    # ======================================================================
    # Manual 'absent' lock survives AI recognition.
    # ======================================================================
    rec = AttendanceRecord.objects.get(session=session, student=s_sammer)
    r = client.post(f"/api/attendance/sessions/{session.pk}/update-records/",
                    {"updates": [{"id": rec.pk, "status": "absent"}]}, format="json")
    check("LOCK1. manual absent correction accepted", r.status_code == 200, r.status_code)
    r = upload(client, session.pk, "sammer.jpg", photo_of(s_sammer))
    rec.refresh_from_db()
    lock = [x for x in r.data.get("detections", []) if x.get("mark_status") == "manual_lock"]
    check("LOCK2. AI did NOT override the manual absent",
          rec.status == "absent" and len(lock) >= 1,
          f"status={rec.status} manual_lock={len(lock)}")
    # restore for the finalize checks
    rec.status = "present"
    rec.manually_updated = False
    rec.save(update_fields=["status", "manually_updated"])

    # ======================================================================
    # Finalize locks the session (with the machine-readable error code).
    # ======================================================================
    r = client.post(f"/api/attendance/sessions/{session.pk}/finalize/")
    check("FIN1. finalize accepted", r.status_code == 200, r.status_code)
    r = upload(client, session.pk, "after.jpg", photo_of(s_parth))
    check("FIN2. recognition blocked after finalize (code=session_finalized)",
          r.status_code in (400, 409) and r.data.get("code") == "session_finalized",
          f"{r.status_code} {r.data}")
    r2 = client.post(f"/api/attendance/sessions/{session.pk}/finalize/")
    check("FIN3. second finalize rejected", r2.status_code == 400, r2.status_code)

    n_logs = RecognitionLog.objects.filter(session=session).count()
    n_matched = RecognitionLog.objects.filter(session=session, result=RecognitionLog.Result.MATCHED).count()
    check("LOG. audit log has matched + rejected rows",
          n_logs >= 8 and n_matched >= 5, f"logs={n_logs} matched={n_matched}")

finally:
    deleted = session.pk
    session.delete()
    leftovers = AttendanceRecord.objects.filter(session_id=deleted).count() \
        + RecognitionLog.objects.filter(session_id=deleted).count()
    print(f"cleaned up test session {deleted} (leftover rows: {leftovers})")

print("\n===== SUMMARY =====")
failed = [x for x in RESULTS if not x[0]]
print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
for _, name, detail in failed:
    print("  FAILED:", name, "|", detail)
sys.exit(1 if failed else 0)
