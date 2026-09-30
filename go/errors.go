package sdk

import (
	"fmt"
)

// APIError wraps any non-2xx response from the ExternalServices API.
// Message is the server's "error" field verbatim, or the HTTP status text
// when the body wasn't JSON. Rate-limit fields are nil unless the response
// carried the corresponding header (always the case on a 429).
type APIError struct {
	Status             int
	Body               string
	Message            string
	RetryAfterSeconds  *int
	RateLimitLimit     *int
	RateLimitRemaining *int
}

func (e *APIError) Error() string {
	return fmt.Sprintf("sdk: %s (status %d)", e.Message, e.Status)
}

// IsRateLimited reports whether the server responded 429 Too Many Requests.
func (e *APIError) IsRateLimited() bool {
	return e.Status == 429
}
