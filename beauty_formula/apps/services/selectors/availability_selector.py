"""
Cálculo de disponibilidade — combina EmployeeWorkingHours (janela base),
EmployeeTimeOff (bloqueios) e Scheduling (agendamentos já existentes)
pra gerar os slots livres de um funcionário numa data.

Não é dado persistido: é sempre calculado on-the-fly a partir do que já
existe nos outros três models.
"""
from datetime import date as date_type, datetime, timedelta
from typing import List, Optional
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


def _get_free_intervals(employee_id: UUID, target_date: date_type, exclude_scheduling_id: Optional[UUID] = None) -> List[Interval]:
    """
    Janela livre "crua" de um funcionário numa data: expediente do dia
    da semana, já com bloqueios (recorrentes + pontuais) e agendamentos
    ativos subtraídos. Sem fatiar em slots — usado tanto por
    `get_available_slots` (que fatia) quanto por `is_slot_available`
    (que só testa se um intervalo específico cabe aqui dentro).

    `exclude_scheduling_id` repassa pra `get_active_schedulings_for_employee_on_date`
    — necessário ao validar disponibilidade na EDIÇÃO de um agendamento
    já existente, pra ele não aparecer ocupando o próprio horário.
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

    for scheduling in get_active_schedulings_for_employee_on_date(
        employee_id, target_date, exclude_scheduling_id=exclude_scheduling_id
    ):
        blocked.append(Interval(scheduling.scheduled_time, scheduling.scheduled_time + scheduling.duration_at_booking))

    return subtract_intervals(free, blocked)


def get_free_intervals_for_date(employee_id: UUID, target_date: date_type) -> List[Interval]:
    """
    Wrapper público de `_get_free_intervals` — janela livre "crua" do dia
    (sem fatiar em slots de um serviço específico). Usado pela visão de
    calendário mensal, que só precisa saber SE existe algum espaço livre
    naquele dia, não o tamanho exato do slot.
    """
    return _get_free_intervals(employee_id, target_date)


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
    free = _get_free_intervals(employee_id, target_date)
    if not free:
        return []

    slots = slice_into_slots(free, slot_duration)

    if target_date == timezone.localdate():
        now = timezone.now()
        slots = [slot for slot in slots if slot.start > now]

    return slots


def has_availability_in_window(employee_id: UUID, slot_duration: timedelta, start_date: date_type, days_ahead: int) -> bool:
    """
    Verifica se o funcionário tem pelo menos um slot livre do tamanho
    `slot_duration` em algum dia entre `start_date` e `start_date + days_ahead`
    (inclusive nas duas pontas). Pára no primeiro dia com vaga — não varre
    a janela inteira à toa.

    Usado pra filtrar a etapa "Profissional" do fluxo de agendamento: só
    listar quem realmente tem horário livre pra aquele serviço, não só
    quem está vinculado a ele.
    """
    for offset in range(days_ahead + 1):
        day = start_date + timedelta(days=offset)
        if get_available_slots(employee_id, day, slot_duration):
            return True
    return False


def is_slot_available(employee_id: UUID, start: datetime, end: datetime, exclude_scheduling_id: Optional[UUID] = None) -> bool:
    """
    Verifica se o intervalo [start, end) cabe inteiro numa janela livre
    do funcionário — dentro do expediente, fora de bloqueios/folgas e
    sem sobrepor outro agendamento ativo.

    Diferente de `get_available_slots`, não fatia nada: só testa o
    intervalo exato que o cliente pediu. Usado pelo `scheduling_service`
    antes de criar/reagendar, pra devolver um erro claro (SchedulingConflict)
    em vez de depender só da validação de conflito do model (que não
    conhece expediente nem folga — só sobreposição com outros agendamentos).

    Ao REAGENDAR um agendamento existente, passe `exclude_scheduling_id`
    com o próprio ID — sem isso o registro sendo editado conta como
    ocupando seu próprio horário atual e a checagem sempre falharia.
    """
    target_date = timezone.localdate(start)
    free = _get_free_intervals(employee_id, target_date, exclude_scheduling_id=exclude_scheduling_id)
    return any(f.start <= start and end <= f.end for f in free)