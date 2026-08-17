"""
Tasks Celery — envio de e-mails relacionados a agendamentos.
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
from beauty_formula.apps.services.repositories.scheduling_repository import update_reminder_sent_at
from beauty_formula.apps.services.models.scheduling import Scheduling

logger = logging.getLogger(__name__)



@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def sending_reminder(self, scheduling_id: uuid.UUID) -> None:
    """
    Envia o e-mail de lembrete para um agendamento.

    O agendamento é buscado novamente pelo ID dentro da task.
    Antes do envio, o status é validado novamente para evitar
    o envio de lembrete caso o agendamento tenha sido cancelado
    ou alterado depois da criação da task.
    """
    try:
        scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
        if not scheduling.is_active:
            logger.info("Skipping reminder for inactive scheduling=%s", scheduling.id)
            return

        if scheduling.status != Scheduling.SchedulingStatus.CONFIRMED:
            logger.info(
                "Skipping reminder for non-confirmed scheduling=%s "
                "(status=%s)",
                scheduling.id,
                scheduling.status,
            )
            return

        user = get_user_by_id(user_id=scheduling.client.user)

        context = {
            "client_name": resolve_client_display_name(user),
            "user_email": user.email,

            **build_service_block(scheduling),
            **build_employee_block(scheduling.employee),
            **build_scheduling_datetime_block(scheduling),

            "scheduling_service_notes": scheduling.notes or "",
            "scheduling_service_created_at": format_datetime_br(
                scheduling.created_at,
            ),

            "appointments_url": client_appointments_url(),
            "saloon_url": saloon_url(),
        }

        send_html_email(
            subject="Lembrete de Agendamento — Fórmula da Beleza",
            to_email=user.email,
            template_name="services/emails/scheduling_reminder.html",
            context=context,
        )

        update_reminder_sent_at(scheduling=scheduling)
        
        logger.info(
            "Scheduling reminder email sent to %s "
            "(scheduling=%s)",
            user.email,
            scheduling.id,
        )

    except Exception as exc:
        logger.exception(
            "Error sending scheduling reminder "
            "(scheduling=%s)",
            scheduling_id,
        )

        raise self.retry(exc=exc)