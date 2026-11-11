"""Route definitions plus request building and response decoding shared by
the sync and async clients."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar
from urllib.parse import quote, urlencode

from .errors import APIError, BlacktoolsError
from .transport import HTTPRequest, HTTPResponse
from .types import (
    Connections,
    ExpandedConnections,
    Moderator,
    NotifyModeratorResult,
    NotifyRequest,
    NotifyServerResult,
    PostSnapshot,
    Profile,
    TokenPair,
    Warn,
    WebhookConfig,
)

__version__ = "0.1.0"

T = TypeVar("T")

DEFAULT_TIMEOUT = 30.0
DEFAULT_GATEWAY_URL = "https://blacktools.odsmod.su/api"
DEFAULT_AUTH_URL = "https://blacktools.odsmod.su/auth"
_USER_AGENT = f"blacktools-sdk-python/{__version__}"


@dataclass(frozen=True)
class Call(Generic[T]):
    """One API call: where it goes, what it sends, and how its JSON decodes."""

    base: Literal["gateway", "auth"]
    method: str
    path: str
    decode: Callable[[Any], T]
    query: Mapping[str, str] | None = None
    body: Any = None
    access_token: str | None = None
    idempotency_key: str | None = None


def _json(data: Any) -> Any:
    """Passes the decoded JSON through unchanged."""
    return data


def _none(_: Any) -> None:
    return None


def _granted(data: Any) -> bool:
    return bool(data["granted"])


def _server_path(server_index: int, suffix: str) -> str:
    return f"/sso/servers/{int(server_index)}{suffix}"


def _moderator_path(server_index: int, user_id: str, suffix: str) -> str:
    return _server_path(server_index, f"/moderators/{quote(user_id, safe='')}{suffix}")


def exchange_code(code: str) -> Call[TokenPair]:
    return Call("auth", "POST", "/sso/exchange", _json, body={"code": code})


def refresh_token(token: str) -> Call[TokenPair]:
    return Call("auth", "POST", "/sso/refresh", _json, body={"refresh_token": token})


def check_permission(user_id: int, permission: str) -> Call[bool]:
    return Call(
        "gateway",
        "GET",
        "/sso/perms/check",
        _granted,
        body={"user_id": user_id, "permission": permission},
    )


def get_profile(
    user_id: int | None, access_token: str | None, expand: bool, email: bool, roles: bool
) -> Call[Profile]:
    flags = {"expand": expand, "email": email, "roles": roles}
    query = {name: "true" for name, on in flags.items() if on}
    body = {"user_id": user_id} if user_id is not None else None
    return Call(
        "gateway",
        "GET",
        "/sso/profile",
        _json,
        query=query,
        body=body,
        access_token=access_token,
    )


def user_route(method: str, path: str, decoder: Callable[[Any], T], token: str) -> Call[T]:
    return Call("gateway", method, path, decoder, access_token=token)


def get_posts(token: str) -> Call[list[PostSnapshot]]:
    return user_route("GET", "/sso/posts", _json, token)


def get_warns(token: str) -> Call[list[Warn]]:
    return user_route("GET", "/sso/warns", _json, token)


def refresh_posts(token: str) -> Call[list[PostSnapshot]]:
    return user_route("POST", "/sso/posts/refresh", _json, token)


def refresh_connections(token: str) -> Call[ExpandedConnections]:
    return user_route("POST", "/sso/connections/refresh", _json, token)


def list_moderators(server_index: int, query: str | None) -> Call[list[Moderator]]:
    return Call(
        "gateway",
        "GET",
        _server_path(server_index, "/moderators"),
        _json,
        query={"query": query} if query else None,
    )


def find_moderator(server_index: int, query: str) -> Call[Moderator]:
    return Call(
        "gateway",
        "GET",
        _server_path(server_index, "/moderator"),
        _json,
        query={"query": query},
    )


def get_moderator_connections(server_index: int, user_id: str) -> Call[Connections]:
    path = _moderator_path(server_index, user_id, "/connections")
    return Call("gateway", "GET", path, _json)


def refresh_moderator_connections(server_index: int, user_id: str) -> Call[Connections]:
    path = _moderator_path(server_index, user_id, "/connections/refresh")
    return Call("gateway", "POST", path, _json)


def get_moderator_posts(server_index: int, user_id: str) -> Call[list[PostSnapshot]]:
    path = _moderator_path(server_index, user_id, "/posts")
    return Call("gateway", "GET", path, _json)


def refresh_moderator_posts(server_index: int, user_id: str) -> Call[list[PostSnapshot]]:
    path = _moderator_path(server_index, user_id, "/posts/refresh")
    return Call("gateway", "POST", path, _json)


def _notify(path: str, notification: NotifyRequest, decoder: Callable[[Any], T]) -> Call[T]:
    body = {k: v for k, v in notification.items() if k != "idempotency_key"}
    key = notification.get("idempotency_key")
    return Call("gateway", "POST", path, decoder, body=body, idempotency_key=key)


def notify_server(server_index: int, notification: NotifyRequest) -> Call[NotifyServerResult]:
    path = _server_path(server_index, "/notify")
    return _notify(path, notification, _json)


def notify_moderator(
    server_index: int, user_id: str, notification: NotifyRequest
) -> Call[NotifyModeratorResult]:
    path = _moderator_path(server_index, user_id, "/notify")
    return _notify(path, notification, _json)


def set_webhook(url: str) -> Call[WebhookConfig]:
    return Call("gateway", "PUT", "/sso/webhook", _json, body={"url": url})


def delete_webhook() -> Call[None]:
    return Call("gateway", "DELETE", "/sso/webhook", _none)


class BaseClient:
    """Holds the client configuration and turns Calls into HTTP exchanges."""

    def __init__(
        self,
        service_token: str,
        *,
        gateway_url: str = DEFAULT_GATEWAY_URL,
        auth_url: str = DEFAULT_AUTH_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        self._gateway_url = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")
        self._auth_url = (auth_url or DEFAULT_AUTH_URL).rstrip("/")
        self._service_token = service_token
        self._timeout = timeout

    def _build(self, call: Call[Any]) -> HTTPRequest:
        url = self._base_url(call.base) + call.path
        if call.query:
            url += "?" + urlencode(call.query)

        headers = {
            "Authorization": f"Bearer {self._service_token}",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if call.access_token:
            headers["X-Access-Token"] = call.access_token
        if call.idempotency_key:
            headers["Idempotency-Key"] = call.idempotency_key

        body = None
        if call.body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(call.body, ensure_ascii=False).encode()
        return HTTPRequest(call.method, url, headers, body, self._timeout)

    def _base_url(self, base: str) -> str:
        return self._gateway_url if base == "gateway" else self._auth_url

    @staticmethod
    def _finish(call: Call[T], response: HTTPResponse) -> T:
        if not 200 <= response.status < 300:
            raise build_api_error(response)
        if not response.body.strip():
            return call.decode(None)
        try:
            data = json.loads(response.body)
        except ValueError as err:
            raise BlacktoolsError(f"decoding response: {err}") from err
        return call.decode(data)


def build_api_error(response: HTTPResponse) -> APIError:
    """Builds the APIError for a non-2xx response."""
    text = response.body.decode("utf-8", errors="replace")
    message = response.reason or str(response.status)
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), str) and parsed["error"]:
        message = parsed["error"]

    return APIError(
        response.status,
        message,
        text,
        retry_after_seconds=_int_header(response, "Retry-After"),
        rate_limit_limit=_int_header(response, "X-RateLimit-Limit"),
        rate_limit_remaining=_int_header(response, "X-RateLimit-Remaining"),
    )


def _int_header(response: HTTPResponse, name: str) -> int | None:
    value = response.header(name)
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None
