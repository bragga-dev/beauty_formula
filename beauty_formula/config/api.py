# from ninja import NinjaAPI, Swagger
# from ninja_jwt.authentication import JWTAuth
# from ninja.errors import ValidationError, AuthenticationError
# from django.http import HttpRequest
# from django.http import JsonResponse
# from beauty_formula.apps.users.exceptions import PermissionDenied
# from beauty_formula.apps.users.api.auth import router as auth_router
# from beauty_formula.apps.users.api import router as users_router
# from beauty_formula.apps.community.api import router as community_router
# from beauty_formula.apps.users.api.admin import router as admin_router

# api = NinjaAPI(
#     title="FÓRMULA DA BEZELA API",
#     version="1.0.0",
#     description="API para agendamento de serviços de beleza.",
#     auth=JWTAuth(),
#     urls_namespace="api",
#     docs=Swagger(settings={
#         "persistAuthorization": True,
#     })
# )


# # ── Routers ───────────────────────────────────────────────────────────────────

# api.add_router("/core/", auth_router, tags=["Core"])
# api.add_router("/auth/", auth_router, tags=["Auth"])
# api.add_router("/accounts/", users_router, tags=["Accounts"])
# api.add_router("/services/", community_router, tags=["Services"])
# api.add_router("/admin/", admin_router, tags=["Admin"])

# # ── Handlers de erro globais ──────────────────────────────────────────────────

# @api.exception_handler(ValidationError)
# def validation_error(request: HttpRequest, exc: ValidationError):
#     return api.create_response(
#         request,
#         {"detail": exc.errors},
#         status=422,
#     )


# @api.exception_handler(AuthenticationError)
# def auth_error(request: HttpRequest, exc: AuthenticationError):
#     return JsonResponse(
#         {"detail": "Credenciais inválidas ou token expirado."},
#         status=401,
#     )


# @api.exception_handler(PermissionDenied)
# def permission_denied(request: HttpRequest, exc: PermissionDenied):
#     return api.create_response(
#         request,
#         {"detail": str(exc)},
#         status=403,
#     )