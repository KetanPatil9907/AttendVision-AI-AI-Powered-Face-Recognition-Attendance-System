from django.contrib.auth import get_user_model

from classes.models import Classroom, Division
from students.models import Student

from .helpers import make_auth_client
from rest_framework.test import APITestCase

User = get_user_model()


class StudentsTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher1", password="Pass12345")
        self.other = User.objects.create_user(username="teacher2", password="Pass12345")
        self.client_a = make_auth_client(self.teacher)
        self.client_b = make_auth_client(self.other)

        self.classroom = Classroom.objects.create(
            teacher=self.teacher, name="TE Computer", academic_year="2026-2027"
        )
        self.division = Division.objects.create(classroom=self.classroom, name="A")
        self.other_division = Division.objects.create(
            classroom=Classroom.objects.create(teacher=self.other, name="SE Computer", academic_year="2026-2027"),
            name="A",
        )

        self.student_payload = {
            "full_name": "Rahul Patil",
            "roll_number": "01",
            "student_id": "PRN2026001",
            "email": "rahul@college.edu",
            "mobile": "9876500001",
            "gender": "male",
            "division": self.division.pk,
            "academic_year": "2026-2027",
            "status": "active",
        }

    def test_create_student(self):
        response = self.client_a.post("/api/students/", self.student_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Student.objects.filter(roll_number="01").exists())

    def test_create_student_required_fields(self):
        payload = self.student_payload.copy()
        payload.pop("full_name")
        response = self.client_a.post("/api/students/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_roll_number_rejected(self):
        self.client_a.post("/api/students/", self.student_payload, format="json")
        response = self.client_a.post("/api/students/", self.student_payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_student_id_rejected(self):
        self.client_a.post("/api/students/", self.student_payload, format="json")
        payload = self.student_payload.copy()
        payload["roll_number"] = "02"
        response = self.client_a.post("/api/students/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_student_update(self):
        student = Student.objects.create(teacher=self.teacher, division=self.division, **{
            "full_name": "Rahul Patil", "roll_number": "01", "student_id": "PRN1"
        })
        response = self.client_a.patch(f"/api/students/{student.pk}/", {"full_name": "Rahul R Patil"}, format="json")
        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.full_name, "Rahul R Patil")

    def test_student_delete(self):
        student = Student.objects.create(teacher=self.teacher, division=self.division, **{
            "full_name": "Rahul", "roll_number": "01", "student_id": "PRN1"
        })
        response = self.client_a.delete(f"/api/students/{student.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Student.objects.filter(pk=student.pk).exists())

    def test_cannot_access_other_teacher_student(self):
        student = Student.objects.create(teacher=self.other, division=self.other_division, **{
            "full_name": "Other", "roll_number": "01", "student_id": "PRNX"
        })
        response = self.client_a.get(f"/api/students/{student.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_student_list_pagination_and_filter(self):
        for i in range(5):
            Student.objects.create(
                teacher=self.teacher, division=self.division,
                full_name=f"Student {i}", roll_number=f"0{i+1}", student_id=f"P{i}",
            )
        response = self.client_a.get("/api/students/", {"page_size": 3})
        self.assertEqual(response.status_code, 200)

        response = self.client_a.get("/api/students/", {"search": "Student 1"})
        self.assertEqual(response.data["count"], 1)

    def test_student_detail_includes_face_status(self):
        student = Student.objects.create(teacher=self.teacher, division=self.division, **{
            "full_name": "Priya", "roll_number": "02", "student_id": "PRN2"
        })
        response = self.client_a.get(f"/api/students/{student.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["face_registered"])
        self.assertEqual(response.data["photo_count"], 0)

    def test_cannot_create_student_in_other_division(self):
        payload = self.student_payload.copy()
        payload["division"] = self.other_division.pk
        response = self.client_a.post("/api/students/", payload, format="json")
        self.assertEqual(response.status_code, 400)
