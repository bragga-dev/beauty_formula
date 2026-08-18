from .base import *


# =========================================================
# CORE
# =========================================================

DEBUG = True

SECRET_KEY = env("SECRET_KEY", default="dev-secret-key")

ALLOWED_HOSTS = [
    "*",
]


# =========================================================
# DATABASE
# =========================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
    }
}
# =========================================================
# STATIC / MEDIA
# =========================================================

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"


# =========================================================
# EMAIL
# =========================================================

# EMAIL_BACKEND = ("django.core.mail.backends.console.EmailBackend")
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend")


# =========================================================
# CACHE
# =========================================================

CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends.locmem."
            "LocMemCache"
        ),
    }
}


# =========================================================
# SESSION
# =========================================================

SESSION_ENGINE = ("django.contrib.sessions.backends.db")


# =========================================================
# SECURITY (DEV)
# =========================================================

CSRF_COOKIE_SECURE = False

SESSION_COOKIE_SECURE = False

SECURE_SSL_REDIRECT = False


# =========================================================
# DJANGO NINJA
# =========================================================

NINJA_PAGINATION_CLASS = (
    "ninja.pagination.LimitOffsetPagination"
)

NINJA_PAGINATION_PER_PAGE = 20


# =========================================================
# CORS (FUTURO FRONTEND SEPARADO)
# =========================================================
# CORS_ALLOW_ALL_ORIGINS foi removido: com CORS_ALLOW_CREDENTIALS=True
# (necessário pro cookie httpOnly do refresh token ir e voltar), o
# django-cors-headers passa a refletir qualquer Origin recebida — ou seja,
# ALLOW_ALL + CREDENTIALS na prática abre a API pra qualquer site ler
# respostas autenticadas via CORS. A lista explícita abaixo já cobre os
# hosts de dev (Vite e o preview em :3000).
CORS_ALLOW_CREDENTIALS = True

# =========================================================
# CELERY
# =========================================================

CELERY_TASK_ALWAYS_EAGER = False

CELERY_TASK_EAGER_PROPAGATES = True


# =========================================================
# DEBUG TOOLBAR
# =========================================================

INTERNAL_IPS = ["127.0.0.1",]


# =========================================================
# MINIO DEV
# =========================================================

AWS_S3_VERIFY = False

AWS_QUERYSTRING_AUTH = False

AWS_S3_CUSTOM_DOMAIN = f"{env('MINIO_PUBLIC_URL', default='localhost:9000')}/{AWS_STORAGE_BUCKET_NAME}"
MEDIA_URL = f"http://{AWS_S3_CUSTOM_DOMAIN}/"
MINIO_URL_PROTOCOL = "http:"


# =========================================================
# JWT
# =========================================================
NINJA_JWT = {
    **NINJA_JWT,
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=90),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=100),
}
# ========================================================
# CORS
# =======================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    # TROCAR pelo domínio real do seu projeto na Vercel
    "https://beauty-formula-front.vercel.app",
]

# Opcional: libera também os domínios de preview que a Vercel gera por
# branch/PR (ex.: formula-da-beleza-frontend-git-minha-branch-user.vercel.app).
# Ajuste o prefixo pro nome real do seu projeto na Vercel.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://beauty-formula-front.*\.vercel\.app$",
]