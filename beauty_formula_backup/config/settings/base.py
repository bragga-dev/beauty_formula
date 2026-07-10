from pathlib import Path
from datetime import timedelta
import environ
from colorlog import ColoredFormatter

# =========================================================
# BASE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# =========================================================
# ENV
# =========================================================

env = environ.Env()

environ.Env.read_env(BASE_DIR / ".env")


# =========================================================
# CORE
# =========================================================

SECRET_KEY = env("SECRET_KEY")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


# =========================================================
# DJANGO APPS
# =========================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


# =========================================================
# THIRD PARTY APPS
# =========================================================

THIRD_PARTY_APPS = [
    "ninja",
    "ninja_extra",
    "ninja_jwt",
    "ninja_jwt.token_blacklist",
    "storages",
    # "encrypted_model_fields",
    "corsheaders",
    "phonenumber_field",
]


# =========================================================
# LOCAL APPS
# =========================================================

LOCAL_APPS = [
    "beauty_formula.apps.core",
    "beauty_formula.apps.accounts",
    "beauty_formula.apps.services",
    "beauty_formula.apps.payment",
   
]


# =========================================================
# INSTALLED APPS
# =========================================================

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
)


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",
    "corsheaders.middleware.CorsMiddleware",
]


# =========================================================
# URLS
# =========================================================

ROOT_URLCONF = "beauty_formula.config.urls"



# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =========================================================
# WSGI / ASGI
# =========================================================

WSGI_APPLICATION = "beauty_formula.config.wsgi.application"

ASGI_APPLICATION = "beauty_formula.config.asgi.application"


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
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# =========================================================
# MEDIA FILES
# =========================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================================================
# SECURITY
# =========================================================

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# =========================================================
# REDIS
# =========================================================

REDIS_URL = env(
    "REDIS_URL",
    default="redis://localhost:6379/0",
)

# =========================================================
# CELERY / RABBITMQ
# =========================================================
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=f"amqp://{env('RABBITMQ_USER')}:{env('RABBITMQ_PASSWORD')}@{env('RABBITMQ_HOST')}:{env('RABBITMQ_PORT')}/{env('RABBITMQ_VHOST', default='')}"
)

CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default=REDIS_URL,
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# =========================================================
# LOGGING
# =========================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "colorized": {
            "()": ColoredFormatter,
            "format": "%(log_color)s[{asctime}] %(levelname)-8s %(name)s %(reset)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            "style": "%",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colorized",
            "stream": "ext://sys.stdout",
        },
    },

    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =========================================================
# ASAAS
# =========================================================
ASAAS_API_KEY = env("ASAAS_API_KEY")
ASAAS_BASE_URL = env("ASAAS_BASE_URL", default="https://api-sandbox.asaas.com/v3")


# =========================================================
# EMAIL
# =========================================================
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="bragawebdevelopment@gmail.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = "[Beauty_formula]"
ADMINS = [("Admin", env("ADMIN_EMAIL")),]
EMAIL_TIMEOUT = 30
EMAIL_USE_LOCALTIME = True
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_CHARSET = "utf-8"
DEFAULT_REPLY_TO_EMAIL = env("DEFAULT_REPLY_TO_EMAIL", default=DEFAULT_FROM_EMAIL)

# =========================================================
# JWT
# =========================================================
NINJA_JWT = {
    # ── Rotação de refresh ────────────────────────────────────────────────
    # A cada uso do refresh, um novo é gerado e o anterior é invalidado
    "ROTATE_REFRESH_TOKENS":    True,  # exige ninja_jwt.token_blacklist
    "BLACKLIST_AFTER_ROTATION": True,  # exige ninja_jwt.token_blacklist

    # ── Login ─────────────────────────────────────────────────────────────
    "UPDATE_LAST_LOGIN": True,  # atualiza User.last_login no login

    # ── Algoritmo e chave ─────────────────────────────────────────────────
    "ALGORITHM":   "HS256",
    "SIGNING_KEY": env("SECRET_KEY"),  # ou uma chave JWT independente (recomendado)
    "VERIFYING_KEY": None,

    # ── Header ────────────────────────────────────────────────────────────
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME":  "HTTP_AUTHORIZATION",

    # ── Identificação do usuário no token ─────────────────────────────────
    # Seu User usa UUID como PK — precisa declarar explicitamente
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    # ── Outros ───────────────────────────────────────────────────────────
    "LEEWAY": 0,
    "AUDIENCE": None,
    "ISSUER": None,
}

# =========================================================
# AUTH
# =========================================================

AUTH_USER_MODEL = "accounts.User"


# =========================================================
# MINIO / S3
# =========================================================

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")

AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")

AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")

AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")

AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1",)

AWS_DEFAULT_ACL = None

AWS_S3_FILE_OVERWRITE = False

AWS_S3_ADDRESSING_STYLE = "path"

STORAGES = {
    "default": {
        "BACKEND": "beauty_formula.config.storages.MediaFilesStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
# =========================================================
# FIELD ENCRYPTION
# =========================================================
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY") 


# =========================================================
# FRONTEND  
# =========================================================
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
BACKEND_URL  = env("BACKEND_URL",  default="http://localhost:8000")


# =========================================================
# CACHES (REDIS)
# =========================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = False  