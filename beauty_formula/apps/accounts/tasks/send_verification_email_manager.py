"""
Tasks Celery — e-mail de boas-vindas do gerente cadastrado pelo admin.
"""
import logging
from celery import shared_task
from django.conf import settings
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_verification_email_manager(self, user_id: str, temporary_password: str) -> None:
    """
    Envia o e-mail de confirmação + senha temporária (texto puro, gerada
    na criação do usuário) para o gerente recém-cadastrado.
    """
    try:
        from beauty_formula.apps.accounts.services.verification import build_verification_url

        user = get_user_by_id(user_id=user_id)
        verify_url = build_verification_url(user)

        send_html_email(
            subject="Confirme seu e-mail — Fórmula da Beleza",
            to_email=user.email,
            template_name="accounts/emails/verification_email_manager.html",
            context={
                "user_email": user.email,
                "verify_url": verify_url,
                "temporary_password": temporary_password,
                "frontend_url": settings.FRONTEND_URL.rstrip("/"),
            },
        )
        logger.info("Verification email (manager) sent to %s", user.email)

    except Exception as exc:
        logger.exception("Error sending manager verification email")
        raise self.retry(exc=exc)