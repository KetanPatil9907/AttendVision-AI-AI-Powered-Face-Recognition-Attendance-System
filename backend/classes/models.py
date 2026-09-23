from django.conf import settings
from django.db import models


class Classroom(models.Model):
    """A class such as 'TE Computer Engineering' for a given academic year."""

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="classrooms")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)
    academic_year = models.CharField(max_length=20, help_text="e.g. 2026-2027")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "name", "academic_year"],
                name="unique_classroom_teacher_year",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

    @property
    def division_count(self):
        return self.divisions.count()

    @property
    def subject_count(self):
        return self.subjects.count()


class Division(models.Model):
    """A division/batch belonging to a class, e.g. 'A'."""

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="divisions")
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "name"],
                name="unique_classroom_division",
            )
        ]

    def __str__(self):
        return f"{self.classroom.name} - {self.name}"

    @property
    def student_count(self):
        return self.students.count()


class Subject(models.Model):
    """A subject offered in a class, e.g. 'Artificial Intelligence'."""

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "name"],
                name="unique_classroom_subject",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name