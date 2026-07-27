from datetime import datetime

from ninja import Schema


class AvailabilitySlotOut(Schema):
    """
    Um slot de horário livre pra agendar. `end - start` é sempre igual
    à duração do serviço consultado (slot dinâmico, não fixo).
    """
    start: datetime
    end: datetime


__all__ = ["AvailabilitySlotOut"]