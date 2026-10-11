from django.utils.translation import gettext_lazy as _


class NotificationNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Notificação não encontrada.")
        super().__init__(self.message)