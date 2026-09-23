# Smart Attendance System — AI Face Recognition

A full-stack, production-style **AI Smart Attendance System** for colleges and schools. Teachers
(`Sir` / `Madam`) sign in, register students along with 1–3 photos, and run real-time attendance
sessions using **webcam / classroom-photo face recognition**. Duplicate detections are rejected,
sessions can be reviewed and corrected manually, and PDF / Excel / CSV reports plus attendance
analytics are generated automatically.

This is a **real working system** — no simulated AI, no fake data. Attendance is marked only when a
detected face genuinely matches an enrolled student above a configurable confidence threshold.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [AI Workflow](#ai-workflow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Database Architecture](#database-architecture)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [1. Backend setup](#1-backend-setup)
  - [2. AI model download](#2-ai-model-download)
  - [3. Frontend setup](#3-frontend-setup)
  - [4. Environment variables](#4-environment-variables)
- [Running the project](#running-the-project)
- [Creating the first teacher account](#creating-the-first-teacher-account)
- [Testing](#testing)
- [Docker deployment](#docker-deployment)
- [Screenshots](#screenshots)
- [Future improvements](#future-improvements)
- [Privacy considerations](#privacy-considerations)
- [License](#license)

---

## Features

- **Teacher authentication** — JWT login with username *or* email, "Remember me", logout,
  change-password, password reset via email link.
- **Roles** — `Teacher` and `Admin`. Only admins can create teacher accounts.
- **Modern dashboard** — student/class/subject counts, today's present & absent, overall average,
  class-wise bar chart, recent sessions.
- **Class management** — classes, divisions, subjects and academic years scoped to each teacher.
- **Student management** — full CRUD with search, division/status/gender filters, sorting and
  pagination.
- **Add student with photo (one step)** — the "Add student" form collects the student's details
  **and** 1–3 face photos (drag & drop upload or webcam capture) in a single save: the student is
  created, each photo is AI-validated, and the consolidated face embedding is registered before the
  list refreshes. Per-photo results ("Registered" / "Rejected" with the reason) are shown inline.
- **Face registration (the core AI module)** — 1–3 photos per student, each validated:
  - exactly **one** face required (no face / multiple faces rejected),
  - image quality check (too blurry / too small rejected),
  - a pre-trained **ArcFace** model converts the aligned face into a 512‑d embedding,
  - embeddings are **normalised and averaged** into one consolidated embedding per student.
- **Real-time attendance** — live webcam or uploaded classroom photo; every detected face produces a
  bounding box plus:
  - matched student name, roll number, confidence % → marked **Present**,
  - below-threshold / unknown faces → **Unknown / Review Required** (never silently marked).
- **Mark Attendance module (photo upload)** — a dedicated page where the teacher picks or creates a
  session, uploads one or more classroom photos (or captures a webcam frame), and lets the AI do the
  roll call: each photo is shown with **bounding boxes and names drawn over the detected faces**,
  summary counters (newly marked / already marked / unknown / manual holds), and a live roster with
  present-absent counts, manual corrections and a finalize action.
- **Duplicate protection** — a unique `(student, attendance_session)` constraint ensures a student
  can only be marked once per session; repeat detections say "Already present".
- **Attendance review** — review Present / Absent / Not Detected students, manually re-mark, search,
  then **finalize** to lock the session.
- **History & analytics** — overall history with filters, daily trend chart, per-student profile with
  monthly + subject-wise charts.
- **Reports** — daily / weekly / monthly / class / subject / student reports exported as
  **PDF, Excel (XLSX), or CSV**.
- **AI recognition log** — every recognition attempt (timestamp, student, confidence, result,
  message) recorded for debugging and demonstration.
- **Privacy** — no raw biometric templates are exposed via APIs; face registrations are removable,
  and face data is restricted to the authenticated teacher.

---

## Architecture

Two cleanly separated applications talk over a JSON REST API.

```
Browser (React SPA)
   │  ./api/*  ./media/*
   ▼
Django REST Framework  ───►  PostgreSQL / SQLite
   │  config · accounts · classes · students ·
   │  attendance · reports
   ▼
ai/ package (isolated, stateless)
   face_detector → face_encoder → face_matcher → attendance_engine
```

- The **frontend** is a Vite + React 19 SPA (Tailwind CSS v4, Recharts, Lucide icons). During
  development Vite proxies `/api` and `/media` to Django; in Docker an nginx container serves the
  built bundle and reverse-proxies the API.
- The **backend** is a Django + DRF application exposing JWT-secured endpoints. All queries are
  scoped to the authenticated teacher (`teacher=_request.user`).
- The **AI package** (`backend/ai/`) is framework-agnostic: it takes image bytes and returns results.
  Django never imports it in a way that couples business logic to model files.

```
Teacher Login → Dashboard → Add Class/Division → Register Students
   → Upload/Capture 1–3 Photos → Generate Embeddings
   → Start Attendance (subject + class/division + date)
   → Webcam / Classroom photo → Detect → Embed → Match → Mark Present
   → Review → Finalize → Reports / Analytics
```

---

## AI Workflow

No model is *trained* per student. The system uses a **pre-trained face-recognition model
(ArcFace `w600k_r50`)** and treats each student as a small gallery of **face embeddings**.

**Registration:**

```
Student photo
   → YuNet face detector (finds exactly one face)
   → 5-point landmark alignment
   → ArcFace encoder → 512-d embedding (L2-normalised)
   → stored PER PHOTO (up to MAX_STUDENT_PHOTOS per student); the legacy
     consolidated mean in FaceEmbedding is kept as a fallback
```

**Recognition (during attendance):**

```
Webcam frame / classroom image
   → YuNet face detector (one box per detected face, each processed independently)
   → per-face quality gate (size / sharpness / detection score → LOW_QUALITY)
   → landmark alignment
   → ArcFace embedding, compared against EVERY photo of EVERY student
   → strongest cosine similarity per student
   → ≥ RECOGNITION_THRESHOLD and beats runner-up by RECOGNITION_MARGIN → Present
   → ≥ RECOGNITION_THRESHOLD but inside the margin → "Ambiguous / Review Required"
   → <  RECOGNITION_THRESHOLD → "Unknown / Review Required"
```

- Model files: YuNet `face_detection_yunet_2023mar.onnx` (~0.2 MB) and ArcFace
  `w600k_r50.onnx` (~166 MB), run on **ONNX Runtime** (CPU). InsightFace's *models* are used,
  but the heavier `insightface` pip package is avoided for reliable cross-platform installs.
- Threshold is configurable via `RECOGNITION_THRESHOLD` (default `0.70`, cosine
  similarity) with a runner-up gate `RECOGNITION_MARGIN` (default `0.15`).
  Quality-gate knobs (`RECOGNITION_MIN_FACE_PX`, `RECOGNITION_MIN_FACE_RATIO`,
  `RECOGNITION_MIN_DETECTOR_SCORE`, `RECOGNITION_MIN_FACE_SHARPNESS`) decide when
  a face is reported `LOW_QUALITY` instead of being identified.
- Only embeddings are compared; raw model activations and photos are never exposed publicly.

---

## Technology Stack

| Layer     | Technology |
| --------- | ---------- |
| Frontend  | React 19, Vite 8, Tailwind CSS v4, React Router 7, Axios, Recharts, Lucide React |
| Backend   | Python 3.11, Django 5.2, Django REST Framework 3.18 |
| AI        | OpenCV, ONNX Runtime, YuNet (detector), ArcFace w600k_r50 (encoder), NumPy, cosine similarity |
| Database  | PostgreSQL 16 (Docker/prod) **or** SQLite (zero-setup dev) |
| Auth      | JWT (djangorestframework-simplejwt) with rotating refresh tokens |
| Reports   | ReportLab (PDF), openpyxl (XLSX), CSV |
| Deploy    | Docker Compose (Postgres + Gunicorn + Nginx) |

---

## Project Structure

```
smart-attendance/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example               # copy to .env
│   ├── config/                    # settings, urls, exceptions, wsgi/asgi
│   ├── accounts/                  # User, JWT login, profile, password reset
│   ├── classes/                   # Classroom, Division, Subject
│   ├── students/                  # Student, StudentFace, FaceEmbedding
│   ├── attendance/                # Sessions, Records, RecognitionLog, analytics
│   ├── reports/                   # PDF/XLSX/CSV export
│   ├── ai/                        # face_detector, face_encoder, face_matcher,
│   │                              # preprocessing, attendance_engine, config
│   ├── media/models/              # ONNX model files (downloaded)
│   ├── media/student_faces/       # compressed enrolment photos
│   └── media/recognition/         # optional recognition-frame store
├── frontend/
│   ├── src/
│   │   ├── components/            # ui, Layout, ProtectedRoute, CameraCapture, FileUpload
│   │   ├── pages/                 # Login, Dashboard, Students, Session, History, Reports, ...
│   │   ├── lib/                   # api (axios + JWT refresh), auth context
│   │   ├── App.jsx                # routes
│   │   ├── main.jsx
│   │   └── index.css              # Tailwind v4 theme
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   └── download_models.py         # fetches the ONNX models
├── docs/
│   ├── architecture.md
│   ├── ai-pipeline.md
│   └── api-reference.md
├── docker-compose.yml
├── backend/Dockerfile
├── frontend/Dockerfile
└── .gitignore
```

---

## Database Architecture

```
User (accounts_user)  ┬─ role: teacher | admin, title: sir | madam | teacher
                      │
                      └── classroom (1:N) ── division (1:N) ── student (1:N)
                              │  classroom_id, academic_year           │ status, roll_number,
                              │                                      │ email, mobile, gender, dob
                              └── subject (1:N, class-scoped)
                                                                       ├── student_face (1:N) - enrolment photos
                                                                       └── face_embedding (1:1) - 512-d vector (JSON)

attendance_session ── teacher, classroom, division, subject, date, lecture_number, status
                             │  status: live | finalized | cancelled
                             ▼
attendance_record ── session, student, status(present|absent), confidence,
                     marked_by_ai, manually_updated, recognized_at
                     UNIQUE(session, student)   ← duplicate-attendance protection

recognition_log ── session, student(nullable), timestamp, confidence, result, message
```

Key indexes: `(teacher, date)` on sessions, `UNIQUE(session, student)` on records,
`(division, roll_number)` on students, `(teacher, role)` on users.

---

## Installation

### Prerequisites

- Python 3.11 (or newer 3.x) — keep a virtual environment per-machine.
- Node.js 20+ and npm.
- (Optional) PostgreSQL 16 for production; SQLite works out of the box for development.
- Internet access once, to download the two ONNX model files.

### 1. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

copy .env.example .env      # Windows
# cp .env.example .env      # macOS / Linux
```

### 2. AI model download

```bash
# From the project root (uses the backend venv):
.venv\Scripts\python.exe scripts\download_models.py          # Windows
# .venv/bin/python scripts/download_models.py                # macOS / Linux
```

This downloads `face_detection_yunet_2023mar.onnx` and `w600k_r50.onnx` into
`backend/media/models/`. The backend refuses to run registration/recognition with
a clear message (`503`) until both files exist.

```bash
cd backend
python manage.py migrate
python manage.py collectstatic --no-input   # optional, for static assets
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Environment variables

All secrets live in `backend/.env` (see `backend/.env.example`). Never commit `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | dev-only value | Django signing secret (set a long random string) |
| `DEBUG` | `True` | Django debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DB_ENGINE` | `sqlite` | `sqlite` for local, `postgres` for Docker/prod |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | `smart_attendance` / `attendance` / `attendance` / `localhost` / `5432` | Postgres connection |
| `ACCESS_TOKEN_MINUTES` | `60` | JWT access-token lifetime |
| `REFRESH_TOKEN_DAYS` | `7` | JWT refresh-token lifetime |
| `REMEMBER_ME_REFRESH_DAYS` | `30` | Refresh lifetime when "Remember me" is checked |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,…` | Allowed browser origins |
| `AI_MODELS_DIR` | `backend/media/models` | Where the ONNX models live (empty = default) |
| `AI_DETECTOR_MODEL` | `face_detection_yunet_2023mar.onnx` | Detector file name |
| `AI_RECOGNITION_MODEL` | `w600k_r50.onnx` | ArcFace file name |
| `RECOGNITION_THRESHOLD` | `0.70` | Cosine-similarity threshold for a confident match |
| `RECOGNITION_MARGIN` | `0.15` | Required gap between the best and runner-up student (otherwise "ambiguous") |
| `RECOGNITION_MIN_FACE_PX` | `40` | Quality gate: minimum face width/height in pixels |
| `RECOGNITION_MIN_FACE_RATIO` | `0.02` | Quality gate: minimum face width relative to image width |
| `RECOGNITION_MIN_DETECTOR_SCORE` | `0.5` | Quality gate: minimum YuNet detection score |
| `RECOGNITION_MIN_FACE_SHARPNESS` | `20` | Quality gate: minimum face-crop sharpness (Laplacian variance) |
| `MAX_STUDENT_PHOTOS` | `5` | Registration photos per student (3-5 varied shots recommended) |
| `EMAIL_BACKEND` / `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | console backend | SMTP settings for password-reset emails; console prints to the terminal |
| `TIME_ZONE` | `Asia/Kolkata` | Application time zone |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_IMAGE_SIZE_MB` | `10` | Accepted image upload limit |

---

## Running the project

**Terminal 1 — backend** (`http://127.0.0.1:8000`):

```bash
cd backend
.venv\Scripts\python.exe manage.py runserver
```

**Terminal 2 — frontend** (`http://localhost:5173`):

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` and `/media` to Django.

### Creating the first teacher account

There is no public sign-up (admins create teachers). Use the Django admin:

```bash
cd backend
.venv\Scripts\python.exe manage.py createsuperuser
# log in at http://127.0.0.1:8000/admin → add a Teacher user,
# or use the Admin module in the UI once signed in as a superuser.
```

> The Django superuser's `role` is `admin`, so it can also use the web UI's
> **Administration** page to create additional teacher accounts.

---

## Testing

```bash
cd backend
.venv\Scripts\python.exe manage.py test tests
```

The suite covers authentication (incl. password reset), registration validation
(no-face / multi-face / poor quality), recognition (matched, unknown, low-confidence,
per-student gallery grouping, quality gate), attendance (create, recognize, duplicate
protection, manual update, finalize), reports and full API permissions. Run status:
**76/76 tests pass** with the real AI models.

To exercise the full recognition pipeline end-to-end against the live database
(8 scenarios: original registration photo, a *different* photo of the same student
via a leave-one-out gallery, group photo with 1/all students known, unknown person,
tiny/blurred face → `LOW_QUALITY`, same student twice in one photo, double-run
duplicate protection, manual lock + finalize):

```bash
cd backend
.venv\Scripts\python.exe verify_recognition.py
```

After changing the detector, alignment, or recognition models — or after
importing photos by other means — recompute every stored face vector so old
embeddings never mismatch new probes:

```bash
.venv\Scripts\python.exe manage.py backfill_face_embeddings --all
```

---

## Docker deployment

Docker Compose provisions **Postgres + backend (Gunicorn) + frontend (Nginx)**, and a one-shot
service that downloads the AI models into a shared volume.

```bash
cp .env.example .env        # wsl / macos / linux (see below for Windows)
# Windows PowerShell:
#   Copy-Item .env.example .env
# Set DJANGO_SECRET_KEY in .env to a long random string.

docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/api
- The first superuser is created with `docker compose run --rm backend python manage.py createsuperuser`.

See `docs/architecture.md` for the container topology and notes on STORAGE for the model volume.

---

## Screenshots

> Add screenshots of the Login, Dashboard, Student list, Face registration, Live camera attendance,
> Attendance review, History and Reports pages in the `docs/screenshots/` folder and reference them here:

- `docs/screenshots/login.png`
- `docs/screenshots/dashboard.png`
- `docs/screenshots/students.png`
- `docs/screenshots/face-registration.png`
- `docs/screenshots/camera-attendance.png`
- `docs/screenshots/attendance-review.png`
- `docs/screenshots/history.png`
- `docs/screenshots/reports.png`

---

## Future improvements

- Dark / light theme toggle.
- Push notifications when a session is finalized.
- QR-code check-in as a fallback when AI matching is unavailable.
- GPU acceleration for the ArcFace encoder (ONNX GPU provider).
- CSV import/export for student rosters (bulk enrolment).
- Attendance report scheduling and email delivery.
- Multi-camera / multiple-session parallel recognition.

---

## Privacy considerations

This system processes biometric information. It is designed to minimise risk:

- **Storage is minimal** — only the 512‑d embedding (not a raw template) and a compressed face
  thumbnail are stored; raw camera frames are not persisted outside optional recognition logs.
- **Access is scoped** — every endpoint filters by the authenticated teacher; embeddings and photos
  are never exposed through public list APIs.
- **Consent & control** — a teacher can remove a student's face registration at any time
  (DELETE) without affecting attendance history.
- **No surveillance** — the system is intended solely for taking attendance for enrolled students of
  the teacher's own classes.
- Face registration should be performed with the student's consent, in line with the institution's
  data-protection policy (e.g., DPDP Act in India / GDPR in the EU as applicable).

---

## License

MIT — see [LICENSE](LICENSE).#   A t t e n d V i s i o n - A I - A I - P o w e r e d - F a c e - R e c o g n i t i o n - A t t e n d a n c e - S y s t e m  
 