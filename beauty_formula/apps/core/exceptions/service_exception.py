from django.utils.translation import gettext_lazy as _


class ServiceNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Serviço não encontrado.")
        super().__init__(self.message)


class AssociationAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Funcionário já está vinculado a esse serviço.")
        super().__init__(self.message)


class AssociationNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Vínculo entre funcionário e serviço não encontrado.")
        super().__init__(self.message)


class InvalidAvailabilityRequest(Exception):
    def __init__(self, message=None):
        self.message = message or _("Requisição de disponibilidade inválida.")
        super().__init__(self.message)


class WorkingHoursNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Horário de trabalho não encontrado.")
        super().__init__(self.message)


class TimeOffConflict(Exception):
    def __init__(self, message=None):
        self.message = message or _("Horário de pausa não estão alinhados.")
        super().__init__(self.message)

class TimeOffNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Horário de pausa não encontrado.")
        super().__init__(self.message)

class InvalidTimeOffRequest(Exception):
    def __init__(self, message=None):
        self.message = message or _("Requisição de folga / pausa inválida.")
        super().__init__(self.message)


class SchedulingNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Agendamento não encontrado.")
        super().__init__(self.message)


class SchedulingConflict(Exception):
    """Horário indisponível: conflito de agenda, fora do expediente ou em bloqueio/folga."""
    def __init__(self, message=None):
        self.message = message or _("Esse horário não está disponível para o funcionário selecionado.")
        super().__init__(self.message)


class InvalidSchedulingRequest(Exception):
    def __init__(self, message=None):
        self.message = message or _("Requisição de agendamento inválida.")
        super().__init__(self.message)


class SchedulingCannotBeModified(Exception):
    def __init__(self, message=None):
        self.message = message or _("Este agendamento não pode mais ser alterado.")
        super().__init__(self.message)


class SchedulingCannotBeCanceled(Exception):
    def __init__(self, message=None):
        self.message = message or _("Este agendamento não pode ser cancelado.")
        super().__init__(self.message)


class InvalidSchedulingStatusTransition(Exception):
    def __init__(self, message=None):
        self.message = message or _("Transição de status inválida para este agendamento.")
        super().__init__(self.message)


class AverageRatingNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Avaliação não encontrada.")
        super().__init__(self.message)


class AverageRatingAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Este agendamento já foi avaliado.")
        super().__init__(self.message)