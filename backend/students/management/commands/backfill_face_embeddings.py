"""Backfill per-photo face embeddings for photos registered before the
per-photo embedding storage existed.

Recognition matches against every registration photo's own embedding
(StudentFace.embedding). Photos uploaded after that feature already carry
their vector; this command upgrades older photos in place (and refreshes
each affected student's legacy consolidated vector).

Run once after upgrading:

    python manage.py backfill_face_embeddings
"""
from django.core.management.base import BaseCommand

from ai.attendance_engine import models_ready
from ai.config import model_missing_message
from students.models import Student, StudentFace
from students.services import _rebuild_consolidated_embedding


class Command(BaseCommand):
    help = (
        "Compute and store per-photo face embeddings for registration photos "
        "that predate per-photo embedding storage. Use --all to recompute "
        "every photo after a detector/alignment/model change."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            dest="recompute_all",
            help="Recompute embeddings for ALL photos (invalidates stored vectors).",
        )

    def handle(self, *args, **options):
        if not models_ready():
            self.stderr.write(model_missing_message())
            return

        all_photos = StudentFace.objects.all()
        if options["recompute_all"]:
            scope = all_photos
            students = set(all_photos.values_list("student_id", flat=True))
            verb = "Recomputed"
        else:
            scope = all_photos.filter(embedding__isnull=True)
            students = set(scope.values_list("student_id", flat=True))
            verb = "Backfilled"
            if not students:
                self.stdout.write("All registration photos already have embeddings.")
                return

        photos = scope.count()
        # The rebuild embeds every flagged photo of the student and stores the
        # vector on each photo, then refreshes the legacy consolidated mean.
        for student_id in sorted(students):
            _rebuild_consolidated_embedding(
                Student.objects.get(pk=student_id),
                force_reembed=options["recompute_all"],
            )
        remaining = all_photos.filter(embedding__isnull=True).count()
        self.stdout.write(
            f"{verb} embeddings for {photos} photo(s) across "
            f"{len(students)} student(s); {remaining} photo(s) without an "
            f"embedding (no usable face)."
        )
