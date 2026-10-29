package sdk

// TokenPair is a fresh user access/refresh token pair.
type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	UserID       int64  `json:"user_id"`
	// ExpiresAt is Unix seconds.
	ExpiresAt int64 `json:"expires_at"`
}

// PermsCheckResult is the result of a permission check.
type PermsCheckResult struct {
	Granted bool `json:"granted"`
}

// Profile is a user's profile as returned by /sso/profile.
type Profile struct {
	UserID    int64   `json:"user_id"`
	DiscordID *string `json:"discord_id,omitempty"`
	Nickname  string  `json:"nickname"`
	VKID      *int64  `json:"vk_id,omitempty"`
	TgID      *int64  `json:"tg_id,omitempty"`
	ForumID   *int64  `json:"forum_id,omitempty"`
	GoogleID  *string `json:"google_id,omitempty"`
	// CreatedAt is RFC3339.
	CreatedAt    string   `json:"created_at"`
	Roles        []string `json:"roles,omitempty"`
	VKName       *string  `json:"vk_name,omitempty"`
	TelegramName *string  `json:"telegram_name,omitempty"`
	ForumName    *string  `json:"forum_name,omitempty"`
	ForumViewURL *string  `json:"forum_view_url,omitempty"`
	Email        *string  `json:"email,omitempty"`
}

// GetProfileOptions configures GetProfile.
type GetProfileOptions struct {
	// UserID looks up a specific user instead of the caller identified by AccessToken.
	UserID *int64
	// AccessToken is the end user's own access token, for a self-lookup.
	AccessToken string
	// Expand includes vk/telegram/forum display names and forum profile URL.
	Expand bool
	// Email includes the linked Google account's email.
	Email bool
	// Roles includes the user's role names.
	Roles bool
}

// PostSnapshot is a single BlackRussia-post snapshot.
type PostSnapshot struct {
	ServerCode      string `json:"server_code"`
	ServerName      string `json:"server_name"`
	PermissionGroup string `json:"permission_group"`
	AccessLevel     int    `json:"access_level"`
	IsTemp          bool   `json:"is_temp"`
	Ticket          string `json:"ticket"`
}

// WarnKind distinguishes a warning from a reprimand.
type WarnKind string

const (
	WarnKindWarning   WarnKind = "warning"
	WarnKindReprimand WarnKind = "reprimand"
)

// Warn is a single issued warning or reprimand.
type Warn struct {
	ID     int64    `json:"id"`
	Reason string   `json:"reason"`
	Value  int      `json:"value"`
	Kind   WarnKind `json:"kind"`
	// IssuedAt is RFC3339.
	IssuedAt string `json:"issued_at"`
	IssuedBy string `json:"issued_by"`
	// RevokedAt is RFC3339.
	RevokedAt *string `json:"revoked_at,omitempty"`
	RevokedBy *string `json:"revoked_by,omitempty"`
}

// ExpandedConnections holds resolved display names for a user's linked accounts.
type ExpandedConnections struct {
	VKName       *string `json:"vk_name,omitempty"`
	TelegramName *string `json:"telegram_name,omitempty"`
	DiscordName  *string `json:"discord_name,omitempty"`
	ForumName    *string `json:"forum_name,omitempty"`
	ForumViewURL *string `json:"forum_view_url,omitempty"`
}

// StaffRoleAssignment is a single sso role assignment held by a moderator.
type StaffRoleAssignment struct {
	AssignmentID int64  `json:"assignment_id"`
	Kind         string `json:"kind"`
	RoleName     string `json:"role_name"`
	GrantedBy    string `json:"granted_by"`
	// CreatedAt is RFC3339.
	CreatedAt string `json:"created_at"`
}

// Moderator is a staff member on a server-type service's bound server.
type Moderator struct {
	UserID           string                `json:"user_id"`
	SSOUserID        int64                 `json:"sso_user_id"`
	Nickname         string                `json:"nickname"`
	TgID             *int64                `json:"tg_id,omitempty"`
	PermissionGroup  string                `json:"permission_group"`
	AccessLevel      int                   `json:"access_level"`
	IsTemp           bool                  `json:"is_temp"`
	ActiveWarnings   int                   `json:"active_warnings"`
	ActiveReprimands int                   `json:"active_reprimands"`
	Roles            []StaffRoleAssignment `json:"roles"`
}

// Connections holds a moderator's linked accounts.
type Connections struct {
	DiscordID    string  `json:"discord_id"`
	DiscordName  *string `json:"discord_name,omitempty"`
	VKID         *int64  `json:"vk_id,omitempty"`
	VKName       *string `json:"vk_name,omitempty"`
	TgID         *int64  `json:"tg_id,omitempty"`
	TelegramName *string `json:"telegram_name,omitempty"`
	ForumID      *int64  `json:"forum_id,omitempty"`
	ForumName    *string `json:"forum_name,omitempty"`
	ForumViewURL *string `json:"forum_view_url,omitempty"`
	GoogleID     *string `json:"google_id,omitempty"`
}

// ButtonStyle is how a notification Button is rendered.
type ButtonStyle string

const (
	ButtonStyleOK   ButtonStyle = "ok"
	ButtonStyleNo   ButtonStyle = "no"
	ButtonStyleGrey ButtonStyle = "grey"
	ButtonStyleWarm ButtonStyle = "warm"
	ButtonStyleLink ButtonStyle = "link"
)

// Button is one action button on a notification, shown in the Mini App and
// in Telegram and Discord DMs. Set at most one of URL and Payload: a URL
// button opens the link, a Payload button POSTs a WebhookEvent carrying
// Payload to the service's webhook (see SetWebhook), and a button with
// neither only records the click.
type Button struct {
	// Label is 1-40 characters.
	Label string `json:"label"`
	// Style defaults to ButtonStyleGrey.
	Style ButtonStyle `json:"style,omitempty"`
	// URL is an absolute https URL of at most 512 characters.
	URL string `json:"url,omitempty"`
	// Payload is at most 1024 bytes, and requires a webhook to be set.
	Payload string `json:"payload,omitempty"`
}

// NotifyRequest is a notification to deliver via NotifyServer/NotifyModerator.
type NotifyRequest struct {
	Kind  string `json:"kind"`
	Title string `json:"title"`
	Body  string `json:"body"`
	// Buttons holds at most 3 action buttons. Only one button per
	// notification can be run by its recipient.
	Buttons []Button `json:"buttons,omitempty"`
	// IdempotencyKey, when set, is sent as the Idempotency-Key header so a
	// retried request does not deliver the notification twice. It must be
	// 1-128 characters from [A-Za-z0-9._:-].
	IdempotencyKey string `json:"-"`
}

// NotifyServerResult is the outcome of NotifyServer.
type NotifyServerResult struct {
	// Delivered is the count of recipients notified.
	Delivered int `json:"delivered"`
	// Failed is the count of recipients whose delivery failed.
	Failed int `json:"failed"`
	// Total is the count of recipients a delivery was attempted for.
	Total int `json:"total"`
}

// NotifyModeratorResult is the outcome of NotifyModerator.
type NotifyModeratorResult struct {
	Delivered bool `json:"delivered"`
}

// WebhookConfig is the result of SetWebhook. Secret is only returned here:
// store it to verify incoming webhook requests with VerifyWebhook.
type WebhookConfig struct {
	URL    string `json:"url"`
	Secret string `json:"secret"`
}
