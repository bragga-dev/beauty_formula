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


class AccountHasProtectedRecords(Exception):
    """
    LGPD — exclusão bloqueada porque a conta tem registros protegidos
    (agendamento, pagamento, comissão, avaliação, atribuição de serviço)
    vinculados. Hard-delete apagaria histórico financeiro/operacional
    que precisa continuar auditável, então o Django recusa via
    `on_delete=PROTECT` — aqui só traduzimos isso pra mensagem amigável.
    """
    def __init__(self, message=None):
        if message is None:
            message = _("Você tem agendamentos, não é possível excluir a conta.")
        super().__init__(message)