/**
 * ExternalServiceApiError wraps any non-2xx API response. `message` is the
 * server's `error` field verbatim. Rate-limit fields are only populated
 * when the response carried the corresponding headers (always the case on
 * a 429).
 */
export class ExternalServiceApiError extends Error {
  readonly status: number;
  readonly body: string;
  readonly retryAfterSeconds?: number;
  readonly rateLimitLimit?: number;
  readonly rateLimitRemaining?: number;

  constructor(
    status: number,
    message: string,
    body: string,
    rateLimit?: {
      retryAfterSeconds?: number;
      rateLimitLimit?: number;
      rateLimitRemaining?: number;
    },
  ) {
    super(message);
    this.name = 'ExternalServiceApiError';
    this.status = status;
    this.body = body;
    this.retryAfterSeconds = rateLimit?.retryAfterSeconds;
    this.rateLimitLimit = rateLimit?.rateLimitLimit;
    this.rateLimitRemaining = rateLimit?.rateLimitRemaining;
  }

  /** True when the server responded 429 Too Many Requests. */
  get isRateLimited(): boolean {
    return this.status === 429;
  }
}
