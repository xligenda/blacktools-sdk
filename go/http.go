package sdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
)

type requestOptions struct {
	query          map[string]string
	body           any
	accessToken    string
	idempotencyKey string
}

func (c *Client) doRequest(
	ctx context.Context,
	baseURL, method, path string,
	opts requestOptions,
) ([]byte, error) {
	req, err := c.buildRequest(ctx, baseURL, method, path, opts)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("sdk: request failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("sdk: reading response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, buildAPIError(resp, data)
	}
	return data, nil
}

func (c *Client) buildRequest(
	ctx context.Context,
	baseURL, method, path string,
	opts requestOptions,
) (*http.Request, error) {
	u, err := url.Parse(baseURL + path)
	if err != nil {
		return nil, fmt.Errorf("sdk: invalid URL: %w", err)
	}
	if len(opts.query) > 0 {
		q := u.Query()
		for k, v := range opts.query {
			q.Set(k, v)
		}
		u.RawQuery = q.Encode()
	}

	var bodyReader io.Reader
	if opts.body != nil {
		encoded, err := json.Marshal(opts.body)
		if err != nil {
			return nil, fmt.Errorf("sdk: encoding request body: %w", err)
		}
		bodyReader = bytes.NewReader(encoded)
	}

	req, err := http.NewRequestWithContext(ctx, method, u.String(), bodyReader)
	if err != nil {
		return nil, fmt.Errorf("sdk: building request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+c.serviceToken)
	if opts.accessToken != "" {
		req.Header.Set("X-Access-Token", opts.accessToken)
	}
	if opts.idempotencyKey != "" {
		req.Header.Set("Idempotency-Key", opts.idempotencyKey)
	}
	if opts.body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	return req, nil
}

func buildAPIError(resp *http.Response, body []byte) *APIError {
	message := resp.Status
	var parsed struct {
		Error string `json:"error"`
	}
	if json.Unmarshal(body, &parsed) == nil && parsed.Error != "" {
		message = parsed.Error
	}

	return &APIError{
		Status:             resp.StatusCode,
		Body:               string(body),
		Message:            message,
		RetryAfterSeconds:  parseIntHeader(resp.Header.Get("Retry-After")),
		RateLimitLimit:     parseIntHeader(resp.Header.Get("X-RateLimit-Limit")),
		RateLimitRemaining: parseIntHeader(resp.Header.Get("X-RateLimit-Remaining")),
	}
}

func parseIntHeader(value string) *int {
	if value == "" {
		return nil
	}
	n, err := strconv.Atoi(value)
	if err != nil {
		return nil
	}
	return &n
}

func decodeJSON[T any](data []byte) (T, error) {
	var out T
	if len(data) == 0 {
		return out, nil
	}
	if err := json.Unmarshal(data, &out); err != nil {
		return out, fmt.Errorf("sdk: decoding response: %w", err)
	}
	return out, nil
}
