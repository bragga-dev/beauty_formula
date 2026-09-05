"""
Task Celery — avisa o cliente que o agendamento pago dele foi cancelado
e o pedido de reembolso entrou na fila de análise do admin. Disparada
junto com `send_refund_request_admin_notification`, no mesmo ponto
(`payment_service._request_refund_for_paid_scheduling`) — sempre que um
RefundRequest é criado, as duas pontas (admin e cliente) são avisadas.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings

from beauty_formula.apps.accounts.selectors.client_selector import get_client_full_name_display
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.payment.selectors.refund_request_selector import get_refund_request_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_refund_request_created_client_notification(self, refund_request_id: uuid.UUID) -> None:
    """Avisa o cliente que o pedido de reembolso dele foi registrado e está em análise."""
    try:
        refund_request = get_refund_request_by_id(refund_request_id)
        if refund_request is None:
            logger.warning("RefundRequest %s não encontrado ao tentar notificar cliente.", refund_request_id)
            return

        client = refund_request.client
        client_email = client.user.email
        scheduling = refund_request.payment.scheduling

        context = {
            "client_name": get_client_full_name_display(client),
            "service_name": scheduling.service.name if scheduling else None,
            "scheduled_time": scheduling.scheduled_time if scheduling else None,
            "original_value": refund_request.original_value,
            "fee_percentage": refund_request.fee_percentage,
            "fee_value": refund_request.fee_value,
            "refund_value": refund_request.refund_value,
            "has_fee": refund_request.fee_percentage > 0,
        }

        send_html_email(
            subject="Pedido de reembolso recebido — Fórmula da Beleza",
            to_email=client_email,
            template_name="payment/emails/refund_request_created_client.html",
            context=context,
        )

        logger.info(
            "Refund request created notification sent to client %s (refund_request=%s)",
            client_email, refund_request.id,
        )

    except Exception as exc:
        logger.exception(
            "Error sending refund request created notification to client (refund_request=%s)", refund_request_id
        )
        raise self.retry(exc=exc)