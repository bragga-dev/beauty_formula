"""
Cálculo de disponibilidade — combina EmployeeWorkingHours (janela base),
EmployeeTimeOff (bloqueios) e Scheduling (agendamentos já existentes)
pra gerar os slots livres de um funcionário numa data.

Não é dado persistido: é sempre calculado on-the-fly a partir do que já
existe nos outros três models.
"""
from datetime import date as date_type, datetime, timedelta
from typing import List
from uuid import UUID

from django.utils import timezone

from beauty_formula.apps.core.utils.time_intervals import Interval, slice_into_slots, subtract_intervals
from beauty_formula.apps.services.selectors.employee_time_off_selector import get_time_off_for_employee_on_date
from beauty_formula.apps.services.selectors.employee_working_hours_selector import (
    get_working_hours_for_employee_weekday,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_active_schedulings_for_employee_on_date


def _to_aware(target_date: date_type, t) -> datetime:
    """Combina uma data com um horário (TimeField) e devolve um datetime timezone-aware."""
    return timezone.make_aware(datetime.combine(target_date, t))


def get_available_slots(employee_id: UUID, target_date: date_type, slot_duration: timedelta) -> List[Interval]:
    """
    Retorna os slots livres de um funcionário numa data, já fatiados no
    tamanho de `slot_duration` (duração do serviço sendo agendado — o
    slot é dinâmico, não um tamanho fixo tipo 15/30min).

    Pipeline: janela de trabalho do dia da semana → subtrai bloqueios
    (recorrentes + pontuais que tocam a data) → subtrai agendamentos já
    ativos → fatia o que sobrou em slots do tamanho do serviço → se a
    data for hoje, descarta slots que já ficaram no passado.
    """
    weekday = target_date.weekday()  # Monday=0 ... Sunday=6, mesmo enum do EmployeeWorkingHours.Weekday

    working_hours = get_working_hours_for_employee_weekday(employee_id, weekday)
    free: List[Interval] = [
        Interval(_to_aware(target_date, wh.start_time), _to_aware(target_date, wh.end_time))
        for wh in working_hours
    ]
    if not free:
        return []

    blocked: List[Interval] = []

    for block in get_time_off_for_employee_on_date(employee_id, weekday, target_date):
        if block.weekday is not None:
            # Bloqueio recorrente (ex: almoço toda terça 12h-13h)
            blocked.append(Interval(_to_aware(target_date, block.start_time), _to_aware(target_date, block.end_time)))
        else:
            # Bloqueio pontual (ex: férias) — já são datetimes aware
            blocked.append(Interval(block.start_datetime, block.end_datetime))

    for scheduling in get_active_schedulings_for_employee_on_date(employee_id, target_date):
        blocked.append(Interval(scheduling.scheduled_time, scheduling.scheduled_time + scheduling.duration_at_booking))

    free = subtract_intervals(free, blocked)
    slots = slice_into_slots(free, slot_duration)

    if target_date == timezone.localdate():
        now = timezone.now()
        slots = [slot for slot in slots if slot.start > now]

    return slots