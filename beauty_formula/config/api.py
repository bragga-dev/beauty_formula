from ninja import NinjaAPI, Swagger
from ninja_jwt.authentication import JWTAuth
from ninja.errors import ValidationError, AuthenticationError
from django.http import HttpRequest
from django.http import JsonResponse
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.accounts.api.auth import router as auth_router
from django_ratelimit.exceptions import Ratelimited


# from beauty_formula.apps.accounts.api.admin import router as admin_router

api = NinjaAPI(
    title="FÓRMULA DA BEZELA API",
    version="1.0.0",
    description="API para agendamento de serviços de beleza.",
    auth=JWTAuth(),
    urls_namespace="api",
    docs=Swagger(settings={
        "persistAuthorization": True,
    })
)


# ── Routers ───────────────────────────────────────────────────────────────────


api.add_router("/auth/", auth_router, tags=["Auth"])


# api.add_router("/admin/", admin_router, tags=["Admin"])

# ── Handlers de erro globais ──────────────────────────────────────────────────

@api.exception_handler(ValidationError)
def validation_error(request: HttpRequest, exc: ValidationError):
    return api.create_response(
        request,
        {"detail": exc.errors},
        status=422,
    )


@api.exception_handler(AuthenticationError)
def auth_error(request: HttpRequest, exc: AuthenticationError):
    return JsonResponse(
        {"detail": "Credenciais inválidas ou token expirado."},
        status=401,
    )


@api.exception_handler(PermissionDenied)
def permission_denied(request: HttpRequest, exc: PermissionDenied):
    return api.create_response(
        request,
        {"detail": str(exc)},
        status=403,
    )


@api.exception_handler(Ratelimited)
def ratelimit_error(request: HttpRequest, exc: Ratelimited):
    return api.create_response(request, {"detail": f"Muitas tentativas. Tente novamente mais tarde."}, status=429,)


import logging

from django.conf import settings

logger = logging.getLogger("django")

# ── Handlers de erro globais ──────────────────────────────────────────────────

# ... seus handlers já existentes (ValidationError, AuthenticationError, PermissionDenied, Ratelimited) ...


@api.exception_handler(Exception)
def internal_server_error(request: HttpRequest, exc: Exception):
    logger.exception("Erro não tratado na API: %s", exc)

    payload = {"detail": "Erro interno do servidor."}

    if settings.DEBUG:
        payload["exception"] = str(exc)

    return api.create_response(
        request,
        payload,
        status=500,
    )