
# AttendVision AI 🎓🤖

## AI-Powered Face Recognition Attendance System
 
AttendVision AI is a web-based smart attendance management system that uses **Artificial Intelligence, Computer Vision, and Face Recognition** to automate classroom attendance.

The system allows teachers to manage classes, divisions, subjects, and students, register student faces, capture classroom images through a camera or upload images, automatically recognize registered students, mark attendance, review attendance records, and generate attendance reports and analytics.

---

## 📌 Project Overview

Traditional attendance systems are often time-consuming and require manual record keeping. AttendVision AI provides an automated approach where students can be identified using facial recognition and their attendance can be recorded digitally.

The system is designed for educational institutions such as:

* Engineering colleges
* Schools
* Universities
* Coaching institutes
* Training centers

The platform provides a complete workflow from **student registration → face enrollment → face recognition → attendance marking → verification → reports and analytics**.

---

## ✨ Key Features

### 👨‍🏫 Teacher Authentication

* Secure teacher login
* JWT-based authentication
* Access and refresh tokens
* Remember-me functionality
* Profile management
* Password change
* Forgot password and reset password
* Protected application routes

### 🏫 Class & Subject Management

Teachers can manage:

* Classes
* Divisions
* Subjects
* Academic years
* Class descriptions
* Subject codes

### 👨‍🎓 Student Management

Teachers can:

* Add students
* Update student information
* View student details
* Manage roll numbers
* Store student ID/PRN
* Store email and mobile number
* Assign students to divisions
* Track face-registration status

### 📸 Face Registration

Students can have their face registered using photographs.

The AI pipeline performs:

1. Face detection
2. Face validation
3. Face alignment/preprocessing
4. Face embedding generation
5. Embedding storage
6. Student identity association

Multiple enrollment photographs can be used to improve recognition across different poses and lighting conditions.

### 🧠 AI Face Recognition

AttendVision AI uses computer vision and deep-learning-based face recognition.

The system:

1. Captures or receives an attendance image
2. Detects faces
3. Processes each detected face independently
4. Generates a face embedding
5. Compares the embedding against registered students
6. Calculates similarity
7. Identifies the student when the similarity passes the configured threshold
8. Marks attendance automatically

Unknown or low-quality faces are not automatically treated as known students.

### 👥 Group Photo Recognition

The system supports multiple faces in a single classroom image.

For example:

```text
Classroom Image
      │
      ▼
Face Detection
      │
 ┌────┼────┐
 ▼    ▼    ▼
Face  Face  Face
 1     2     3
 │     │     │
 ▼     ▼     ▼
Embedding Generation
 │     │     │
 └─────┼─────┘
       ▼
Face Matching
       │
       ▼
Attendance Records
```

Each detected face is processed independently.

### ✅ Attendance Management

The attendance module supports:

* Attendance session creation
* Automatic attendance marking
* Present/absent records
* Manual attendance correction
* AI-marked attendance
* Manually updated attendance
* Attendance finalization
* Duplicate attendance protection
* Attendance history
* Session details

### 📊 Dashboard & Analytics

The dashboard provides information such as:

* Total students
* Total classes
* Total divisions
* Total subjects
* Today's attendance
* Overall attendance percentage
* Class-wise attendance
* Recent attendance sessions
* Attendance trends

### 📑 Reports

The system is designed to provide attendance reporting functionality for teachers and administrators.

Reports can include:

* Student attendance
* Class attendance
* Subject attendance
* Attendance percentage
* Session records
* Attendance history

---

# 🧠 AI Technology

AttendVision AI uses a modern face-recognition pipeline.

## Face Detection

**OpenCV YuNet**

YuNet is used to detect faces from:

* Registration images
* Uploaded attendance images
* Classroom/group images
* Camera frames

## Face Recognition

**InsightFace / ArcFace**

The recognition model generates a numerical representation called a **face embedding**.

The project uses a **512-dimensional embedding** representation.

The embedding allows the system to compare faces mathematically instead of comparing raw images.

## Face Matching

The system uses **cosine similarity** to compare the query face embedding with registered face embeddings.

Conceptually:

```text
Registration Image
        ↓
Face Detection
        ↓
Face Embedding
        ↓
Store Embedding
        ↓
        ┌───────────────────────┐
        │ Attendance Image      │
        └───────────┬───────────┘
                    ↓
             Face Detection
                    ↓
             Face Embedding
                    ↓
          Similarity Comparison
                    ↓
             Match / Unknown
                    ↓
          Attendance Decision
```

---

# 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      Teacher        │
                    │      Web Browser    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    React Frontend   │
                    │       + Vite        │
                    └──────────┬──────────┘
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │   Django Backend    │
                    │ Django REST API     │
                    └───────┬─────┬───────┘
                            │     │
                ┌───────────┘     └────────────┐
                ▼                              ▼
      ┌─────────────────┐             ┌─────────────────┐
      │   PostgreSQL    │             │   AI Engine     │
      │    Database     │             │ OpenCV +        │
      │                 │             │ YuNet +         │
      │ Students        │             │ InsightFace     │
      │ Classes         │             │ ArcFace         │
      │ Attendance      │             └────────┬────────┘
      │ Subjects        │                      │
      │ Sessions        │                      ▼
      └─────────────────┘             ┌─────────────────┐
                                      │ Face Embeddings │
                                      │ & Recognition   │
                                      └─────────────────┘
```

---

# 🛠️ Technology Stack

## Frontend

| Technology            | Purpose             |
| --------------------- | ------------------- |
| React.js              | User interface      |
| Vite                  | Frontend build tool |
| Tailwind CSS          | Styling             |
| Axios                 | API communication   |
| React Router          | Application routing |
| Lucide                | Icons               |
| Recharts / Charts     | Data visualization  |
| WebRTC / MediaDevices | Camera access       |

## Backend

| Technology            | Purpose                    |
| --------------------- | -------------------------- |
| Python                | Backend and AI development |
| Django                | Web backend                |
| Django REST Framework | REST APIs                  |
| JWT                   | Authentication             |
| PostgreSQL            | Database                   |

## AI / Computer Vision

| Technology        | Purpose              |
| ----------------- | -------------------- |
| OpenCV            | Image processing     |
| YuNet             | Face detection       |
| InsightFace       | Face recognition     |
| ArcFace           | Face embeddings      |
| NumPy             | Numerical operations |
| Cosine Similarity | Face matching        |

## Development Tools

* Git
* GitHub
* VS Code
* PowerShell
* Postman
* PostgreSQL
* Python Virtual Environment

---

# 📁 Project Structure

```text
AttendVision-AI/
│
├── backend/
│   ├── manage.py
│   ├── config/
│   ├── accounts/
│   ├── students/
│   ├── classes/
│   ├── attendance/
│   ├── reports/
│   ├── ai/
│   ├── media/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── lib/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│
├── scripts/
│
├── docker-compose.yml
├── .gitignore
├── .env.example
├── LICENSE
└── README.md
```

---

# 🔄 Attendance Workflow

## Step 1 — Teacher Login

The teacher logs into the AttendVision AI dashboard.

```text
Teacher
   ↓
Login
   ↓
JWT Authentication
   ↓
Dashboard
```

## Step 2 — Create Class

Teacher creates:

* Class
* Division
* Subject
* Academic Year

## Step 3 — Register Students

Teacher adds student information and uploads student photographs.

```text
Student Information
        +
Student Photograph
        ↓
Face Detection
        ↓
Face Validation
        ↓
Face Embedding
        ↓
Face Registration
```

## Step 4 — Start Attendance Session

Teacher selects the required class/division/subject and starts an attendance session.

## Step 5 — Capture Classroom Image

The teacher can use the camera or upload a classroom photograph.

## Step 6 — AI Recognition

The system detects all faces in the image.

Each face is processed separately.

```text
Classroom Image
       ↓
Detect Faces
       ↓
Extract Face
       ↓
Generate Embedding
       ↓
Compare With Registered Faces
       ↓
Similarity Score
       ↓
Known / Unknown / Low Quality
```

## Step 7 — Attendance Marking

Recognized students are marked present.

Students who are not recognized remain absent unless manually corrected.

## Step 8 — Review

The teacher can review the AI-generated attendance and manually correct records when required.

## Step 9 — Finalize

After verification, the teacher finalizes the attendance session.

---

# 🔐 Security

The application includes several security mechanisms:

* JWT authentication
* Protected API endpoints
* Protected frontend routes
* Teacher-specific data access
* Password protection
* Token refresh mechanism
* Database constraints
* Duplicate attendance prevention
* Configurable face-recognition threshold
* Unknown-face handling
* Environment variables for secrets

Sensitive configuration such as database passwords and Django secret keys should be stored in `.env` and should **never be committed to GitHub**.

---

# 📊 Attendance Logic

Attendance records use a session-based approach.

Each attendance session is associated with:

```text
Class
  │
  ├── Division
  │
  ├── Subject
  │
  └── Attendance Session
           │
           ├── Student 1 → Present
           ├── Student 2 → Absent
           ├── Student 3 → Present
           └── Student 4 → Absent
```

The system prevents duplicate attendance records for the same student within the same session.

---

# 🧪 AI Recognition States

The recognition system can classify detected faces into different states:

| State         | Meaning                                                 |
| ------------- | ------------------------------------------------------- |
| `KNOWN`       | Face successfully matched with a registered student     |
| `UNKNOWN`     | Face detected but no sufficiently strong identity match |
| `LOW_QUALITY` | Face quality is insufficient for reliable recognition   |

The recognition threshold is configurable and should be calibrated using representative genuine and unknown samples rather than blindly lowering the threshold.

---

# ⚙️ Installation

## Requirements

Install the following:

* Python 3.x
* Node.js
* npm
* PostgreSQL
* Git

---

# 🚀 Backend Setup

Navigate to the backend:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create your environment file:

```powershell
Copy-Item .env.example .env
```

Configure your PostgreSQL database and application settings inside `.env`.

Run migrations:

```powershell
python manage.py migrate
```

Create an administrator:

```powershell
python manage.py createsuperuser
```

Start the Django server:

```powershell
python manage.py runserver
```

Backend:

```text
http://127.0.0.1:8000
```

---

# 🎨 Frontend Setup

Open another terminal.

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🔌 API Structure

The backend exposes REST APIs for the main application modules.

```text
/api/auth/
/api/classes/
/api/students/
/api/attendance/
/api/reports/
/api/dashboard/statistics
```

### Authentication

```text
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/profile
POST /api/auth/change-password
```

### Classes

```text
/api/classes/
```

### Students

```text
/api/students/
```

### Attendance

```text
/api/attendance/sessions/
/api/attendance/history
/api/attendance/trend
/api/attendance/summary/<student_id>
```

### Dashboard

```text
GET /api/dashboard/statistics
```

---

# 🖥️ Main Application Modules

```text
┌──────────────────────────────────────────┐
│              AttendVision AI             │
├──────────────────────────────────────────┤
│                                          │
│  🔐 Authentication                       │
│                                          │
│  📊 Dashboard                            │
│                                          │
│  🏫 Classes & Divisions                  │
│                                          │
│  👨‍🎓 Student Management                  │
│                                          │
│  📸 Face Registration                    │
│                                          │
│  🤖 AI Attendance                        │
│                                          │
│  📋 Attendance History                   │
│                                          │
│  📈 Analytics                            │
│                                          │
│  📑 Reports                              │
│                                          │
│  👤 Profile                              │
│                                          │
└──────────────────────────────────────────┘
```

---

# 🧪 Testing

The project includes testing of important attendance and recognition scenarios such as:

* Registered student recognition
* Unknown face detection
* Group photo recognition
* Multiple faces
* Absent students
* Manual attendance correction
* Duplicate attendance prevention
* Attendance finalization
* Attendance history
* Attendance statistics

Example recognition result:

```text
Student: Parth Ahire
Similarity: 99.9%
Status: KNOWN
Attendance: PRESENT
```

Example unknown result:

```text
Similarity: 56.2%
Status: UNKNOWN
Attendance: NOT MARKED
```

---

# 📈 Future Enhancements

Possible future improvements include:

* Real-time classroom camera recognition
* Multi-camera attendance
* Improved face-quality assessment
* Multiple face enrollment per student
* Email notifications
* Student attendance portal
* Parent notification system
* Mobile application
* Advanced attendance analytics
* PDF and Excel report generation
* Cloud deployment
* Docker-based deployment
* Role-based Admin/Teacher/Student access
* Attendance prediction
* Anti-spoofing / liveness detection
* Improved recognition threshold calibration
* Audit logs

---

# 🔒 Privacy & Responsible AI

AttendVision AI processes biometric information for the purpose of attendance management.

A production deployment should implement appropriate:

* Student consent procedures
* Institutional privacy policies
* Data retention policies
* Access controls
* Encryption
* Secure storage
* Data deletion procedures
* Audit logging

Face embeddings and student photographs should not be publicly exposed.

---

# 🎓 Academic Project

**Project:** AttendVision AI
**Type:** Final Year Engineering Project
**Domain:** Artificial Intelligence / Computer Vision / Web Development
**Application:** Smart Classroom Attendance System

---

# 👨‍💻 Project Team

| Member         | Role        |
| -------------- | ----------- |
| Ketan Patil    | Developer   |
| Shubham Tidke  | Team Member |
| Darshan Shinde | Team Member |
| Tejas Lodha    | Team Member |

**Group:** 27

---

# 📜 License

This project is developed for educational and academic purposes.

Add an appropriate open-source license to the repository if you intend to distribute the project publicly.

---

# ⭐ Project Vision

The goal of AttendVision AI is to transform traditional classroom attendance into a **faster, smarter, and AI-assisted digital attendance experience**.

```text
Traditional Attendance
        ↓
Manual Roll Call
        ↓
Time Consuming
        ↓
Paper / Manual Records

              ↓

             AI

              ↓

AttendVision AI
        ↓
Face Detection
        ↓
Face Recognition
        ↓
Automatic Attendance
        ↓
Teacher Verification
        ↓
Digital Reports
        ↓
Analytics
```

**AttendVision AI — Making classroom attendance smarter with Artificial Intelligence.** 🤖🎓









































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

MIT — see [LICENSE](LICENSE).#   A t t e n d V i s i o n - A I - A I - P o w e r e d - F a c e - R e c o g n i t i o n - A t t e n d a n c e - S y s t e m 
 
 
