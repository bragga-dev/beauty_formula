import uuid
from datetime import time
from enum import IntEnum
from typing import Optional

from ninja import Schema

from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours


class WeekdayEnum(IntEnum):
    """Espelha EmployeeWorkingHours.Weekday pro client validar/documentar via OpenAPI."""
    MONDAY = EmployeeWorkingHours.Weekday.MONDAY
    TUESDAY = EmployeeWorkingHours.Weekday.TUESDAY
    WEDNESDAY = EmployeeWorkingHours.Weekday.WEDNESDAY
    THURSDAY = EmployeeWorkingHours.Weekday.THURSDAY
    FRIDAY = EmployeeWorkingHours.Weekday.FRIDAY
    SATURDAY = EmployeeWorkingHours.Weekday.SATURDAY
    SUNDAY = EmployeeWorkingHours.Weekday.SUNDAY


class EmployeeWorkingHoursCreateIn(Schema):
    weekday: WeekdayEnum
    start_time: time
    end_time: time


class EmployeeWorkingHoursUpdateIn(Schema):
    """PATCH parcial — todos os campos opcionais, None mantém o valor atual."""
    weekday: Optional[WeekdayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class EmployeeWorkingHoursOut(Schema):
    id: uuid.UUID
    weekday: int
    weekday_display: str
    start_time: time
    end_time: time
    total_hours: float

    @staticmethod
    def resolve_weekday_display(obj):
        return obj.get_weekday_display()

    @staticmethod
    def resolve_total_hours(obj):
        return obj.total_hours


__all__ = [
    "WeekdayEnum",
    "EmployeeWorkingHoursCreateIn",
    "EmployeeWorkingHoursUpdateIn",
    "EmployeeWorkingHoursOut",
]