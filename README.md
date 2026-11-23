# blacktools-sdk

Clients for the blacktools **ExternalServices** API: the REST surface a
third-party integration reaches with a service bearer token
(`svc_<id>.<version>.<secret>`).

| Language   | Directory     | Install                                                   |
|------------|---------------|-----------------------------------------------------------|
| Go         | [`go/`](go/)  | `go get github.com/xligenda/blacktools-sdk/go`            |
| TypeScript | [`ts/`](ts/)  | `pnpm add 'github:xligenda/blacktools-sdk#main&path:/ts'` |
| Python     | [`python/`](python/) | `pip install "blacktools-sdk @ git+https://github.com/xligenda/blacktools-sdk#subdirectory=python"` |

All three clients expose the same methods, routes and JSON shapes, and default to
the production deployment:

- API: `https://blacktools.odsmod.su/api`
- Auth (token exchange/refresh): `https://blacktools.odsmod.su/auth`

## Service types

- **`user`**: redeems a one-time link code (`ExchangeCode`) for an
  access/refresh token pair acting as a specific end user, then calls the
  user-scoped routes (`GetPosts`, `GetPostHistory`, `GetWarns`, `RefreshPosts`,
  `RefreshConnections`) with that user's access token.
- **`server`**: bound to a single server; lists and manages its moderators
  (`ListModerators`, `FindModerator`, `GetModeratorConnections`, `RefreshModeratorConnections`,
  `GetModeratorPosts`, `RefreshModeratorPosts`), reads the post history a user
  has on it (`GetUserPostHistory`) and sends notifications (`NotifyServer`,
  `NotifyModerator`) with up to 3 buttons. Payload buttons are delivered to
  the service's webhook (`SetWebhook`/`DeleteWebhook`) as signed events.

Post history comes in two kinds, each behind its own scope: Discord moderator
posts (`moderator`, scope `public.posts.history.moderator`) and every other post
(`other`, scope `public.posts.history.other`). A `user` service sees the history
of the signed-in user across every server, global posts included in `other`. A
`server` service sees only its own server's posts, and only for a user who holds
an active post of that kind there (404 otherwise).

`CheckPermission` and `GetProfile` work for both types. See each directory's
README for usage, webhook verification and error handling.
