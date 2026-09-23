from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Student(models.Model):
    """A registered student belonging to a teacher's division."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        TRANSFERRED = "transferred", "Transferred"

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="students")
    division = models.ForeignKey(
        "classes.Division", on_delete=models.CASCADE, related_name="students"
    )
    full_name = models.CharField(max_length=150)
    roll_number = models.CharField(max_length=20)
    student_id = models.CharField("Student ID / PRN", max_length=50)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    date_of_birth = models.DateField(null=True, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["roll_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "student_id"], name="unique_student_id_per_teacher"
            ),
            models.UniqueConstraint(
                fields=["teacher", "division", "roll_number"], name="unique_roll_per_division"
            ),
        ]
        indexes = [
            models.Index(fields=["teacher", "division"]),
            models.Index(fields=["full_name"]),
        ]

    def clean(self):
        self.roll_number = self.roll_number.strip()
        self.student_id = self.student_id.strip()
        if self.email:
            self.email = self.email.strip().lower()

    def __str__(self):
        return self.full_name

    @property
    def face_registered(self):
        return hasattr(self, "face_embedding")

    @property
    def photo_count(self):
        return self.faces.count()


def _validate_image_size(file):
    if file.size > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image too large (max {settings.MAX_IMAGE_SIZE_MB} MB).")


class StudentFace(models.Model):
    """A stored registration photo for a student.

    Up to settings.MAX_STUDENT_PHOTOS photos per student (3-5 varied shots
    recommended). Each photo carries its OWN normalized 512-d embedding, so
    recognition can compare a probe against every photo of a student and
    keep the strongest similarity.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="faces")
    image = models.ImageField(upload_to=settings.STUDENT_PHOTO_DIR, validators=[_validate_image_size])
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Normalized 512-d ArcFace embedding for THIS photo (null for photos registered before per-photo embeddings existed).",
    )
    embedding_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.student.full_name} face {self.pk}"


class FaceEmbedding(models.Model):
    """One consolidated (legacy) normalized embedding per student.

    Computed as the mean (then re-normalized) of the per-photo embeddings.
    Matching uses StudentFace.embedding (one vector per photo) when
    available; this consolidated vector remains as the fallback for photos
    registered before per-photo embeddings existed, and backs the
    `face_registered` API flag. Stores only the compact vector - enough for
    matching, keeps biometric data minimal.
    """

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="face_embedding")
    embedding = models.JSONField(help_text="Normalized 512-d ArcFace embedding.")
    model_name = models.CharField(max_length=50, default="arcface-w600k-r50")
    photo_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Embedding for {self.student.full_name}"