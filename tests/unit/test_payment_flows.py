import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from nostr_dvm.utils import zap_utils


class PaymentFlowTests(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            LNBITS_URL="https://wallet.example.com",
            LNBITS_ADMIN_KEY="test-admin-key",
            LNBITS_INVOICE_KEY="test-invoice-key",
        )

    def test_payment_request_is_sent_once(self):
        response = SimpleNamespace(text=json.dumps({"payment_hash": "test-payment-hash"}))
        with patch.object(zap_utils.requests, "post", return_value=response) as post:
            result = zap_utils.pay_bolt11_ln_bits("test-invoice", self.config)
        self.assertEqual(result, "test-payment-hash")
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "https://wallet.example.com/api/v1/payments")
        self.assertEqual(post.call_args.kwargs["json"], {"out": True, "bolt11": "test-invoice"})
        self.assertEqual(post.call_args.kwargs["headers"]["X-API-Key"], "test-admin-key")

    def test_payment_errors_do_not_retry_or_report_success(self):
        for response in ({"detail": "payment failed"}, {}):
            with self.subTest(response=response), patch.object(
                zap_utils.requests, "post", return_value=SimpleNamespace(text=json.dumps(response))
            ) as post:
                self.assertEqual(zap_utils.pay_bolt11_ln_bits("test-invoice", self.config), "Error")
                post.assert_called_once()
        with patch.object(zap_utils.requests, "post", side_effect=requests.Timeout("test timeout")) as post:
            self.assertEqual(zap_utils.pay_bolt11_ln_bits("test-invoice", self.config), "Error")
            post.assert_called_once()

    def test_payment_status_distinguishes_pending_and_unavailable(self):
        for paid in (True, False):
            with self.subTest(paid=paid), patch.object(
                zap_utils.requests, "get", return_value=SimpleNamespace(text=json.dumps({"paid": paid}))
            ):
                self.assertIs(zap_utils.check_bolt11_ln_bits_is_paid("test-hash", self.config), paid)
        with patch.object(zap_utils.requests, "get", side_effect=requests.Timeout("test timeout")):
            self.assertIsNone(zap_utils.check_bolt11_ln_bits_is_paid("test-hash", self.config))


if __name__ == "__main__":
    unittest.main()
