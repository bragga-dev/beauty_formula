"""
Tasks assíncronas do módulo de serviços.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="services.expire_unpaid_scheduling")
def expire_unpaid_scheduling(scheduling_id: str) -> None:
    """
    Deleta automaticamente uma reserva (Scheduling em CREATED) que não
    foi paga dentro do prazo — libera o registro em vez de deixá-lo
    órfão para sempre aguardando um pagamento que pode nunca vir.

    Agendada (via apply_async com eta) toda vez que um agendamento é
    criado — ver `create_scheduling_for_client`, em scheduling_service.py.

    Reconfirma o estado antes de agir, no mesmo espírito de
    `expire_punctual_time_off`:
    - Se o agendamento não existe mais (excluído por um admin), não há
      nada a fazer.
    - Se já não está mais CREATED (foi confirmado, ou já foi cancelado
      pelo próprio cliente antes do prazo), essa execução é um no-op —
      outra coisa já decidiu o destino dele.
    """
    from beauty_formula.apps.payment.services.payment_service import cancel_payment_for_scheduling
    from beauty_formula.apps.services.models.scheduling import Scheduling
    from beauty_formula.apps.services.repositories.scheduling_repository import delete_scheduling
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        return

    if scheduling.status != Scheduling.SchedulingStatus.CREATED:
        return

    delete_scheduling(scheduling=scheduling)
   
    cancel_payment_for_scheduling(scheduling_id)

    logger.info("Reserva %s expirada automaticamente por falta de pagamento.", scheduling_id)