# AI Pipeline

## Design principle

The system does **not** train a face-recognition network per student. It uses two **pre-trained**
ONNX models and treats each student as a small gallery of **face embeddings**:

| Step | Module | Output |
| --- | --- | --- |
| Image decode | `ai/preprocessing.py` | BGR numpy array (`decode_image`) |
| Face detection | `ai/face_detector.py` (YuNet) | list of `{bbox, kps, score}` |
| Alignment | `ai/preprocessing.py` `align_face` | 112×112 aligned RGB face |
| Embedding | `ai/face_encoder.py` (ArcFace `w600k_r50`) | 512-d L2‑normalised vector |
| Matching | `ai/face_matcher.py` `best_match` | cosine similarity vs gallery |
| Decision | `ai/attendance_engine.py` `recognize_faces` | matched student or UNKNOWN |

## Registration (student enrolment)

For each uploaded photo (`POST /api/students/{id}/face-registration/`):

1. Decode the image; reject invalid images.
2. Detect faces with YuNet.
   - no faces → reject `"No face detected"` (422).
   - face smaller than `MIN_FACE_RATIO` (10% of image width) → reject `"face too small"`.
   - more than one face → reject `"Multiple faces detected"`.
3. `quality_check` — blur (Laplacian variance) and alignment (roll angle) validation.
4. Align the single face and generate its 512-d ArcFace embedding.
5. Save a **compressed JPEG thumbnail** (`student_faces/`) and the embedding.
6. Recompute the student's **consolidated embedding** as the L2‑normalised mean of all
   enrolled-photo embeddings (up to `MAX_STUDENT_PHOTOS = 3`).

Only the consolidated embedding (a 512‑float JSON array) is used for matching.
`DELETE` on the same action removes all photos + the embedding (consent/withdrawal).

## Recognition (attendance)

`process_recognition(session, image_bytes)`:

1. Build the gallery from the session's division students who have an enrolled embedding:
   `[{student_id, roll_number, name, embedding}]`.
2. `recognize_faces(...)`:
   - decode image,
   - detect every face (YuNet) and drop those below the min-size ratio,
   - for each remaining face: align → embed → `best_match` against the gallery using
     cosine similarity,
   - `best_match` returns the single best candidate **above `RECOGNITION_THRESHOLD`**
     (default 0.35); otherwise the face is `UNKNOWN`.
3. Mark attendance:
   - matched & record not yet present → `PRESENT` with `confidence`, `marked_by_ai=True`,
     `recognized_at=now`.
   - already present → counted as `repeated` (duplicate protection), no new record.
   - unknown / low confidence → **never** marked; reported for review.
4. Append a `RecognitionLog` per detection (timestamp, student?, confidence, result, message).

## Threshold semantics

- `confidence` is the cosine similarity between the probe embedding and the best gallery match.
- A higher threshold means stricter matching (fewer false positives, more "Unknown").
- `RECOGNITION_THRESHOLD=0.35` is a good default for ArcFace cosine similarity; you can tune it in
  `backend/.env` and re-run. Scores below threshold surface as **"Unknown / Review Required"** on the
  attendance review screen rather than being auto-marked.

## Model files & download

- `face_detection_yunet_2023mar.onnx`  (~0.2 MB)
- `w600k_r50.onnx`                      (~166 MB, ArcFace, 512-d output)

Both are fetched by `scripts/download_models.py` into `backend/media/models/`
(`AI_MODELS_DIR`, configurable). `models_ready()` guards every AI endpoint and returns a friendly
503 message when the files are missing. The chosen provider for the ArcFace model is
[InsightFace's repo](https://github.com/deepinsight/insightface) (the `w600k_r50` weights), while
runtime inference uses the lightweight `onnxruntime` (no C++ build required — this is why the full
`insightface` pip package is not a dependency).

## Testing the AI logic

- `backend/tests` includes recognition tests using `tests/data/face_test.jpg`:
  matched student, unknown face, low-confidence face, registration restrictions.
- Ad-hoc smoke helper: `backend/ai/smoke_test.py` and `smoke_test_photo.py` print pipeline
  diagnostics for a chosen image (detector + encoder availability and quality).

## Privacy of embeddings

- Embeddings are only stored server-side, tied to `student_id`, and never serialized by any
  list/detail API. Only the **model name and dimension** are exposed for display.
- Media files are served under `/media` (authenticated app, dev server); consider signing media URLs
  in a hardened deployment.