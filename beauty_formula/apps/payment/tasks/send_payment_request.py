"""
Tasks Celery — envio de e-mails de pagamento (solicitação de pagamento ao cliente).
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.emails.scheduling_context import (
    resolve_client_display_name,
    saloon_url,
)
from beauty_formula.apps.payment.selectors.payment_selector import get_payment_by_id
from beauty_formula.apps.payment.emails.payment_context import (
    build_payment_block,
    client_payments_url,
)
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_payment_request(self, user_id: uuid.UUID, payment_id: uuid.UUID) -> None:
    """
    Envia o e-mail de solicitação de pagamento para confirmação do agendamento.
    Caso o cliente ainda não tenha completado o perfil,
    utiliza o e-mail como identificação.
    """
    try:
        user = get_user_by_id(user_id=user_id)
        payment = get_payment_by_id(payment_id=payment_id)

        context = {
            "client_name": resolve_client_display_name(user),
            "user_email": user.email,

            **build_payment_block(payment=payment),

            "client_payments_url": client_payments_url(),
            "saloon_url": saloon_url(),
        }

        send_html_email(
            subject="Pagamento — Fórmula da Beleza",
            to_email=user.email,
            template_name="payment/emails/send_payment_request.html",
            context=context,
        )

        logger.info("Payment confirmation email sent to %s (payment=%s)", user.email, payment.id)

    except Exception as exc:
        logger.exception("Error sending payment confirmation email (user=%s, payment=%s)", user_id, payment_id)
        raise self.retry(exc=exc)