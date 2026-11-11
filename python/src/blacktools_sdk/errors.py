from __future__ import annotations


class BlacktoolsError(Exception):
    pass


class TransportError(BlacktoolsError):
    pass


class APIError(BlacktoolsError):
    def __init__(
        self,
        status: int,
        message: str,
        body: str,
        *,
        retry_after_seconds: int | None = None,
        rate_limit_limit: int | None = None,
        rate_limit_remaining: int | None = None,
    ) -> None:
        super().__init__(f"{message} (status {status})")
        self.status = status
        self.message = message
        self.body = body
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit_limit = rate_limit_limit
        self.rate_limit_remaining = rate_limit_remaining

    @property
    def is_rate_limited(self) -> bool:
        return self.status == 429


class InvalidWebhookSignatureError(BlacktoolsError):
    def __init__(self) -> None:
        super().__init__("invalid webhook signature")
