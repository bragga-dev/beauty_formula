from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ninja import Schema
from pydantic import field_validator, model_validator

from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission


class CommissionStatusEnum(str, Enum):
    """Espelha EmployeeCommission.CommissionStatus."""
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        choices_dict = dict(EmployeeCommission.CommissionStatus.choices)
        return choices_dict.get(value, value)


class CommissionOut(Schema):
    """
    Representação de uma comissão. Segue o padrão flat do PaymentResponseSchema:
    em vez de aninhar o Scheduling inteiro, expõe só os campos relevantes pra
    conferência do repasse (serviço, cliente, data do atendimento, percentual
    e valor aplicados).
    """
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    scheduling_id: uuid.UUID
    service_name: str
    client_name: str
    scheduled_time: datetime
    price_at_booking: Decimal
    commission_percentage: Decimal
    commission_value: Decimal
    status: CommissionStatusEnum
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, commission: EmployeeCommission) -> "CommissionOut":
        scheduling = commission.scheduling
        return cls(
            id=commission.id,
            employee_id=commission.employee_id,
            employee_name=commission.employee.get_full_name(),
            scheduling_id=commission.scheduling_id,
            service_name=scheduling.service.name,
            client_name=scheduling.client.get_full_name(),
            scheduled_time=scheduling.scheduled_time,
            price_at_booking=scheduling.price_at_booking,
            commission_percentage=scheduling.service.commission_percentage,
            commission_value=commission.commission_value,
            status=commission.status,
            paid_at=commission.paid_at,
            created_at=commission.created_at,
            updated_at=commission.updated_at,
        )


class CommissionCreateIn(Schema):
    """
    Gera a comissão de UM atendimento já concluído. O valor não é informado
    manualmente: é sempre calculado a partir de
    `scheduling.price_at_booking * scheduling.service.commission_percentage / 100`.
    O funcionário também é sempre derivado do próprio agendamento.
    """
    scheduling_id: uuid.UUID


class CommissionUpdateValueIn(Schema):
    """Ajuste manual pontual do valor de uma comissão ainda PENDING (exceção à regra automática)."""
    commission_value: Decimal

    @field_validator("commission_value")
    @classmethod
    def validate_commission_value(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("O valor da comissão não pode ser negativo.")
        return v


class CommissionFilter(Schema):
    """Filtros combináveis para listagem — todos opcionais."""
    employee_id: Optional[uuid.UUID] = None
    status: Optional[CommissionStatusEnum] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CommissionBulkGenerateIn(Schema):
    """
    Geração em lote: cria a comissão de todo atendimento COMPLETED no
    período que ainda não tem comissão registrada.

    `employee_id` omitido = gera para TODOS os funcionários que tiveram
    atendimentos concluídos no período. Atendimentos que já têm comissão
    são automaticamente pulados (o OneToOneField garante isso), então
    rodar a geração de novo pro mesmo período é seguro e idempotente —
    nada é duplicado.
    """
    employee_id: Optional[uuid.UUID] = None
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_date < self.start_date:
            raise ValueError("A data final não pode ser anterior à data inicial.")
        return self


class CommissionBulkGenerateOut(Schema):
    """Resultado da geração em lote."""
    created: list[CommissionOut]
    created_count: int
    skipped_count: int
    total_completed_schedulings: int


class CommissionBulkStatusIn(Schema):
    """
    Atualiza de uma vez o status de todas as comissões PENDING de um
    período (opcionalmente restrito a um funcionário) — usado pra marcar
    o lote inteiro como pago (ou cancelar) após a conferência.
    Só aceita PAID ou CANCELED como destino: voltar pra PENDING em massa
    não é uma operação suportada.
    """
    employee_id: Optional[uuid.UUID] = None
    start_date: date
    end_date: date
    status: CommissionStatusEnum

    @field_validator("status")
    @classmethod
    def validate_target_status(cls, v: CommissionStatusEnum) -> CommissionStatusEnum:
        if v == CommissionStatusEnum.PENDING:
            raise ValueError("Não é possível voltar comissões para PENDING em lote.")
        return v

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_date < self.start_date:
            raise ValueError("A data final não pode ser anterior à data inicial.")
        return self


class CommissionBulkStatusOut(Schema):
    """Resultado da atualização de status em lote."""
    updated_count: int
    commission_ids: list[uuid.UUID]