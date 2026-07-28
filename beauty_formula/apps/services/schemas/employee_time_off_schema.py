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


class BlockModalityEnum(str, Enum):
    """Espelha EmployeeTimeOff.BlockModality."""
    RECURRING = "recurring"
    PUNCTUAL = "punctual"


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
    block_modality: BlockModalityEnum
    weekday: Optional[WeekdayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class EmployeeTimeOffRecurringCreateIn(Schema):
    """
    Cria um bloqueio RECORRENTE — ex: almoço toda terça, 12h-13h.
    Repete toda semana até ser editado ou excluído.
    """
    block_type: BlockTypeEnum
    weekday: WeekdayEnum
    start_time: time
    end_time: time


class EmployeeTimeOffPunctualCreateIn(Schema):
    """
    Cria um bloqueio PONTUAL — uma janela específica de data/hora, ex:
    consulta médica dia 15/08 das 14h às 15h. Expira sozinho (soft
    delete automático) 1 minuto depois de end_datetime.
    """
    block_type: BlockTypeEnum
    start_datetime: datetime
    end_datetime: datetime


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
    "BlockModalityEnum",
    "EmployeeTimeOffOut",
    "EmployeeTimeOffRecurringCreateIn",
    "EmployeeTimeOffPunctualCreateIn",
    "EmployeeTimeOffUpdateIn",
    "EmployeeTimeOffList",

]