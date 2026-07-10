from django.utils.translation import gettext_lazy as _


class PermissionDenied(Exception):
    """Exceção lançada quando um usuário não tem permissão."""
    def __init__(self, msg: str = "Você não tem permissão para realizar esta ação."):
        super().__init__(_(msg))


class ChurchNotFoundError(Exception):
    """Exceção lançada quando a igreja não é encontrada."""
    pass


class MemberNotActiveError(Exception):
    """Exceção lançada quando o membro não está ativo na igreja."""
    pass