"""
Task Celery — notificação ao admin quando um novo `RefundRequest` entra
na fila de análise (qualquer origem: cliente cancelando um agendamento
pago, ou o sistema cancelando automaticamente por conflito de horário
com pagamento já recebido — ver `scheduling_service.
cancel_scheduling_due_to_payment_conflict`).
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
def send_refund_request_admin_notification(self, refund_request_id: uuid.UUID) -> None:
    """Avisa o admin que há um novo pedido de reembolso esperando análise."""
    try:
        refund_request = get_refund_request_by_id(refund_request_id)
        if refund_request is None:
            logger.warning("RefundRequest %s não encontrado ao tentar notificar admin.", refund_request_id)
            return

        admin_email = settings.ADMIN_EMAIL
        client = refund_request.client
        scheduling = refund_request.payment.scheduling

        context = {
            "client_name": get_client_full_name_display(client),
            "service_name": scheduling.service.name if scheduling else None,
            "reason": refund_request.reason,
            "original_value": refund_request.original_value,
            "fee_percentage": refund_request.fee_percentage,
            "fee_value": refund_request.fee_value,
            "refund_value": refund_request.refund_value,
            "requested_by_name": refund_request.requested_by.email,
            "admin_refunds_url": f"{settings.FRONTEND_URL}/painel/reembolsos",
        }

        send_html_email(
            subject="💸 Novo pedido de reembolso — Fórmula da Beleza",
            to_email=admin_email,
            template_name="payment/emails/refund_request_admin_notification.html",
            context=context,
        )

        logger.info(
            "Refund request admin notification sent to %s (refund_request=%s)",
            admin_email, refund_request.id,
        )

    except Exception as exc:
        logger.exception(
            "Error sending refund request admin notification (refund_request=%s)", refund_request_id
        )
        raise self.retry(exc=exc)