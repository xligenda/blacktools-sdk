// Package sdk is a client for the "ExternalServices" API: the machine-to-machine
// REST surface exposed by auth (token exchange/refresh) and gateway (everything
// else), reachable with a service bearer token of the form
// "svc_<id>.<version>.<secret>".
package sdk

import (
	"context"
	"net/http"
	"strconv"
	"strings"
)

// Default base URLs of the production blacktools deployment.
const (
	DefaultGatewayURL = "https://blacktools.odsmod.su/api"
	DefaultAuthURL    = "https://blacktools.odsmod.su/auth"
)

// ClientOptions configures a Client.
type ClientOptions struct {
	// GatewayURL is the base URL of the gateway service; defaults to DefaultGatewayURL.
	GatewayURL string
	// AuthURL is the base URL of the auth service; defaults to DefaultAuthURL.
	AuthURL string
	// ServiceToken is this service's own bearer token.
	ServiceToken string
	// HTTPClient overrides the default HTTP client; defaults to http.DefaultClient.
	HTTPClient *http.Client
}

// Client calls the ExternalServices API as either a "user"-type or
// "server"-type service. CheckPermission and GetProfile apply to both types.
// ExchangeCode, RefreshToken, GetPosts, GetWarns, RefreshPosts, and
// RefreshConnections apply only to a "user"-type service. ListModerators,
// GetModeratorConnections, RefreshModeratorConnections, RefreshModeratorPosts,
// NotifyServer, and NotifyModerator apply only to a "server"-type service.
// The backend rejects a call from a mismatched service type at runtime.
type Client struct {
	gatewayURL   string
	authURL      string
	serviceToken string
	httpClient   *http.Client
}

// NewClient builds a Client from opts.
func NewClient(opts ClientOptions) *Client {
	httpClient := opts.HTTPClient
	if httpClient == nil {
		httpClient = http.DefaultClient
	}
	return &Client{
		gatewayURL:   strings.TrimRight(orDefault(opts.GatewayURL, DefaultGatewayURL), "/"),
		authURL:      strings.TrimRight(orDefault(opts.AuthURL, DefaultAuthURL), "/"),
		serviceToken: opts.ServiceToken,
		httpClient:   httpClient,
	}
}

// ExchangeCode redeems a one-time link code for a fresh user access/refresh token pair.
func (c *Client) ExchangeCode(ctx context.Context, code string) (TokenPair, error) {
	data, err := c.doRequest(ctx, c.authURL, http.MethodPost, "/sso/exchange", requestOptions{
		body: map[string]string{"code": code},
	})
	if err != nil {
		return TokenPair{}, err
	}
	return decodeJSON[TokenPair](data)
}

// RefreshToken rotates a refresh token for a fresh access/refresh token pair.
func (c *Client) RefreshToken(ctx context.Context, refreshToken string) (TokenPair, error) {
	data, err := c.doRequest(ctx, c.authURL, http.MethodPost, "/sso/refresh", requestOptions{
		body: map[string]string{"refresh_token": refreshToken},
	})
	if err != nil {
		return TokenPair{}, err
	}
	return decodeJSON[TokenPair](data)
}

// CheckPermission checks whether userID holds permission.
func (c *Client) CheckPermission(
	ctx context.Context, userID int64, permission string,
) (bool, error) {
	data, err := c.doRequest(ctx, c.gatewayURL, http.MethodGet, "/sso/perms/check", requestOptions{
		body: map[string]any{"user_id": userID, "permission": permission},
	})
	if err != nil {
		return false, err
	}
	result, err := decodeJSON[PermsCheckResult](data)
	if err != nil {
		return false, err
	}
	return result.Granted, nil
}

// GetProfile looks up a user's profile, by opts.UserID, by opts.AccessToken, or
// (server-type) neither.
func (c *Client) GetProfile(ctx context.Context, opts GetProfileOptions) (Profile, error) {
	const trueValue = "true"
	query := map[string]string{}
	if opts.Expand {
		query["expand"] = trueValue
	}
	if opts.Email {
		query["email"] = trueValue
	}
	if opts.Roles {
		query["roles"] = trueValue
	}

	var body any
	if opts.UserID != nil {
		body = map[string]int64{"user_id": *opts.UserID}
	}

	data, err := c.doRequest(ctx, c.gatewayURL, http.MethodGet, "/sso/profile", requestOptions{
		query:       query,
		body:        body,
		accessToken: opts.AccessToken,
	})
	if err != nil {
		return Profile{}, err
	}
	return decodeJSON[Profile](data)
}

// GetPosts returns the caller's current role/post snapshots.
func (c *Client) GetPosts(ctx context.Context, accessToken string) ([]PostSnapshot, error) {
	data, err := c.doRequest(ctx, c.gatewayURL, http.MethodGet, "/sso/posts", requestOptions{
		accessToken: accessToken,
	})
	if err != nil {
		return nil, err
	}
	return decodeJSON[[]PostSnapshot](data)
}

// GetWarns returns the caller's active and revoked warns/reprimands.
func (c *Client) GetWarns(ctx context.Context, accessToken string) ([]Warn, error) {
	data, err := c.doRequest(ctx, c.gatewayURL, http.MethodGet, "/sso/warns", requestOptions{
		accessToken: accessToken,
	})
	if err != nil {
		return nil, err
	}
	return decodeJSON[[]Warn](data)
}

// RefreshPosts forces a fresh role/post sync for the caller, returning the result.
func (c *Client) RefreshPosts(ctx context.Context, accessToken string) ([]PostSnapshot, error) {
	data, err := c.doRequest(
		ctx,
		c.gatewayURL,
		http.MethodPost,
		"/sso/posts/refresh",
		requestOptions{
			accessToken: accessToken,
		},
	)
	if err != nil {
		return nil, err
	}
	return decodeJSON[[]PostSnapshot](data)
}

// RefreshConnections forces a fresh service-connection display-name resolution
// for the caller.
func (c *Client) RefreshConnections(
	ctx context.Context,
	accessToken string,
) (ExpandedConnections, error) {
	data, err := c.doRequest(
		ctx,
		c.gatewayURL,
		http.MethodPost,
		"/sso/connections/refresh",
		requestOptions{
			accessToken: accessToken,
		},
	)
	if err != nil {
		return ExpandedConnections{}, err
	}
	return decodeJSON[ExpandedConnections](data)
}

// ListModerators lists moderators on serverIndex, optionally filtered by
// Discord id or nickname substring via query.
func (c *Client) ListModerators(
	ctx context.Context,
	serverIndex int,
	query string,
) ([]Moderator, error) {
	opts := requestOptions{}
	if query != "" {
		opts.query = map[string]string{"query": query}
	}
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodGet,
		"/sso/servers/"+strconv.Itoa(serverIndex)+"/moderators", opts,
	)
	if err != nil {
		return nil, err
	}
	return decodeJSON[[]Moderator](data)
}

// GetModeratorConnections returns a moderator's current linked connections on serverIndex.
func (c *Client) GetModeratorConnections(
	ctx context.Context,
	serverIndex int,
	userID string,
) (Connections, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodGet,
		moderatorPath(serverIndex, userID, "/connections"), requestOptions{},
	)
	if err != nil {
		return Connections{}, err
	}
	return decodeJSON[Connections](data)
}

// RefreshModeratorConnections forces a fresh connection resolution for a
// moderator on serverIndex.
func (c *Client) RefreshModeratorConnections(
	ctx context.Context, serverIndex int, userID string,
) (Connections, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodPost,
		moderatorPath(serverIndex, userID, "/connections/refresh"), requestOptions{},
	)
	if err != nil {
		return Connections{}, err
	}
	return decodeJSON[Connections](data)
}

// RefreshModeratorPosts forces a fresh role/post sync for a moderator on serverIndex.
func (c *Client) RefreshModeratorPosts(
	ctx context.Context, serverIndex int, userID string,
) ([]PostSnapshot, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodPost,
		moderatorPath(serverIndex, userID, "/posts/refresh"), requestOptions{},
	)
	if err != nil {
		return nil, err
	}
	return decodeJSON[[]PostSnapshot](data)
}

// NotifyServer notifies every staff member designated to receive notifications
// for serverIndex.
func (c *Client) NotifyServer(
	ctx context.Context, serverIndex int, notification NotifyRequest,
) (NotifyServerResult, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodPost,
		"/sso/servers/"+strconv.Itoa(serverIndex)+"/notify",
		requestOptions{body: notification, idempotencyKey: notification.IdempotencyKey},
	)
	if err != nil {
		return NotifyServerResult{}, err
	}
	return decodeJSON[NotifyServerResult](data)
}

// NotifyModerator notifies a single moderator on serverIndex.
func (c *Client) NotifyModerator(
	ctx context.Context, serverIndex int, userID string, notification NotifyRequest,
) (NotifyModeratorResult, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodPost,
		moderatorPath(serverIndex, userID, "/notify"),
		requestOptions{body: notification, idempotencyKey: notification.IdempotencyKey},
	)
	if err != nil {
		return NotifyModeratorResult{}, err
	}
	return decodeJSON[NotifyModeratorResult](data)
}

// SetWebhook sets the https URL that receives a signed WebhookEvent whenever
// a recipient runs one of this service's Payload buttons. Every call issues a
// new signing secret, invalidating the previous one.
func (c *Client) SetWebhook(ctx context.Context, url string) (WebhookConfig, error) {
	data, err := c.doRequest(
		ctx, c.gatewayURL, http.MethodPut, "/sso/webhook",
		requestOptions{body: map[string]string{"url": url}},
	)
	if err != nil {
		return WebhookConfig{}, err
	}
	return decodeJSON[WebhookConfig](data)
}

// DeleteWebhook removes this service's webhook. Payload buttons already sent
// fail when run until a webhook is set again.
func (c *Client) DeleteWebhook(ctx context.Context) error {
	_, err := c.doRequest(ctx, c.gatewayURL, http.MethodDelete, "/sso/webhook", requestOptions{})
	return err
}

func moderatorPath(serverIndex int, userID, suffix string) string {
	return "/sso/servers/" + strconv.Itoa(serverIndex) + "/moderators/" + userID + suffix
}

// orDefault returns value, or fallback when value is empty.
func orDefault(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}
