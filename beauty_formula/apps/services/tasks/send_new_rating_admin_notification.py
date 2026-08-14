"""
Tasks Celery — notificação ao admin sobre uma nova avaliação recebida.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings

from beauty_formula.apps.accounts.selectors.client_selector import get_client_full_name_display
from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_full_name_display
from beauty_formula.apps.core.emails.sender import send_html_email
from beauty_formula.apps.services.selectors.average_rating_selector import get_average_rating_by_id

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_new_rating_admin_notification(self, rating_id: uuid.UUID) -> None:
    """
    Avisa o admin que uma nova avaliação chegou e está aguardando
    moderação (`is_authorized=False`) — só depois de autorizada ela
    aparece publicamente no site.
    """
    try:
        rating = get_average_rating_by_id(rating_id=rating_id)
        admin_email = settings.ADMIN_EMAIL

        context = {
            "client_name": get_client_full_name_display(rating.client),
            "employee_full_name": get_employee_full_name_display(rating.employee),
            "service_name": rating.service.name,
            "rating_value": rating.rating,
            "rating_stars": "★" * rating.rating + "☆" * (5 - rating.rating),
            "comment": rating.comment or "",
            "admin_ratings_url": f"{settings.FRONTEND_URL}/painel/avaliacoes",
        }

        send_html_email(
            subject=f"Nova avaliação recebida ({rating.rating}★) — Fórmula da Beleza",
            to_email=admin_email,
            template_name="services/emails/new_rating_admin_notification.html",
            context=context,
        )

        logger.info("New rating admin notification sent to %s (rating=%s)", admin_email, rating.id)

    except Exception as exc:
        logger.exception("Error sending new rating admin notification (rating=%s)", rating_id)
        raise self.retry(exc=exc)