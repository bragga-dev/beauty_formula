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
def send_verification_email_employee(self, user_id: str, temporary_password: str) -> None:
    """
    Envia e-mail de confirmação de conta.

    Gera:
    - uid seguro para URL
    - token do Django
    - e-mail HTML + fallback texto

    `temporary_password` deve ser a senha em texto puro, gerada no
    momento da criação do usuário — nunca lida de user.password (que
    guarda apenas o hash e é inútil pro funcionário logar).
    """
    try:
        from beauty_formula.apps.accounts.services.verification import build_verification_url

        user = get_user_by_id(user_id=user_id)

        verify_url = build_verification_url(user)

        logger.info("Verification URL generated: %s", verify_url)

        context = {
            "user_email": user.email,
            "verify_url": verify_url,
            "temporary_password": temporary_password,
        }

        send_html_email(
            subject="Confirme seu e-mail — Fórmula da Beleza",
            to_email=user.email,
            template_name="accounts/emails/verification_email_employee.html",
            context=context,
        )

        logger.info("Verification email sent to %s", user.email)

    except Exception as exc:
        logger.exception("Error sending verification email")
        raise self.retry(exc=exc)