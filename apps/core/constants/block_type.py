class BlockType:
    LUNCH = "lunch"
    BREAK = "break"
    PERSONAL = "personal"
    MEDICAL = "medical"
    DAY_OFF = "day_off"
    VACATION = "vacation"
    OTHER = "other"

    CHOICES = [
        (LUNCH, "Almoço"),
        (BREAK, "Pausa"),
        (PERSONAL, "Pessoal"),
        (MEDICAL, "Médico"),
        (DAY_OFF, "Folga"),
        (VACATION, "Férias"),
        (OTHER, "Outro"),
    ]