"""
Tasks Celery — envio de e-mails de agendamento (confirmação ao cliente).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    build_employee_block,
    build_scheduling_datetime_block,
    build_service_block,
    client_appointments_url,
    format_datetime_br,
    resolve_client_display_name,
    saloon_url,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_confirm_scheduling_to_client(self, user_id: str, scheduling_id: uuid.UUID) -> None:
    """
    Envia o e-mail de confirmação de agendamento ao cliente.
    Caso o cliente ainda não tenha completado o perfil,
    utiliza o e-mail como identificação.
    """
    try:
        user = get_user_by_id(user_id=user_id)
        scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)

        context = {
            
            "client_name": resolve_client_display_name(user),
            "user_email": user.email,

            **build_service_block(scheduling),
            **build_employee_block(scheduling.employee),
            **build_scheduling_datetime_block(scheduling),

            "scheduling_service_notes": scheduling.notes or "",
            "scheduling_service_created_at": format_datetime_br(scheduling.created_at),

            "appointments_url": client_appointments_url(),
            "saloon_url": saloon_url(),
        }

        send_html_email(
            subject="Confirmação de Agendamento — Fórmula da Beleza",
            to_email=user.email,
            template_name="services/emails/confirm_scheduling_client.html",
            context=context,
        )

        logger.info("Scheduling confirmation email sent to %s (scheduling=%s)", user.email, scheduling.id)

    except Exception as exc:
        logger.exception("Error sending scheduling confirmation email (user=%s, scheduling=%s)", user_id, scheduling_id)
        raise self.retry(exc=exc)