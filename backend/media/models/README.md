# AI model files

This directory stores the two pre-trained ONNX models used by the Smart Attendance System:

| File | Model | Size | Purpose |
| --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | YuNet (OpenCV Zoo) | ~0.2 MB | Face detection |
| `w600k_r50.onnx` | ArcFace w600k_r50 (InsightFace) | ~166 MB | 512-d face embeddings |

The files are **not committed** to git (see `.gitignore`). Download them with:

```bash
python scripts/download_models.py
```

or let the Docker `models` service fetch them automatically. The backend returns a friendly
"AI models missing" message (HTTP 503) until both files are present.