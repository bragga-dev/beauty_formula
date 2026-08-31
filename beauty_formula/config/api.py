from ninja import NinjaAPI, Swagger
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import AuthenticationFailed as JWTAuthenticationFailed
from ninja.errors import ValidationError, AuthenticationError
from django.http import HttpRequest
from django.http import JsonResponse
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.accounts.api.auth import router as auth_router
from beauty_formula.apps.accounts.api.admin import router as admin_router
from beauty_formula.apps.accounts.api.employees import router as employees_router
from beauty_formula.apps.services.api.service import router as services_router
from beauty_formula.apps.services.api.employee_service import router as employee_services_router
from beauty_formula.apps.services.api.employee_working_hours import router as employee_working_hours_router
from beauty_formula.apps.services.api.employee_time_off import router as employee_time_off_router
from beauty_formula.apps.services.api.scheduling import router as scheduling_router
from beauty_formula.apps.services.api.availability import router as availability_router
from beauty_formula.apps.services.api.average_rating import router as average_rating_router
from beauty_formula.apps.website.api.product import router as product_router
from beauty_formula.apps.website.api.contact import router as contact_router
from beauty_formula.apps.payment.api.payment import router as payment_router
from beauty_formula.apps.payment.api.employee_commission import router as commission_router
from beauty_formula.apps.reports.api.monthly_report import router as reports_router


from django_ratelimit.exceptions import Ratelimited
import logging
from django.conf import settings
logger = logging.getLogger("django")


from beauty_formula.apps.core.permissions.auth_classes import (
    AdminOnlyAuth,
    EmployeeOnlyAuth,
    ClientOnlyAuth,
    VerifiedUserAuth,
    ActiveUserAuth,
)

api = NinjaAPI(
    title="FÓRMULA DA BELEZA API",
    version="1.0.0",
    description="API para agendamento de serviços de beleza.",
    auth=[JWTAuth(), AdminOnlyAuth(), EmployeeOnlyAuth(), ClientOnlyAuth(), VerifiedUserAuth(), ActiveUserAuth()],
    urls_namespace="api",
    docs=Swagger(settings={"persistAuthorization": True}),
)


# ── Routers ───────────────────────────────────────────────────────────────────


api.add_router("/auth/", auth_router, tags=["Auth"])
api.add_router("/admin/", admin_router, tags=["Admin"])
api.add_router("/employees/", employees_router, tags=["Employees"])
api.add_router("/services/", services_router, tags=["Services"])
api.add_router("/employee-services/", employee_services_router, tags=["Employee Services"])
api.add_router("/employee-working-hours/", employee_working_hours_router, tags=["Employee Working Hours"])
api.add_router("/employee-time-off/", employee_time_off_router, tags=["Employee Time Off"])
api.add_router("/scheduling/", scheduling_router, tags=["Scheduling"])
api.add_router("/availability/", availability_router, tags=["Availability"])
api.add_router("/average-ratings/", average_rating_router, tags=["Average Ratings"])
api.add_router("/products/", product_router, tags=["Products"])
api.add_router("/contacts/", contact_router, tags=["Contacts"])
api.add_router("/payments/", payment_router, tags=["Payments"])
api.add_router("/commissions/", commission_router, tags=["Commissions"])
api.add_router("/reports/", reports_router, tags=["Reports"])

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


@api.exception_handler(JWTAuthenticationFailed)
def jwt_authentication_failed(request: HttpRequest, exc: JWTAuthenticationFailed):
    """
    Cobre AuthenticationFailed/InvalidToken do ninja_jwt (ex.: usuário
    inativo, token expirado/blacklistado). Sem esse handler, o ninja cai no
    handler genérico de Exception e devolve o dict interno cru do DRF
    (`{'detail': ErrorDetail(...), 'code': ErrorDetail(...)}`) como texto
    pro frontend — foi o que apareceu na tela de cadastro.
    """
    detail = exc.args[0] if exc.args else {}
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    return api.create_response(
        request,
        {"detail": str(message)},
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