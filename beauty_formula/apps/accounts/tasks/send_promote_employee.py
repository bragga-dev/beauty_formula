"""
Tasks Celery — verificação de email.
"""
import logging
from celery import shared_task
from django.conf import settings
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_user_id,
    get_employee_full_name_display,
)


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_promote_employee(self, user_id: str) -> None:
    """
    Envia e-mail de notificação de promoção de Cliente para Funcionário.
    """
    try:

        user = get_user_by_id(user_id=user_id)
        employee = get_employee_by_user_id(user_id=user.id)
        employee_name = get_employee_full_name_display(employee) if employee else user.email

        context = {
            "user_email": user.email,
            "employee_name": employee_name,
            "complete_profile_url": f"{settings.FRONTEND_URL}/painel/perfil",
            "dashboard_url": f"{settings.FRONTEND_URL}/painel",
        }

        send_html_email(
            subject="Boas Vindas — Fórmula da Beleza",
            to_email=user.email,
            template_name="accounts/emails/send_promote_employee.html",
            context=context,
        )

        logger.info("Promotion email sent to %s", user.email)

    except Exception as exc:
        logger.exception("Error sending promotion email")
        raise self.retry(exc=exc)