from __future__ import annotations

from typing import TypeVar

from . import _core
from ._core import DEFAULT_AUTH_URL, DEFAULT_GATEWAY_URL, DEFAULT_TIMEOUT, BaseClient, Call
from .transport import AsyncTransport, Transport, threaded_urllib_transport, urllib_transport
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

T = TypeVar("T")


class Client(BaseClient):
    def __init__(
        self,
        service_token: str,
        *,
        gateway_url: str = DEFAULT_GATEWAY_URL,
        auth_url: str = DEFAULT_AUTH_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        transport: Transport | None = None,
    ) -> None:
        super().__init__(service_token, gateway_url=gateway_url, auth_url=auth_url, timeout=timeout)
        self._transport = transport or urllib_transport

    def _call(self, call: Call[T]) -> T:
        return self._finish(call, self._transport(self._build(call)))

    def exchange_code(self, code: str) -> TokenPair:
        return self._call(_core.exchange_code(code))

    def refresh_token(self, refresh_token: str) -> TokenPair:
        return self._call(_core.refresh_token(refresh_token))

    def check_permission(self, user_id: int, permission: str) -> bool:
        return self._call(_core.check_permission(user_id, permission))

    def get_profile(
        self,
        *,
        user_id: int | None = None,
        access_token: str | None = None,
        expand: bool = False,
        email: bool = False,
        roles: bool = False,
    ) -> Profile:
        return self._call(_core.get_profile(user_id, access_token, expand, email, roles))

    def get_posts(self, access_token: str) -> list[PostSnapshot]:
        return self._call(_core.get_posts(access_token))

    def get_warns(self, access_token: str) -> list[Warn]:
        return self._call(_core.get_warns(access_token))

    def refresh_posts(self, access_token: str) -> list[PostSnapshot]:
        return self._call(_core.refresh_posts(access_token))

    def refresh_connections(self, access_token: str) -> ExpandedConnections:
        return self._call(_core.refresh_connections(access_token))

    def list_moderators(self, server_index: int, query: str | None = None) -> list[Moderator]:
        return self._call(_core.list_moderators(server_index, query))

    def find_moderator(self, server_index: int, query: str) -> Moderator:
        return self._call(_core.find_moderator(server_index, query))

    def get_moderator_connections(self, server_index: int, user_id: str) -> Connections:
        return self._call(_core.get_moderator_connections(server_index, user_id))

    def refresh_moderator_connections(self, server_index: int, user_id: str) -> Connections:
        return self._call(_core.refresh_moderator_connections(server_index, user_id))

    def get_moderator_posts(self, server_index: int, user_id: str) -> list[PostSnapshot]:
        return self._call(_core.get_moderator_posts(server_index, user_id))

    def refresh_moderator_posts(self, server_index: int, user_id: str) -> list[PostSnapshot]:
        return self._call(_core.refresh_moderator_posts(server_index, user_id))

    def notify_server(self, server_index: int, notification: NotifyRequest) -> NotifyServerResult:
        return self._call(_core.notify_server(server_index, notification))

    def notify_moderator(
        self, server_index: int, user_id: str, notification: NotifyRequest
    ) -> NotifyModeratorResult:
        return self._call(_core.notify_moderator(server_index, user_id, notification))

    def set_webhook(self, url: str) -> WebhookConfig:
        return self._call(_core.set_webhook(url))

    def delete_webhook(self) -> None:
        self._call(_core.delete_webhook())


class AsyncClient(BaseClient):
    def __init__(
        self,
        service_token: str,
        *,
        gateway_url: str = DEFAULT_GATEWAY_URL,
        auth_url: str = DEFAULT_AUTH_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        transport: AsyncTransport | None = None,
    ) -> None:
        super().__init__(service_token, gateway_url=gateway_url, auth_url=auth_url, timeout=timeout)
        self._transport = transport or threaded_urllib_transport

    async def _call(self, call: Call[T]) -> T:
        return self._finish(call, await self._transport(self._build(call)))

    async def exchange_code(self, code: str) -> TokenPair:
        return await self._call(_core.exchange_code(code))

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        return await self._call(_core.refresh_token(refresh_token))

    async def check_permission(self, user_id: int, permission: str) -> bool:
        return await self._call(_core.check_permission(user_id, permission))

    async def get_profile(
        self,
        *,
        user_id: int | None = None,
        access_token: str | None = None,
        expand: bool = False,
        email: bool = False,
        roles: bool = False,
    ) -> Profile:
        return await self._call(_core.get_profile(user_id, access_token, expand, email, roles))

    async def get_posts(self, access_token: str) -> list[PostSnapshot]:
        return await self._call(_core.get_posts(access_token))

    async def get_warns(self, access_token: str) -> list[Warn]:
        return await self._call(_core.get_warns(access_token))

    async def refresh_posts(self, access_token: str) -> list[PostSnapshot]:
        return await self._call(_core.refresh_posts(access_token))

    async def refresh_connections(self, access_token: str) -> ExpandedConnections:
        return await self._call(_core.refresh_connections(access_token))

    async def list_moderators(self, server_index: int, query: str | None = None) -> list[Moderator]:
        return await self._call(_core.list_moderators(server_index, query))

    async def find_moderator(self, server_index: int, query: str) -> Moderator:
        return await self._call(_core.find_moderator(server_index, query))

    async def get_moderator_connections(self, server_index: int, user_id: str) -> Connections:
        return await self._call(_core.get_moderator_connections(server_index, user_id))

    async def refresh_moderator_connections(self, server_index: int, user_id: str) -> Connections:
        return await self._call(_core.refresh_moderator_connections(server_index, user_id))

    async def get_moderator_posts(self, server_index: int, user_id: str) -> list[PostSnapshot]:
        return await self._call(_core.get_moderator_posts(server_index, user_id))

    async def refresh_moderator_posts(self, server_index: int, user_id: str) -> list[PostSnapshot]:
        return await self._call(_core.refresh_moderator_posts(server_index, user_id))

    async def notify_server(
        self, server_index: int, notification: NotifyRequest
    ) -> NotifyServerResult:
        return await self._call(_core.notify_server(server_index, notification))

    async def notify_moderator(
        self, server_index: int, user_id: str, notification: NotifyRequest
    ) -> NotifyModeratorResult:
        return await self._call(_core.notify_moderator(server_index, user_id, notification))

    async def set_webhook(self, url: str) -> WebhookConfig:
        return await self._call(_core.set_webhook(url))

    async def delete_webhook(self) -> None:
        await self._call(_core.delete_webhook())
