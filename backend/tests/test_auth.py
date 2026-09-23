from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .helpers import login_client, make_auth_client

User = get_user_model()


class AuthTestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="sir",
            email="sir@college.edu",
            password="SecretPass123",
            first_name="Rakesh",
            last_name="Patil",
            role=User.Role.TEACHER,
        )

    def test_login_with_username(self):
        client, response = login_client("sir", "SecretPass123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "sir")

    def test_login_with_email(self):
        client, response = login_client("sir@college.edu", "SecretPass123")
        self.assertEqual(response.status_code, 200)

    def test_login_case_insensitive_username(self):
        client, response = login_client("SIR", "SecretPass123")
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password(self):
        client, response = login_client("sir", "wrong-password")
        self.assertEqual(response.status_code, 401)

    def test_remember_me_returns_tokens(self):
        response = self.client.post(
            "/api/auth/login",
            {"username": "sir", "password": "SecretPass123", "remember_me": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["remember_me"])

    def test_me_endpoint(self):
        client = make_auth_client(self.teacher)
        response = client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "sir")
        self.assertEqual(response.data["title"], "teacher")

    def test_protected_route_rejects_anonymous(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_profile_update(self):
        client = make_auth_client(self.teacher)
        response = client.patch(
            "/api/auth/profile",
            {"first_name": "Rajesh", "title": "sir", "mobile": "9876543210"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, "Rajesh")

    def test_change_password(self):
        client = make_auth_client(self.teacher)
        response = client.post(
            "/api/auth/change-password",
            {"old_password": "SecretPass123", "new_password": "NewSecret456"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("NewSecret456"))

    def test_change_password_wrong_old(self):
        client = make_auth_client(self.teacher)
        response = client.post(
            "/api/auth/change-password",
            {"old_password": "nope", "new_password": "NewSecret456"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_teacher_registration_admin_only(self):
        client = make_auth_client(self.teacher)
        response = client.post(
            "/api/auth/register-teacher",
            {"username": "madam", "email": "madam@college.edu", "password": "MadamPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        admin = User.objects.create_superuser("admin", "admin@college.edu", "AdminPass123")
        admin_client = make_auth_client(admin)
        response = admin_client.post(
            "/api/auth/register-teacher",
            {"username": "madam", "email": "madam@college.edu", "password": "MadamPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="madam", role=User.Role.TEACHER).exists())

    def test_duplicate_email_rejected(self):
        admin = User.objects.create_superuser("admin", "admin@college.edu", "AdminPass123")
        admin_client = make_auth_client(admin)
        response = admin_client.post(
            "/api/auth/register-teacher",
            {"username": "someone", "email": "SIR@college.edu", "password": "SomeonePass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_blacklists_token(self):
        client = make_auth_client(self.teacher)
        response = client.post("/api/auth/logout", {"refresh": self.teacher_jwt_refresh()}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_forgot_password_sends_link(self):
        response = self.client.post(
            "/api/auth/forgot-password",
            {"email": "sir@college.edu"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("reset link", response.data["message"].lower())

    def test_forgot_password_hides_unknown_email(self):
        response = self.client.post(
            "/api/auth/forgot-password",
            {"email": "ghost@nowhere.com"},
            format="json",
        )
        # Same payload shape so account existence is not leaked.
        self.assertEqual(response.status_code, 200)
        self.assertIn("reset link", response.data["message"].lower())

    def test_reset_password_flow(self):
        self.teacher.email = "sir@college.edu"
        self.teacher.save()
        token = self.teacher.password_reset_token()
        response = self.client.post(
            "/api/auth/reset-password",
            {"email": "sir@college.edu", "token": token, "new_password": "BrandNewPass789"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("BrandNewPass789"))

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            "/api/auth/reset-password",
            {"email": "sir@college.edu", "token": "bad-token", "new_password": "BrandNewPass789"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("SecretPass123"))

    def teacher_jwt_refresh(self):
        client, login = login_client("sir", "SecretPass123")
        return login.data["refresh"]