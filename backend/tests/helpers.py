"""Shared test helpers."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient


def photo_upload(name="photo.jpg", content_type="image/jpeg"):
    """Yields a SimpleUploadedFile from the bundled face test image."""
    from pathlib import Path

    path = Path(__file__).resolve().parent / "data" / "face_test.jpg"
    return SimpleUploadedFile(name, path.read_bytes(), content_type=content_type)


def blank_image_bytes(width=200, height=200):
    """PNG bytes of a uniform (face-less) image."""
    import struct
    import zlib

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    raw = b""
    row = b"\x00" + b"\x64\x64\x64" * width
    for _ in range(height):
        raw += row
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw))
    png += chunk(b"IEND", b"")
    return png


def make_auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def login_client(username, password):
    client = APIClient()
    response = client.post("/api/auth/login", {"username": username, "password": password}, format="json")
    return client, response