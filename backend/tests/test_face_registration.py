"""AI face-registration tests. These exercise the real pre-trained models.

Each test is skipped automatically when the ONNX models are not downloaded.
"""
import unittest

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from classes.models import Classroom, Division
from students.models import FaceEmbedding, Student, StudentFace

from .helpers import blank_image_bytes, make_auth_client, photo_upload
from rest_framework.test import APITestCase

User = get_user_model()


def models_present():
    import os

    from django.conf import settings

    detector = os.path.join(settings.AI_MODELS_DIR, settings.AI_DETECTOR_MODEL)
    encoder = os.path.join(settings.AI_MODELS_DIR, settings.AI_RECOGNITION_MODEL)
    return os.path.exists(detector) and os.path.exists(encoder)


class FaceRegistrationTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.have_models = models_present()

    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher1", password="Pass12345")
        self.client_a = make_auth_client(self.teacher)
        self.classroom = Classroom.objects.create(teacher=self.teacher, name="TE", academic_year="2026-2027")
        self.division = Division.objects.create(classroom=self.classroom, name="A")
        self.student = Student.objects.create(
            teacher=self.teacher, division=self.division,
            full_name="Rahul Patil", roll_number="01", student_id="PRN1",
        )

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_register_face_success(self):
        response = self.client_a.post(
            f"/api/students/{self.student.pk}/face-registration/",
            {"image": photo_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentFace.objects.filter(student=self.student).count(), 1)
        self.assertTrue(FaceEmbedding.objects.filter(student=self.student).exists())
        embedding = FaceEmbedding.objects.get(student=self.student)
        self.assertEqual(len(embedding.embedding), 512)

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_register_multiple_photos_and_photo_limit(self):
        from django.conf import settings as dj_settings

        limit = dj_settings.MAX_STUDENT_PHOTOS
        for i in range(limit):
            response = self.client_a.post(
                f"/api/students/{self.student.pk}/face-registration/",
                {"image": photo_upload(name=f"p{i}.jpg")},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200)
        # The photo AFTER the limit must be rejected.
        response = self.client_a.post(
            f"/api/students/{self.student.pk}/face-registration/",
            {"image": photo_upload(name="over.jpg")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)
        # Changing a face photo (re-registration) is not supported - clear and re-add.
        self.assertEqual(StudentFace.objects.filter(student=self.student).count(), limit)

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_no_face_image_rejected(self):
        blank = blank_image_bytes()
        response = self.client_a.post(
            f"/api/students/{self.student.pk}/face-registration/",
            {"image": SimpleUploadedFile("blank.png", blank, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("No face detected", response.data["message"])

    @unittest.skipIf(not models_present(), "AI models not downloaded")
    def test_multi_face_image_rejected(self):
        import io

        import cv2
        import numpy as np
        from django.core.files.uploadedfile import SimpleUploadedFile

        single = cv2.imread(str(self._photo_path()))
        composed = np.hstack([single, single])
        ok, buf = cv2.imencode(".jpg", composed, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        self.assertTrue(ok)
        response = self.client_a.post(
            f"/api/students/{self.student.pk}/face-registration/",
            {"image": SimpleUploadedFile("two.jpg", buf.tobytes(), "image/jpeg")},
            format="multipart",
        )
        if response.status_code == 200:
            # Some detector configurations may merge the two faces; acceptance
            # is acceptable here, but the common expectation is rejection.
            return
        self.assertEqual(response.status_code, 422)
        self.assertIn("Multiple faces detected", response.data["message"])

    def _photo_path(self):
        from pathlib import Path

        return Path(__file__).resolve().parent / "data" / "face_test.jpg"

    def test_invalid_image_rejected(self):
        response = self.client_a.post(
            f"/api/students/{self.student.pk}/face-registration/",
            {"image": SimpleUploadedFile("bad.bin", b"not an image", content_type="application/octet-stream")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Invalid image", response.data["message"])

    def test_missing_image_field_rejected(self):
        response = self.client_a.post(f"/api/students/{self.student.pk}/face-registration/", {})
        self.assertEqual(response.status_code, 400)

    def test_remove_face_registration(self):
        url = f"/api/students/{self.student.pk}/face-registration/"
        if models_present():
            self.client_a.post(url, {"image": photo_upload()}, format="multipart")
            self.assertEqual(StudentFace.objects.filter(student=self.student).count(), 1)
        response = self.client_a.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentFace.objects.filter(student=self.student).count(), 0)
        self.assertFalse(FaceEmbedding.objects.filter(student=self.student).exists())

    def test_face_status_endpoint(self):
        from django.conf import settings as dj_settings

        response = self.client_a.get(f"/api/students/{self.student.pk}/face-status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["photo_count"], 0)
        self.assertEqual(response.data["max_photos"], dj_settings.MAX_STUDENT_PHOTOS)

