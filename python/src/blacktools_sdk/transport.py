from __future__ import annotations

import asyncio
import http.client
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from .errors import TransportError


@dataclass(frozen=True)
class HTTPRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    timeout: float | None


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    reason: str
    headers: Mapping[str, str]
    body: bytes

    def header(self, name: str) -> str | None:
        wanted = name.lower()
        for key, value in self.headers.items():
            if key.lower() == wanted:
                return value
        return None


Transport = Callable[[HTTPRequest], HTTPResponse]
AsyncTransport = Callable[[HTTPRequest], Awaitable[HTTPResponse]]

_opener = urllib.request.build_opener()


def urllib_transport(request: HTTPRequest) -> HTTPResponse:
    req = urllib.request.Request(
        request.url, data=request.body, headers=dict(request.headers), method=request.method
    )
    try:
        with _opener.open(req, timeout=request.timeout) as resp:
            return HTTPResponse(resp.status, resp.reason, dict(resp.headers.items()), resp.read())
    except urllib.error.HTTPError as err:
        with err:
            body = err.read()
        headers = dict(err.headers.items()) if err.headers is not None else {}
        return HTTPResponse(err.code, str(err.reason or ""), headers, body)
    except (OSError, http.client.HTTPException) as err:
        raise TransportError(f"request failed: {err}") from err


async def threaded_urllib_transport(request: HTTPRequest) -> HTTPResponse:
    return await asyncio.to_thread(urllib_transport, request)
