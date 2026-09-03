"""
Repository de Scheduling — funções de persistência (criação, atualização,
transições de status e exclusão) de agendamentos.

Como nos demais repositories, essas funções recebem valores já resolvidos
(instâncias de model, não IDs) — resolver `service_id`/`employee_id`/
`client_id` para instância, e qualquer validação de disponibilidade, é
responsabilidade da camada de `services.py`, não daqui.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.service_exception import SchedulingConflict
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.models.service import Service
from django.utils import timezone

@transaction.atomic
def create_scheduling(
    *,
    service: Service,
    client: Client,
    employee: Employee,
    scheduled_time: datetime,
    notes: Optional[str] = None,
    status: Optional[str] = None,
) -> Scheduling:
   
    scheduling = Scheduling(
        service=service,
        client=client,
        employee=employee,
        scheduled_time=scheduled_time,
        notes=notes,
        **({"status": status} if status is not None else {}),
    )
    try:
        scheduling.save()
    except ValidationError as e:
        raise SchedulingConflict("; ".join(e.messages)) from e
    except IntegrityError as e:
        # Rede de segurança final: o ExclusionConstraint do Postgres
        # (`exclude_overlapping_confirmed_slots_per_employee`) pega
        # sobreposição mesmo quando duas transações concorrentes passaram
        # pela validação em Python (`clean()`/`_validate_slot_available`)
        # antes de qualquer uma commitar — o cenário que o lock do
        # funcionário (`_lock_employee_for_scheduling`, em
        # scheduling_service.py) reduz mas não elimina 100%, já que o
        # lock só serializa quem já está dentro da mesma transação
        # Django, não chamadas concorrentes de workers/processos
        # diferentes competindo pelo mesmo lock.
        raise SchedulingConflict("Horário não está mais disponível.") from e
    return scheduling


@transaction.atomic
def update_scheduling(
    scheduling: Scheduling,
    *,
    service: Optional[Service] = None,
    employee: Optional[Employee] = None,
    scheduled_time: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> Scheduling:
    """
    Atualiza campos editáveis de um agendamento existente. Se `service`
    mudar, `price_at_booking`/`duration_at_booking` NÃO são recalculados
    automaticamente pelo `save()` (que só define esses campos na criação),
    então recalculamos aqui pra manter os valores coerentes com o novo
    serviço escolhido.
    """
    update_fields = []

    if service is not None and service.pk != scheduling.service_id:
        scheduling.service = service
        scheduling.price_at_booking = service.price
        scheduling.duration_at_booking = service.duration
        update_fields += ["service", "price_at_booking", "duration_at_booking"]

    if employee is not None:
        scheduling.employee = employee
        update_fields.append("employee")

    if scheduled_time is not None:
        scheduling.scheduled_time = scheduled_time
        update_fields.append("scheduled_time")

    if notes is not None:
        scheduling.notes = notes
        update_fields.append("notes")

    if not update_fields:
        return scheduling

    try:
        # Scheduling.save() já chama full_clean() internamente em toda
        # chamada — não precisamos repetir aqui.
        scheduling.save(update_fields=update_fields + ["updated_at"])
    except ValidationError as e:
        raise SchedulingConflict("; ".join(e.messages)) from e

    return scheduling


@transaction.atomic
def cancel_scheduling(scheduling: Scheduling, *, reason: str, canceled_by: Optional[User]) -> Scheduling:
    """
    Cancela o agendamento (usa o método de domínio já definido no model).
    `canceled_by=None` é válido — usado por cancelamentos automáticos do
    sistema, como `expire_unpaid_scheduling`, que não têm um usuário por
    trás da ação.
    """
    scheduling.cancel(reason=reason, canceled_by=canceled_by)
    return scheduling


@transaction.atomic
def confirm_scheduling(scheduling: Scheduling) -> Scheduling:
    """
    Confirma um atendimento. `scheduling.confirm()` -> `save()` roda o
    `full_clean()` do model, que reconfere sobreposição com outros
    agendamentos CONFIRMED — necessário porque, entre a criação (CREATED)
    e o pagamento cair, outro cliente pode ter confirmado o mesmo horário
    primeiro (ver docstring de `scheduling_service.py`). Sem este
    try/except, esse conflito vira `ValidationError` do Django não
    tratada — que sobe direto pro webhook da Asaas e devolve 500 em vez
    do 200 esperado. Convertida pra `SchedulingConflict`, que
    `payment_service._confirm_scheduling_if_paid` já sabe tratar
    (cancela a reserva perdedora e notifica o admin pra estorno manual).

    O `except IntegrityError` é a mesma rede de segurança do
    ExclusionConstraint descrita em `create_scheduling` — aqui pega o
    caso de duas CONFIRMAÇÕES concorrentes (dois pagamentos quase
    simultâneos pra reservas que conflitam entre si).
    """
    try:
        scheduling.confirm()
    except ValidationError as e:
        raise SchedulingConflict("; ".join(e.messages)) from e
    except IntegrityError as e:
        raise SchedulingConflict("Horário não está mais disponível.") from e
    return scheduling

@transaction.atomic
def complete_scheduling(scheduling: Scheduling) -> Scheduling:
    """Conclui um atendimento ."""
    scheduling.complete()
    return scheduling


@transaction.atomic
def mark_scheduling_as_no_show(scheduling: Scheduling) -> Scheduling:
    """Marca um agendamento como não comparecido."""
    scheduling.mark_as_no_show()
    return scheduling


@transaction.atomic
def reschedule_scheduling(
    scheduling: Scheduling,
    *,
    service: Service,
    employee: Employee,
    scheduled_time: datetime,
    notes: Optional[str] = None,
) -> Scheduling:
  
    new_scheduling = create_scheduling(
        service=service,
        client=scheduling.client,
        employee=employee,
        scheduled_time=scheduled_time,
        notes=notes if notes is not None else scheduling.notes,
        status=Scheduling.SchedulingStatus.CONFIRMED,
    )
    
    scheduling.mark_as_rescheduled(new_scheduling)
    return new_scheduling


@transaction.atomic
def delete_scheduling(scheduling: Scheduling) -> None:
   
    scheduling.delete()

def update_reminder_sent_at(scheduling: Scheduling) -> Scheduling:
    scheduling.reminder_sent_at = timezone.now()
    scheduling.save(update_fields=["reminder_sent_at"])