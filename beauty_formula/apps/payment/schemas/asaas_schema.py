# payments/schemas/asaas.py

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date
from ninja import Schema

class AsaasCustomerCreateSchema(Schema):
    name: str
    email: str
    phone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    address_number: Optional[str] = None
    complement: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    external_reference: Optional[str] = None

class AsaasCustomerResponseSchema(Schema):
    id: str
    name: str
    email: str
    cpf_cnpj: Optional[str]
    external_reference: Optional[str]

class AsaasPaymentCreateSchema(Schema):
    customer: str
    billing_type: str
    value: Decimal
    due_date: str
    description: Optional[str] = None
    external_reference: Optional[str] = None
    days_after_due_date_to_registration_cancellation: Optional[int] = 3
    discount: Optional[Dict[str, Any]] = None
    interest: Optional[Dict[str, Any]] = None
    fine: Optional[Dict[str, Any]] = None
    split: Optional[List[Dict[str, Any]]] = None
    callback: Optional[Dict[str, Any]] = None
    pix_automatic_authorization_id: Optional[str] = None

class AsaasPaymentResponseSchema(Schema):
    id: str
    customer: str
    value: Decimal
    net_value: Optional[Decimal]
    billing_type: str
    status: str
    due_date: date
    description: Optional[str]
    external_reference: Optional[str]
    invoice_url: Optional[str]
    bank_slip_url: Optional[str]
    payment_date: Optional[datetime]
    pix_qr_code: Optional[Dict[str, Any]]

class AsaasPixQrCodeSchema(Schema):
    encoded_image: str
    payload: str
    expiration_time: Optional[datetime]

class AsaasWebhookPayloadSchema(Schema):
    event: str
    payment: Dict[str, Any]
    customer: Optional[Dict[str, Any]] = None