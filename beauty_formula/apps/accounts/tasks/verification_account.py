"""
Tasks Celery — verificação de email.
"""
import logging
from celery import shared_task
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.core.tokens.signing import generate_uid_token
from beauty_formula.apps.accounts.services.verification import build_verification_url


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_verification_email(self, user_id: str) -> None:
    """
    Envia e-mail de confirmação de conta.

    Gera:
    - uid seguro para URL
    - token do Django
    - e-mail HTML + fallback texto
    """
    try:
        user = User.objects.get(pk=user_id)
        
        uid, token = generate_uid_token(user)
        verify_url = build_verification_url(uid, token)
        
        logger.info("Verification URL generated: %s", verify_url)

        context = {
            "user_email": user.email,
            "verify_url": verify_url,
        }

        send_html_email(
            subject="Confirme seu e-mail — Fórmula da Beleza",
            to_email=user.email,
            template_name="accounts/emails/verification_email.html",
            context=context,
        )

        logger.info("Verification email sent to %s", user.email)

    except Exception as exc:
        logger.exception("Error sending verification email")
        raise self.retry(exc=exc)