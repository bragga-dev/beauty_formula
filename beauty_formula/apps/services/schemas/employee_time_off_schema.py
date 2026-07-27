import uuid
from datetime import time, datetime
from enum import Enum
from typing import Optional
from ninja import Schema

from beauty_formula.apps.core.constants.block_type import BlockType
from beauty_formula.apps.services.schemas.employee_working_hours_schema import WeekdayEnum


class BlockTypeEnum(str, Enum):
    """Enum baseado nos valores do BlockType"""
    
    LUNCH = BlockType.LUNCH
    BREAK = BlockType.BREAK
    PERSONAL = BlockType.PERSONAL
    MEDICAL = BlockType.MEDICAL
    DAY_OFF = BlockType.DAY_OFF
    VACATION = BlockType.VACATION
    OTHER = BlockType.OTHER
    
    @classmethod
    def get_color(cls, value: str) -> str:
        return BlockType.COLORS.get(value, "gray")
    
    @classmethod
    def get_icon(cls, value: str) -> str:
        return BlockType.ICONS.get(value, "📌")
    
    @classmethod
    def get_display_name(cls, value: str) -> str:
        choices_dict = dict(BlockType.CHOICES)
        return choices_dict.get(value, value)


class EmployeeTimeOffOut(Schema):
    """
    Bloqueio de horário do funcionário - visão do próprio funcionário.

    Não expõe `employee`/`employee_id`: é o próprio funcionário vendo os
    próprios bloqueios (endpoint filtra por request.auth), repetir quem
    ele é seria redundante — mesmo padrão já usado em EmployeeServiceOut.
    Isso também evita depender de accounts.schemas.employee_schema aqui,
    que já importa de volta beauty_formula.apps.services.schemas
    (service_schema) — manter os dois lados sem essa dependência cruzada
    evita reabrir o ciclo de import que já resolvemos antes.
    """
    id: uuid.UUID
    block_type: BlockTypeEnum
    weekday: Optional[WeekdayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmployeeTimeOffCreateIn(Schema):
    """
    Criação de bloqueio de horário.
    Funcionário pode ser recorrente (weekday + start_time + end_time)
    ou pontual (start_datetime + end_datetime).

    Sem `employee_id`: quem cria é sempre o próprio funcionário
    autenticado (request.auth) — não faz sentido o client mandar um
    employee_id que o endpoint vai ignorar de qualquer forma.
    """
    block_type: BlockTypeEnum
    weekday: Optional[WeekdayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None


class EmployeeTimeOffUpdateIn(Schema):
    """
    Atualização de bloqueio - PATCH parcial, todos os campos opcionais.
    """
    block_type: Optional[BlockTypeEnum] = None
    weekday: Optional[WeekdayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None


class EmployeeTimeOffList(Schema):
    """Lista paginada de bloqueios."""
    items: list[EmployeeTimeOffOut]


__all__ = [

    "BlockTypeEnum",
    "EmployeeTimeOffOut",
    "EmployeeTimeOffCreateIn",
    "EmployeeTimeOffUpdateIn",
    "EmployeeTimeOffList",

]