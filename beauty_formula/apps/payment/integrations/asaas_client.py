import requests
from django.conf import settings
from beauty_formula.apps.core.exceptions.payment_exception import AsaasAPIError


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

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as e:
            raise AsaasAPIError(f"Falha de conexão com a Asaas: {e}")

        if not response.ok:
            try:
                payload = response.json()
                message = payload.get("errors", [{}])[0].get("description", response.text)
            except (ValueError, IndexError, KeyError):
                payload = {}
                message = response.text
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
            "value": float(value),
            "dueDate": due_date,
            "description": description,
            "externalReference": external_reference,
        }
        return self._request("POST", "/payments", json=payload)

    def get_payment(self, payment_id: str) -> dict:
        return self._request("GET", f"/payments/{payment_id}")

    def get_pix_qrcode(self, payment_id: str) -> dict:
        """Só retorna algo útil se billingType da cobrança for PIX (ou UNDEFINED)."""
        return self._request("GET", f"/payments/{payment_id}/pixQrCode")

    def cancel_payment(self, payment_id: str) -> dict:
        return self._request("DELETE", f"/payments/{payment_id}")