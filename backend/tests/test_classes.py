from django.contrib.auth import get_user_model

from classes.models import Classroom, Division, Subject

from .helpers import make_auth_client
from rest_framework.test import APITestCase

User = get_user_model()


class ClassesTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher1", password="Pass12345")
        self.other = User.objects.create_user(username="teacher2", password="Pass12345")
        self.client_a = make_auth_client(self.teacher)
        self.client_b = make_auth_client(self.other)
        self.classroom_payload = {
            "name": "TE Computer Engineering",
            "code": "TE-CMPN",
            "academic_year": "2026-2027",
            "description": "Third year",
        }

    def test_create_classroom(self):
        response = self.client_a.post("/api/classes/classrooms/", self.classroom_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Classroom.objects.count(), 1)
        self.assertEqual(response.data["teacher"], self.teacher.pk)

    def test_duplicate_classroom_rejected(self):
        self.client_a.post("/api/classes/classrooms/", self.classroom_payload, format="json")
        response = self.client_a.post("/api/classes/classrooms/", self.classroom_payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_classroom_scoped_to_owner(self):
        self.client_a.post("/api/classes/classrooms/", self.classroom_payload, format="json")
        response = self.client_b.get("/api/classes/classrooms/")
        self.assertEqual(response.data.get("count", 0), 0)

    def test_classroom_delete(self):
        classroom = Classroom.objects.create(teacher=self.teacher, name="Class X", academic_year="2026-2027")
        response = self.client_b.delete(f"/api/classes/classrooms/{classroom.pk}/")
        self.assertEqual(response.status_code, 404)
        response = self.client_a.delete(f"/api/classes/classrooms/{classroom.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Classroom.objects.filter(pk=classroom.pk).exists())

    def test_create_division_and_subject(self):
        classroom = Classroom.objects.create(teacher=self.teacher, name="Class X", academic_year="2026-2027")
        response = self.client_a.post(
            "/api/classes/divisions/", {"classroom": classroom.pk, "name": "A"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client_a.post(
            "/api/classes/subjects/",
            {"classroom": classroom.pk, "name": "Artificial Intelligence", "code": "AI"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_division_from_other_classroom_rejected(self):
        classroom_b = Classroom.objects.create(teacher=self.other, name="Other", academic_year="2026-2027")
        response = self.client_a.post(
            "/api/classes/divisions/", {"classroom": classroom_b.pk, "name": "A"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_access_other_classrooms_division(self):
        classroom_other = Classroom.objects.create(teacher=self.other, name="Other", academic_year="2026-2027")
        Division.objects.create(classroom=classroom_other, name="B")
        response = self.client_a.get("/api/classes/divisions/")
        self.assertNotIn("B", response.getvalue().decode())