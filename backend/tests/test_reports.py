"""Report export tests (PDF / Excel / CSV)."""
from django.contrib.auth import get_user_model

from classes.models import Classroom, Division, Subject
from students.models import Student

from .helpers import make_auth_client
from rest_framework.test import APITestCase

from attendance.models import AttendanceRecord, AttendanceSession

User = get_user_model()


class ReportsTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher1", password="Pass12345")
        self.client = make_auth_client(self.teacher)
        classroom = Classroom.objects.create(teacher=self.teacher, name="TE Computer", academic_year="2026-2027")
        division = Division.objects.create(classroom=classroom, name="A")
        subject = Subject.objects.create(classroom=classroom, name="AI")
        s = Student.objects.create(
            teacher=self.teacher, division=division,
            full_name="Rahul", roll_number="01", student_id="PRN1",
        )
        session = AttendanceSession.objects.create(
            teacher=self.teacher, classroom=classroom, division=division, subject=subject,
            date="2026-09-22", status=AttendanceSession.Status.FINALIZED,
        )
        AttendanceRecord.objects.create(session=session, student=s, status="present")

    def _export(self, report_type, fmt):
        return self.client.get(
            "/api/reports/export",
            {"type": report_type, "format": fmt, "date_from": "2026-09-01", "date_to": "2026-09-30"},
        )

    def test_pdf_export(self):
        response = self._export("all", "pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_csv_export(self):
        response = self._export("all", "csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(b"Date,Class", response.content[:200])

    def test_xlsx_export(self):
        response = self._export("all", "xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))

    def test_daily_export(self):
        response = self._export("daily", "csv")
        self.assertEqual(response.status_code, 200)

    def test_student_export(self):
        response = self._export("student", "xlsx")
        self.assertEqual(response.status_code, 200)

    def test_class_export(self):
        response = self._export("class", "pdf")
        self.assertEqual(response.status_code, 200)

    def test_invalid_format_rejected(self):
        response = self._export("all", "doc")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_rejected(self):
        from rest_framework.test import APIClient

        response = APIClient().get("/api/reports/export")
        self.assertEqual(response.status_code, 401)