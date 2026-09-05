"""
Task Celery — avisa o cliente do resultado da análise do pedido de
reembolso: aprovado (com o valor e prazo de estorno) ou rejeitado (com o
motivo que o admin registrou). Disparada por
`payment_service.approve_refund_request_service`/`reject_refund_request_service`
depois que o status já foi persistido.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings

from beauty_formula.apps.accounts.selectors.client_selector import get_client_full_name_display
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.payment.models.refund_request_model import RefundRequest
from beauty_formula.apps.payment.selectors.refund_request_selector import get_refund_request_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_refund_request_reviewed_client_notification(self, refund_request_id: uuid.UUID) -> None:
    """Avisa o cliente que o pedido de reembolso foi aprovado ou rejeitado."""
    try:
        refund_request = get_refund_request_by_id(refund_request_id)
        if refund_request is None:
            logger.warning("RefundRequest %s não encontrado ao tentar notificar cliente.", refund_request_id)
            return

        if refund_request.status not in (
            RefundRequest.RefundRequestStatus.APPROVED,
            RefundRequest.RefundRequestStatus.REJECTED,
        ):
            logger.warning(
                "RefundRequest %s ainda não foi revisado (status=%s) — notificação de resultado não enviada.",
                refund_request.id, refund_request.status,
            )
            return

        client = refund_request.client
        client_email = client.user.email
        scheduling = refund_request.payment.scheduling
        was_approved = refund_request.status == RefundRequest.RefundRequestStatus.APPROVED

        context = {
            "client_name": get_client_full_name_display(client),
            "service_name": scheduling.service.name if scheduling else None,
            "was_approved": was_approved,
            "original_value": refund_request.original_value,
            "fee_percentage": refund_request.fee_percentage,
            "fee_value": refund_request.fee_value,
            "refund_value": refund_request.refund_value,
            "has_fee": refund_request.fee_percentage > 0,
            "admin_notes": refund_request.admin_notes,
        }

        subject = (
            "✅ Reembolso aprovado — Fórmula da Beleza"
            if was_approved
            else "Sobre seu pedido de reembolso — Fórmula da Beleza"
        )

        send_html_email(
            subject=subject,
            to_email=client_email,
            template_name="payment/emails/refund_request_reviewed_client.html",
            context=context,
        )

        logger.info(
            "Refund request reviewed notification sent to client %s (refund_request=%s, approved=%s)",
            client_email, refund_request.id, was_approved,
        )

    except Exception as exc:
        logger.exception(
            "Error sending refund request reviewed notification to client (refund_request=%s)", refund_request_id
        )
        raise self.retry(exc=exc)