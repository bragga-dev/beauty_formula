from django.utils.translation import gettext_lazy as _


class ContactNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Contato não encontrado.")
        super().__init__(self.message)


class ContactNameAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe um contato com esse nome.")
        super().__init__(self.message)