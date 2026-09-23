"""Attendance workflow tests: session creation, recognition, duplicates,
finalization and manual correction. Recognition tests use the real models.
"""
import unittest

from django.contrib.auth import get_user_model

from classes.models import Classroom, Division, Subject
from students.models import Student

from .helpers import make_auth_client, photo_upload
from rest_framework.test import APITestCase

from attendance.models import AttendanceRecord, AttendanceSession

User = get_user_model()


def models_present():
    import os

    from django.conf import settings

    detector = os.path.join(settings.AI_MODELS_DIR, settings.AI_DETECTOR_MODEL)
    encoder = os.path.join(settings.AI_MODELS_DIR, settings.AI_RECOGNITION_MODEL)
    return os.path.exists(detector) and os.path.exists(encoder)


def _lena_bytes():
    from pathlib import Path

    return Path(__file__).resolve().parent / "data" / "face_test.jpg"


class AttendanceTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.have_models = models_present()

    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher1", password="Pass12345")
        self.client_a = make_auth_client(self.teacher)
        self.classroom = Classroom.objects.create(teacher=self.teacher, name="TE", academic_year="2026-2027")
        self.division = Division.objects.create(classroom=self.classroom, name="A")
        self.subject = Subject.objects.create(classroom=self.classroom, name="Artificial Intelligence")

        self.s1 = Student.objects.create(
            teacher=self.teacher, division=self.division,
            full_name="Rahul Patil", roll_number="01", student_id="PRN1",
        )
        self.s2 = Student.objects.create(
            teacher=self.teacher, division=self.division,
            full_name="Priya Sharma", roll_number="02", student_id="PRN2",
        )
        self.session_payload = {
            "classroom": self.classroom.pk,
            "division": self.division.pk,
            "subject": self.subject.pk,
            "date": "2026-09-22",
            "lecture_number": "L1",
        }

    def _create_session(self):
        response = self.client_a.post("/api/attendance/sessions/", self.session_payload, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def test_create_session_creates_present_records_for_all_students(self):
        session_id = self._create_session()
        self.assertEqual(AttendanceRecord.objects.filter(session_id=session_id).count(), 2)
        self.assertEqual(
            AttendanceRecord.objects.filter(session_id=session_id, status="absent").count(), 2
        )

    def test_session_validation_invalid_division(self):
        payload = self.session_payload.copy()
        other = Division.objects.create(
            classroom=Classroom.objects.create(teacher=self.teacher, name="SE", academic_year="2026-2027"),
            name="A",
        )
        payload["division"] = other.pk
        response = self.client_a.post("/api/attendance/sessions/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_session_rejected_by_unique_constraint(self):
        self._create_session()
        response = self.client_a.post("/api/attendance/sessions/", self.session_payload, format="json")
        self.assertEqual(response.status_code, 400)

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_recognition_matches_registered_student(self):
        # Register the face first.
        response = self.client_a.post(
            f"/api/students/{self.s1.pk}/face-registration/",
            {"image": photo_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)

        session_id = self._create_session()
        response = self.client_a.post(
            f"/api/attendance/sessions/{session_id}/recognize/",
            {"image": photo_upload(name="frame.jpg")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertGreaterEqual(data["detected"], 1)
        matched = [d for d in data["detections"] if d["matched"]]
        self.assertGreaterEqual(len(matched), 1)
        self.assertEqual(matched[0]["student_id"], self.s1.pk)
        self.assertEqual(matched[0]["student_name"], "Rahul Patil")

        # Attendance marked present once.
        record = AttendanceRecord.objects.get(session_id=session_id, student_id=self.s1.pk)
        self.assertEqual(record.status, "present")
        self.assertTrue(record.marked_by_ai)
        self.assertGreater(record.confidence, 0.5)

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_duplicate_recognition_does_not_create_duplicate_record(self):
        self.client_a.post(
            f"/api/students/{self.s1.pk}/face-registration/",
            {"image": photo_upload()},
            format="multipart",
        )
        session_id = self._create_session()

        for _ in range(3):
            response = self.client_a.post(
                f"/api/attendance/sessions/{session_id}/recognize/",
                {"image": photo_upload(name="frame.jpg")},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200)

        records = AttendanceRecord.objects.filter(session_id=session_id, student_id=self.s1.pk)
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().status, "present")

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_recognition_logs_written(self):
        from attendance.models import RecognitionLog

        self.client_a.post(
            f"/api/students/{self.s1.pk}/face-registration/",
            {"image": photo_upload()},
            format="multipart",
        )
        session_id = self._create_session()
        self.client_a.post(
            f"/api/attendance/sessions/{session_id}/recognize/",
            {"image": photo_upload(name="frame.jpg")},
            format="multipart",
        )
        self.assertTrue(RecognitionLog.objects.filter(session_id=session_id).exists())

    def test_finalize_session(self):
        session_id = self._create_session()
        response = self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        self.assertEqual(response.status_code, 200)
        session = AttendanceSession.objects.get(pk=session_id)
        self.assertEqual(session.status, AttendanceSession.Status.FINALIZED)
        self.assertIsNotNone(session.finalized_at)

    def test_cannot_finalize_twice(self):
        session_id = self._create_session()
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        self.assertEqual(response.status_code, 400)

    def test_cannot_recognize_after_finalization(self):
        session_id = self._create_session()
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.post(
            f"/api/attendance/sessions/{session_id}/recognize/",
            {"image": photo_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("finalized", response.data["message"].lower())

    def test_manual_record_update(self):
        session_id = self._create_session()
        record = AttendanceRecord.objects.get(session_id=session_id, student_id=self.s1.pk)
        response = self.client_a.post(
            f"/api/attendance/sessions/{session_id}/update-records/",
            {"updates": [{"id": record.pk, "status": "present"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.status, "present")
        self.assertTrue(record.manually_updated)

    def test_cannot_edit_finalized_session(self):
        session_id = self._create_session()
        record = AttendanceRecord.objects.get(session_id=session_id, student_id=self.s1.pk)
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.post(
            f"/api/attendance/sessions/{session_id}/update-records/",
            {"updates": [{"id": record.pk, "status": "present"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_history_endpoint(self):
        session_id = self._create_session()
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.get(
            "/api/attendance/history", {"date_from": "2026-09-20", "date_to": "2026-09-24"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["sessions"]), 1)
        session_row = response.data["sessions"][0]
        self.assertEqual(session_row["total"], 2)
        self.assertEqual(session_row["present"], 0)
        self.assertEqual(session_row["absent"], 2)

    def test_student_summary_endpoint(self):
        session_id = self._create_session()
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.get(f"/api/attendance/summary/{self.s1.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["total_lectures"], 1)
        self.assertEqual(response.data["summary"]["present"], 0)

    def test_dashboard_statistics(self):
        session_id = self._create_session()
        self.client_a.post(f"/api/attendance/sessions/{session_id}/finalize/")
        response = self.client_a.get("/api/dashboard/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counts"]["students"], 2)
        self.assertEqual(response.data["counts"]["classes"], 1)
        self.assertEqual(response.data["counts"]["subjects"], 1)

    def test_build_gallery_prefers_per_photo_embeddings_with_fallback(self):
        """Section 7: one gallery entry per photo; legacy students still work."""
        from attendance.models import AttendanceSession
        from attendance.services import build_gallery
        from students.models import FaceEmbedding, StudentFace

        session = AttendanceSession.objects.create(
            teacher=self.teacher, classroom=self.classroom, division=self.division,
            subject=self.subject, date="2026-09-22", lecture_number="LG1",
        )
        try:
            # Legacy student: only a consolidated vector -> single entry.
            legacy = Student.objects.create(
                teacher=self.teacher, division=self.division,
                full_name="Legacy Student", roll_number="98", student_id="PRN98",
            )
            FaceEmbedding.objects.create(student=legacy, embedding=[1.0] + [0.0] * 511)

            # Modern student: two photos, each with its own vector.
            modern = Student.objects.create(
                teacher=self.teacher, division=self.division,
                full_name="Modern Student", roll_number="99", student_id="PRN99",
            )
            StudentFace.objects.create(
                student=modern, image="student_faces/a.jpg",
                embedding=[0.0, 1.0] + [0.0] * 510, embedding_generated=True,
            )
            StudentFace.objects.create(
                student=modern, image="student_faces/b.jpg",
                embedding=[0.0, 0.0, 1.0] + [0.0] * 509, embedding_generated=True,
            )

            gallery, students = build_gallery(session)
            by_student = {}
            for entry in gallery:
                by_student.setdefault(entry["student_id"], []).append(entry["embedding"])
            # setUp() already added two faceless students to this division -
            # they appear in the roster but contribute no gallery entries.
            self.assertEqual(len(students), 4)
            self.assertEqual(set(by_student), {legacy.pk, modern.pk})
            self.assertEqual(len(by_student[legacy.pk]), 1)  # consolidated fallback
            self.assertEqual(len(by_student[modern.pk]), 2)  # per-photo vectors
        finally:
            session.delete()


class FaceMatcherUnitTestCase(APITestCase):
    """Pure unit tests for similarity/threshold logic (no models needed)."""

    def test_cosine_similarity_identical(self):
        from ai.face_matcher import cosine_similarity

        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_cosine_similarity_perpendicular(self):
        from ai.face_matcher import cosine_similarity

        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_best_match_above_threshold(self):
        import numpy as np

        from ai.face_matcher import best_match

        gallery = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        idx, score = best_match([0.0, 1.0, 0.0], gallery, threshold=0.5)
        self.assertEqual(idx, 1)
        self.assertAlmostEqual(score, 1.0)

    def test_best_match_below_threshold_returns_none(self):
        import numpy as np

        from ai.face_matcher import best_match

        gallery = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        idx, score = best_match([0.707, 0.707, 0.0], gallery, threshold=0.85)
        self.assertIsNone(idx)

    def test_best_match_groups_embeddings_per_student(self):
        """Multiple photos of one student are ONE identity for the margin rule.

        Student 1 has two photos that both strongly resemble the probe;
        student 2 does not. The runner-up must be student 2 - not student 1's
        own second photo - so the genuine match is never margin-rejected.
        """
        from ai.face_matcher import best_match

        gallery = [
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [1.0, 0.0, 0.0]},                      # sim 1.00
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [0.90, 0.43588989, 0.0]},              # sim 0.90 (same student!)
            {"student_id": 2, "name": "B", "roll_number": "02",
             "embedding": [0.0, 1.0, 0.0]},                      # sim 0.00
        ]
        # Flat matching would see a 0.10 gap (1.00 vs 0.90) and margin-reject;
        # grouped matching sees 1.00 vs 0.00 and matches student 1.
        idx, score = best_match([1.0, 0.0, 0.0], gallery, threshold=0.70, margin=0.15)
        self.assertEqual(idx, 0)
        self.assertAlmostEqual(score, 1.0, places=6)
        # The winning gallery entry belongs to the best-scoring photo of student 1.
        self.assertEqual(gallery[idx]["student_id"], 1)

    def test_best_match_margin_rejects_close_rival_student(self):
        """A rival student inside the margin still yields ambiguous (None)."""
        from ai.face_matcher import best_match

        # probe = [1, 0], so each similarity is simply the entry's x-component.
        gallery = [
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [0.75, 0.66143783]},   # student 1, sim 0.75
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [0.74, 0.67260688]},   # same student's 2nd photo, sim 0.74
            {"student_id": 2, "name": "B", "roll_number": "02",
             "embedding": [0.72, 0.69392038]},   # rival student, sim 0.72
        ]
        idx, score = best_match([1.0, 0.0], gallery, threshold=0.70, margin=0.15)
        # Student 1 best = 0.75, rival = 0.72 -> gap 0.03 < 0.15 -> ambiguous.
        self.assertIsNone(idx)
        # similarity >= threshold proves it was the margin rule, not low confidence.
        self.assertAlmostEqual(score, 0.75, places=6)

    def test_best_match_single_student_margin_skipped(self):
        """A one-student gallery never margin-rejects (its own photos aren't rivals)."""
        from ai.face_matcher import best_match

        gallery = [
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [1.0, 0.0, 0.0]},
            {"student_id": 1, "name": "A", "roll_number": "01",
             "embedding": [0.0, 1.0, 0.0]},
        ]
        idx, score = best_match([1.0, 0.0, 0.0], gallery, threshold=0.70, margin=0.15)
        self.assertEqual(idx, 0)
        self.assertAlmostEqual(score, 1.0, places=6)

    def test_assess_face_quality_gates(self):
        """The LOW_QUALITY gate rejects tiny / weak / blurry faces only."""
        import numpy as np

        from ai.preprocessing import assess_face_quality

        # A sharp, large, confidently-detected face passes.
        sharp = np.random.default_rng(0).integers(0, 255, (300, 300, 3), dtype=np.uint8)
        ok, metrics, issues = assess_face_quality(
            sharp, {"bbox": (50, 50, 200, 220), "score": 0.95}
        )
        self.assertTrue(ok, issues)
        self.assertEqual(metrics["width"], 200)
        self.assertGreater(metrics["sharpness"], 20)

        # Too small (below RECOGNITION_MIN_FACE_PX) -> rejected.
        ok, _m, issues = assess_face_quality(sharp, {"bbox": (0, 0, 30, 35), "score": 0.95})
        self.assertFalse(ok)
        self.assertTrue(any("too small" in i for i in issues), issues)

        # Weak detector score -> rejected.
        ok, _m, issues = assess_face_quality(sharp, {"bbox": (50, 50, 200, 220), "score": 0.2})
        self.assertFalse(ok)
        self.assertTrue(any("weak detection" in i for i in issues), issues)

        # Untextured / blurred face region (zero Laplacian variance) -> rejected.
        flat = np.full((300, 300, 3), 128, dtype=np.uint8)
        ok, _m, issues = assess_face_quality(flat, {"bbox": (50, 50, 200, 220), "score": 0.95})
        self.assertFalse(ok)
        self.assertTrue(any("blurry" in i for i in issues), issues)

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_recognition_reports_low_quality_instead_of_dropping(self):
        """Failing faces must APPEAR in the results as LOW_QUALITY (section 4)."""
        from ai.attendance_engine import recognize_faces

        bytes_data = _lena_bytes().read_bytes()
        gallery = [{"student_id": 1, "name": "X", "roll_number": "01",
                    "embedding": [1.0] + [0.0] * 511}]
        # Caller ratio gate of 0.99 forces EVERY face through the quality gate.
        results, err = recognize_faces(
            bytes_data, gallery, threshold=0.5, min_face_ratio=0.99
        )
        self.assertIsNone(err)
        self.assertTrue(results, "detected face must not be silently dropped")
        for res in results:
            data = res.as_dict()
            self.assertEqual(data["status"], "LOW_QUALITY")
            self.assertTrue(data["low_quality"])
            self.assertFalse(data["matched"])
            self.assertTrue(data["quality_issues"])
            self.assertIsNotNone(data["face_index"])
            self.assertGreater(data["face_width"], 0)

    def test_readiness_report(self):
        from ai.attendance_engine import models_ready

        # Just confirm this returns a bool without exploding.
        self.assertIsInstance(models_ready(), bool)

