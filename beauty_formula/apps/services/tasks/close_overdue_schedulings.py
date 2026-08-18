"""
Tasks assíncronas do módulo de serviços.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Quanto tempo depois do scheduled_time um agendamento CONFIRMED (que
# ninguém fechou manualmente) é fechado automaticamente como COMPLETED.
SCHEDULING_AUTO_COMPLETE_GRACE_HOURS = getattr(settings, "SCHEDULING_AUTO_COMPLETE_GRACE_HOURS", 12)


@shared_task(name="services.close_overdue_schedulings")
def close_overdue_schedulings() -> None:
    """
    Localiza os agendamentos CONFIRMED vencidos há mais de
    SCHEDULING_AUTO_COMPLETE_GRACE_HOURS e dispara uma task individual
    (`complete_overdue_scheduling`) para cada um — mesmo desenho da
    orquestradora de lembretes (`send_next_day_scheduling_reminders`):
    uma task periódica fazendo fan-out, não uma task por agendamento
    acumulando no schedule.

    Não precisa de campo de idempotência dedicado (tipo reminder_sent_at):
    o próprio filtro por status=CONFIRMED garante que um agendamento já
    fechado (por essa task ou manualmente) não é pego de novo na próxima
    execução.
    """
    from beauty_formula.apps.services.selectors.scheduling_selector import (
        list_confirmed_schedulings_overdue_for_auto_completion,
    )
    from beauty_formula.apps.services.tasks.complete_overdue_scheduling import complete_overdue_scheduling

    grace_period = timedelta(hours=SCHEDULING_AUTO_COMPLETE_GRACE_HOURS)
    schedulings = list_confirmed_schedulings_overdue_for_auto_completion(grace_period=grace_period)

    total = schedulings.count()
    logger.info("Found %s confirmed schedulings overdue for auto-completion.", total)

    for scheduling in schedulings.iterator():
        complete_overdue_scheduling.delay(scheduling.id)
        logger.info("Auto-complete task queued for scheduling=%s", scheduling.id)