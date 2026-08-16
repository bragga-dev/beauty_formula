"""
Helpers privados de montagem de contexto para os e-mails de pagamento..
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from django.conf import settings

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,
    get_client_full_name_display,
)

from beauty_formula.apps.core.permissions.roles import is_client, is_employee
from beauty_formula.apps.payment.models.payment_model import Payment

# ─────────────────────────────────────────────────────────────────────────
# Rotas do frontend usadas nos botões/links dos e-mails.
# Único lugar que precisa mudar se as rotas reais do app front-end forem
# diferentes dessas.
#
# Não existe uma página "meus pagamentos" no frontend — o pagamento é
# resolvido dentro do próprio agendamento (`PaymentPanel` na tela de
# detalhe), então o CTA do e-mail aponta pra "Meus agendamentos", igual
# aos outros e-mails de agendamento.
# ─────────────────────────────────────────────────────────────────────────
_CLIENT_APPOINTMENTS_PATH = "/painel/meus-agendamentos"
_SALOON_PATH = "/"

def build_frontend_url(path: str) -> str:
    """Monta uma URL absoluta do frontend a partir de um path relativo."""
    return f"{settings.FRONTEND_URL}{path}"


def client_appointments_url() -> str:
    """Link para a área 'Meus agendamentos' do cliente."""
    return build_frontend_url(_CLIENT_APPOINTMENTS_PATH)

def saloon_url() -> str:
    """Link para a página do salão."""
    return build_frontend_url(_SALOON_PATH)



def build_payment_block(payment: Payment) -> dict:
    """Campos praticados no momento do pagamento."""
    return {
        # Código exibido ao cliente como referência do pagamento — usa o
        # ID da cobrança na Asaas (visível/rastreável pra ela, inclusive
        # no suporte deles), nunca o `payment.id` interno do nosso banco.
        "code_payment": payment.asaas_payment_id or payment.id,
        "payment_description": payment.description,
        "payment_value": payment.value,
        "payment_scheduling": payment.scheduling,
        "payment_client": payment.client,
        "payment_asaas_customer_id": payment.asaas_customer_id,
        "payment_asaas_id": payment.asaas_payment_id,
        "payment_billing_type": payment.billing_type,
        "payment_due_date": payment.due_date,
        "payment_invoice_url": payment.invoice_url,
        # A Asaas devolve o QR Code como base64 "cru" (sem o prefixo
        # data URI) — é assim que fica salvo em `payment.pix_qr_code`.
        # O front sabe disso e monta a data URI na hora de exibir
        # (`data:image/png;base64,${pix_qr_code}`); o e-mail precisa do
        # mesmo tratamento, senão o <img src="..."> não é uma URL válida
        # e o QR Code simplesmente não renderiza.
        "payment_pix_qr_code": f"data:image/png;base64,{payment.pix_qr_code}" if payment.pix_qr_code else None,
        "payment_created_at": payment.created_at,
        "payment_pix_copy_paste": payment.pix_copy_paste,    
        
    }