# External Services API Client

TypeScript client for the "ExternalServices" API: a small set of REST
routes reachable by a service bearer token (`svc_<id>.<version>.<secret>`),
plus a token-exchange/refresh pair of routes for `type=user` services.

Node.js only (built on `node:http`/`node:https`, not `fetch`) — a couple of
this API's `GET` routes read a JSON request body, and the Fetch spec
forbids a body on `GET`/`HEAD` requests in both browsers and Node's own
`fetch`. Since a service token is a secret that should never reach a
browser anyway, this isn't a real limitation in practice.

## Install / build

From this repository's `ts/` directory:

```sh
npm install
npm run build
```

Compiles `src/` to `dist/` (ESM, with `.d.ts` declarations). With pnpm the
package can be installed straight from git:

```sh
pnpm add 'github:xligenda/blacktools-sdk#main&path:/ts'
```

## Usage

```ts
import { ExternalServiceClient, ExternalServiceApiError } from 'blacktools-sdk';

const opts = {
  serviceToken: process.env.SERVICE_TOKEN!,
};
```

`gatewayUrl` and `authUrl` default to the production deployment
(`DEFAULT_GATEWAY_URL` = `https://blacktools.odsmod.su/api`,
`DEFAULT_AUTH_URL` = `https://blacktools.odsmod.su/auth`); pass them only to
point the client somewhere else.

`ExternalServiceClient` is generic over the service token's actual `type`
(`'user'` or `'server'`) — pass it explicitly as a type argument to unlock
the matching subset of methods at **compile time**. This is a
TypeScript-only guard: the backend already rejects a mismatched call at
runtime regardless, so this just catches the mistake before the request
ever goes out. Omitting the type argument (`new ExternalServiceClient(opts)`)
only exposes the two type-agnostic methods, `checkPermission`/`getProfile`.

### `type=user` service: exchange a link code, then act on that user

```ts
const client = new ExternalServiceClient<'user'>(opts);

const tokens = await client.exchangeCode(code);
const posts = await client.getPosts(tokens.access_token);
const warns = await client.getWarns(tokens.access_token);

// later, once access_token expires:
const refreshed = await client.refreshToken(tokens.refresh_token);

client.listModerators(1); // compile error: not a member of ExternalServiceClient<'user'>
```

### `type=server` service: act within the service's bound server

```ts
const client = new ExternalServiceClient<'server'>(opts);

const moderators = await client.listModerators(serverIndex);

await client.notifyModerator(serverIndex, moderators[0].user_id, {
  kind: 'reminder', // the backend namespaces this itself before delivery
  title: 'Напоминание',
  body: 'Не забудьте сдать отчёт.',
});

client.getPosts(accessToken); // compile error: not a member of ExternalServiceClient<'server'>
```

### Notification buttons and the webhook

A notification carries up to 3 buttons. A `url` button opens a link; a
`payload` button sends the payload back to your webhook when the recipient
presses it (in the Mini App, Telegram or Discord); a button with neither only
records the press. Each notification can be acted on once.

```ts
// once: register the webhook and keep the returned secret
const { secret } = await client.setWebhook('https://bot.example.com/blacktools/webhook');

await client.notifyModerator(serverIndex, userID, {
  kind: 'leave_request',
  title: 'Заявка на отпуск',
  body: 'Иван просит отпуск с 1 по 7 октября.',
  buttons: [
    { label: 'Одобрить', style: 'ok', payload: 'leave:42:approve' },
    { label: 'Отклонить', style: 'no', payload: 'leave:42:reject' },
    { label: 'Подробнее', style: 'link', url: 'https://bot.example.com/leave/42' },
  ],
});
```

Receiving a press (the raw body is needed to check the signature):

```ts
import { createServer } from 'node:http';
import { parseWebhookEvent, type WebhookResponse } from 'blacktools-sdk';

createServer((req, res) => {
  const chunks: Buffer[] = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    try {
      const event = parseWebhookEvent(secret, req.headers, Buffer.concat(chunks));
      // event.action.payload === 'leave:42:approve', event.user.discord_id, ...
      const reply: WebhookResponse = { acted_label: 'Одобрено' };
      res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(reply));
    } catch {
      res.writeHead(401).end();
    }
  });
}).listen(8080);
```

Answer 2xx to accept the press (anything else lets the user retry). Requests
are signed `x-blacktools-signature: sha256=<hex HMAC-SHA256 of
"<x-blacktools-timestamp>.<raw body>">`; `parseWebhookEvent` also rejects
timestamps more than 5 minutes off. Deduplicate on `event.id` if your handler
is not idempotent. Webhook requests time out after 5 seconds.

### Any service type

```ts
const client = new ExternalServiceClient(opts); // no type argument needed

const granted = await client.checkPermission(userId, 'reports.view');
const profile = await client.getProfile({ userId, expand: true, email: true });
```

## Error handling

Every non-2xx response throws `ExternalServiceApiError` (`message` is the
server's `error` field verbatim). On a 429, `retryAfterSeconds`,
`rateLimitLimit`, and `rateLimitRemaining` are populated from the
`Retry-After`/`X-RateLimit-Limit`/`X-RateLimit-Remaining` response headers:

```ts
try {
  await client.notifyServer(serverIndex, { kind: 'x', title: 't', body: 'b' });
} catch (err) {
  if (err instanceof ExternalServiceApiError && err.isRateLimited) {
    console.log(`retry after ${err.retryAfterSeconds}s`);
  }
  throw err;
}
```

The client does not retry automatically — callers decide their own backoff
policy.
