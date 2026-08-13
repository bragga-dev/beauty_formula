

from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ninja import Schema, Field

from beauty_formula.apps.payment.models.payment_model import Payment


class PaymentBillingTypeEnum(str, Enum):
    """Espelha Payment.PaymentMode — forma de cobrança."""
    UNDEFINED = "UNDEFINED"
    BOLETO = "BOLETO"
    PIX = "PIX"
    CREDIT_CARD = "CREDIT_CARD"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        choices_dict = dict(Payment.PaymentMode.choices)
        return choices_dict.get(value, value)


class PaymentStatusEnum(str, Enum):
    """Espelha Payment.PaymentStatus."""
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    OVERDUE = "OVERDUE"
    REFUNDED = "REFUNDED"
    RECEIVED_IN_CASH = "RECEIVED_IN_CASH"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUND_IN_PROGRESS = "REFUND_IN_PROGRESS"
    CHARGEBACK_REQUESTED = "CHARGEBACK_REQUESTED"
    CHARGEBACK_DISPUTE = "CHARGEBACK_DISPUTE"
    AWAITING_CHARGEBACK_REVERSAL = "AWAITING_CHARGEBACK_REVERSAL"
    DUNNING_REQUESTED = "DUNNING_REQUESTED"
    DUNNING_RECEIVED = "DUNNING_RECEIVED"
    AWAITING_RISK_ANALYSIS = "AWAITING_RISK_ANALYSIS"
    CANCELLED = "CANCELLED"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        choices_dict = dict(Payment.PaymentStatus.choices)
        return choices_dict.get(value, value)


class PaymentCreateSchema(Schema):
    """
    Criação de cobrança — só pede o essencial.
    scheduling_id é string para evitar problemas de validação com UUID.
    """
    scheduling_id: str  
    billing_type: PaymentBillingTypeEnum
    cpf_cnpj: Optional[str] = None
    


class PaymentResponseSchema(Schema):
    id: uuid.UUID
    scheduling_id: uuid.UUID
    asaas_payment_id: Optional[str] = None
    asaas_customer_id: Optional[str] = None
    value: Decimal
    billing_type: PaymentBillingTypeEnum
    status: PaymentStatusEnum
    due_date: date
    description: str
    external_reference: Optional[str] = None
    invoice_url: Optional[str] = None
    bank_slip_url: Optional[str] = None
    pix_qr_code: Optional[str] = None
    pix_copy_paste: Optional[str] = None
    payment_date: Optional[datetime] = None
    net_value: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    synced_with_asaas: bool

    @classmethod
    def from_orm(cls, payment: Payment) -> "PaymentResponseSchema":
        return cls(
            id=payment.id,
            scheduling_id=payment.scheduling_id,
            asaas_payment_id=payment.asaas_payment_id,
            asaas_customer_id=payment.asaas_customer_id,
            value=payment.value,
            billing_type=payment.billing_type,
            status=payment.status,
            due_date=payment.due_date,
            description=payment.description,
            external_reference=payment.external_reference,
            invoice_url=payment.invoice_url,
            bank_slip_url=payment.bank_slip_url,
            pix_qr_code=payment.pix_qr_code,
            pix_copy_paste=payment.pix_copy_paste,
            payment_date=payment.payment_date,
            net_value=payment.net_value,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            synced_with_asaas=payment.synced_with_asaas,
        )


class PaymentUpdateSchema(Schema):
    """PATCH administrativo — status é atualizado via webhook, não por aqui (ver PaymentStatusUpdateSchema)."""
    billing_type: Optional[PaymentBillingTypeEnum] = None
    due_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)


class PaymentStatusUpdateSchema(Schema):
    """Usado pelo endpoint de webhook pra aplicar a mudança de status vinda da Asaas."""
    status: PaymentStatusEnum


class PaymentFilterSchema(Schema):
    client_id: Optional[uuid.UUID] = None
    status: Optional[PaymentStatusEnum] = None
    billing_type: Optional[PaymentBillingTypeEnum] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    synced: Optional[bool] = None

class PaymentRefundSchema(Schema):
    """
    Estorno acionado manualmente pelo admin. value ausente = estorno
    integral. value informado = estorno parcial (ex: reter taxa de
    cancelamento) — a Asaas valida se cabe no saldo disponível.
    """
    value: Optional[Decimal] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, max_length=500)