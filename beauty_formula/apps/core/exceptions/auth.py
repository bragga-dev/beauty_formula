from django.utils.translation import gettext_lazy as _


class InvalidCredentials(Exception):
    def __init__(self, message=None):
        self.message = message or _("E-mail ou senha inválidos.")
        super().__init__(self.message)


class InvalidPassword(Exception):
    def __init__(self, message=None):
        self.message = message or _("Senha atual incorreta.")
        super().__init__(self.message)


class InvalidToken(Exception):
    def __init__(self, message=None):
        self.message = message or _("Token inválido ou expirado.")
        super().__init__(self.message)


class InvalidGoogleToken(Exception):
    def __init__(self, message=None):
        self.message = message or _("Token do Google inválido ou expirado.")
        super().__init__(self.message)