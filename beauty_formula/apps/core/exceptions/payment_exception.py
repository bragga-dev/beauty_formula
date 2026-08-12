from django.utils.translation import gettext as _


class AsaasAPIError(Exception):
    """Erro genérico de comunicação com a API da Asaas."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        payload: dict | None = None,
    ):
        self.message = message or _("Erro ao se comunicar com a Asaas.")
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(self.message)


class PaymentNotFound(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Pagamento não encontrado.")
        super().__init__(self.message)


class SchedulingAlreadyPaid(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Já existe uma cobrança em aberto ou paga para este agendamento."
        )
        super().__init__(self.message)

class CpfOrCnpjRequired(Exception):
    """
    Só é levantada na 1ª cobrança via cartão de um cliente: a Asaas exige
    CPF/CNPJ pra criar o customer dele. Nas cobranças seguintes o
    customer_id já fica salvo no Client e isso não é mais pedido.
    """
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Informe o CPF ou CNPJ para pagar com cartão de crédito."
        )
        super().__init__(self.message)