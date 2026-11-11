import hashlib
import hmac
import json
import time
import unittest
from unittest import mock

from blacktools_sdk import (
    InvalidWebhookSignatureError,
    parse_webhook_event,
    verify_webhook,
)

# Produced by notifications/internal/webhook.Sign, the real sender.
GO_SECRET = "whsec_test"
GO_TIMESTAMP = "1700000000"
GO_BODY = (
    b'{"type":"notification.action","id":"abc","action":{"payload":"leave:42:approve"},'
    b'"user":{"id":7,"discord_id":"123"}}'
)
GO_SIGNATURE = "sha256=10b9e54f070c3481fd3ce988f7b274ea3cb31da33fdb45bffbe8451453c3215e"


def sign(secret: str, timestamp: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


class VerifyWebhookTest(unittest.TestCase):
    def test_matches_go_signer(self) -> None:
        with mock.patch("blacktools_sdk.webhook.time.time", return_value=1700000010.0):
            verify_webhook(GO_SECRET, GO_TIMESTAMP, GO_SIGNATURE, GO_BODY)
            verify_webhook(GO_SECRET, GO_TIMESTAMP, GO_SIGNATURE, GO_BODY.decode())

    def test_rejects_tampered_body(self) -> None:
        with (
            mock.patch("blacktools_sdk.webhook.time.time", return_value=1700000010.0),
            self.assertRaises(InvalidWebhookSignatureError),
        ):
            verify_webhook(GO_SECRET, GO_TIMESTAMP, GO_SIGNATURE, GO_BODY + b" ")

    def test_rejects_wrong_secret(self) -> None:
        with (
            mock.patch("blacktools_sdk.webhook.time.time", return_value=1700000010.0),
            self.assertRaises(InvalidWebhookSignatureError),
        ):
            verify_webhook("other", GO_TIMESTAMP, GO_SIGNATURE, GO_BODY)

    def test_rejects_stale_and_future_timestamps(self) -> None:
        for now in (1700000000.0 + 301, 1700000000.0 - 301):
            with (
                mock.patch("blacktools_sdk.webhook.time.time", return_value=now),
                self.assertRaises(InvalidWebhookSignatureError),
            ):
                verify_webhook(GO_SECRET, GO_TIMESTAMP, GO_SIGNATURE, GO_BODY)

    def test_rejects_malformed_input(self) -> None:
        now = str(int(time.time()))
        good = sign("s", now, b"{}")
        cases = [
            ("", good),
            ("-1", good),
            ("１２", good),
            (now, ""),
            (now, "sha256=пп"),
        ]
        for timestamp, signature in cases:
            with (
                self.subTest(timestamp=timestamp, signature=signature),
                self.assertRaises(InvalidWebhookSignatureError),
            ):
                verify_webhook("s", timestamp, signature, b"{}")


class ParseWebhookEventTest(unittest.TestCase):
    def test_parses_with_any_header_case(self) -> None:
        body = json.dumps({"type": "notification.action", "action": {"payload": "p"}}).encode()
        now = str(int(time.time()))
        signature = sign("s", now, body)
        for headers in (
            {"X-Blacktools-Timestamp": now, "X-Blacktools-Signature": signature},
            {"x-blacktools-timestamp": now, "x-blacktools-signature": signature},
        ):
            event = parse_webhook_event("s", headers, body)
            self.assertEqual(event["action"]["payload"], "p")

    def test_missing_headers(self) -> None:
        with self.assertRaises(InvalidWebhookSignatureError):
            parse_webhook_event("s", {}, b"{}")


if __name__ == "__main__":
    unittest.main()
