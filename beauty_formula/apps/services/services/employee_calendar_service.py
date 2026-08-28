"""
Monta a visão de calendário mensal de um funcionário — expediente
recorrente, bloqueios (folgas/férias) e agendamentos, dia a dia, dentro
de um mês. Não é um dado persistido: sempre calculado on-the-fly a
partir de EmployeeWorkingHours + EmployeeTimeOff + Scheduling, igual o
`availability_selector` já faz pro cálculo de slots — aqui só empacota
numa visão de mês inteiro em vez de slots de um serviço específico.

Alimenta a tela de calendário do painel administrativo (o "libera os 30
dias conforme a agenda" do funcionário, agora em formato de mês visual e
com a janela de disponibilidade — `booking_window_days` — configurável
por funcionário).
"""
import calendar
from datetime import date as date_type, timedelta
from uuid import UUID

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_id
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import InvalidAvailabilityRequest
from beauty_formula.apps.services.schemas.employee_calendar_schema import (
    EmployeeCalendarDayOut,
    EmployeeCalendarOut,
    FreeIntervalOut,
    PublicEmployeeCalendarDayOut,
    PublicEmployeeCalendarOut,
    SchedulingSummaryOut,
    TimeOffBlockOut,
    WorkingHoursBlockOut,
)
from beauty_formula.apps.services.selectors.availability_selector import get_free_intervals_for_date
from beauty_formula.apps.services.selectors.employee_time_off_selector import get_time_off_for_employee_on_date
from beauty_formula.apps.services.selectors.employee_working_hours_selector import (
    get_working_hours_for_employee_weekday,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_schedulings_for_employee_calendar_date

MAX_MONTHS_RANGE = 24


def _build_working_hours_and_time_off(employee_id: UUID, target_date: date_type, weekday: int):
    """
    Parte comum aos dois calendários (admin e público): expediente do dia
    da semana e bloqueios (recorrentes + pontuais) que caem na data. Nem
    um nem outro carrega dado de cliente, então dá pra reusar sem
    restrição entre a view admin e a pública.
    """
    working_hours = [
        WorkingHoursBlockOut(start_time=wh.start_time, end_time=wh.end_time)
        for wh in get_working_hours_for_employee_weekday(employee_id=employee_id, weekday=weekday)
    ]

    time_off_blocks = [
        TimeOffBlockOut(
            id=block.id,
            block_type=block.block_type,
            is_recurring=block.is_recurring,
            start_time=block.start_time if block.is_recurring else timezone.localtime(block.start_datetime).time(),
            end_time=block.end_time if block.is_recurring else timezone.localtime(block.end_datetime).time(),
        )
        for block in get_time_off_for_employee_on_date(employee_id=employee_id, weekday=weekday, target_date=target_date)
    ]

    return working_hours, time_off_blocks


def _build_day(employee_id: UUID, target_date: date_type, booking_window_days: int, today: date_type) -> EmployeeCalendarDayOut:
    weekday = target_date.weekday()
    working_hours, time_off_blocks = _build_working_hours_and_time_off(employee_id, target_date, weekday)

    schedulings = [
        SchedulingSummaryOut(
            id=s.id,
            start_time=timezone.localtime(s.scheduled_time).time(),
            end_time=timezone.localtime(s.end_time).time(),
            service_name=s.service.name,
            client_name=s.client.get_full_name(),
            status=s.status,
        )
        for s in get_schedulings_for_employee_calendar_date(employee_id=employee_id, target_date=target_date)
    ]

    has_open_slots = bool(get_free_intervals_for_date(employee_id=employee_id, target_date=target_date)) if target_date >= today else False
    is_within_booking_window = today <= target_date <= today + timedelta(days=booking_window_days)

    return EmployeeCalendarDayOut(
        date=target_date,
        weekday=weekday,
        weekday_label=calendar.day_name[weekday],
        is_within_booking_window=is_within_booking_window,
        working_hours=working_hours,
        time_off_blocks=time_off_blocks,
        schedulings=schedulings,
        has_open_slots=has_open_slots,
    )


def get_employee_calendar(employee_id: UUID, month: date_type) -> EmployeeCalendarOut:
    """
    Calendário mensal completo (todo dia do mês de `month`, de dia 1 ao
    último dia) de um funcionário — expediente, bloqueios e agendamentos
    já resolvidos, mais um sinal (`is_within_booking_window`) marcando
    quais dias caem dentro da janela de agendamento atual dele.
    """
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    today = timezone.localdate()
    months_diff = (month.year - today.year) * 12 + (month.month - today.month)
    if abs(months_diff) > MAX_MONTHS_RANGE:
        raise InvalidAvailabilityRequest(
            _("Só é possível consultar o calendário até %(months)s meses de distância de hoje.") % {"months": MAX_MONTHS_RANGE}
        )

    first_day = month.replace(day=1)
    _, days_in_month = calendar.monthrange(first_day.year, first_day.month)

    days = [
        _build_day(employee_id, first_day.replace(day=day_number), employee.booking_window_days, today)
        for day_number in range(1, days_in_month + 1)
    ]

    return EmployeeCalendarOut(
        employee_id=employee.id,
        employee_name=employee.get_full_name(),
        month=first_day,
        booking_window_days=employee.booking_window_days,
        days=days,
    )


def _build_public_day(
    employee_id: UUID, target_date: date_type, booking_window_days: int, today: date_type
) -> PublicEmployeeCalendarDayOut:
    weekday = target_date.weekday()
    working_hours, time_off_blocks = _build_working_hours_and_time_off(employee_id, target_date, weekday)
    free_intervals = (
        [
            FreeIntervalOut(start_time=timezone.localtime(interval.start).time(), end_time=timezone.localtime(interval.end).time())
            for interval in get_free_intervals_for_date(employee_id=employee_id, target_date=target_date)
        ]
        if target_date >= today
        else []
    )
    is_within_booking_window = today <= target_date <= today + timedelta(days=booking_window_days)

    return PublicEmployeeCalendarDayOut(
        date=target_date,
        weekday=weekday,
        weekday_label=calendar.day_name[weekday],
        is_within_booking_window=is_within_booking_window,
        working_hours=working_hours,
        time_off_blocks=time_off_blocks,
        free_intervals=free_intervals,
        has_open_slots=bool(free_intervals),
    )


def get_public_employee_calendar(employee_id: UUID, month: date_type) -> PublicEmployeeCalendarOut:
    """
    Versão pública (sem auth) do calendário mensal: mesmo expediente e
    bloqueios da view admin, mas troca a lista de agendamentos (que leva
    `client_name`) pelos intervalos livres já calculados — dá pra ver
    toda a disponibilidade e todos os bloqueios do funcionário sem
    expor nenhum dado de cliente.
    """
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    today = timezone.localdate()
    months_diff = (month.year - today.year) * 12 + (month.month - today.month)
    if abs(months_diff) > MAX_MONTHS_RANGE:
        raise InvalidAvailabilityRequest(
            _("Só é possível consultar o calendário até %(months)s meses de distância de hoje.") % {"months": MAX_MONTHS_RANGE}
        )

    first_day = month.replace(day=1)
    _, days_in_month = calendar.monthrange(first_day.year, first_day.month)

    days = [
        _build_public_day(employee_id, first_day.replace(day=day_number), employee.booking_window_days, today)
        for day_number in range(1, days_in_month + 1)
    ]

    return PublicEmployeeCalendarOut(
        employee_id=employee.id,
        employee_name=employee.get_full_name(),
        month=first_day,
        booking_window_days=employee.booking_window_days,
        days=days,
    )