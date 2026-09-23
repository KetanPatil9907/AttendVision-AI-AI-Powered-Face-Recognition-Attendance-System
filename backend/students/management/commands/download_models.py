"""Download the pre-trained AI models required for face recognition.

Usage:
    python manage.py download_models
"""
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand

SCRIPT = Path(__file__).resolve().parent.parent.parent.parent.parent / "scripts" / "download_models.py"


class Command(BaseCommand):
    help = "Download the YuNet + ArcFace ONNX models used by the AI pipeline."

    def handle(self, *args, **options):
        if not SCRIPT.exists():
            self.stderr.write(self.style.ERROR(f"Missing script: {SCRIPT}"))
            return
        self.stdout.write(f"Running {SCRIPT} ...")
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=SCRIPT.parent.parent)
        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("Models downloaded."))
        else:
            self.stderr.write(self.style.ERROR("Model download failed. See output above."))