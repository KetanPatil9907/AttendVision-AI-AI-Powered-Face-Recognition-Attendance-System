  #!/usr/bin/env python
"""Download the pre-trained ONNX models required by the Smart Attendance System.

Models:
  1. YuNet face detector       (OpenCV Zoo)   ~230 KB   -> face_detection_yunet_2023mar.onnx
  2. ArcFace w600k_r50 embeder (InsightFace)  ~166 MB   -> w600k_r50.onnx

These are the same pre-trained models InsightFace ships (buffalo_l pack). No
model is trained in this project; students are represented by 512-d ArcFace
embeddings.

Usage:
    python scripts/download_models.py [models_dir]
Default models_dir: backend/media/models (overridable via AI_MODELS_DIR).
"""
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

DETECTOR_NAME = "face_detection_yunet_2023mar.onnx"
RECOGNITION_NAME = "w600k_r50.onnx"

DETECTOR_MIRRORS = [
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]

# Multiple mirrors of the insightface buffalo_l w600k_r50.onnx model.
RECOGNITION_MIRRORS = [
    "https://huggingface.co/public-data/insightface/resolve/main/models/buffalo_l/w600k_r50.onnx",
    "https://huggingface.co/Aitrepreneur/insightface/resolve/main/models/buffalo_l/w600k_r50.onnx",
    "https://huggingface.co/Kuvshin/kuvshin8/resolve/main/insightface/models/buffalo_l/w600k_r50.onnx",
    "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/arcface_w600k_r50.onnx",
]

BUFFALO_L_ZIP = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"


def _default_target_dir():
    env = os.getenv("AI_MODELS_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "media", "models")


def _download(url, dest, chunk=1024 * 256):
    """Stream a file. Raises on HTTP errors. Returns bytes downloaded."""
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 smart-attendance"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        while True:
            data = resp.read(chunk)
            if not data:
                break
            out.write(data)
            total += len(data)
    return total


def _try_mirrors(mirrors, dest, label, min_size):
    for mirror in mirrors:
        tmp = dest + ".part"
        try:
            print(f"Downloading {label} from {mirror} ...")
            size = _download(mirror, tmp)
            if size < min_size:
                print("  downloaded file too small, skipping mirror")
                os.remove(tmp)
                continue
            os.replace(tmp, dest)
            print(f"  OK - {size / (1024 * 1024):.1f} MB saved to {dest}")
            return True
        except Exception as exc:
            print(f"  failed ({exc})")
            if os.path.exists(tmp):
                os.remove(tmp)
    return False


def _download_buffalo_l_zip(dest):
    """Fallback: grab the full buffalo_l release zip and extract w600k_r50.onnx."""
    try:
        print("Attempting fallback download of the insightface buffalo_l release ...")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "buffalo_l.zip")
            _download(BUFFALO_L_ZIP, zip_path)
            with zipfile.ZipFile(zip_path) as zf:
                names = [n for n in zf.namelist() if n.endswith(RECOGNITION_NAME)]
                if not names:
                    print("  model not present inside buffalo_l.zip")
                    return False
                with zf.open(names[0]) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
            print(f"  OK - extracted {RECOGNITION_NAME} to {dest}")
            return True
    except Exception as exc:
        print(f"  fallback failed ({exc})")
        return False


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else _default_target_dir()
    os.makedirs(target_dir, exist_ok=True)

    detector_dest = os.path.join(target_dir, DETECTOR_NAME)
    recognition_dest = os.path.join(target_dir, RECOGNITION_NAME)

    ok_tracker = []
    if os.path.exists(detector_dest) and os.path.getsize(detector_dest) > 100_000:
        print(f"{DETECTOR_NAME} already present, skipping.")
        ok_tracker.append(True)
    else:
        ok_tracker.append(_try_mirrors(DETECTOR_MIRRORS, detector_dest, DETECTOR_NAME, 100_000))

    if os.path.exists(recognition_dest) and os.path.getsize(recognition_dest) > 50_000_000:
        print(f"{RECOGNITION_NAME} already present, skipping.")
        ok_tracker.append(True)
    else:
        ok = _try_mirrors(RECOGNITION_MIRRORS, recognition_dest, RECOGNITION_NAME, 50_000_000)
        if not ok:
            ok = _download_buffalo_l_zip(recognition_dest)
        ok_tracker.append(ok)

    if all(ok_tracker):
        print("\nAll models are ready.")
        sys.exit(0)
    print(
        "\nSome models failed to download. Check your network connection and try again,"
        "\nor place the .onnx files manually in the models directory."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
