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
from django.db import transaction

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.service_exception import SchedulingConflict
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.models.service import Service


@transaction.atomic
def create_scheduling(
    *, service: Service, client: Client, employee: Employee, scheduled_time: datetime, notes: Optional[str] = None
) -> Scheduling:
    """
    Cria um novo agendamento. `price_at_booking`/`duration_at_booking` são
    preenchidos automaticamente pelo `Scheduling.save()` a partir do
    `service`. `full_clean()` (chamado no save do model) valida conflito
    de horário do funcionário — convertido aqui pra `SchedulingConflict`,
    a exceção de domínio usada pelas camadas acima.
    """
    scheduling = Scheduling(
        service=service,
        client=client,
        employee=employee,
        scheduled_time=scheduled_time,
        notes=notes,
    )
    try:
        scheduling.save()
    except ValidationError as e:
        raise SchedulingConflict("; ".join(e.messages)) from e
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
def cancel_scheduling(scheduling: Scheduling, *, reason: str, canceled_by: User) -> Scheduling:
    """Cancela o agendamento (usa o método de domínio já definido no model)."""
    scheduling.cancel(reason=reason, canceled_by=canceled_by)
    return scheduling


@transaction.atomic
def confirm_scheduling(scheduling: Scheduling) -> Scheduling:
    """Confirma um agendamento pendente."""
    scheduling.confirm()
    return scheduling


@transaction.atomic
def start_scheduling(scheduling: Scheduling) -> Scheduling:
    """Inicia o atendimento de um agendamento confirmado."""
    scheduling.start()
    return scheduling


@transaction.atomic
def complete_scheduling(scheduling: Scheduling) -> Scheduling:
    """Conclui um atendimento em andamento."""
    scheduling.complete()
    return scheduling


@transaction.atomic
def mark_scheduling_as_no_show(scheduling: Scheduling) -> Scheduling:
    """Marca um agendamento como não comparecido."""
    scheduling.mark_as_no_show()
    return scheduling


@transaction.atomic
def delete_scheduling(scheduling: Scheduling) -> None:
    """
    Exclui o agendamento permanentemente do banco.
    Use com cautela — prefira cancelar (soft delete) na maioria dos casos,
    já que isso apaga o histórico do agendamento de vez.
    """
    scheduling.delete()