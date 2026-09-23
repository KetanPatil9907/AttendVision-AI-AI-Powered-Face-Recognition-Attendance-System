# API Reference

Base URL: `/api` (Django dev server `http://127.0.0.1:8000/api`; proxied from the SPA).

Authentication: `Authorization: Bearer <access>` for every protected route. Access tokens live
60 min by default; the client refreshes automatically (`POST /api/auth/refresh`) and retries once.
Errors are uniform: `{"message": string, "errors": {}}` with an appropriate HTTP status.

> Trailing-slash convention: router-generated routes require a trailing `/`
> (`/students/`, `/attendance/sessions/…/`); hand-wired routes have **no** trailing slash
> (`/auth/login`, `/attendance/history`, `/dashboard/statistics`, `/reports/export`).

---

## Authentication (`/api/auth/…`)

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| POST | `/auth/login` | public | `{username, password, remember_me}` → `{access, refresh, remember_me, user}`. Username *or* email accepted. |
| POST | `/auth/refresh` | public | `{refresh}` → rotated `{access, refresh}`. |
| POST | `/auth/logout` | auth | `{refresh}` → blacklists token. |
| GET | `/auth/me` | auth | Current user profile. |
| PATCH | `/auth/profile` | auth | Update `first_name`, `last_name`, `title`, `mobile`, `email`. |
| POST | `/auth/change-password` | auth | `{old_password, new_password}`. |
| POST | `/auth/forgot-password` | public | `{email}` → always returns the same generic message (no account enumeration). Emails a signed reset link (console/STMP). |
| POST | `/auth/reset-password` | public | `{email, token, new_password}` → sets a new password; 400 on invalid/expired token. |
| POST | `/auth/register-teacher` | admin | Create a Teacher account (`{username, email, password, first_name, last_name, title, mobile}`). |
| GET | `/auth/teachers` | admin | List teacher accounts. |

---

## Classes (`/api/classes/…`)

All scoped to the authenticated teacher. Router routes end with `/`.

| Method | Path | Description |
| --- | --- | --- |
| GET/POST | `/classes/classrooms/` | List/create classrooms. `search` qparam. |
| GET/PATCH/DELETE | `/classes/classrooms/{id}/` | Retrieve/update/delete. |
| GET/POST | `/classes/divisions/` | List/create. `classroom={id}` filter. |
| GET/PATCH/DELETE | `/classes/divisions/{id}/` | Retrieve/update/delete (ownership checked). |
| GET/POST | `/classes/subjects/` | List/create. `classroom={id}` filter. |
| GET/PATCH/DELETE | `/classes/subjects/{id}/` | Retrieve/update/delete. |

Classroom serializer fields: `id, name, code, academic_year, description, created_at,
division_count, subject_count, student_count`.
Division: `id, classroom, classroom_id, class_name, name, code, academic_year, student_count`.
Subject: `id, classroom, className, class_name, name, code, created_at`.

---

## Students (`/api/students/…`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/students/` | Paginated list `{count,next,previous,results}`. Filters: `search`, `division`, `classroom`, `status`, `gender`; `ordering` = `roll_number`/`-roll_number`/`full_name`/`-full_name`/`created_at`/`-created_at`. |
| POST | `/students/` | Create: `{full_name, roll_number, student_id, email, mobile, gender, date_of_birth, academic_year, status, division}`. |
| GET | `/students/{id}/` | Detail incl. `faces` (photo urls) and `has_embedding`/`embedding_dim`. |
| PATCH | `/students/{id}/` | Partial update (same fields as create). |
| DELETE | `/students/{id}/` | Delete (attendance history retained). |
| POST | `/students/{id}/face-registration/` | Multipart `image` (≤10 MB). Exactly one usable face required; no-face / multi-face / poor quality → 422 with a friendly message; missing models → 503. |
| DELETE | `/students/{id}/face-registration/` | Remove all photos + embedding (privacy consent/withdraw). |
| GET | `/students/{id}/face-status/` | `{photo_count, max_photos: 3, face_registered, photos:[{id, image}]}`. |

---

## Attendance (`/api/attendance/…`)

### Sessions (router, trailing `/`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/sessions/` | Paginated list. Filters: `classroom`, `division`, `subject`, `date`, `status`. |
| POST | `/sessions/` | Create `{classroom, division, subject, date, lecture_number}`; auto-creates a roster of `AttendanceRecord`s. |
| GET | `/sessions/{id}/` | Session detail with counts (`present_count`, `absent_count`, `total_students`, `percentage`). |
| PATCH/DELETE | `/sessions/{id}/` | Update / delete. |
| GET | `/sessions/{id}/records/` | `{session, records:[…]}`; `status` and `search` qparams. |
| POST | `/sessions/{id}/recognize/` | Multipart `image` → AI recognition; every detected face is processed independently. Returns `{detections, detected, present, unknown, ambiguous, low_quality, new_marks, repeated, manual_lock, session_status, threshold, margin}`. Error responses carry a machine-readable `code` (e.g. `code: "session_finalized"`). |
| POST | `/sessions/{id}/update-records/` | `{updates:[{id, status: present|absent}]}` manual correction (live sessions only). |
| POST | `/sessions/{id}/finalize/` | Lock the session; remaining unmarked students become absent. |
| GET | `/sessions/{id}/recognition-logs/` | Paginated recognition attempt log. |

Recognition detection shape:

```json
{
  "bbox": [x, y, w, h],
  "confidence": 0.941,
  "confidence_pct": 94.1,
  "detector_score": 0.993,
  "student_id": 4,
  "student_name": "Rahul Patil",
  "roll_number": "01",
  "matched": true,
  "ambiguous": false,
  "low_quality": false,
  "status": "MATCHED",         // MATCHED | AMBIGUOUS | UNKNOWN | LOW_QUALITY
  "mark_status": "marked",     // marked | already_present | manual_lock | unknown | ambiguous | low_quality
  "face_index": 0,             // detection order (largest face first)
  "face_width": 142,
  "face_height": 158,
  "quality": "GOOD",           // GOOD | LOW_QUALITY
  "quality_issues": [],        // reasons when quality fails (identification not attempted)
  "sharpness": 203.0           // face-crop Laplacian variance
}
```

`manual_lock` = the face matched, but the teacher had manually marked that student
absent for this session, so the manual correction is kept (a `manual_lock` counter is
returned alongside `new_marks`).

`ambiguous` = the face cleared `threshold` but not the `margin` rule (too close to the
runner-up student — a look-alike). It is logged as `REJECTED` and **never** marked;
the response's `ambiguous` counter reports how many faces were too close to call.

`low_quality` = the face failed the configurable quality gate (too small, blurry, or
weakly detected). Identification is not attempted: the face is logged as `REJECTED`
with the reasons in `quality_issues`, and the response's `low_quality` counter
reports how many faces were skipped this way.

### Analytics (hand-wired, no trailing slash)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/attendance/history` | All sessions with per-session totals. Filters: `date_from`, `date_to`, `classroom`, `division`, `subject`, `status` (`finalized`), `student`, `search`. |
| GET | `/attendance/trend` | Daily present/absent series (30 days default, `days` max 90). |
| GET | `/attendance/summary/{student_id}` | Per-student profile: `summary` (total/present/absent/% ), `monthly` (6 months), `subjects`. |
| GET | `/dashboard/statistics` | Dashboard aggregate: `counts`, `today`, `average_attendance`, `class_wise`, `recent_sessions`, `teacher`. |

---

## Reports (`/api/reports/…`)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/reports/export` | File download. Query params: `type` (`all`, `daily`, `weekly`, `monthly`, `class`, `subject`, `student`), `format` (`pdf`, `xlsx`, `csv`), `date_from`, `date_to`, `classroom`, `division`, `subject`. |

Only **finalized** sessions are exported. Augmented `Content-Disposition: attachment;
filename="<type>_report.<ext>"`. The `?format=` parameter is interpreted by the endpoint itself
(special content-negotiation avoids DRF's renderer override).

---

## HTTP statuses used

| Code | Meaning |
| --- | --- |
| 200/201 | Success / created |
| 400 | Validation / bad request (message explains) |
| 401 | Missing/invalid token |
| 403 | Forbidden (e.g., teacher on admin-only route) |
| 404 | Not found / trailing-slash redirect on router URLs |
| 422 | AI registration rejection (no face, multiple faces, poor quality) |
| 503 | AI models not downloaded |

## Sample login flow

```bash
# 1. Login (username or email)
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"sir","password":"YourPass"}'   # => {access, refresh, user}

# 2. Use the token
curl http://127.0.0.1:8000/api/dashboard/statistics \
  -H "Authorization: Bearer <access>"

# 3. Export a PDF report
curl -OJ "http://127.0.0.1:8000/api/reports/export?type=class&format=pdf&classroom=1" \
  -H "Authorization: Bearer <access>"
```