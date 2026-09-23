"""
Django settings for the Smart Attendance System backend.

All secret configuration lives in environment variables / .env.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=None):
    raw = os.getenv(name, "")
    if not raw:
        return default or []
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "accounts",
    "classes",
    "students",
    "attendance",
    "reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------
# Database: PostgreSQL by default when available, SQLite as local fallback.
# --------------------------------------------------------------------------
DATABASE_ENGINE = os.getenv("DB_ENGINE", "postgres")

if DATABASE_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "smart_attendance"),
            "USER": os.getenv("POSTGRES_USER", "attendance"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "attendance"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# DRF + JWT
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
}

ACCESS_TOKEN_LIFETIME = timedelta(
    minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
)
REFRESH_TOKEN_LIFETIME = timedelta(
    days=int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
)
REMEMBER_ME_REFRESH_LIFETIME = timedelta(
    days=int(os.getenv("REMEMBER_ME_REFRESH_DAYS", "30"))
)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": ACCESS_TOKEN_LIFETIME,
    "REFRESH_TOKEN_LIFETIME": REFRESH_TOKEN_LIFETIME,
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)

# --------------------------------------------------------------------------
# Face recognition (AI) configuration
# --------------------------------------------------------------------------
AI_MODELS_DIR = os.getenv("AI_MODELS_DIR") or str(BASE_DIR / "media" / "models")
AI_DETECTOR_MODEL = os.getenv("AI_DETECTOR_MODEL", "face_detection_yunet_2023mar.onnx")
AI_RECOGNITION_MODEL = os.getenv("AI_RECOGNITION_MODEL", "w600k_r50.onnx")
# Cosine similarity threshold - configurable per deployment. Detections at or
# above this cosine similarity are treated as a confident match. Measured on
# this deployment's gallery (aligned pipeline): enrolled students score
# 0.85-1.00 (same photo ~1.00, a different photo of the same student
# >= 0.85) while unenrolled faces score 0.03-0.16 and the closest
# cross-student pair sits at 0.21, so 0.70 separates them with a wide gap.
# (0.35 was the historic default and let ANY unenrolled face match.)
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.70"))
# The best match must also beat the runner-up STUDENT by this cosine gap,
# otherwise the detection is reported as ambiguous instead of guessing
# between look-alike classmates. Genuine matches measure >= 0.70 margin;
# rejected probes measure <= 0.01 - the rule keeps protecting as the roster
# (and look-alike chances) grows.
RECOGNITION_MARGIN = float(os.getenv("RECOGNITION_MARGIN", "0.15"))
# --- Face quality gate (reported as LOW_QUALITY) ---------------------------
# A detected face must clear ALL of these before an embedding is generated.
# Failing faces are reported with status LOW_QUALITY (never matched, never
# marked). Defaults were measured on this deployment: genuine registration
# photos have face-crop sharpness >= 73 and face widths >= 120 px, while
# heavily blurred crops measure <= 8 and junk detections sit under 40 px.
# The absolute pixel floor is what matters for embedding quality; the
# relative (ratio) gate is a secondary sanity check - the old 0.04 default
# silently dropped distant students in large (4000 px) classroom photos,
# hence the looser 0.02 default.
RECOGNITION_MIN_FACE_PX = int(os.getenv("RECOGNITION_MIN_FACE_PX", "40"))
RECOGNITION_MIN_FACE_RATIO = float(os.getenv("RECOGNITION_MIN_FACE_RATIO", "0.02"))
RECOGNITION_MIN_DETECTOR_SCORE = float(os.getenv("RECOGNITION_MIN_DETECTOR_SCORE", "0.5"))
RECOGNITION_MIN_FACE_SHARPNESS = float(os.getenv("RECOGNITION_MIN_FACE_SHARPNESS", "20"))

# --------------------------------------------------------------------------
# Upload / file limits
# --------------------------------------------------------------------------
MAX_IMAGE_SIZE_MB = 10
# 3-5 varied enrollment photos per student (front / angles / lighting) give
# the matcher the most to work with.
MAX_STUDENT_PHOTOS = 5
STUDENT_PHOTO_DIR = "student_faces"
RECOGNITION_LOG_IMAGE_DIR = "recognition"

# --------------------------------------------------------------------------
# Email (used by the password-reset flow).
# In development emails are printed to the console; override with SMTP
# environment variables for production.
# --------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Smart Attendance <no-reply@smartattendance.local>"
)
PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT", "86400"))

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {module} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
}