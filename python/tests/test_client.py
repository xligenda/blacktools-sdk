import asyncio
import json
import threading
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from blacktools_sdk import (
    DEFAULT_AUTH_URL,
    DEFAULT_GATEWAY_URL,
    APIError,
    AsyncClient,
    BlacktoolsError,
    Client,
    HTTPRequest,
    HTTPResponse,
    TransportError,
)


class Recorder:
    """A transport that records requests and answers with a canned response."""

    def __init__(self, status: int = 200, body: Any = None, headers: Any = None) -> None:
        self.requests: list[HTTPRequest] = []
        raw = b"" if body is None else json.dumps(body).encode()
        self.response = HTTPResponse(status, "Reason", headers or {}, raw)

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        self.requests.append(request)
        return self.response

    @property
    def last(self) -> HTTPRequest:
        return self.requests[-1]

    def last_json(self) -> Any:
        assert self.last.body is not None
        return json.loads(self.last.body)


def client(transport: Recorder) -> Client:
    return Client(
        "svc_1.1.secret",
        gateway_url="https://gw.example/",
        auth_url="https://auth.example",
        transport=transport,
    )


class RequestShapeTest(unittest.TestCase):
    def test_exchange_code_goes_to_auth(self) -> None:
        rec = Recorder(body={"access_token": "a", "refresh_token": "r", "user_id": 1})
        tokens = client(rec).exchange_code("ABC123")
        self.assertEqual(tokens["access_token"], "a")
        self.assertEqual(rec.last.method, "POST")
        self.assertEqual(rec.last.url, "https://auth.example/sso/exchange")
        self.assertEqual(rec.last_json(), {"code": "ABC123"})
        self.assertEqual(rec.last.headers["Authorization"], "Bearer svc_1.1.secret")
        self.assertEqual(rec.last.headers["Content-Type"], "application/json")

    def test_defaults_to_production(self) -> None:
        rec = Recorder(body={"granted": True})
        c = Client("t", transport=rec)
        c.check_permission(1, "x")
        self.assertEqual(rec.last.url, DEFAULT_GATEWAY_URL + "/sso/perms/check")
        rec.response = HTTPResponse(200, "OK", {}, b'{"access_token":"a"}')
        c.refresh_token("r")
        self.assertEqual(rec.last.url, DEFAULT_AUTH_URL + "/sso/refresh")

    def test_check_permission_sends_get_body(self) -> None:
        rec = Recorder(body={"granted": True})
        self.assertTrue(client(rec).check_permission(5, "reports.view"))
        self.assertEqual(rec.last.method, "GET")
        self.assertEqual(rec.last.url, "https://gw.example/sso/perms/check")
        self.assertEqual(rec.last_json(), {"user_id": 5, "permission": "reports.view"})

    def test_get_profile_flags_and_token(self) -> None:
        rec = Recorder(body={"user_id": 1, "nickname": "n", "created_at": "x"})
        client(rec).get_profile(access_token="tok", expand=True, roles=True)
        self.assertEqual(rec.last.url, "https://gw.example/sso/profile?expand=true&roles=true")
        self.assertEqual(rec.last.headers["X-Access-Token"], "tok")
        self.assertIsNone(rec.last.body)

    def test_get_profile_by_user_id(self) -> None:
        rec = Recorder(body={"user_id": 9, "nickname": "n", "created_at": "x"})
        client(rec).get_profile(user_id=9)
        self.assertEqual(rec.last.url, "https://gw.example/sso/profile")
        self.assertEqual(rec.last_json(), {"user_id": 9})
        self.assertNotIn("X-Access-Token", rec.last.headers)

    def test_user_routes(self) -> None:
        rec = Recorder(body=[])
        c = client(rec)
        cases = [
            (c.get_posts, "GET", "/sso/posts"),
            (c.get_warns, "GET", "/sso/warns"),
            (c.refresh_posts, "POST", "/sso/posts/refresh"),
            (c.refresh_connections, "POST", "/sso/connections/refresh"),
        ]
        for method, verb, path in cases:
            with self.subTest(path=path):
                method("tok")
                self.assertEqual(rec.last.method, verb)
                self.assertEqual(rec.last.url, "https://gw.example" + path)
                self.assertEqual(rec.last.headers["X-Access-Token"], "tok")

    def test_server_routes(self) -> None:
        rec = Recorder(body=[])
        c = client(rec)
        base = "https://gw.example/sso/servers/3"
        c.list_moderators(3)
        self.assertEqual(rec.last.url, base + "/moderators")
        c.list_moderators(3, "Иван")
        self.assertEqual(rec.last.url, base + "/moderators?query=%D0%98%D0%B2%D0%B0%D0%BD")
        c.find_moderator(3, "123")
        self.assertEqual(rec.last.url, base + "/moderator?query=123")
        cases = [
            (c.get_moderator_connections, "GET", "/connections"),
            (c.refresh_moderator_connections, "POST", "/connections/refresh"),
            (c.get_moderator_posts, "GET", "/posts"),
            (c.refresh_moderator_posts, "POST", "/posts/refresh"),
        ]
        for method, verb, suffix in cases:
            with self.subTest(suffix=suffix):
                method(3, "123")
                self.assertEqual(rec.last.method, verb)
                self.assertEqual(rec.last.url, base + "/moderators/123" + suffix)
                self.assertNotIn("X-Access-Token", rec.last.headers)

    def test_user_id_is_path_escaped(self) -> None:
        rec = Recorder(body={"discord_id": "x"})
        client(rec).get_moderator_connections(3, "../../webhook?x=1")
        self.assertEqual(
            rec.last.url,
            "https://gw.example/sso/servers/3/moderators/..%2F..%2Fwebhook%3Fx%3D1/connections",
        )

    def test_notify_splits_idempotency_key(self) -> None:
        rec = Recorder(body={"delivered": True})
        client(rec).notify_moderator(
            3,
            "123",
            {
                "kind": "reminder",
                "title": "Т",
                "body": "Б",
                "buttons": [{"label": "Ок", "payload": "p"}],
                "idempotency_key": "k-1",
            },
        )
        self.assertEqual(rec.last.headers["Idempotency-Key"], "k-1")
        self.assertEqual(
            rec.last_json(),
            {
                "kind": "reminder",
                "title": "Т",
                "body": "Б",
                "buttons": [{"label": "Ок", "payload": "p"}],
            },
        )

    def test_notify_without_key(self) -> None:
        rec = Recorder(body={"delivered": 1, "failed": 0, "total": 1})
        result = client(rec).notify_server(3, {"kind": "k", "title": "t", "body": "b"})
        self.assertEqual(result["total"], 1)
        self.assertEqual(rec.last.url, "https://gw.example/sso/servers/3/notify")
        self.assertNotIn("Idempotency-Key", rec.last.headers)

    def test_webhook_routes(self) -> None:
        rec = Recorder(body={"url": "https://h", "secret": "s"})
        self.assertEqual(client(rec).set_webhook("https://h")["secret"], "s")
        self.assertEqual((rec.last.method, rec.last_json()), ("PUT", {"url": "https://h"}))
        rec.response = HTTPResponse(204, "No Content", {}, b"")
        client(rec).delete_webhook()
        self.assertEqual(rec.last.method, "DELETE")


class ErrorTest(unittest.TestCase):
    def test_rate_limited(self) -> None:
        rec = Recorder(
            429,
            {"error": "rate limit exceeded"},
            {"retry-after": "7", "X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "0"},
        )
        with self.assertRaises(APIError) as ctx:
            client(rec).get_posts("t")
        err = ctx.exception
        self.assertTrue(err.is_rate_limited)
        self.assertEqual(err.message, "rate limit exceeded")
        self.assertEqual(
            (err.retry_after_seconds, err.rate_limit_limit, err.rate_limit_remaining), (7, 60, 0)
        )

    def test_non_json_error_uses_reason(self) -> None:
        rec = Recorder()
        rec.response = HTTPResponse(502, "Bad Gateway", {}, b"<html>")
        with self.assertRaises(APIError) as ctx:
            client(rec).get_posts("t")
        self.assertEqual((ctx.exception.status, ctx.exception.message), (502, "Bad Gateway"))
        self.assertEqual(ctx.exception.body, "<html>")
        self.assertIsNone(ctx.exception.retry_after_seconds)

    def test_bad_json_success(self) -> None:
        rec = Recorder()
        rec.response = HTTPResponse(200, "OK", {}, b"not json")
        with self.assertRaises(BlacktoolsError):
            client(rec).get_posts("t")


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._answer()

    def do_POST(self) -> None:
        self._answer()

    def _answer(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        if self.path.startswith("/sso/perms/check"):
            granted = json.loads(body)["permission"] == "ok" if body else False
            payload, status = {"granted": granted}, 200
        else:
            payload, status = {"error": "nope"}, 401
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_: Any) -> None:
        pass


@contextmanager
def local_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


class UrllibTransportTest(unittest.TestCase):
    def test_get_body_reaches_server(self) -> None:
        with local_server() as url:
            c = Client("t", gateway_url=url)
            self.assertTrue(c.check_permission(1, "ok"))
            self.assertFalse(c.check_permission(1, "no"))

    def test_http_error_becomes_api_error(self) -> None:
        with local_server() as url, self.assertRaises(APIError) as ctx:
            Client("t", gateway_url=url).get_posts("x")
        self.assertEqual((ctx.exception.status, ctx.exception.message), (401, "nope"))

    def test_connection_refused(self) -> None:
        with local_server() as url:
            pass
        with self.assertRaises(TransportError):
            Client("t", gateway_url=url, timeout=2).get_posts("x")

    def test_async_client(self) -> None:
        async def run() -> bool:
            with local_server() as url:
                return await AsyncClient("t", gateway_url=url).check_permission(1, "ok")

        self.assertTrue(asyncio.run(run()))


class AsyncTransportTest(unittest.TestCase):
    def test_custom_async_transport(self) -> None:
        rec = Recorder(body={"granted": False})

        async def transport(request: HTTPRequest) -> HTTPResponse:
            return rec(request)

        async def run() -> bool:
            return await AsyncClient(
                "t", gateway_url="https://gw", transport=transport
            ).check_permission(2, "x")

        self.assertFalse(asyncio.run(run()))
        self.assertEqual(rec.last_json(), {"user_id": 2, "permission": "x"})


if __name__ == "__main__":
    unittest.main()
