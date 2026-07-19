from django.utils.translation import gettext_lazy as _


class InvalidImageFile(Exception):
    def __init__(self, message=None):
        self.message = message or _("Arquivo de imagem inválido.")
        super().__init__(self.message)