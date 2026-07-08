from .base import *


# =========================================================
# CORE
# =========================================================

DEBUG = False

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


# =========================================================
# DATABASE
# =========================================================

DATABASES = {
    "default": env.db("DATABASE_URL")
}


DATABASES["default"]["CONN_MAX_AGE"] = 60


# =========================================================
# SECURITY
# =========================================================

SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = 31536000

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# =========================================================
# CSRF
# =========================================================

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS"
)


# =========================================================
# STATIC / MEDIA
# =========================================================

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"


# =========================================================
# CACHE (REDIS)
# =========================================================

CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends.redis."
            "RedisCache"
        ),
        "LOCATION": env(
            "REDIS_URL",
            default="redis://127.0.0.1:6379/1"
        ),
    }
}


# =========================================================
# SESSION
# =========================================================

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

SESSION_CACHE_ALIAS = "default"


# =========================================================
# CELERY
# =========================================================

CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"


# =========================================================
# DJANGO NINJA
# =========================================================

NINJA_PAGINATION_CLASS = ("ninja.pagination.LimitOffsetPagination")
NINJA_PAGINATION_PER_PAGE = 20


# =========================================================
# CORS
# =========================================================

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[]
)




# =========================================================
# ASAAS
# =========================================================

ASAAS_API_KEY = env("ASAAS_API_KEY")

ASAAS_BASE_URL = env(
    "ASAAS_BASE_URL",
    default="https://api.asaas.com/v3"
)


# =========================================================
# FILE UPLOAD
# =========================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760


# =========================================================
# ADMIN
# =========================================================

ADMINS = [
    ("Admin", env("ADMIN_EMAIL")),
]


# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 8
        }
    },
]


# =========================================================
# PERFORMANCE
# =========================================================

USE_ETAGS = True


# =========================================================
# MINIO PROD
# =========================================================

AWS_S3_VERIFY = True

AWS_QUERYSTRING_AUTH = False

AWS_S3_CUSTOM_DOMAIN = env("MINIO_PUBLIC_URL")

MEDIA_URL = (
    f"https://"
    f"{env('MINIO_PUBLIC_URL')}/"
)

MINIO_URL_PROTOCOL = "https:"


# =========================================================
# JWT
# =========================================================
NINJA_JWT = {
    # ── Tempo de vida dos tokens ──────────────────────────────────────────
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

}