from django.contrib.auth.models import AbstractUser
from django.contrib.auth.tokens import default_token_generator
from django.db import models


class User(AbstractUser):
    """Teacher / admin account. Teachers may optionally provide a title
    (used for the 'Sir' / 'Madam' greeting labels)."""

    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        ADMIN = "admin", "Admin"

    TITLE_CHOICES = [
        ("sir", "Sir"),
        ("madam", "Madam"),
        ("teacher", "Teacher"),
    ]

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TEACHER)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, default="teacher")
    mobile = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_joined"]

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def password_reset_token(self):
        """Short-lived signed token for resetting the password without a login."""
        return default_token_generator.make_token(self)

    def is_password_reset_token_valid(self, token):
        return default_token_generator.check_token(self, token)

    def __str__(self):
        return f"{self.full_name} ({self.role})"