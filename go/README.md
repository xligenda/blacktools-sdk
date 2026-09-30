# External Services API Client (Go)

Go client for the "ExternalServices" API: a small set of REST routes reachable
by a service bearer token (`svc_<id>.<version>.<secret>`), plus a
token-exchange/refresh pair of routes for `type=user` services.

Standard library only (`net/http`) — zero non-stdlib dependencies, mirroring
the sibling TypeScript client's zero-runtime-dependency design.

## Install

```sh
go get github.com/xligenda/blacktools-sdk/go
```

```go
import sdk "github.com/xligenda/blacktools-sdk/go"
```

## Usage

```go
client := sdk.NewClient(sdk.ClientOptions{
    ServiceToken: os.Getenv("SERVICE_TOKEN"),
})
```

`GatewayURL` and `AuthURL` default to the production deployment
(`sdk.DefaultGatewayURL` = `https://blacktools.odsmod.su/api`,
`sdk.DefaultAuthURL` = `https://blacktools.odsmod.su/auth`); set them only to
point the client somewhere else.

Unlike the TypeScript client, `Client` is not generic over the service
token's `type` (`user` or `server`) — Go has no equivalent of TypeScript's
compile-time `Pick<>` narrowing. Every method is always present; calling one
that doesn't match your service's actual `type` fails at runtime with an
`*sdk.APIError`, same as it would in TypeScript once past the type check. See
the doc comment on `Client` for which methods apply to which `type`.

### `type=user` service: exchange a link code, then act on that user

```go
tokens, err := client.ExchangeCode(ctx, code)
posts, err := client.GetPosts(ctx, tokens.AccessToken)
warns, err := client.GetWarns(ctx, tokens.AccessToken)

// later, once AccessToken expires:
refreshed, err := client.RefreshToken(ctx, tokens.RefreshToken)
```

### `type=server` service: act within the service's bound server

```go
moderators, err := client.ListModerators(ctx, serverIndex, "")

_, err = client.NotifyModerator(ctx, serverIndex, moderators[0].UserID, sdk.NotifyRequest{
    Kind:  "reminder", // the backend namespaces this itself before delivery
    Title: "Напоминание",
    Body:  "Не забудьте сдать отчёт.",
})
```

### Notification buttons and the webhook

A notification carries up to 3 buttons. A `URL` button opens a link; a
`Payload` button sends the payload back to your webhook when the recipient
presses it (in the Mini App, Telegram or Discord); a button with neither only
records the press. Each notification can be acted on once.

```go
// Once: register the webhook and keep the returned secret.
hook, err := client.SetWebhook(ctx, "https://bot.example.com/blacktools/webhook")
// store hook.Secret

_, err = client.NotifyModerator(ctx, serverIndex, userID, sdk.NotifyRequest{
    Kind:  "leave_request",
    Title: "Заявка на отпуск",
    Body:  "Иван просит отпуск с 1 по 7 октября.",
    Buttons: []sdk.Button{
        {Label: "Одобрить", Style: sdk.ButtonStyleOK, Payload: "leave:42:approve"},
        {Label: "Отклонить", Style: sdk.ButtonStyleNo, Payload: "leave:42:reject"},
        {Label: "Подробнее", Style: sdk.ButtonStyleLink, URL: "https://bot.example.com/leave/42"},
    },
})
```

Receiving a press:

```go
http.HandleFunc("/blacktools/webhook", func(w http.ResponseWriter, r *http.Request) {
    event, err := sdk.ParseWebhookRequest(r, secret)
    if err != nil {
        http.Error(w, "bad signature", http.StatusUnauthorized)
        return
    }
    // event.Action.Payload == "leave:42:approve", event.User.DiscordID, ...
    // Answer 2xx to accept the press (anything else lets the user retry),
    // optionally with a message and the label shown in place of the buttons.
    _ = json.NewEncoder(w).Encode(sdk.WebhookResponse{ActedLabel: "Одобрено"})
})
```

Requests are signed `X-Blacktools-Signature: sha256=<hex HMAC-SHA256 of
"<X-Blacktools-Timestamp>.<raw body>">`; `ParseWebhookRequest` also rejects
timestamps more than 5 minutes off. Deduplicate on `event.ID` if your handler
is not idempotent. Webhook requests time out after 5 seconds.

### Any service type

```go
granted, err := client.CheckPermission(ctx, userID, "reports.view")
profile, err := client.GetProfile(ctx, sdk.GetProfileOptions{
    UserID: &userID,
    Expand: true,
    Email:  true,
})
```

## Error handling

Every non-2xx response returns an `*sdk.APIError` (`Message` is the server's
`error` field verbatim). On a 429, `RetryAfterSeconds`, `RateLimitLimit`, and
`RateLimitRemaining` are populated from the
`Retry-After`/`X-RateLimit-Limit`/`X-RateLimit-Remaining` response headers:

```go
_, err := client.NotifyServer(ctx, serverIndex, sdk.NotifyRequest{Kind: "x", Title: "t", Body: "b"})
var apiErr *sdk.APIError
if errors.As(err, &apiErr) && apiErr.IsRateLimited() {
    log.Printf("retry after %ds", *apiErr.RetryAfterSeconds)
}
```

The client does not retry automatically — callers decide their own backoff
policy.
