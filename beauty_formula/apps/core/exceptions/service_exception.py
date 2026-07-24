from django.utils.translation import gettext_lazy as _


class ServiceNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Serviço não encontrado.")
        super().__init__(self.message)