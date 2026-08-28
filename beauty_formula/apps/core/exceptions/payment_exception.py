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

class PaymentNotRefundable(Exception):
    """
    Cobrança fora das condições de estorno: ainda não foi paga, já foi
    totalmente estornada, é boleto (fluxo próprio, exige dados bancários
    do pagador — não suportado por aqui), ou o valor pedido não cabe no
    saldo disponível da cobrança.
    """
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Essa cobrança não pode ser estornada — só cobranças pagas via "
            "Pix ou cartão, ainda não totalmente estornadas."
        )
        super().__init__(self.message)

class SchedulingPaymentPending(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Este agendamento possui um pagamento pendente."
        )
        super().__init__(self.message)

class CommissionNotFound(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Comissão não encontrada.")
        super().__init__(self.message)


class CommissionAlreadyExists(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Este agendamento já possui uma comissão registrada.")
        super().__init__(self.message)


class SchedulingNotCompleted(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Só é possível gerar comissão para um atendimento concluído (COMPLETED)."
        )
        super().__init__(self.message)


class CommissionCannotBeModified(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Esta comissão não pode mais ser alterada — só comissões pendentes podem ser editadas ou canceladas."
        )
        super().__init__(self.message)


class CommissionNotPaid(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Só é possível reverter comissões que estejam pagas."
        )
        super().__init__(self.message)