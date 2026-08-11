

from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from beauty_formula.apps.core.exceptions.payment_exception import AsaasAPIError
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient


class AsaasIntegrationFixTests(SimpleTestCase):
    def test_asaas_error_message_is_a_real_string(self):
        error = AsaasAPIError()
        self.assertIsInstance(error.message, str)
        self.assertEqual(str(error), error.message)

    def test_money_is_sent_with_two_decimal_places(self):
        self.assertEqual(AsaasClient._money(Decimal("19.899999999")), 19.90)
        self.assertEqual(AsaasClient._money(Decimal("10.005")), 10.01)

    @patch("beauty_formula.apps.payment.integrations.asaas_client.requests.Session")
    def test_none_fields_are_not_sent_to_asaas(self, session_cls):
        session = Mock()
        session_cls.return_value = session

        response = Mock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"id": "pay_123"}'
        response.json.return_value = {"id": "pay_123"}
        session.request.return_value = response

        client = AsaasClient()
        client.create_payment(
            customer_id="cus_123",
            billing_type="PIX",
            value=Decimal("19.899999999"),
            due_date="2026-08-11",
        )

        kwargs = session.request.call_args.kwargs
        payload = kwargs["json"]

        self.assertEqual(payload["value"], 19.90)
        self.assertNotIn("description", payload)
        self.assertNotIn("externalReference", payload)

