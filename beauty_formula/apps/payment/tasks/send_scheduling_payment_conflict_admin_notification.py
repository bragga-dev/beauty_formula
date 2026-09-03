"""
Task Celery — notificação ao admin quando um pagamento é recebido mas o
agendamento vinculado não pôde ser confirmado porque outro cliente já
tinha confirmado o mesmo horário primeiro (ver
`scheduling_service.cancel_scheduling_due_to_payment_conflict`).

Caso raro (só ocorre se duas reservas concorrentes pro mesmo funcionário/
horário forem pagas quase ao mesmo tempo), mas quando acontece precisa de
ação humana: o cliente perdedor já pagou e precisa ser reembolsado
manualmente (`POST /payments/{id}/refund`) e contatado pra reagendar.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings

from beauty_formula.apps.accounts.selectors.client_selector import get_client_full_name_display
from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_full_name_display
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.payment.selectors.payment_selector import get_payment_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_scheduling_payment_conflict_admin_notification(self, payment_id: uuid.UUID) -> None:
    """
    Avisa o admin que um pagamento RECEIVED ficou sem agendamento
    confirmado — o registro já foi cancelado automaticamente pelo
    sistema (ver `cancel_scheduling_due_to_payment_conflict`); falta o
    admin decidir o estorno e o contato com o cliente.
    """
    try:
        payment = get_payment_by_id(payment_id=payment_id)
        scheduling = payment.scheduling
        admin_email = settings.ADMIN_EMAIL

        context = {
            "client_name": get_client_full_name_display(scheduling.client),
            "employee_full_name": get_employee_full_name_display(scheduling.employee),
            "service_name": scheduling.service.name,
            "scheduled_time": scheduling.scheduled_time,
            "payment_value": payment.value,
            "payment_asaas_id": payment.asaas_payment_id,
            "admin_payments_url": f"{settings.FRONTEND_URL}/painel/pagamentos",
        }

        send_html_email(
            subject="⚠️ Conflito de horário com pagamento recebido — Fórmula da Beleza",
            to_email=admin_email,
            template_name="payment/emails/scheduling_payment_conflict_admin_notification.html",
            context=context,
        )

        logger.warning(
            "Scheduling payment conflict admin notification sent to %s (payment=%s, scheduling=%s)",
            admin_email, payment.id, scheduling.id,
        )

    except Exception as exc:
        logger.exception(
            "Error sending scheduling payment conflict admin notification (payment=%s)", payment_id
        )
        raise self.retry(exc=exc)