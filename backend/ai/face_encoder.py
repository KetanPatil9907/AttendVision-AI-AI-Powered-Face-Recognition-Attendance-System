"""Face embedding generation using InsightFace ArcFace (w600k_r50, ONNX).

A pre-trained ArcFace network converts a 112x112 aligned face into a
512-dimensional embedding. Embeddings are L2-normalised so that cosine
similarity can be computed as a plain dot product. The model is only run in
inference mode - it is never fine-tuned or trained on student data.
"""
import logging
import os
import threading

import numpy as np
import onnxruntime as ort

from .config import EMBEDDING_DIM, RECOGNITION_MODEL_PATH, model_missing_message
from .preprocessing import preprocess_for_recognition

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_session = None


def _ensure_session():
    global _session
    with _lock:
        if _session is not None:
            return _session
        if not os.path.exists(RECOGNITION_MODEL_PATH):
            raise FileNotFoundError(model_missing_message())
        try:
            providers = ["CPUExecutionProvider"]
            _session = ort.InferenceSession(RECOGNITION_MODEL_PATH, providers=providers)
            logger.info("ArcFace recognition model loaded from %s", RECOGNITION_MODEL_PATH)
        except Exception as exc:
            logger.exception("Failed to load ArcFace model")
            raise RuntimeError(f"Could not load the face recognition model: {exc}") from exc
        return _session


def is_available():
    return os.path.exists(RECOGNITION_MODEL_PATH)


def generate_embedding(aligned_112):
    """Generate a normalized 512-d embedding from an aligned 112x112 face."""
    session = _ensure_session()
    tensor = preprocess_for_recognition(aligned_112)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    embedding = session.run([output_name], {input_name: tensor})[0]
    embedding = np.asarray(embedding).reshape(-1).astype(np.float64)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    if embedding.shape[0] != EMBEDDING_DIM:
        raise ValueError(
            f"Unexpected embedding dimension {embedding.shape[0]} (expected {EMBEDDING_DIM})."
        )
    return embedding