from datetime import date

from django.conf import settings
from django.db import models


class AttendanceSession(models.Model):
    """An attendance session for a class/division/subject on a date."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        FINALIZED = "finalized", "Finalized"

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_sessions")
    classroom = models.ForeignKey("classes.Classroom", on_delete=models.CASCADE, related_name="attendance_sessions")
    division = models.ForeignKey("classes.Division", on_delete=models.CASCADE, related_name="attendance_sessions")
    subject = models.ForeignKey("classes.Subject", on_delete=models.CASCADE, related_name="attendance_sessions")
    date = models.DateField(default=date.today)
    lecture_number = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "division", "subject", "date", "lecture_number"],
                name="unique_attendance_session",
            )
        ]

    def __str__(self):
        return f"{self.classroom.name} {self.division.name} {self.subject.name} {self.date}"


class AttendanceRecord(models.Model):
    """One student's attendance status for a session.

    The unique constraint (session, student) is the backend-level duplicate
    prevention: a student can only ever have a single record per session.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABSENT)
    confidence = models.FloatField(default=0.0)
    marked_by_ai = models.BooleanField(default=False)
    manually_updated = models.BooleanField(default=False)
    recognized_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student__roll_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"], name="unique_record_per_session"
            )
        ]
        indexes = [
            models.Index(fields=["session", "student"]),
            models.Index(fields=["session", "status"]),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.status}"


class RecognitionLog(models.Model):
    """Debug/audit log of every AI recognition attempt during a session."""

    class Result(models.TextChoices):
        MATCHED = "MATCHED", "Matched"
        UNKNOWN = "UNKNOWN", "Unknown"
        REJECTED = "REJECTED", "Rejected"

    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="recognition_logs", null=True, blank=True
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.SET_NULL, related_name="recognition_logs", null=True, blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    confidence = models.FloatField(default=0.0)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.UNKNOWN)
    message = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to=settings.RECOGNITION_LOG_IMAGE_DIR, blank=True, null=True, validators=[]
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["session", "timestamp"])]

    def __str__(self):
        return f"{self.timestamp} {self.result} {self.confidence:.2f}"