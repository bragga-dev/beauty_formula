"""
Employees endpoints — listagem/detalhe públicos ("Nosso Time") e ajustes
administrativos pontuais (janela de agendamento).
"""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import File, Router, UploadedFile
from django_ratelimit.decorators import ratelimit

from beauty_formula.apps.accounts.schemas.employee_schema import (
    EmployeeBookingWindowOut,
    EmployeeBookingWindowUpdateIn,
    EmployeeOut,
    EmployeeTeamDetailOut,
    EmployeeTeamOut,
    EmployeeUpdateIn,
)
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_id,
    get_public_team_employees,
)
from beauty_formula.apps.accounts.services.employee_service import (
    update_employee_booking_window,
    update_employee_profile_for_admin,
    update_photo_employee_for_admin,
)
from beauty_formula.apps.services.selectors.employee_service_selector import (
    get_services_for_employee,
)
from beauty_formula.apps.core.exceptions.media import InvalidImageFile
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.core.utils.pagination import paginate_queryset
from beauty_formula.apps.core.schemas.deafult_schema import PageOut

router = Router()


@router.get(
    "/team",
    response={200: PageOut[EmployeeTeamOut]},
    auth=None,
    summary="Lista pública de funcionários (\"Nosso Time\")",
    description=(
        "Vitrine pública dos funcionários ativos, sem exigir login. "
        "Filtro opcional por serviço prestado."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def team_list_router(request, service_id: uuid.UUID = None, page: int = 1, page_size: int = 20):
    qs = get_public_team_employees(service_id=service_id)
    return 200, paginate_queryset(qs, page, page_size, EmployeeTeamOut.from_orm)


@router.get(
    "/team/{employee_id}",
    response={200: EmployeeTeamDetailOut, 404: MessageOut},
    auth=None,
    summary="Detalhe público de um funcionário",
    description="Página de perfil público de um funcionário: dados + serviços que ele presta.",
)
@ratelimit(key="ip", rate="60/m", block=True)
def team_detail_router(request, employee_id: uuid.UUID):
    employee = get_employee_by_id(employee_id)
    if not employee or not employee.user.is_active:
        return 404, {"detail": "Funcionário não encontrado."}

    services = get_services_for_employee(employee_id)
    return 200, EmployeeTeamDetailOut.from_orm(employee, services=services)


@router.get(
    "/team/{employee_id}/admin",
    response={200: EmployeeOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin: detalhe completo de um funcionário",
    description=(
        "Mesmo funcionário do endpoint público, mas incluindo username, "
        "gênero, telefone e data de nascimento — dados que a vitrine "
        "pública (\"Nosso Time\") não expõe. Usado na tela de edição do "
        "dashboard admin."
    ),
)
def team_detail_admin_router(request, employee_id: uuid.UUID):
    employee = get_employee_by_id(employee_id)
    if not employee:
        return 404, {"detail": "Funcionário não encontrado."}
    return 200, EmployeeOut.from_orm(employee)


@router.patch(
    "/team/{employee_id}/booking-window",
    response={200: EmployeeBookingWindowOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin ajusta a janela de agendamento (dias à frente) de um funcionário",
    description=(
        "Quantos dias à frente a agenda deste funcionário fica aberta pra "
        "clientes agendarem (padrão: 30). Substitui a antiga constante "
        "global fixa — cada funcionário agora tem a sua própria janela."
    ),
)
@ratelimit(key="user", rate="20/m", block=True)
def update_employee_booking_window_router(request, employee_id: uuid.UUID, payload: EmployeeBookingWindowUpdateIn):
    try:
        result = update_employee_booking_window(employee_id=employee_id, booking_window_days=payload.booking_window_days)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/team/{employee_id}/profile",
    response={200: EmployeeOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin atualiza os dados de perfil de um funcionário",
    description="Atualiza nome, sobrenome, username, gênero, telefone, data de nascimento, instagram e bio.",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_employee_profile_for_admin_router(request, employee_id: uuid.UUID, payload: EmployeeUpdateIn):
    try:
        result = update_employee_profile_for_admin(employee_id=employee_id, payload=payload)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.post(
    "/team/{employee_id}/photo",
    response={200: EmployeeOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin substitui a foto de um funcionário",
)
@ratelimit(key="user", rate="10/h", block=True)
def upload_employee_photo_for_admin_router(request, employee_id: uuid.UUID, photo: UploadedFile = File(...)):
    try:
        result = update_photo_employee_for_admin(employee_id=employee_id, photo=photo)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}