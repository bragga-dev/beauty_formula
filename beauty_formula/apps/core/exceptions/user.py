from django.utils.translation import gettext_lazy as _


class UserAlreadyExists(Exception):
    def __init__(self, field: str = "email"):
        self.field = field
        super().__init__(_(f"Já existe um usuário com este {field}."))


class UserNotFound(Exception):
    def __init__(self):
        super().__init__(_("Usuário não encontrado."))


class EmailNotVerified(Exception):
    pass