"""Webhook do Asaas: autenticação, robustez do payload e idempotência."""
import json
from decimal import Decimal

import pytest

from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

URL = "/api/payments/webhook"
TOKEN = "token-de-teste"


@pytest.fixture(autouse=True)
def _webhook_token(settings):
    settings.ASAAS_WEBHOOK_TOKEN = TOKEN


def _post(client, body, token=TOKEN, raw=False):
    headers = {"HTTP_ASAAS_ACCESS_TOKEN": token} if token is not None else {}
    data = body if raw else json.dumps(body)
    return client.post(URL, data=data, content_type="application/json", **headers)


def _event(payment_id="pay_123", status="RECEIVED"):
    return {"event": "PAYMENT_RECEIVED", "payment": {"id": payment_id, "status": status}}


def test_rejects_missing_token(client, pending_payment):
    assert _post(client, _event(), token=None).status_code == 401


def test_rejects_wrong_token(client, pending_payment):
    assert _post(client, _event(), token="errado").status_code == 401
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.PENDING


def test_rejects_when_server_token_is_not_configured(client, pending_payment, settings):
    settings.ASAAS_WEBHOOK_TOKEN = ""
    assert _post(client, _event(), token="").status_code == 401


def test_invalid_json_is_400_not_500(client):
    assert _post(client, "{isso não é json", raw=True).status_code == 400


def test_json_that_is_not_an_object_is_400(client):
    assert _post(client, "[1,2,3]", raw=True).status_code == 400


def test_unknown_payment_is_acknowledged_so_asaas_does_not_retry_forever(client):
    assert _post(client, _event(payment_id="pay_inexistente")).status_code == 200


def test_payload_without_payment_is_acknowledged(client):
    assert _post(client, {"event": "ALGO"}).status_code == 200


def test_received_confirms_payment_and_scheduling(client, pending_payment, scheduling):
    assert _post(client, _event(status="RECEIVED")).status_code == 200
    pending_payment.refresh_from_db()
    scheduling.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.RECEIVED
    assert pending_payment.payment_date is not None
    assert scheduling.status == Scheduling.SchedulingStatus.CONFIRMED


def test_webhook_is_idempotent(client, pending_payment, scheduling):
    assert _post(client, _event()).status_code == 200
    first_date = Payment.objects.get(pk=pending_payment.pk).payment_date
    assert _post(client, _event()).status_code == 200
    pending_payment.refresh_from_db()
    scheduling.refresh_from_db()
    assert pending_payment.payment_date == first_date
    assert scheduling.status == Scheduling.SchedulingStatus.CONFIRMED


def test_late_pending_event_does_not_downgrade_a_paid_payment(client, pending_payment):
    _post(client, _event(status="RECEIVED"))
    _post(client, _event(status="PENDING"))
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.RECEIVED


def test_late_overdue_event_does_not_downgrade_a_paid_payment(client, pending_payment):
    _post(client, _event(status="CONFIRMED"))
    _post(client, _event(status="OVERDUE"))
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.CONFIRMED


def test_unknown_status_is_ignored_instead_of_corrupting_the_record(client, pending_payment):
    assert _post(client, _event(status="STATUS_NOVO_DO_ASAAS")).status_code == 200
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.PENDING


def test_refund_after_payment_is_applied(client, pending_payment):
    _post(client, _event(status="RECEIVED"))
    _post(client, _event(status="REFUNDED"))
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.REFUNDED


def test_overdue_on_pending_payment_is_applied(client, pending_payment):
    _post(client, _event(status="OVERDUE"))
    pending_payment.refresh_from_db()
    assert pending_payment.status == Payment.PaymentStatus.OVERDUE