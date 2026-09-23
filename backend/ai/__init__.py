"""AI package for the Smart Attendance System.

Architecture:
- Pre-trained OpenCV YuNet face detector (ONNX)
- Pre-trained InsightFace/ArcFace embedding model (w600k_r50, ONNX)
- Cosine-similarity matching against enrolled student embeddings

No neural network is trained from scratch in this project.
"""

from .attendance_engine import RecognitionResult, models_ready, recognize_faces  # noqa: F401
from .face_detector import detect_faces, is_available as detector_available  # noqa: F401
from .face_encoder import generate_embedding  # noqa: F401
from .face_matcher import cosine_similarity  # noqa: F401