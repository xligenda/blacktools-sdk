# blacktools-sdk

Clients for the blacktools **ExternalServices** API: the REST surface a
third-party integration reaches with a service bearer token
(`svc_<id>.<version>.<secret>`).

| Language   | Directory     | Install                                                   |
|------------|---------------|-----------------------------------------------------------|
| Go         | [`go/`](go/)  | `go get github.com/xligenda/blacktools-sdk/go`            |
| TypeScript | [`ts/`](ts/)  | `pnpm add 'github:xligenda/blacktools-sdk#main&path:/ts'` |

Both clients expose the same methods, routes and JSON shapes, and default to
the production deployment:

- API: `https://blacktools.odsmod.su/api`
- Auth (token exchange/refresh): `https://blacktools.odsmod.su/auth`

## Service types

- **`user`**: redeems a one-time link code (`ExchangeCode`) for an
  access/refresh token pair acting as a specific end user, then calls the
  user-scoped routes (`GetPosts`, `GetWarns`, `RefreshPosts`,
  `RefreshConnections`) with that user's access token.
- **`server`**: bound to a single server; lists and manages its moderators
  (`ListModerators`, `GetModeratorConnections`, `RefreshModeratorConnections`,
  `RefreshModeratorPosts`) and sends notifications (`NotifyServer`,
  `NotifyModerator`) with up to 3 buttons. Payload buttons are delivered to
  the service's webhook (`SetWebhook`/`DeleteWebhook`) as signed events.

`CheckPermission` and `GetProfile` work for both types. See each directory's
README for usage, webhook verification and error handling.
