"""
Tasks Celery — envio de e-mails de agendamento (agradecimento pós-conclusão).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    build_employee_block,
    build_service_block,
    format_datetime_br,
    new_scheduling_url,
    rate_scheduling_url,
    resolve_client_display_name,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_scheduling_completed_thanks(self, scheduling_id: uuid.UUID) -> None:
    """
    Agradece ao cliente pela preferência após a conclusão do atendimento
    (status COMPLETED) e convida a avaliar o serviço e agendar novamente
    — incentivo à fidelização.
    """
    try:
        scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
        client_user = scheduling.client.user
        client_email = client_user.email

        context = {
            "client_name": resolve_client_display_name(client_user),

            **build_service_block(scheduling),
            **build_employee_block(scheduling.employee),

            "completed_at": format_datetime_br(scheduling.scheduled_time),
            "rate_url": rate_scheduling_url(scheduling.id),
            "new_scheduling_url": new_scheduling_url(),
        }

        send_html_email(
            subject="Obrigado pela preferência! — Fórmula da Beleza",
            to_email=client_email,
            template_name="services/emails/scheduling_completed.html",
            context=context,
        )

        logger.info(
            "Scheduling completion thank-you email sent to %s (scheduling=%s)", client_email, scheduling.id
        )

    except Exception as exc:
        logger.exception("Error sending scheduling completion email (scheduling=%s)", scheduling_id)
        raise self.retry(exc=exc)