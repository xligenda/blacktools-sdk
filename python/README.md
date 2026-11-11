# External Services API Client (Python)

Python client for the "ExternalServices" API: a small set of REST routes reachable
by a service bearer token (`svc_<id>.<version>.<secret>`), plus a
token-exchange/refresh pair of routes for `type=user` services. Same methods,
routes and JSON shapes as the sibling Go and TypeScript clients.

Standard library only (`urllib`, `hmac`, `json`), Python 3.10+, fully typed
(`py.typed`, checked with `mypy --strict`).

## Install

```sh
pip install "blacktools-sdk @ git+https://github.com/xligenda/blacktools-sdk#subdirectory=python"
```

## Usage

```python
from blacktools_sdk import Client

client = Client(os.environ["SERVICE_TOKEN"])
```

`gateway_url` and `auth_url` default to the production deployment
(`DEFAULT_GATEWAY_URL` = `https://blacktools.odsmod.su/api`,
`DEFAULT_AUTH_URL` = `https://blacktools.odsmod.su/auth`); pass them only to
point the client somewhere else. `timeout` (seconds per request, default 30)
is the other keyword option.

`AsyncClient` has the same methods as coroutines (for aiogram, FastAPI and
the like). Its default transport runs urllib in a worker thread; pass
`transport=` to plug in your own HTTP stack (see "Transports" below).

```python
from blacktools_sdk import AsyncClient

client = AsyncClient(token)
moderators = await client.list_moderators(server_index)
```

As in Go, every method is always present: calling one that doesn't match
your service's `type` fails with an `APIError` (403). Each method's docstring
names the type it is for.

Responses are plain `dict`s/`list`s typed as `TypedDict`s with the exact JSON
field names (`profile["nickname"]`, `moderator.get("active_warnings")`).
Optional fields are absent rather than `None`, so read them with `.get()`.

### `type=user` service: exchange a sign-in code, then act on that user

```python
tokens = client.exchange_code(code)
posts = client.get_posts(tokens["access_token"])
warns = client.get_warns(tokens["access_token"])  # active ones only

# later, once the access token expires (tokens["expires_at"], Unix seconds):
tokens = client.refresh_token(tokens["refresh_token"])
```

### `type=server` service: act within the service's bound server

```python
moderators = client.list_moderators(server_index)  # or (server_index, "nick")
moderator = client.find_moderator(server_index, "123456789")  # first match, 404 if none

client.notify_moderator(
    server_index,
    moderator["user_id"],
    {
        "kind": "reminder",  # the backend namespaces this as "external.reminder"
        "title": "Напоминание",
        "body": "Не забудьте сдать отчёт.",
        "idempotency_key": "report-reminder:2026-11-11:123456789",  # optional
    },
)
```

`idempotency_key` is sent as the `Idempotency-Key` header, not in the body, so
retrying the same request never delivers twice.

### Notification buttons and the webhook

A notification carries up to 3 buttons. A `url` button opens a link; a
`payload` button sends the payload back to your webhook when the recipient
presses it (in the Mini App, Telegram or Discord); a button with neither only
records the press. Each notification can be acted on once.

```python
# Once: register the webhook and keep the returned secret.
hook = client.set_webhook("https://bot.example.com/blacktools/webhook")
store_secret(hook["secret"])  # returned only here; every call issues a new one

client.notify_moderator(
    server_index,
    user_id,
    {
        "kind": "leave_request",
        "title": "Заявка на отпуск",
        "body": "Иван просит отпуск с 1 по 7 октября.",
        "buttons": [
            {"label": "Одобрить", "style": "ok", "payload": "leave:42:approve"},
            {"label": "Отклонить", "style": "no", "payload": "leave:42:reject"},
            {"label": "Подробнее", "style": "link", "url": "https://bot.example.com/leave/42"},
        ],
    },
)
```

Receiving a press (FastAPI shown, any framework works: pass the headers and
the **exact raw body bytes**, never re-serialized JSON):

```python
from blacktools_sdk import InvalidWebhookSignatureError, parse_webhook_event


@app.post("/blacktools/webhook")
async def webhook(request: Request):
    try:
        event = parse_webhook_event(secret, request.headers, await request.body())
    except InvalidWebhookSignatureError:
        raise HTTPException(401)
    # event["action"]["payload"] == "leave:42:approve", event["user"].get("discord_id"), ...
    # Answer 2xx to accept the press (anything else lets the user retry),
    # optionally with a message and the label shown in place of the buttons.
    return {"acted_label": "Одобрено"}
```

Requests are signed `X-Blacktools-Signature: sha256=<hex HMAC-SHA256 of
"<X-Blacktools-Timestamp>.<raw body>">`; `parse_webhook_event` (and the
lower-level `verify_webhook`) also reject timestamps more than 5 minutes off.
Deduplicate on `event["id"]` if your handler is not idempotent. Webhook
requests time out after 5 seconds, so answer quickly.

### Any service type

```python
granted = client.check_permission(user_id, "reports.view")

# type=server: by sso user id (only a moderator of the bound server)
profile = client.get_profile(user_id=user_id, expand=True, email=True, roles=True)
# type=user: by the end user's access token
profile = client.get_profile(access_token=tokens["access_token"])
```

## Error handling

| Exception | When |
| --- | --- |
| `APIError` | any non-2xx response. `message` is the server's `error` field, `status`, `body` |
| `TransportError` | connection failure, timeout, broken response |
| `BlacktoolsError` | base class of all of the above; also raised for a non-JSON 2xx body |
| `InvalidWebhookSignatureError` | webhook request not authentic or too old |

On a 429, `retry_after_seconds`, `rate_limit_limit` and `rate_limit_remaining`
are filled from the `Retry-After`/`X-RateLimit-*` headers:

```python
from blacktools_sdk import APIError

try:
    client.notify_server(server_index, {"kind": "x", "title": "t", "body": "b"})
except APIError as err:
    if err.is_rate_limited:
        time.sleep(err.retry_after_seconds or 1)
```

The client does not retry automatically, so callers decide their own backoff
policy.

## Transports

A transport is a callable taking an `HTTPRequest` (`method`, `url`, `headers`,
`body: bytes | None`, `timeout`) and returning an `HTTPResponse` (`status`,
`reason`, `headers`, `body: bytes`), or an awaitable of one for `AsyncClient`.
It must return non-2xx responses rather than raise. Note that
`check_permission` and `get_profile(user_id=...)` send a JSON body on `GET`,
which the transport has to pass through. An `httpx` example:

```python
import httpx
from blacktools_sdk import AsyncClient, HTTPRequest, HTTPResponse, TransportError

http = httpx.AsyncClient()


async def httpx_transport(req: HTTPRequest) -> HTTPResponse:
    try:
        resp = await http.request(
            req.method, req.url, headers=req.headers, content=req.body, timeout=req.timeout
        )
    except httpx.HTTPError as err:
        raise TransportError(str(err)) from err
    return HTTPResponse(resp.status_code, resp.reason_phrase, resp.headers, resp.content)


client = AsyncClient(token, transport=httpx_transport)
```

## Development

```sh
cd python
PYTHONPATH=src python -m unittest discover -s tests
ruff check . && ruff format --check .
mypy src tests
```
