"""Create a teacher account from the command line.

Usage:
    python manage.py create_teacher --username janedoe --email janedoe@college.edu \
        --password secret123 --first-name Jane --last-name Doe --title madam
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a teacher account for the Smart Attendance System."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument("--title", default="teacher", choices=["sir", "madam", "teacher"])

    def handle(self, *args, **options):
        username = options["username"]
        if User.objects.filter(username__iexact=username).exists():
            self.stderr.write(self.style.ERROR(f"Username '{username}' already exists."))
            return
        user = User(
            username=username,
            email=options["email"].strip().lower(),
            first_name=options["first_name"],
            last_name=options["last_name"],
            title=options["title"],
            role=User.Role.TEACHER,
        )
        user.set_password(options["password"])
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Teacher '{username}' created successfully."))