"""Real-photo smoke test of the AI pipeline (requires downloaded models)."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

import cv2
import numpy as np

from ai.attendance_engine import recognize_faces
from ai.face_detector import detect_faces
from ai.face_encoder import generate_embedding
from ai.preprocessing import align_face

PHOTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "data", "face_test.jpg")
PHOTO = os.path.abspath(PHOTO)

image = cv2.imread(PHOTO)
print("loaded:", image is not None, PHOTO)

faces = detect_faces(image)
print("detected faces:", len(faces))
for f in faces:
    x, y, w, h = [int(v) for v in f["bbox"]]
    print("  bbox:", (x, y, w, h), "score:", round(f["score"], 3))
    aligned = align_face(image, f["kps"])
    emb = generate_embedding(aligned)
    print("  embedding dim:", emb.shape[0], "norm:", round(float(np.linalg.norm(emb)), 4))

# Full engine path with gallery
data = open(PHOTO, "rb").read()
results, err = recognize_faces(data, [{"student_id": 1, "name": "Test", "roll_number": "01", "embedding": [0.0] * 512}], threshold=0.35)
print("engine results:", len(results) if results else err)
if results:
    print("engine detections:", [r.as_dict()["status"] for r in results])