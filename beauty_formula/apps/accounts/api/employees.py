"""
Employees endpoints — listagem/detalhe públicos ("Nosso Time").
"""
import uuid
from ninja import Router
from django_ratelimit.decorators import ratelimit

from beauty_formula.apps.accounts.schemas.employee_schema import (
    EmployeeTeamDetailOut,
    EmployeeTeamOut,
)
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_id,
    get_public_team_employees,
)
from beauty_formula.apps.services.selectors.service_selector import get_services_for_employee
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