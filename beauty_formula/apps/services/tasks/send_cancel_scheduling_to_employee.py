"""
Tasks Celery — envio de e-mails de agendamento (cancelamento ao funcionário).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    build_scheduling_datetime_block,
    build_service_block,
    employee_appointments_url,
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
def send_cancel_scheduling_to_employee(self, scheduling_id: uuid.UUID) -> None:
    """
    Notifica o funcionário de que um agendamento da sua agenda foi
    cancelado, informando cliente, motivo e quem realizou o cancelamento.
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

            "canceled_reason": scheduling.canceled_reason or "Não informado.",
            "canceled_by_name": resolve_actor_display_name(scheduling.canceled_by),
            "appointments_url": employee_appointments_url(),
        }

        send_html_email(
            subject="Agendamento cancelado — Fórmula da Beleza",
            to_email=employee_email,
            template_name="services/emails/cancel_scheduling_employee.html",
            context=context,
        )

        logger.info(
            "Scheduling cancellation email sent to employee %s (scheduling=%s)", employee_email, scheduling.id
        )

    except Exception as exc:
        logger.exception(
            "Error sending scheduling cancellation email to employee (scheduling=%s)", scheduling_id
        )
        raise self.retry(exc=exc)