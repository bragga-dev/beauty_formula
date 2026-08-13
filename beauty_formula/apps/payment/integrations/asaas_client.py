import logging

import requests
from django.conf import settings
from beauty_formula.apps.core.exceptions.payment_exception import AsaasAPIError

logger = logging.getLogger(__name__)


class AsaasClient:
    """
    Wrapper fino sobre a API REST da Asaas (v3). Só monta requisições e
    traduz erro HTTP em AsaasAPIError — nenhuma regra de negócio aqui
    (isso fica no payment_service). Base URL/chave vêm de ASAAS_BASE_URL
    e ASAAS_API_KEY (settings/base.py), configuráveis por .env
    (sandbox vs produção).
    """

    def __init__(self):
        self.base_url = settings.ASAAS_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "access_token": settings.ASAAS_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "beauty-formula",
        })

    @staticmethod
    def _redact_body(body):
        """Mascara CPF/CNPJ antes de logar — nunca em texto puro no log."""
        if not isinstance(body, dict) or "cpfCnpj" not in body:
            return body
        redacted = dict(body)
        redacted["cpfCnpj"] = "***"
        return redacted

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"

        # Log da request ANTES de disparar — se dar 401/erro de novo, isso
        # mostra a URL final e o corpo exatos que saíram, em vez de a gente
        # ficar adivinhando. A chave só aparece mascarada (8 primeiros +
        # 6 últimos caracteres) — nunca loga o token inteiro.
        masked_key = settings.ASAAS_API_KEY
        if masked_key and len(masked_key) > 14:
            masked_key = f"{masked_key[:8]}...{masked_key[-6:]}"
        logger.info("Asaas request: %s %s | access_token=%s | body=%s", method, url, masked_key, self._redact_body(kwargs.get("json")),)

        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as e:
            raise AsaasAPIError(f"Falha de conexão com a Asaas: {e}")

        logger.info("Asaas response: %s %s -> %s | headers=%s | body=%r", method, url, response.status_code, dict(response.headers), response.text[:500],)

        if not response.ok:
            payload = {}
            message = response.text
            try:
                payload = response.json()
                message = payload.get("errors", [{}])[0].get("description", response.text)
            except (ValueError, IndexError, KeyError):
                pass

            if not message:
                message = (
                    f"Asaas retornou {response.status_code} sem corpo de resposta "
                    f"para {method} {path}. Veja o log 'Asaas request/response' "
                    "logo acima pra conferir URL, corpo e headers de resposta."
                )

            raise AsaasAPIError(message, status_code=response.status_code, payload=payload)

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ── Payments (Cobranças) ─────────────────────────────────────────────

    def create_payment(
        self,
        *,
        customer_id: str,
        billing_type: str,
        value: float,
        due_date: str,
        description: str = None,
        external_reference: str = None,
    ) -> dict:
        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            # round explícito: Decimal -> float pode gerar erro de ponto
            # flutuante (ex: 19.9 -> 19.899999999999998) e a Asaas rejeita
            # valor com mais de 2 casas decimais.
            "value": round(float(value), 2),
            "dueDate": due_date,
            "description": description,
            "externalReference": external_reference,
        }
        # Não manda chave com valor None: a Asaas trata alguns campos nulos
        # como "resetar" a config (ex: os objetos interest/fine sobrescrevem
        # a config global da conta se enviados vazios/nulos — mesmo padrão
        # vale aqui, então é mais seguro só omitir o que não foi passado).
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/payments", json=payload)

    def get_payment(self, payment_id: str) -> dict:
        return self._request("GET", f"/payments/{payment_id}")

    def get_pix_qrcode(self, payment_id: str) -> dict:
        """Só retorna algo útil se billingType da cobrança for PIX (ou UNDEFINED)."""
        return self._request("GET", f"/payments/{payment_id}/pixQrCode")

    def cancel_payment(self, payment_id: str) -> dict:
        return self._request("DELETE", f"/payments/{payment_id}")

    # ── Customers (Clientes) ─────────────────────────────────────────────

    def create_customer(
        self,
        *,
        name: str,
        cpf_cnpj: str,
        email: str = None,
        external_reference: str = None,
    ) -> dict:
        """
        Cria um customer na Asaas — só usado na 1ª cobrança via cartão de
        cada cliente (a Asaas exige cpfCnpj pra criar customer via API,
        não tem como pular esse campo). PIX/Boleto continuam usando o
        customer único do dono do salão, não passam por aqui.
        """
        payload = {
            "name": name,
            "cpfCnpj": cpf_cnpj,
            "email": email,
            "externalReference": external_reference,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/customers", json=payload)



    def refund_payment(self, payment_id: str, *, value: float = None, description: str = None) -> dict:
        """
        Estorna uma cobrança PIX ou cartão já RECEIVED/CONFIRMED. Sem
        `value`, estorna o valor integral; com `value`, estorno parcial
        (ex: reter taxa de cancelamento) — a Asaas valida se cabe no saldo
        disponível da cobrança.

        Boleto tem fluxo próprio (POST /payments/{id}/bankSlip/refund),
        que exige o pagador informar dados bancários — não coberto aqui.
        """
        payload = {"value": value, "description": description}
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", f"/payments/{payment_id}/refund", json=payload)