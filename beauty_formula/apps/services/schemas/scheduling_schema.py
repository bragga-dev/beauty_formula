from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from django.utils import timezone
from ninja import Schema
from pydantic import field_validator

from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.accounts.schemas.client_schema import ClientOut
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut
from beauty_formula.apps.services.schemas.service_schema import ServiceOut


class SchedulingStatusEnum(str, Enum):
    """Enum para status do agendamento - espelha o modelo Scheduling.SchedulingStatus"""
    CREATED = "created"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELED = "canceled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        choices_dict = dict(Scheduling.SchedulingStatus.choices)
        return choices_dict.get(value, value)


def _duration_to_minutes(scheduling: Scheduling) -> int:
    """Converte DurationField para minutos."""
    return int(scheduling.duration_at_booking.total_seconds() // 60)


class SchedulingOut(Schema):
    """
    Representação de um agendamento para visualização do cliente.

    Segue o padrão dos demais Out schemas: expõe objetos relacionados
    completos (service, client, employee) em vez de apenas IDs.

    Client/Employee/User usam um `from_orm` próprio (por causa do
    `photo_url` calculado), então este schema também precisa de um
    `from_orm` próprio — a resolução automática do Ninja/Pydantic não
    chamaria esses métodos customizados sozinha.
    """
    id: uuid.UUID
    service: ServiceOut
    client: ClientOut
    employee: EmployeeOut
    scheduled_time: datetime
    status: SchedulingStatusEnum
    price_at_booking: Decimal
    duration_at_booking: int
    notes: Optional[str] = None
    canceled_at: Optional[datetime] = None
    canceled_reason: Optional[str] = None
    canceled_by: Optional[UserOut] = None
    rated_at: Optional[datetime] = None
    rescheduled_to_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, scheduling: Scheduling) -> "SchedulingOut":
        return cls(
            id=scheduling.id,
            service=ServiceOut.from_orm(scheduling.service),
            client=ClientOut.from_orm(scheduling.client),
            employee=EmployeeOut.from_orm(scheduling.employee),
            scheduled_time=scheduling.scheduled_time,
            status=scheduling.status,
            price_at_booking=scheduling.price_at_booking,
            duration_at_booking=_duration_to_minutes(scheduling),
            notes=scheduling.notes,
            canceled_at=scheduling.canceled_at,
            canceled_reason=scheduling.canceled_reason,
            canceled_by=UserOut.from_orm(scheduling.canceled_by) if scheduling.canceled_by_id else None,
            rated_at=scheduling.rated_at,
            rescheduled_to_id=scheduling.rescheduled_to_id,
            created_at=scheduling.created_at,
            updated_at=scheduling.updated_at,
        )


class SchedulingPrivateOut(Schema):
    """
    Representação administrativa de um agendamento - inclui campos
    adicionais como is_active e objetos completos relacionados.
    """
    id: uuid.UUID
    service: ServiceOut
    client: ClientOut
    employee: EmployeeOut
    canceled_by: Optional[UserOut] = None
    scheduled_time: datetime
    status: SchedulingStatusEnum
    price_at_booking: Decimal
    duration_at_booking: int
    notes: Optional[str] = None
    canceled_at: Optional[datetime] = None
    canceled_reason: Optional[str] = None
    rated_at: Optional[datetime] = None
    rescheduled_to_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, scheduling: Scheduling) -> "SchedulingPrivateOut":
        return cls(
            id=scheduling.id,
            service=ServiceOut.from_orm(scheduling.service),
            client=ClientOut.from_orm(scheduling.client),
            employee=EmployeeOut.from_orm(scheduling.employee),
            canceled_by=UserOut.from_orm(scheduling.canceled_by) if scheduling.canceled_by_id else None,
            scheduled_time=scheduling.scheduled_time,
            status=scheduling.status,
            price_at_booking=scheduling.price_at_booking,
            duration_at_booking=_duration_to_minutes(scheduling),
            notes=scheduling.notes,
            canceled_at=scheduling.canceled_at,
            canceled_reason=scheduling.canceled_reason,
            rated_at=scheduling.rated_at,
            rescheduled_to_id=scheduling.rescheduled_to_id,
            is_active=scheduling.is_active,
            created_at=scheduling.created_at,
            updated_at=scheduling.updated_at,
        )


class SchedulingCreateIn(Schema):
    """
    Criação de um novo agendamento.

    O cliente informa o serviço, funcionário, horário e observações.
    O preço e duração são preenchidos automaticamente a partir do serviço.
    """
    service_id: uuid.UUID
    employee_id: uuid.UUID
    scheduled_time: datetime
    notes: Optional[str] = None

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time_create(cls, v: datetime) -> datetime:
        """
        Normaliza para aware (o cliente pode mandar um ISO sem offset) e
        valida se o horário agendado não está no passado.

        USE_TZ=True no projeto faz `timezone.now()` retornar aware — sem
        essa normalização, comparar com um `v` naive (vindo direto do
        parse do JSON) explode com TypeError, e o mesmo problema se
        repetiria mais à frente, na validação de conflito de horário do
        model.
        """
        if timezone.is_naive(v):
            v = timezone.make_aware(v)
        if v < timezone.now():
            raise ValueError("O horário agendado não pode ser no passado.")
        return v


class SchedulingUpdateIn(Schema):
    """
    Atualização parcial de um agendamento - PATCH.

    Apenas campos que podem ser alterados manualmente. Mudança de status
    tem endpoint e validação próprios (transições) — não é feita aqui.
    """
    service_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None
    scheduled_time: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time_update(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Normaliza para aware e valida se o horário agendado não está no passado."""
        if v is None:
            return v
        if timezone.is_naive(v):
            v = timezone.make_aware(v)
        if v < timezone.now():
            raise ValueError("O horário agendado não pode ser no passado.")
        return v


class SchedulingCancelIn(Schema):
    """Schema específico para cancelamento de agendamento."""
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Motivo do cancelamento é obrigatório.")
        return v


class SchedulingRescheduleIn(Schema):
    """
    Reagendamento de um atendimento confirmado.

    Não altera o registro atual — ele é marcado como RESCHEDULED e um
    novo agendamento é criado (já CONFIRMED) com o novo horário e,
    opcionalmente, novo serviço/funcionário. Isso preserva o histórico
    do agendamento original para auditoria e relatórios.
    """
    scheduled_time: datetime
    service_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time_reschedule(cls, v: datetime) -> datetime:
        """Normaliza para aware e valida se o novo horário não está no passado."""
        if timezone.is_naive(v):
            v = timezone.make_aware(v)
        if v < timezone.now():
            raise ValueError("O horário agendado não pode ser no passado.")
        return v


class SchedulingStatusUpdateIn(Schema):
    """Atualização administrativa apenas do status do agendamento."""
    status: SchedulingStatusEnum


class SchedulingFilter(Schema):
    """Filtros para listagem administrativa de agendamentos — todos opcionais."""
    service_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    status: Optional[SchedulingStatusEnum] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class SchedulingList(Schema):
    """Lista paginada de agendamentos - visão do cliente."""
    items: list[SchedulingOut]


class SchedulingPrivateList(Schema):
    """Lista paginada de agendamentos - visão administrativa."""
    items: list[SchedulingPrivateOut]