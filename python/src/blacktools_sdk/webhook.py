"""Verification of the signed webhook requests sent for payload buttons."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import cast

from .errors import BlacktoolsError, InvalidWebhookSignatureError
from .types import WebhookEvent

SIGNATURE_HEADER = "X-Blacktools-Signature"
TIMESTAMP_HEADER = "X-Blacktools-Timestamp"
DELIVERY_HEADER = "X-Blacktools-Delivery"
EVENT_HEADER = "X-Blacktools-Event"

WEBHOOK_EVENT_ACTION = "notification.action"
"""Type of the event sent when a recipient runs a payload button."""

DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300


def _as_bytes(value: bytes | str) -> bytes:
    return value.encode() if isinstance(value, str) else value


def verify_webhook(
    secret: str,
    timestamp: str,
    signature: str,
    raw_body: bytes | str,
    tolerance_seconds: float = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
) -> None:
    """Raises InvalidWebhookSignatureError unless signature signs raw_body under
    secret for timestamp, and timestamp is within tolerance_seconds of now."""
    if not (timestamp.isascii() and timestamp.isdigit()):
        raise InvalidWebhookSignatureError
    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        raise InvalidWebhookSignatureError

    mac = hmac.new(secret.encode(), timestamp.encode() + b"." + _as_bytes(raw_body), hashlib.sha256)
    want = b"sha256=" + mac.hexdigest().encode()
    if not hmac.compare_digest(want, signature.encode()):
        raise InvalidWebhookSignatureError


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if value is not None:
        return value
    wanted = name.lower()
    for key, candidate in headers.items():
        if key.lower() == wanted:
            return candidate
    return ""


def parse_webhook_event(
    secret: str, headers: Mapping[str, str], raw_body: bytes | str
) -> WebhookEvent:
    """Verifies a webhook request from its headers and exact raw body, and
    returns the decoded event."""
    verify_webhook(
        secret, _header(headers, TIMESTAMP_HEADER), _header(headers, SIGNATURE_HEADER), raw_body
    )
    try:
        return cast(WebhookEvent, json.loads(raw_body))
    except ValueError as err:
        raise BlacktoolsError(f"decoding webhook event: {err}") from err
