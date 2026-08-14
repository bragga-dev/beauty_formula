from django.utils.translation import gettext_lazy as _


class ProductNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Produto não encontrado.")
        super().__init__(self.message)

