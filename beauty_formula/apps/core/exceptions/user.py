from django.utils.translation import gettext_lazy as _


class UserAlreadyExists(Exception):
    def __init__(self, field: str = "email"):
        self.field = field
        super().__init__(_(f"Já existe um usuário com este {field}."))


class UserNotFound(Exception):
    def __init__(self, message=None):
        if message is None:
            message = _("Usuário não encontrado.")
        super().__init__(message)

class EmailNotVerified(Exception):
    pass