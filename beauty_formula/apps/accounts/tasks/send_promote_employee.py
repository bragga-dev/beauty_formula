"""
Tasks Celery — verificação de email.
"""
import logging
from celery import shared_task
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id


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

        context = {
            "user_email": user.email,
        }

        send_html_email(
            subject="Boas Vindas — Fórmula da Beleza",
            to_email=user.email,
            template_name="accounts/emails/send_promote_employee.html",
            context=context,
        )

        logger.info("Verification email sent to %s", user.email)

    except Exception as exc:
        logger.exception("Error sending verification email")
        raise self.retry(exc=exc)