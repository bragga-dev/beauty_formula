"""
Regras de negócio de Scheduling (agendamentos).

Fluxo geral (simplificado — sem confirmação manual nem status "em
andamento"):
- Todo agendamento já nasce CONFIRMED: a disponibilidade e os conflitos
  já são validados na criação, então não existe um estado pendente
  aguardando aprovação.
- Cliente cria/edita/cancela/reagenda os PRÓPRIOS agendamentos.
- Funcionário conclui o atendimento, marca não comparecimento ou cancela
  os agendamentos que atende.
- Admin tem visão total: lista qualquer agendamento, cancela, e é o
  único que pode excluir (hard delete) um registro.
- Reagendar NÃO altera o registro atual: ele é marcado como RESCHEDULED
  e um novo agendamento (já CONFIRMED) é criado em seu lugar, preservando
  o histórico para auditoria e relatórios.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils.translation import gettext_lazy as _


from beauty_formula.apps.payment.models.payment_model import Payment
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
    SchedulingCannotBeConfirmed,
)
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.repositories.scheduling_repository import (
    cancel_scheduling as cancel_scheduling_repo,
    complete_scheduling as complete_scheduling_repo,
    create_scheduling as create_scheduling_repo,
    confirm_scheduling as confirm_scheduling_repo,
    delete_scheduling as delete_scheduling_repo,
    mark_scheduling_as_no_show as mark_no_show_repo,
    reschedule_scheduling as reschedule_scheduling_repo,
    update_scheduling as update_scheduling_repo,
)
from beauty_formula.apps.services.schemas.scheduling_schema import (
    SchedulingCreateIn,
    SchedulingOut,
    SchedulingPrivateOut,
    SchedulingRescheduleIn,
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
from beauty_formula.apps.services.tasks.send_confirm_scheduling_to_client import send_confirm_scheduling_to_client
from beauty_formula.apps.services.tasks.send_confirm_scheduling_to_employee import send_confirm_scheduling_to_employee
from beauty_formula.apps.services.tasks.send_cancel_scheduling_to_client import send_cancel_scheduling_to_client
from beauty_formula.apps.services.tasks.send_cancel_scheduling_to_employee import send_cancel_scheduling_to_employee
from beauty_formula.apps.services.tasks.send_scheduling_completed_thanks import send_scheduling_completed_thanks

FINAL_STATUSES = [
    Scheduling.SchedulingStatus.COMPLETED,
    Scheduling.SchedulingStatus.CANCELED,
    Scheduling.SchedulingStatus.NO_SHOW,
    Scheduling.SchedulingStatus.RESCHEDULED,
]
from beauty_formula.apps.payment.services.payment_service import cancel_payment_for_scheduling
from beauty_formula.apps.payment.selectors.payment_selector import get_payments_by_scheduling
from beauty_formula.apps.core.exceptions.payment_exception import (SchedulingPaymentPending)








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


def _dispatch_cancellation_emails(scheduling: Scheduling) -> None:
    """
    Dispara os dois e-mails de cancelamento (cliente e funcionário).

    Extraído porque os três fluxos de cancelamento (cliente, funcionário,
    admin) precisam notificar exatamente as mesmas duas pontas — só quem
    tem permissão pra cancelar é que muda entre eles.
    """
    send_cancel_scheduling_to_client.delay(scheduling_id=scheduling.id)
    send_cancel_scheduling_to_employee.delay(scheduling_id=scheduling.id)


# ═══════════════════════════════════════════════════════════════════════════════
# Criação
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
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
    
    service.increment_bookings()
    return SchedulingOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Confirmação
# ═══════════════════════════════════════════════════════════════════════════════
def confirm_scheduling_for_client(user_id: UUID, scheduling_id:UUID) -> SchedulingOut:
    """Confirma um agendamento mediante pagamento alterando o Status de Criado para Confirmado"""
    scheduling = _get_own_client_scheduling(user_id=user_id, scheduling_id=scheduling_id)
    if scheduling.SchedulingStatus != Scheduling.SchedulingStatus.CREATED:
        raise SchedulingCannotBeConfirmed()
    
    payment = get_payments_by_scheduling(scheduling_id=scheduling_id)
    if not payment.PaymentStatus != Payment.PaymentStatus.RECEIVED:
        raise SchedulingPaymentPending()

    scheduling_confirmed = confirm_scheduling_repo(scheduling)
    send_confirm_scheduling_to_client.delay(user_id=user_id, scheduling_id=scheduling_confirmed.id)
    send_confirm_scheduling_to_employee.delay(scheduling_id=scheduling_confirmed.id)
    return SchedulingOut.from_orm(scheduling_confirmed)

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
    Cliente edita um agendamento próprio.

    Como todo agendamento já nasce CONFIRMED e ocupa a agenda do
    funcionário desde a criação, mudar serviço/funcionário/horário aqui
    passaria por trás da máquina de estados — esse tipo de alteração deve
    usar o endpoint de reagendamento (`reschedule_own_scheduling_for_client`),
    que preserva o histórico do agendamento original. Este endpoint só
    permite editar campos que não afetam a agenda, como `notes`.
    """
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)

    if scheduling.status != Scheduling.SchedulingStatus.CONFIRMED:
        raise SchedulingCannotBeModified(_("Só é possível editar um agendamento enquanto ele estiver confirmado."))

    if data.service_id is not None or data.employee_id is not None or data.scheduled_time is not None:
        raise SchedulingCannotBeModified(_("Para trocar serviço, funcionário ou horário, use o reagendamento."))

    scheduling = update_scheduling_repo(scheduling, notes=data.notes)
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


@transaction.atomic
def cancel_own_scheduling_as_client(user_id: UUID, scheduling_id: UUID, reason: str) -> SchedulingOut:
    """Cliente cancela um agendamento próprio, respeitando a janela mínima de 2h."""
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)

    if not scheduling.can_be_canceled_by_client:
        raise SchedulingCannotBeCanceled(_("Cancelamentos só são permitidos até 2h antes do horário agendado."))

    user = User.objects.get(pk=user_id)
    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    cancel_payment_for_scheduling(scheduling.id)
    _dispatch_cancellation_emails(scheduling)
    return SchedulingOut.from_orm(scheduling)

@transaction.atomic
def cancel_scheduling_as_employee(user_id: UUID, scheduling_id: UUID, reason: str) -> SchedulingOut:
    """Funcionário cancela um agendamento próprio."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)

    if not scheduling.can_be_canceled_by_admin:
        raise SchedulingCannotBeCanceled()

    user = User.objects.get(pk=user_id)
    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    cancel_payment_for_scheduling(scheduling.id)
    _dispatch_cancellation_emails(scheduling)
    return SchedulingOut.from_orm(scheduling)

@transaction.atomic
def cancel_scheduling_as_admin(user: User, scheduling_id: UUID, reason: str) -> SchedulingPrivateOut:
    """Admin cancela qualquer agendamento."""
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()

    if not scheduling.can_be_canceled_by_admin:
        raise SchedulingCannotBeCanceled()

    scheduling = cancel_scheduling_repo(scheduling, reason=reason, canceled_by=user)
    cancel_payment_for_scheduling(scheduling.id)
    _dispatch_cancellation_emails(scheduling)
    return SchedulingPrivateOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Transições de status (funcionário/admin)
#
# Sem confirmação manual nem "em andamento": todo agendamento já nasce
# CONFIRMED. Daqui só se sai por COMPLETED, CANCELED, NO_SHOW ou
# RESCHEDULED — a checagem em si é feita pela máquina de estados do
# model (`Scheduling.can_transition_to`), essas funções só resolvem o
# agendamento do funcionário e traduzem a falha de transição pra
# exceção de domínio esperada pelo router.
# ═══════════════════════════════════════════════════════════════════════════════


@transaction.atomic
def complete_scheduling_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário conclui um atendimento confirmado."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if not scheduling.can_transition_to(Scheduling.SchedulingStatus.COMPLETED):
        raise InvalidSchedulingStatusTransition(_("Só é possível concluir um agendamento confirmado."))
    scheduling = complete_scheduling_repo(scheduling)
    send_scheduling_completed_thanks.delay(scheduling_id=scheduling.id)
    return SchedulingOut.from_orm(scheduling)


def mark_scheduling_as_no_show_for_employee(user_id: UUID, scheduling_id: UUID) -> SchedulingOut:
    """Funcionário marca um agendamento confirmado como não comparecido."""
    scheduling = _get_own_employee_scheduling(user_id, scheduling_id)
    if not scheduling.can_transition_to(Scheduling.SchedulingStatus.NO_SHOW):
        raise InvalidSchedulingStatusTransition(_("Só é possível marcar não comparecimento em agendamentos confirmados."))
    scheduling = mark_no_show_repo(scheduling)
    return SchedulingOut.from_orm(scheduling)


# ═══════════════════════════════════════════════════════════════════════════════
# Reagendamento (cliente)
# ═══════════════════════════════════════════════════════════════════════════════

def reschedule_own_scheduling_for_client(user_id: UUID, scheduling_id: UUID, data: SchedulingRescheduleIn) -> SchedulingOut:
    """
    Cliente reagenda um atendimento confirmado.

    O agendamento atual é marcado como RESCHEDULED (preservando data,
    serviço, funcionário e histórico originais) e um novo agendamento,
    já CONFIRMED, é criado com o novo horário e, opcionalmente, novo
    serviço/funcionário.
    """
    scheduling = _get_own_client_scheduling(user_id, scheduling_id)

    if not scheduling.can_be_rescheduled:
        raise SchedulingCannotBeModified(_("Só é possível reagendar um agendamento confirmado."))

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

    _validate_slot_available(
        employee_id=employee.id,
        scheduled_time=data.scheduled_time,
        duration=service.duration,
        exclude_scheduling_id=scheduling.id,
    )

    new_scheduling = reschedule_scheduling_repo(
        scheduling,
        service=service,
        employee=employee,
        scheduled_time=data.scheduled_time,
        notes=data.notes,
    )
    service.increment_bookings()
    return SchedulingOut.from_orm(new_scheduling)

# ═══════════════════════════════════════════════════════════════════════════════
# Exclusão (somente admin)
# ═══════════════════════════════════════════════════════════════════════════════
@transaction.atomic
def delete_scheduling_by_admin(scheduling_id: UUID) -> None:
    """
    Admin exclui um agendamento permanentemente.
    Use com cautela — prefira cancelar na maioria dos casos, já que isso
    apaga o histórico do agendamento de vez.
    """
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()

    service = scheduling.service  
    delete_scheduling_repo(scheduling)
    service.decrement_bookings()