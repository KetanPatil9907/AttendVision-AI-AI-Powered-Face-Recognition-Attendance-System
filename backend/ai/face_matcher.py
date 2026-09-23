"""Matching of face embeddings using cosine similarity.

ArcFace embeddings are L2-normalised, so cosine similarity equals the dot
product of two normalized vectors.

Two gates decide whether a probe matches an enrolled student:
  * RECOGNITION_THRESHOLD - the absolute similarity the best student must
    reach (measured on this gallery: enrolled students score 0.85-1.00 -
    same photo ~1.00, a different photo of the same student >= 0.85 - while
    unenrolled faces score 0.03-0.16, so 0.70 separates them with margin).
  * RECOGNITION_MARGIN - the best student must also beat the runner-up
    student by this much. As a roster grows, look-alike classmates and
    degraded/low-resolution probes drift toward each other; genuine matches
    measure top1-vs-runner-up margins >= 0.70 while rejected probes measure
    <= 0.01, so a 0.15 margin rejects ambiguity without ever rejecting a
    confident genuine match.
"""
import numpy as np

from .config import EMBEDDING_DIM


def cosine_similarity(embedding_a, embedding_b):
    """Cosine similarity between two normalized embeddings (0..1)."""
    a = np.asarray(embedding_a, dtype=np.float64).reshape(-1)
    b = np.asarray(embedding_b, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        raise ValueError("Embedding dimension mismatch.")
    return float(np.dot(a, b))


def identity_similarity_matrix(gallery, probe):
    """Cosine similarity between a probe embedding and every gallery entry.

    gallery: list of normalized embeddings (raw vectors), or of dicts that
        carry them under the "embedding" key (one entry per student photo).
    probe: a single normalized embedding.
    Returns a list of floats aligned with gallery.
    """
    g = np.asarray(
        [e["embedding"] if isinstance(e, dict) else e for e in gallery],
        dtype=np.float64,
    )  # (N, EMBEDDING_DIM)
    p = np.asarray(probe, dtype=np.float64).reshape(-1)
    if g.ndim == 1:
        g = g.reshape(1, -1)
    return (g @ p).tolist()


def best_match(probe, gallery, threshold=0.70, margin=0.0):
    """Return the strongest match that passes both confidence gates.

    Gallery entries may hold MULTIPLE embeddings per student (one per
    registration photo), so matching is grouped per student:

      * each student's score is the BEST similarity among their own photos
        (one weak registration photo never sinks the student),
      * the threshold applies to the strongest student,
      * the margin rule compares the best student against the best OTHER
        student - never against the same student's other photos.

    Entries that are not dicts (unit tests pass raw vectors) count as one
    distinct identity each, which preserves the plain flat-list semantics.

    threshold: absolute similarity the best student must reach.
    margin: the best student must also beat the runner-up student by at
        least this much (skipped when the gallery holds a single identity).

    Returns (index, similarity) into the ORIGINAL gallery, or (None,
    similarity) when no student passes. None with similarity >= threshold
    means the margin rule rejected an ambiguous look-alike rather than low
    confidence - callers report "too close to call" instead of "unknown".
    """
    if not gallery:
        return None, 0.0
    similarities = identity_similarity_matrix(gallery, probe)

    best_by_identity = {}  # identity key -> (gallery index, similarity)
    for i, sim in enumerate(similarities):
        entry = gallery[i]
        key = entry.get("student_id") if isinstance(entry, dict) else None
        if key is None:
            key = i  # raw / unattributed entry = its own identity
        current = best_by_identity.get(key)
        if current is None or sim > current[1]:
            best_by_identity[key] = (i, float(sim))

    ranked = sorted(best_by_identity.values(), key=lambda t: t[1], reverse=True)
    best_idx, best_score = ranked[0]
    if best_score < threshold:
        return None, best_score
    if margin and len(ranked) > 1:
        if best_score - ranked[1][1] < margin:
            return None, best_score
    return best_idx, best_score