"""
Tasks assíncronas do módulo de serviços.
"""
import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="services.complete_overdue_scheduling",
)
def complete_overdue_scheduling(self, scheduling_id: uuid.UUID) -> None:
    """
    Fecha automaticamente (CONFIRMED -> COMPLETED) um agendamento cujo
    horário já passou há mais de SCHEDULING_AUTO_COMPLETE_GRACE_HOURS e
    que ninguém fechou manualmente.

    Disparada pela orquestradora `close_overdue_schedulings`. Toda a
    revalidação de estado (o agendamento ainda existe? ainda está
    CONFIRMED?) acontece dentro de `auto_complete_overdue_scheduling`, no
    service — aqui só chamamos e tratamos falha/retry.
    """
    from beauty_formula.apps.services.services.scheduling_service import auto_complete_overdue_scheduling

    try:
        auto_complete_overdue_scheduling(scheduling_id=scheduling_id)
    except Exception as exc:
        logger.exception(
            "Erro ao concluir automaticamente o agendamento vencido %s", scheduling_id
        )
        raise self.retry(exc=exc)