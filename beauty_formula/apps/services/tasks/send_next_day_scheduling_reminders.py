"""
Tasks Celery — envio de e-mails relacionados a agendamentos.
"""

import logging
import uuid

from celery import shared_task

from beauty_formula.apps.services.selectors.scheduling_selector import list_confirmed_schedulings_for_reminder
from beauty_formula.apps.services.tasks.send_reminder import sending_reminder


logger = logging.getLogger(__name__)


@shared_task
def send_next_day_scheduling_reminders() -> None:
    """
    Localiza os agendamentos confirmados para o dia seguinte
    e dispara uma task individual para cada agendamento.

    Essa task funciona como orquestradora.
    """
    schedulings = list_confirmed_schedulings_for_reminder()

    total = schedulings.count()

    logger.info("Found %s confirmed schedulings for next-day reminders.", total)

    for scheduling in schedulings.iterator():
        sending_reminder.delay(scheduling.id)
        logger.info("Reminder task queued for scheduling=%s", scheduling.id)

