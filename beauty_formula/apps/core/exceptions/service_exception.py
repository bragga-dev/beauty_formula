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