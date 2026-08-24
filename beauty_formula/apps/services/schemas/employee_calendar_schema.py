from datetime import date, time
from typing import List, Optional
from uuid import UUID

from ninja import Schema


class WorkingHoursBlockOut(Schema):
    """Um turno de expediente (ex.: 09:00–12:00) dentro do dia."""
    start_time: time
    end_time: time


class TimeOffBlockOut(Schema):
    """Um bloqueio (folga/férias/pausa) que afeta o dia."""
    id: UUID
    block_type: str
    is_recurring: bool
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class SchedulingSummaryOut(Schema):
    """Resumo de um agendamento do dia — o suficiente pra render no calendário."""
    id: UUID
    start_time: time
    end_time: time
    service_name: str
    client_name: str
    status: str


class EmployeeCalendarDayOut(Schema):
    """Um dia do calendário mensal de um funcionário."""
    date: date
    weekday: int
    weekday_label: str
    is_within_booking_window: bool
    working_hours: List[WorkingHoursBlockOut]
    time_off_blocks: List[TimeOffBlockOut]
    schedulings: List[SchedulingSummaryOut]
    has_open_slots: bool


class EmployeeCalendarOut(Schema):
    """
    Calendário mensal completo de um funcionário — expediente + bloqueios
    + agendamentos já resolvidos dia a dia, pra alimentar a tela de
    calendário do painel administrativo.
    """
    employee_id: UUID
    employee_name: str
    month: date
    booking_window_days: int
    days: List[EmployeeCalendarDayOut]


__all__ = [
    "WorkingHoursBlockOut",
    "TimeOffBlockOut",
    "SchedulingSummaryOut",
    "EmployeeCalendarDayOut",
    "EmployeeCalendarOut",
]