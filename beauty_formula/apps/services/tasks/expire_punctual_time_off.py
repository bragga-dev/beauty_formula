"""
Tasks assíncronas do módulo de serviços.
"""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from beauty_formula.apps.services.selectors.employee_time_off_selector import get_time_off_by_id

@shared_task(name="services.expire_punctual_time_off")
def expire_punctual_time_off(time_off_id: str) -> None:
    """
    Marca um bloqueio pontual (EmployeeTimeOff) como inativo (soft
    delete) depois que ele expira.

    Agendada (via apply_async com eta=end_datetime + 1min) toda vez que
    um bloqueio pontual é criado ou atualizado — ver
    services/employee_time_off_service.py.

    Reconfirma tudo sozinha antes de agir, em vez de confiar cegamente
    que "se a task rodou agora, é porque expirou de verdade":
    - Se o registro foi excluído de vez (hard delete) nesse meio tempo,
      não existe mais nada a fazer.
    - Se foi editado e virou recorrente (perdeu end_datetime), a task
      não se aplica mais a ele.
    - Se já está inativo (outra execução já cuidou disso), não repete.
    - Se a data foi adiada pra depois de quando essa task foi agendada,
      esse end_datetime específico ainda não expirou de verdade — essa
      execução vira um no-op e é a task nova (agendada na hora da
      edição, pro novo end_datetime) que vai realmente agir depois.
    Isso evita ter que rastrear/revogar o ID da task antiga no Celery
    toda vez que a data é editada — deixa a task antiga inofensiva.
    """
    from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff

    try:
        time_off = get_time_off_by_id(time_off_id=time_off_id)
    except EmployeeTimeOff.DoesNotExist:
        return

    if not time_off.is_punctual:
        return

    if not time_off.is_active:
        return

    if timezone.now() < time_off.end_datetime + timedelta(minutes=1):
        return

    time_off.is_active = False
    time_off.save(update_fields=["is_active"])