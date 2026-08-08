from django.utils.translation import gettext_lazy as _


class AsaasAPIError(Exception):
    """Erro genérico de comunicação com a API da Asaas."""

    def __init__(self, message: str = None, status_code: int = None, payload: dict = None):
        self.message = message or _("Erro ao se comunicar com a Asaas.")
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(self.message)


class PaymentNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Pagamento não encontrado.")
        super().__init__(self.message)


class SchedulingAlreadyPaid(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe uma cobrança em aberto ou paga para este agendamento.")
        super().__init__(self.message)