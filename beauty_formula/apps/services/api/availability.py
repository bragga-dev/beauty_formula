"""
Rota pública de disponibilidade — cliente consulta os horários livres
de um funcionário pra um serviço antes de agendar.
"""
from datetime import date
from typing import List
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeTeamOut
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AssociationNotFound,
    InvalidAvailabilityRequest,
    ServiceNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.services.schemas.availability_schema import AvailabilitySlotOut
from beauty_formula.apps.services.schemas.employee_calendar_schema import (
    EmployeeCalendarOut,
    PublicEmployeeCalendarOut,
)
from beauty_formula.apps.services.services.availability_service import (
    get_employee_availability,
    list_eligible_employees_for_service,
)
from beauty_formula.apps.services.services.employee_calendar_service import (
    get_employee_calendar,
    get_public_employee_calendar,
)

router = Router()


@router.get(
    "/eligible-employees/{service_id}",
    response={200: List[EmployeeTeamOut], 400: MessageOut, 404: MessageOut},
    auth=None,
    summary="Profissionais aptos e com disponibilidade real pra um serviço",
    description=(
        "Etapa 'Profissional' do fluxo de agendamento: devolve só quem "
        "realmente atende esse serviço (EmployeeService ativo) E tem "
        "pelo menos um horário livre na janela de agendamento — não só "
        "quem está vinculado. Lista vazia = nenhum profissional disponível "
        "agora pra esse serviço."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def eligible_employees_router(request, service_id: UUID):
    try:
        employees = list_eligible_employees_for_service(service_id=service_id)
        return 200, [EmployeeTeamOut.from_orm(employee) for employee in employees]
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee/{employee_id}",
    response={200: List[AvailabilitySlotOut], 400: MessageOut, 404: MessageOut},
    auth=None,
    summary="Disponibilidade pública de um funcionário pra um serviço numa data",
    description=(
        "Retorna os slots livres do funcionário na data pedida, já do "
        "tamanho da duração do serviço. Sem login exigido — o cliente "
        "precisa ver isso antes de decidir agendar."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def employee_availability_router(request, employee_id: UUID, service_id: UUID, date: date):
    try:
        slots = get_employee_availability(employee_id=employee_id, service_id=service_id, target_date=date)
        return 200, slots
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except InvalidAvailabilityRequest as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee/{employee_id}/public-calendar",
    response={200: PublicEmployeeCalendarOut, 400: MessageOut, 404: MessageOut},
    auth=None,
    summary="Calendário mensal público de um funcionário (expediente, bloqueios e disponibilidade real, sem dado de cliente)",
    description=(
        "Versão pública da tela de calendário: pra cada dia do mês pedido, "
        "devolve o expediente, os bloqueios (folgas/férias/pausas) e os "
        "intervalos realmente livres (já descontando expediente, bloqueios "
        "e agendamentos existentes) — sem login exigido e sem nenhum dado "
        "de cliente ou agendamento específico."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def public_employee_calendar_router(request, employee_id: UUID, month: date):
    try:
        calendar_data = get_public_employee_calendar(employee_id=employee_id, month=month)
        return 200, calendar_data
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except InvalidAvailabilityRequest as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee/{employee_id}/calendar",
    response={200: EmployeeCalendarOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê o calendário mensal de um funcionário (expediente, bloqueios e agendamentos, dia a dia)",
    description=(
        "Alimenta a tela de calendário do painel: pra cada dia do mês "
        "pedido, devolve o expediente daquele dia da semana, os bloqueios "
        "(folgas/férias/pausas) que caem nele, os agendamentos ativos e um "
        "sinal se o dia ainda está dentro da janela de agendamento do "
        "funcionário (`booking_window_days`)."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def employee_calendar_router(request, employee_id: UUID, month: date):
    try:
        calendar_data = get_employee_calendar(employee_id=employee_id, month=month)
        return 200, calendar_data
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except InvalidAvailabilityRequest as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}