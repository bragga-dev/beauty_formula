# apps/core/constants/block_type.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class BlockType:
    """Tipos de bloqueio de horário"""
    
    LUNCH = "lunch"
    BREAK = "break"
    PERSONAL = "personal"
    MEDICAL = "medical"
    DAY_OFF = "day_off"
    VACATION = "vacation"
    OTHER = "other"
    
    CHOICES = [
        (LUNCH, _("Almoço")),
        (BREAK, _("Pausa")),
        (PERSONAL, _("Pessoal")),
        (MEDICAL, _("Médico")),
        (DAY_OFF, _("Folga")),
        (VACATION, _("Férias")),
        (OTHER, _("Outro")),
    ]
    
   
    COLORS = {
        LUNCH: "orange",
        BREAK: "yellow",
        PERSONAL: "purple",
        MEDICAL: "red",
        DAY_OFF: "blue",
        VACATION: "green",
        OTHER: "gray",
    }
    
    
    ICONS = {
        LUNCH: "🍽️",
        BREAK: "☕",
        PERSONAL: "🧘",
        MEDICAL: "🏥",
        DAY_OFF: "🏖️",
        VACATION: "✈️",
        OTHER: "📌",
    }