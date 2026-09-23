"""Quick smoke test of the AI pipeline using a synthetic face-like image."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

import cv2
import numpy as np

from ai.face_detector import detect_faces
from ai.face_encoder import generate_embedding
from ai.preprocessing import align_face
from ai.face_matcher import cosine_similarity

# Synthetic image: a bright ellipse on dark background (approximates a face).
img = np.zeros((300, 300, 3), dtype=np.uint8)
cv2.ellipse(img, (150, 150), (70, 95), 0, 0, 360, (205, 205, 205), -1)
cv2.circle(img, (130, 120), 12, (0, 0, 0), -1)
cv2.circle(img, (170, 120), 12, (0, 0, 0), -1)
cv2.ellipse(img, (150, 185), (28, 14), 0, 0, 180, (60, 60, 60), -1)

faces = detect_faces(img)
print("detected faces:", len(faces))
if not faces:
    print("No face found on synthetic image - detector may need a real photo.")
    sys.exit(1)

aligned = align_face(img, faces[0]["kps"])
emb1 = generate_embedding(aligned)
print("embedding dim:", emb1.shape, "norm:", round(float(np.linalg.norm(emb1)), 4))

# Distort slightly, realign, re-embed - similarity should remain high.
shifted = np.roll(img, 3, axis=1)
faces2 = detect_faces(shifted)
aligned2 = align_face(shifted, faces2[0]["kps"])
emb2 = generate_embedding(aligned2)
print("cosine similarity (same-ish image):", round(cosine_similarity(emb1, emb2), 4))

noise = np.random.default_rng(0).normal(size=emb1.shape).astype(np.float64)
noise = noise / np.linalg.norm(noise)
print("cosine similarity (random):", round(cosine_similarity(emb1, noise), 4))

print("AI PIPELINE OK")