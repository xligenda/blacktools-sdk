// Wire types for the ExternalServices API, field names kept snake_case to
// match the JSON exactly as the API returns it.

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  user_id: number;
  /** Unix seconds. */
  expires_at: number;
}

export interface PermsCheckResult {
  granted: boolean;
}

export interface Profile {
  user_id: number;
  discord_id?: string;
  nickname: string;
  vk_id?: number;
  tg_id?: number;
  forum_id?: number;
  google_id?: string;
  /** RFC3339. */
  created_at: string;
  roles?: string[];
  vk_name?: string;
  telegram_name?: string;
  forum_name?: string;
  forum_view_url?: string;
  email?: string;
}

export interface GetProfileOptions {
  /** Look up a specific user instead of the caller identified by accessToken. */
  userId?: number;
  /** The end user's own access token, for a self-lookup. */
  accessToken?: string;
  /** Include vk/telegram/forum display names and forum profile URL. */
  expand?: boolean;
  /** Include the linked Google account's email. */
  email?: boolean;
  /** Include the user's role names. */
  roles?: boolean;
}

export interface PostSnapshot {
  server_code: string;
  server_name: string;
  permission_group: string;
  access_level: number;
  is_temp: boolean;
  ticket: string;
}

export type WarnKind = 'warning' | 'reprimand';

export interface Warn {
  id: number;
  reason: string;
  value: number;
  kind: WarnKind;
  /** RFC3339. */
  issued_at: string;
  issued_by: string;
  /** RFC3339. */
  revoked_at?: string;
  revoked_by?: string;
}

export interface ExpandedConnections {
  vk_name?: string;
  telegram_name?: string;
  discord_name?: string;
  forum_name?: string;
  forum_view_url?: string;
}

export interface StaffRoleAssignment {
  assignment_id: string;
  kind: string;
  role_name: string;
  granted_by: string;
  /** RFC3339. */
  created_at: string;
}

export interface Moderator {
  user_id: string;
  sso_user_id: number;
  nickname: string;
  tg_id?: number;
  permission_group: string;
  access_level: number;
  is_temp: boolean;
  active_warnings: number;
  active_reprimands: number;
  roles: StaffRoleAssignment[];
}

export interface Connections {
  discord_id: string;
  discord_name?: string;
  vk_id?: number;
  vk_name?: string;
  tg_id?: number;
  telegram_name?: string;
  forum_id?: number;
  forum_name?: string;
  forum_view_url?: string;
  google_id?: string;
}

/** how a notification Button is rendered */
export type ButtonStyle = 'ok' | 'no' | 'grey' | 'warm' | 'link';

/**
 * one action button on a notification, shown in the Mini App and in Telegram
 * and Discord DMs. set at most one of url and payload: a url button opens the
 * link, a payload button POSTs a WebhookEvent carrying payload to the
 * service's webhook (see setWebhook), and a button with neither only records
 * the click
 */
export interface Button {
  /** 1-40 characters */
  label: string;
  /** defaults to 'grey' */
  style?: ButtonStyle;
  /** absolute https url of at most 512 characters */
  url?: string;
  /** at most 1024 bytes, requires a webhook to be set */
  payload?: string;
}

export interface NotifyRequest {
  kind: string;
  title: string;
  body: string;
  /** at most 3 action buttons; a recipient can run only one per notification */
  buttons?: Button[];
  /**
   * sent as the Idempotency-Key header (not in the body) so a retried request
   * does not deliver the notification twice; 1-128 chars of [A-Za-z0-9._:-]
   */
  idempotencyKey?: string;
}

export interface NotifyServerResult {
  /** count of recipients notified */
  delivered: number;
  /** count of recipients whose delivery failed */
  failed: number;
  /** count of recipients a delivery was attempted for */
  total: number;
}

export interface NotifyModeratorResult {
  delivered: boolean;
}

/** result of setWebhook; secret is only returned here, store it for verifyWebhook */
export interface WebhookConfig {
  url: string;
  secret: string;
}
