"""End-to-end workflow test mirroring the real user journey:

Teacher Login -> Add Class -> Add Division -> Add Subject -> Add Student
-> Register Face -> Start Attendance Session -> Recognize -> Mark Present
-> Duplicate Check -> Finalize -> View Report.
"""
import unittest

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from attendance.models import AttendanceRecord, AttendanceSession
from students.models import Student

User = get_user_model()


def models_present():
    import os

    from django.conf import settings

    detector = os.path.join(settings.AI_MODELS_DIR, settings.AI_DETECTOR_MODEL)
    encoder = os.path.join(settings.AI_MODELS_DIR, settings.AI_RECOGNITION_MODEL)
    return os.path.exists(detector) and os.path.exists(encoder)


class FullWorkflowTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="sir", email="sir@college.edu", password="SecretPass123"
        )

    def _login(self):
        response = self.client.post(
            "/api/auth/login", {"username": "sir", "password": "SecretPass123"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_complete_workflow(self):
        self._login()

        # 1. Classroom
        response = self.client.post(
            "/api/classes/classrooms/",
            {"name": "TE Computer Engineering", "academic_year": "2026-2027"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        classroom_id = response.data["id"]

        # 2. Division
        response = self.client.post(
            "/api/classes/divisions/", {"classroom": classroom_id, "name": "A"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        division_id = response.data["id"]

        # 3. Subject
        response = self.client.post(
            "/api/classes/subjects/",
            {"classroom": classroom_id, "name": "Artificial Intelligence"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        subject_id = response.data["id"]

        # 4. Student (two students - only one will have a registered face)
        student_ids = []
        for roll, name, sid in [("01", "Rahul Patil", "PRN1"), ("02", "Priya Sharma", "PRN2")]:
            response = self.client.post(
                "/api/students/",
                {
                    "full_name": name,
                    "roll_number": roll,
                    "student_id": sid,
                    "division": division_id,
                    "academic_year": "2026-2027",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)
            student_ids.append(response.data["id"])

# 5-6. Face registration (real model, only when models are present)
        if models_present():
            from .helpers import photo_upload
            from rest_framework import serializers

            with open(__import__("pathlib").Path(__file__).resolve().parent / "data" / "face_test.jpg", "rb") as fh:
                image = fh.read()
            from django.core.files.uploadedfile import SimpleUploadedFile

            response = self.client.post(
                f"/api/students/{student_ids[0]}/face-registration/",
                {"image": SimpleUploadedFile("face.jpg", image, "image/jpeg")},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200)

        # 7. Start attendance session
        response = self.client.post(
            "/api/attendance/sessions/",
            {
                "classroom": classroom_id,
                "division": division_id,
                "subject": subject_id,
                "date": "2026-09-22",
                "lecture_number": "L1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        session_id = response.data["id"]
        self.assertEqual(AttendanceRecord.objects.filter(session_id=session_id).count(), 2)

        # 8-9. Recognize -> mark present (+duplicate protection)
        if models_present():
            from django.core.files.uploadedfile import SimpleUploadedFile

            with open(__import__("pathlib").Path(__file__).resolve().parent / "data" / "face_test.jpg", "rb") as fh:
                image = fh.read()
            for _ in range(2):
                response = self.client.post(
                    f"/api/attendance/sessions/{session_id}/recognize/",
                    {"image": SimpleUploadedFile("frame.jpg", image, "image/jpeg")},
                    format="multipart",
                )
                self.assertEqual(response.status_code, 200)

            self.assertEqual(
                AttendanceRecord.objects.filter(session_id=session_id, student_id=student_ids[0]).count(),
                1,
            )
            present = AttendanceRecord.objects.get(session_id=session_id, student_id=student_ids[0])
            self.assertEqual(present.status, "present")
            manual_records = AttendanceRecord.objects.filter(session_id=session_id, student_id=student_ids[1])
            self.assertEqual(manual_records.first().status, "absent")

        # 10-11. Finalize
        response = self.client.post(f"/api/attendance/sessions/{session_id}/finalize/")
        self.assertEqual(response.status_code, 200)
        session = AttendanceSession.objects.get(pk=session_id)
        self.assertEqual(session.status, "finalized")

        # 12. Reporting + history
        response = self.client.get(
            "/api/attendance/history", {"date_from": "2026-09-20", "date_to": "2026-09-30"}
        )
        self.assertEqual(response.status_code, 200)
        row = response.data["sessions"][0]
        self.assertEqual(row["classroom"], "TE Computer Engineering")
        self.assertEqual(row["division"], "A")
        self.assertEqual(row["subject"], "Artificial Intelligence")

        export = self.client.get(
            "/api/reports/export",
            {"type": "all", "format": "pdf", "date_from": "2026-09-01", "date_to": "2026-09-30"},
        )
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export.content.startswith(b"%PDF"))

