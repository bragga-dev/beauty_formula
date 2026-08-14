"""
Tasks Celery — envio de e-mails de agendamento (cancelamento ao cliente).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    build_scheduling_datetime_block,
    build_service_block,
    new_scheduling_url,
    resolve_actor_display_name,
    resolve_client_display_name,
    resolve_employee_display_name,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_cancel_scheduling_to_client(self, scheduling_id: uuid.UUID) -> None:
    """
    Notifica o cliente de que seu agendamento foi cancelado, informando o
    motivo e quem realizou o cancelamento, com um convite pra criar um
    novo agendamento.

    Lê `canceled_reason`/`canceled_by` diretamente do model — ambos já
    foram gravados por `Scheduling.cancel()` antes desta task ser
    disparada, então não é preciso passá-los como parâmetro.
    """
    try:
        scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
        client_user = scheduling.client.user
        client_email = client_user.email

        context = {
            "client_name": resolve_client_display_name(client_user),
            "employee_full_name": resolve_employee_display_name(scheduling.employee),

            **build_service_block(scheduling),
            **build_scheduling_datetime_block(scheduling),

            "canceled_reason": scheduling.canceled_reason or "Não informado.",
            "canceled_by_name": resolve_actor_display_name(scheduling.canceled_by),
            "new_scheduling_url": new_scheduling_url(),
        }

        send_html_email(
            subject="Agendamento cancelado — Fórmula da Beleza",
            to_email=client_email,
            template_name="services/emails/cancel_scheduling_client.html",
            context=context,
        )

        logger.info(
            "Scheduling cancellation email sent to client %s (scheduling=%s)", client_email, scheduling.id
        )

    except Exception as exc:
        logger.exception(
            "Error sending scheduling cancellation email to client (scheduling=%s)", scheduling_id
        )
        raise self.retry(exc=exc)