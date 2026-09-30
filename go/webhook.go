package sdk

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"
)

// Headers sent with every webhook request.
const (
	WebhookSignatureHeader = "X-Blacktools-Signature"
	WebhookTimestampHeader = "X-Blacktools-Timestamp"
	WebhookDeliveryHeader  = "X-Blacktools-Delivery"
	WebhookEventHeader     = "X-Blacktools-Event"

	// WebhookEventAction is the type of the event sent when a recipient runs
	// a Payload button.
	WebhookEventAction = "notification.action"

	// DefaultWebhookTolerance is how far a webhook timestamp may drift from
	// now before VerifyWebhook rejects it.
	DefaultWebhookTolerance = 5 * time.Minute

	maxWebhookBody = 64 << 10
)

// ErrInvalidWebhookSignature is returned by VerifyWebhook and
// ParseWebhookRequest when a request is not authentic or is too old.
var ErrInvalidWebhookSignature = errors.New("sdk: invalid webhook signature")

// WebhookEvent is the JSON body of a webhook request.
type WebhookEvent struct {
	Type string `json:"type"`
	// ID is unique per delivery, and equals the X-Blacktools-Delivery header.
	ID             string `json:"id"`
	NotificationID int64  `json:"notification_id"`
	Kind           string `json:"kind"`
	// ServerIndex is the server the notification was sent for.
	ServerIndex *int `json:"server_index,omitempty"`
	Action      struct {
		Index   int    `json:"index"`
		Label   string `json:"label"`
		Payload string `json:"payload"`
	} `json:"action"`
	User struct {
		ID        int    `json:"id"`
		DiscordID string `json:"discord_id,omitempty"`
		TgID      int64  `json:"tg_id,omitempty"`
	} `json:"user"`
	// Channel is where the button was pressed: "app", "telegram" or "discord".
	Channel    string    `json:"channel"`
	OccurredAt time.Time `json:"occurred_at"`
}

// WebhookResponse is an optional JSON body a webhook may answer a 2xx with.
// Any non-2xx answer fails the button press and lets the recipient retry.
type WebhookResponse struct {
	// Message is shown to the recipient (at most 200 characters).
	Message string `json:"message,omitempty"`
	// ActedLabel replaces the button's label in the "already done" line
	// shown in place of the buttons, e.g. "Одобрено".
	ActedLabel string `json:"acted_label,omitempty"`
}

// VerifyWebhook reports whether signature is body's valid signature under
// secret for timestamp, and timestamp is within tolerance of now.
func VerifyWebhook(
	secret, timestamp, signature string,
	body []byte,
	tolerance time.Duration,
) error {
	sec, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil {
		return ErrInvalidWebhookSignature
	}
	if drift := time.Since(time.Unix(sec, 0)); drift > tolerance || drift < -tolerance {
		return ErrInvalidWebhookSignature
	}

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(timestamp))
	mac.Write([]byte("."))
	mac.Write(body)
	want := "sha256=" + hex.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(want), []byte(signature)) {
		return ErrInvalidWebhookSignature
	}
	return nil
}

// ParseWebhookRequest reads r's body, verifies its signature under secret
// with DefaultWebhookTolerance, and decodes the event.
func ParseWebhookRequest(r *http.Request, secret string) (WebhookEvent, error) {
	body, err := io.ReadAll(io.LimitReader(r.Body, maxWebhookBody))
	if err != nil {
		return WebhookEvent{}, fmt.Errorf("sdk: reading webhook body: %w", err)
	}
	if err := VerifyWebhook(
		secret,
		r.Header.Get(WebhookTimestampHeader),
		r.Header.Get(WebhookSignatureHeader),
		body,
		DefaultWebhookTolerance,
	); err != nil {
		return WebhookEvent{}, err
	}

	var event WebhookEvent
	if err := json.Unmarshal(body, &event); err != nil {
		return WebhookEvent{}, fmt.Errorf("sdk: decoding webhook event: %w", err)
	}
	return event, nil
}
