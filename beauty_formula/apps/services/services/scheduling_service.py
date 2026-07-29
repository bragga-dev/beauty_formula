"""
Regras de negócio de Scheduling (agendamentos).

Fluxo geral:
- Cliente cria/edita/cancela os PRÓPRIOS agendamentos.
- Funcionário avança o status dos agendamentos que atende (confirmar,
  iniciar, concluir, marcar não comparecimento) e também pode cancelar.
- Admin tem visão total: lista qualquer agendamento, cancela, e é o
  único que pode excluir (hard delete) um registro.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_id, get_employee_by_user_id
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError, EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AssociationNotFound,
    InvalidSchedulingStatusTransition,
    SchedulingCannotBeCanceled,
    SchedulingCannotBeModified,
    SchedulingConflict,
    SchedulingNotFound,
    ServiceNotFound,
)
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.repositories.scheduling_repository import (
    cancel_scheduling as cancel_scheduling_repo,
    complete_scheduling as complete_scheduling_repo,
    confirm_scheduling as confirm_scheduling_repo,
    create_scheduling as create_scheduling_repo,
    delete_scheduling as delete_scheduling_repo,
    mark_scheduling_as_no_show as mark_no_show_repo,
    start_scheduling as start_scheduling_repo,
    update_scheduling as update_scheduling_repo,
)
from beauty_formula.apps.services.schemas.scheduling_schema import (
    SchedulingCreateIn,
    SchedulingOut,
    SchedulingPrivateOut,
    SchedulingUpdateIn,
)
from beauty_formula.apps.services.selectors.availability_selector import is_slot_available
from beauty_formula.apps.services.selectors.employee_service_selector import get_employee_service
from beauty_formula.apps.services.selectors.scheduling_selector import (
    filter_schedulings,
    get_scheduling_by_id,
    get_schedulings_by_client,
    get_schedulings_by_employee,
)
from beauty_formula.apps.services.selectors.service_selector import get_service_by_id

# Status finais — um agendamento nesses estados não pode mais ser editado,
# reagendado ou cancelado, só consultado.
FINAL_STATUSES = [
    Scheduling.SchedulingStatus.COMPLETED,
    Scheduling.SchedulingStatus.CANCELED,
    Scheduling.SchedulingStatus.NO_SHOW,
]


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_employee_offers_service(employee_id: UUID, service_id: UUID) -> None:
    """Garante que o funcionário realmente atende o serviço escolhido."""
    employee_service = get_employee_service(employee_id=employee_id, service_id=service_id)
    if employee_service is None or not employee_service.is_active:
        raise AssociationNotFound(_("Esse funcionário não atende esse serviço."))


def _get_own_client_scheduling(user_id: UUID, scheduling_id: UUID) -> Scheduling:
    """Resolve o Client dono do agendamento e garante que pertence a ele."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return scheduling


def _get_own_employee_scheduling(user_id: UUID, scheduling_id: UUID) -> Scheduling:
    """Resolve o Employee dono do agendamento e garante que pertence a ele."""
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.employee_id != employee.id:
        raise SchedulingNotFound()

    return scheduling


def _validate_slot_available(
    employee_id: UUID,
    scheduled_time: datetime,
    duration: timedelta,
    exclude_scheduling_id: Optional[UUID] = None,
) -> None:
    """
    Garante que o horário pedido cabe na agenda do funcionário — dentro do
    expediente, fora de folgas/bloqueios e sem sobrepor outro agendamento
    ativo (`is_slot_available`, de availability_selector).

    A validação de conflito do model (`Scheduling.clean()`) SÓ enxerga
    sobreposição com outros agendamentos — não sabe nada sobre expediente
    ou folga. Sem essa checagem aqui, seria possível criar/reagendar um
    atendimento fora do horário de trabalho do funcionário ou durante uma
    folga, já que o `full_clean()` do model deixaria passar.

    `exclude_scheduling_id` deve ser passado ao reagendar um agendamento
    já existente, senão ele conta como ocupando o próprio horário atual.
    """
    end_time = scheduled_time + duration
    if not is_slot_available(
        employee_id=employee_id,
        start=scheduled_time,
        end=end_time,
        exclude_scheduling_id=exclude_scheduling_id,
    ):
        raise SchedulingConflict()


# ═══════════════════════════════════════════════════════════════════════════════
# Criação
# ═══════════════════════════════════════════════════════════════════════════════

def create_scheduling_for_client(user_id: UUID, data: SchedulingCreateIn) -> SchedulingOut:
    """Cliente cria um novo agendamento."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    service = get_service_by_id(service_id=data.service_id)
    if service is None or not service.is_active:
        raise ServiceNotFound()

    employee = get_employee_by_id(employee_id=data.employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    _validate_employee_offers_service(employee_id=employee.id, service_id=service.id)
    _validate_slot_available(employee_id=employee.id, scheduled_time=data.scheduled_time, duration=service.duration)

    scheduling = create_scheduling_repo(
        service=service,
        client=client,
        employee=employee,
        scheduled_time=data.scheduled_time,
        notes=data.notes,
    )
    return SchedulingOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem
# ═══════════════════════════════════════════════════════════════════════════════

def list_own_schedulings_for_client(user_id: UUID, active_only: bool = False):
    """Cliente lista os próprios agendamentos (queryset cru — serializado no router)."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    return get_schedulings_by_client(client_id=client.id, active_only=active_only)


def list_own_schedulings_for_employee(user_id: UUID, active_only: bool = False):
    """Funcionário lista os próprios agendamentos (queryset cru — serializado no router)."""
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_schedulings_by_employee(employee_id=employee.id, active_only=active_only)


def list_all_schedulings(
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date=None,
    end_date=None,
    is_active: Optional[bool] = None,
):
    """Admin lista todos os agendamentos, com filtros combináveis."""
    return filter_schedulings(
        service_id=service_id,
        employee_id=employee_id,
        client_id=client_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )


def get_scheduling_detail(scheduling_id: UUID) -> SchedulingPrivateOut:
    """Detalhe administrativo de um agendamento pelo ID."""
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()
    return SchedulingPrivateOut.from_orm(scheduling)


def get_own_scheduling_detail_for_client(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Cliente vê o detalhe de um agendamento próprio."""
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)
    return SchedulingOut.from_orm(scheduling)


def get_own_scheduling_detail_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário vê o detalhe de um agendamento próprio."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    return SchedulingOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Atualização
# ═══════════════════════════════════════════════════════════════════════════════

def update_own_scheduling_for_client(user_id: UUID, scheduling_id: UUID, data: SchedulingUpdateIn) -> SchedulingOut:
    """
    Cliente edita um agendamento próprio — só permitido enquanto o
    agendamento ainda estiver pendente (depois de confirmado, a alteração
    já impacta a agenda do funcionário e deve passar por cancelamento).
    """
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)

    if scheduling.status != Scheduling.SchedulingStatus.PENDING:
        raise SchedulingCannotBeModified(
            _("Só é possível editar um agendamento enquanto ele estiver pendente.")
        )

    service = scheduling.service
    if data.service_id is not None and data.service_id != scheduling.service_id:
        service = get_service_by_id(service_id=data.service_id)
        if service is None or not service.is_active:
            raise ServiceNotFound()

    employee = scheduling.employee
    if data.employee_id is not None and data.employee_id != scheduling.employee_id:
        employee = get_employee_by_id(employee_id=data.employee_id)
        if employee is None:
            raise EmployeeNotFoundError()

    if data.service_id is not None or data.employee_id is not None:
        _validate_employee_offers_service(employee_id=employee.id, service_id=service.id)

    # Reavalia disponibilidade se algo que afeta a agenda mudou: serviço
    # (duração), funcionário ou o próprio horário. `exclude_scheduling_id`
    # evita que o agendamento conte como ocupando seu próprio horário atual.
    if data.service_id is not None or data.employee_id is not None or data.scheduled_time is not None:
        _validate_slot_available(
            employee_id=employee.id,
            scheduled_time=data.scheduled_time or scheduling.scheduled_time,
            duration=service.duration,
            exclude_scheduling_id=scheduling.id,
        )

    scheduling = update_scheduling_repo(
        scheduling,
        service=service if data.service_id is not None else None,
        employee=employee if data.employee_id is not None else None,
        scheduled_time=data.scheduled_time,
        notes=data.notes,
    )
    return SchedulingOut.from_orm(scheduling)


def update_scheduling_by_admin(scheduling_id: UUID, data: SchedulingUpdateIn) -> SchedulingPrivateOut:
    """Admin edita qualquer agendamento que ainda não esteja em status final."""
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()

    if scheduling.status in FINAL_STATUSES:
        raise SchedulingCannotBeModified()

    service = scheduling.service
    if data.service_id is not None and data.service_id != scheduling.service_id:
        service = get_service_by_id(service_id=data.service_id)
        if service is None or not service.is_active:
            raise ServiceNotFound()

    employee = scheduling.employee
    if data.employee_id is not None and data.employee_id != scheduling.employee_id:
        employee = get_employee_by_id(employee_id=data.employee_id)
        if employee is None:
            raise EmployeeNotFoundError()

    if data.service_id is not None or data.employee_id is not None:
        _validate_employee_offers_service(employee_id=employee.id, service_id=service.id)

    if data.service_id is not None or data.employee_id is not None or data.scheduled_time is not None:
        _validate_slot_available(
            employee_id=employee.id,
            scheduled_time=data.scheduled_time or scheduling.scheduled_time,
            duration=service.duration,
            exclude_scheduling_id=scheduling.id,
        )

    scheduling = update_scheduling_repo(
        scheduling,
        service=service if data.service_id is not None else None,
        employee=employee if data.employee_id is not None else None,
        scheduled_time=data.scheduled_time,
        notes=data.notes,
    )
    return SchedulingPrivateOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Cancelamento
# ═══════════════════════════════════════════════════════════════════════════════

def cancel_own_scheduling_as_client(user_id: UUID, scheduling_id: UUID, reason: str) -> SchedulingOut:
    """Cliente cancela um agendamento próprio, respeitando a janela mínima de 2h."""
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)

    if not scheduling.can_be_canceled_by_client:
        raise SchedulingCannotBeCanceled(
            _("Cancelamentos só são permitidos até 2h antes do horário agendado.")
        )

    user = User.objects.get(pk=user_id)
    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    return SchedulingOut.from_orm(scheduling)


def cancel_scheduling_as_employee(user_id: UUID, scheduling_id: UUID, reason: str) -> SchedulingOut:
    """Funcionário cancela um agendamento próprio."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)

    if not scheduling.can_be_canceled_by_admin:
        raise SchedulingCannotBeCanceled()

    user = User.objects.get(pk=user_id)
    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    return SchedulingOut.from_orm(scheduling)


def cancel_scheduling_as_admin(user: User, scheduling_id: UUID, reason: str) -> SchedulingPrivateOut:
    """Admin cancela qualquer agendamento."""
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()

    if not scheduling.can_be_canceled_by_admin:
        raise SchedulingCannotBeCanceled()

    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    return SchedulingPrivateOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Transições de status (funcionário/admin)
# ═══════════════════════════════════════════════════════════════════════════════

def confirm_scheduling_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário confirma um agendamento pendente."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if scheduling.status != Scheduling.SchedulingStatus.PENDING:
        raise InvalidSchedulingStatusTransition(_("Só é possível confirmar um agendamento pendente."))
    scheduling = confirm_scheduling_repo(scheduling)
    return SchedulingOut.from_orm(scheduling)


def start_scheduling_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário inicia o atendimento de um agendamento confirmado."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if scheduling.status != Scheduling.SchedulingStatus.CONFIRMED:
        raise InvalidSchedulingStatusTransition(_("Só é possível iniciar um agendamento confirmado."))
    scheduling = start_scheduling_repo(scheduling)
    return SchedulingOut.from_orm(scheduling)


def complete_scheduling_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário conclui um atendimento em andamento."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if scheduling.status != Scheduling.SchedulingStatus.IN_PROGRESS:
        raise InvalidSchedulingStatusTransition(_("Só é possível concluir um agendamento em andamento."))
    scheduling = complete_scheduling_repo(scheduling)
    return SchedulingOut.from_orm(scheduling)


def mark_scheduling_as_no_show_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário marca um agendamento pendente/confirmado como não comparecido."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if scheduling.status not in (Scheduling.SchedulingStatus.PENDING, Scheduling.SchedulingStatus.CONFIRMED):
        raise InvalidSchedulingStatusTransition(
            _("Só é possível marcar não comparecimento em agendamentos pendentes ou confirmados.")
        )
    scheduling = mark_no_show_repo(scheduling)
    return SchedulingOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Exclusão (somente admin)
# ═══════════════════════════════════════════════════════════════════════════════

def delete_scheduling_by_admin(scheduling_id: UUID) -> None:
    """
    Admin exclui um agendamento permanentemente.
    Use com cautela — prefira cancelar na maioria dos casos, já que isso
    apaga o histórico do agendamento de vez.
    """
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()
    delete_scheduling_repo(scheduling)