import { createHmac, timingSafeEqual } from 'node:crypto';

/** headers sent with every webhook request (lower-cased, as node exposes them) */
export const WEBHOOK_HEADERS = {
  signature: 'x-blacktools-signature',
  timestamp: 'x-blacktools-timestamp',
  delivery: 'x-blacktools-delivery',
  event: 'x-blacktools-event',
} as const;

/** type of the event sent when a recipient runs a payload button */
export const WEBHOOK_EVENT_ACTION = 'notification.action';

/** how far a webhook timestamp may drift from now before verifyWebhook rejects it */
export const DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300;

/** thrown when a webhook request is not authentic or is too old */
export class InvalidWebhookSignatureError extends Error {
  constructor() {
    super('invalid webhook signature');
    this.name = 'InvalidWebhookSignatureError';
  }
}

/** JSON body of a webhook request */
export interface WebhookEvent {
  type: string;
  /** unique per delivery, equals the x-blacktools-delivery header */
  id: string;
  notification_id: number;
  kind: string;
  /** server the notification was sent for */
  server_index?: number;
  action: { index: number; label: string; payload: string };
  user: { id: number; discord_id?: string; tg_id?: number };
  /** where the button was pressed */
  channel: 'app' | 'telegram' | 'discord';
  occurred_at: string;
}

/**
 * optional JSON body a webhook may answer a 2xx with; any non-2xx answer
 * fails the button press and lets the recipient retry
 */
export interface WebhookResponse {
  /** shown to the recipient (at most 200 characters) */
  message?: string;
  /** replaces the button's label in the "already done" line, e.g. "Одобрено" */
  acted_label?: string;
}

/**
 * checks signature is the valid signature of rawBody under secret for
 * timestamp, and timestamp is within toleranceSeconds of now; throws
 * InvalidWebhookSignatureError otherwise. rawBody must be the exact bytes
 * received, not re-serialized JSON
 */
export function verifyWebhook(
  secret: string,
  timestamp: string,
  signature: string,
  rawBody: string | Buffer,
  toleranceSeconds = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
): void {
  const sent = Number(timestamp);
  if (!/^\d+$/.test(timestamp) || Math.abs(Date.now() / 1000 - sent) > toleranceSeconds) {
    throw new InvalidWebhookSignatureError();
  }

  const want = Buffer.from(
    'sha256=' + createHmac('sha256', secret).update(`${timestamp}.`).update(rawBody).digest('hex'),
  );
  const got = Buffer.from(signature);
  if (got.length !== want.length || !timingSafeEqual(got, want)) {
    throw new InvalidWebhookSignatureError();
  }
}

/**
 * verifies a webhook request from its headers and raw body, and returns the
 * decoded event
 */
export function parseWebhookEvent(
  secret: string,
  headers: Record<string, string | string[] | undefined>,
  rawBody: string | Buffer,
): WebhookEvent {
  verifyWebhook(
    secret,
    headerValue(headers, WEBHOOK_HEADERS.timestamp),
    headerValue(headers, WEBHOOK_HEADERS.signature),
    rawBody,
  );
  return JSON.parse(rawBody.toString()) as WebhookEvent;
}

function headerValue(headers: Record<string, string | string[] | undefined>, name: string): string {
  const value = headers[name];
  return (Array.isArray(value) ? value[0] : value) ?? '';
}
