"""
Repository de RefundRequest — EXCLUSIVAMENTE persistência (criação,
transições de status). Nenhuma consulta/filtro/leitura aqui — isso é
responsabilidade do refund_request_selector.

Recebe sempre valores/instâncias já resolvidos e já validados pelo
payment_service — este módulo só escreve no banco.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.payment_exception import RefundRequestAlreadyExists
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.models.refund_request_model import RefundRequest


@transaction.atomic
def create_refund_request(
    *,
    payment: Payment,
    client: Client,
    requested_by: User,
    reason: str,
    original_value: Decimal,
    fee_percentage: Decimal,
    fee_value: Decimal,
    refund_value: Decimal,
) -> RefundRequest:
    try:
        return RefundRequest.objects.create(
            payment=payment,
            client=client,
            requested_by=requested_by,
            reason=reason,
            original_value=original_value,
            fee_percentage=fee_percentage,
            fee_value=fee_value,
            refund_value=refund_value,
        )
    except IntegrityError as e:
        raise RefundRequestAlreadyExists() from e


@transaction.atomic
def approve_refund_request(refund_request: RefundRequest, *, reviewed_by: User, admin_notes: str = "") -> RefundRequest:
    refund_request.status = RefundRequest.RefundRequestStatus.APPROVED
    refund_request.reviewed_by = reviewed_by
    refund_request.reviewed_at = timezone.now()
    refund_request.admin_notes = admin_notes
    refund_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])
    return refund_request


@transaction.atomic
def reject_refund_request(refund_request: RefundRequest, *, reviewed_by: User, admin_notes: str) -> RefundRequest:
    refund_request.status = RefundRequest.RefundRequestStatus.REJECTED
    refund_request.reviewed_by = reviewed_by
    refund_request.reviewed_at = timezone.now()
    refund_request.admin_notes = admin_notes
    refund_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes", "updated_at"])
    return refund_request