"""
Tasks Celery — envio de e-mails de agendamento (confirmação ao funcionário).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    build_scheduling_datetime_block,
    build_service_block,
    employee_appointments_url,
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
def send_confirm_rescheduling_to_employee(self, scheduling_id: uuid.UUID) -> None:
    """
    Notifica o funcionário responsável de que um novo agendamento foi
    confirmado em sua agenda.
    """
    try:
        scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
        employee = scheduling.employee
        employee_email = employee.user.email

        context = {
            "employee_name": resolve_employee_display_name(employee),
            "client_name": resolve_client_display_name(scheduling.client.user),

            **build_service_block(scheduling),
            **build_scheduling_datetime_block(scheduling),

            "scheduling_service_notes": scheduling.notes or "",
            "appointments_url": employee_appointments_url(),
        }

        send_html_email(
            subject="Reagendamento — Fórmula da Beleza",
            to_email=employee_email,
            template_name="services/emails/confirm_rescheduling_employee.html",
            context=context,
        )

        logger.info(
            "Rescheduling confirmation email sent to employee %s (scheduling=%s)", employee_email, scheduling.id
        )

    except Exception as exc:
        logger.exception(
            "Error sending rescheduling confirmation email to employee (scheduling=%s)", scheduling_id
        )
        raise self.retry(exc=exc)