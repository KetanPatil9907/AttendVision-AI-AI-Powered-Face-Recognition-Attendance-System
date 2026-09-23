# Architecture

## Overview

The Smart Attendance System is a two-tier web application:

```
┌────────────────────────────┐        ┌──────────────────────────────────────┐
│  React SPA (frontend)      │  JSON  │  Django REST API (backend)          │
│  Vite + Tailwind + Recharts│ ─────► │  JWT-secured resource endpoints     │
│  axios client              │  /api  │  Postgres / SQLite data store        │
└────────────────────────────┘        │  ai/ recognition package (stateless) │
                                      └──────────────────────────────────────┘
```

- **Frontend** talks only to `/api/*` and `/media/*`. During development Vite proxies both
  to the Django dev server. In production an nginx container serves the built SPA and proxies
  `/api` and `/media` to the backend.
- **Backend** is DRF with `PageNumberPagination` (20 per page), a global `custom_exception_handler`
  that returns `{message, errors}` (never raw stack traces), and JWT via simplejwt.
- **AI** lives in `backend/ai/` as pure functions operating on image bytes; Django callers wrap them
  in services (`students/services.py`, `attendance/services.py`) that also handle storage.

## Backend applications

| App | Responsibility |
| --- | --- |
| `accounts` | Custom `User` (role + title + mobile), JWT login (username or email) with remember-me expiry, profile, change password, password reset (email link with signed token), admin-only teacher registration. |
| `classes` | `Classroom`, `Division`, `Subject` — all records scoped to `teacher`. |
| `students` | `Student`, `StudentFace`, `FaceEmbedding`, face-registration + face-status actions, list filters/search/ordering. |
| `attendance` | `AttendanceSession`, `AttendanceRecord`, `RecognitionLog`; session routes (records/recognize/finalize/update-records/recognition-logs); analytics views (history, trend, per-student summary, dashboard stats). |
| `reports` | Stateless export service producing PDF (ReportLab), XLSX (openpyxl) or CSV; `ExportContentNegotiation` disables DRF's `?format=` renderer override. |

## Request flow — recognition

```
POST /api/attendance/sessions/{id}/recognize/  (multipart: image)
   │
   ├─ models_ready()?  ── no ──► 503 + friendly model-missing message
   ├─ image size ≤ 10 MB (MAX_IMAGE_SIZE_MB)
   ▼
attendance/services.process_recognition(session, bytes)
   │  gallery = enrolled FaceEmbeddings for the session's division
   ▼
ai.attendance_engine.recognize_faces(bytes, gallery, threshold=0.35)
   │  decode → YuNet detect → align → ArcFace embed → best_match
   ▼
for each face: matched ? mark PRESENT (guarded by UNIQUE(session, student))
               : report UNKNOWN
   │  write RecognitionLog entries (one per detection)
   ▼
{ detections, detected, present, unknown, new_marks, repeated, session_status, threshold }
```

## Database

PostgreSQL in Docker/production (`DB_ENGINE=postgres`), SQLite in local dev (`DB_ENGINE=sqlite`).
Migrations are standard Django migrations in each app.

Critical constraints:

- `AttendanceRecord`: `UniqueConstraint("session", "student")` — duplicate-attendance protection.
- Every queryable model carries a `teacher` FK and all viewsets re-scope to `request.user`.

## Concurrency & session state

- Sessions are `live` → `finalized` → (status locked). `finalize` is idempotent (returns 400 if
  already finalized). Records can be edited only while `live`.
- Recognition is stateless on the AI side; repeated detections of one student update nothing
  (record already `present`) and increment the "repeated" counter.

## Logging & errors

- Django logging to console (`LOG_LEVEL=INFO` default).
- `config/exceptions.py` converts DRF/django errors into `{"message": …, "errors": {…}}`,
  masking internal details for 4xx/5xx.

## Container topology (Docker Compose)

```
nginx (port 8080)
  ├── serves frontend build (dist/)
  └── proxies /api, /media → backend:8000
backend (Gunicorn, port 8000)
  ├── depends_on postgres
  └── mounts shared model/media volume  (see docker-compose.yml "models" volume)
postgres:16 (port 5432, name smart_attendance)
models: one-shot service downloading ONNX files into the shared volume
```

Production note: if you deploy behind a load balancer, keep `ALLOWED_HOSTS` and
`CORS_ALLOWED_ORIGINS` aligned with your public hostnames, and serve `/media` from the same
shared volume.

See `docs/api-reference.md` for endpoints and `docs/ai-pipeline.md` for the recognition details.