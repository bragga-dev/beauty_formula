"""
Tasks Celery — envio de e-mails de agendamento.
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.core.emails.sender import send_html_email
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

        # O perfil do cliente pode ainda não existir.
        try:
            client = get_client_by_user_id(user_id=user_id)
        except Exception:
            client = None

        client_name = user.email

        if client:
            full_name = f"{client.first_name or ''} {client.last_name or ''}".strip()

            if full_name:
                client_name = full_name
            elif client.first_name:
                client_name = client.first_name
            elif client.last_name:
                client_name = client.last_name

        employee_name = (f"{scheduling.employee.first_name or ''} "f"{scheduling.employee.last_name or ''}").strip()

        context = {
            # Cliente
            "client_name": client_name,
            "user_email": user.email,

            # Serviço
            "service_name": scheduling.service.name,
            "service_description": scheduling.service.description,
            "service_image": scheduling.service.image_url,

            # Funcionário
            "employee_full_name": employee_name,
            "employee_photo": scheduling.employee.photo_url,
            "employee_bio": scheduling.employee.bio,

            # Agendamento
            "scheduling_service_price": scheduling.price_at_booking,
            "scheduling_service_duration": int(scheduling.duration_at_booking.total_seconds() // 60),
            "scheduling_service_status": scheduling.get_status_display(),
            "scheduling_service_notes": scheduling.notes or "",
            "scheduling_service_time": scheduling.scheduled_time.strftime("%d/%m/%Y às %H:%M"),
            "scheduling_service_created_at": scheduling.created_at.strftime("%d/%m/%Y às %H:%M"),
        }

        send_html_email(
            subject="Confirmação de Agendamento — Fórmula da Beleza",
            to_email=user.email,
            template_name="services/emails/confirm_scheduling.html",
            context=context,
        )

        logger.info("Scheduling confirmation email sent to %s (scheduling=%s)",user.email, scheduling.id)

    except Exception as exc:
        logger.exception("Error sending scheduling confirmation email (user=%s, scheduling=%s)", user_id, scheduling_id)
        raise self.retry(exc=exc)