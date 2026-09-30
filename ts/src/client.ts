import { HttpClient, type RequestOptions } from './http.js';
import type { Transport } from './transport.js';
import type {
  Connections,
  ExpandedConnections,
  GetProfileOptions,
  Moderator,
  NotifyRequest,
  NotifyModeratorResult,
  NotifyServerResult,
  PermsCheckResult,
  PostSnapshot,
  Profile,
  TokenPair,
  Warn,
  WebhookConfig,
} from './types.js';

/** base URL of the production gateway API */
export const DEFAULT_GATEWAY_URL = 'https://blacktools.odsmod.su/api';
/** base URL of the production auth API */
export const DEFAULT_AUTH_URL = 'https://blacktools.odsmod.su/auth';

export interface ExternalServiceClientOptions {
  /** base URL of the primary API, defaults to DEFAULT_GATEWAY_URL */
  gatewayUrl?: string;
  /** base URL used for token exchange/refresh, defaults to DEFAULT_AUTH_URL */
  authUrl?: string;
  /** the service's own bearer token */
  serviceToken: string;
  /** override for testing; defaults to nodeHttpTransport */
  transport?: Transport;
}


export class ExternalServiceClientImpl {
  private readonly gatewayUrl: string;
  private readonly authUrl: string;
  private readonly http: HttpClient;

  constructor(options: ExternalServiceClientOptions) {
    this.gatewayUrl = (options.gatewayUrl || DEFAULT_GATEWAY_URL).replace(/\/+$/, '');
    this.authUrl = (options.authUrl || DEFAULT_AUTH_URL).replace(/\/+$/, '');
    this.http = new HttpClient({
      serviceToken: options.serviceToken,
      transport: options.transport,
    });
  }

  /** redeems a one-time link code for a fresh user access/refresh token pair */
  async exchangeCode(code: string): Promise<TokenPair> {
    return this.http.request<TokenPair>(this.authUrl, 'POST', '/sso/exchange', {
      body: { code },
    });
  }

  /** rotates a refresh token for a fresh access/refresh token pair */
  async refreshToken(refreshToken: string): Promise<TokenPair> {
    return this.http.request<TokenPair>(this.authUrl, 'POST', '/sso/refresh', {
      body: { refresh_token: refreshToken },
    });
  }

  /** checks whether userId holds permission */
  async checkPermission(userId: number, permission: string): Promise<boolean> {
    const result = await this.http.request<PermsCheckResult>(
      this.gatewayUrl,
      'GET',
      '/sso/perms/check',
      { body: { user_id: userId, permission } },
    );
    return result.granted;
  }

  /** looks up a user's profile, by userId, by accessToken, or (server-type) neither */
  async getProfile(options: GetProfileOptions = {}): Promise<Profile> {
    const query: Record<string, string> = {};
    if (options.expand) query.expand = 'true';
    if (options.email) query.email = 'true';
    if (options.roles) query.roles = 'true';

    const body = options.userId !== undefined ? { user_id: options.userId } : undefined;

    return this.http.request<Profile>(this.gatewayUrl, 'GET', '/sso/profile', {
      query,
      body,
      accessToken: options.accessToken,
    });
  }

  /** returns the caller's current role/post snapshots */
  async getPosts(accessToken: string): Promise<PostSnapshot[]> {
    return this.http.request<PostSnapshot[]>(this.gatewayUrl, 'GET', '/sso/posts', {
      accessToken,
    });
  }

  /** returns the caller's active and revoked warns/reprimands */
  async getWarns(accessToken: string): Promise<Warn[]> {
    return this.http.request<Warn[]>(this.gatewayUrl, 'GET', '/sso/warns', { accessToken });
  }

  /** forces a fresh role/post sync for the caller, returning the result */
  async refreshPosts(accessToken: string): Promise<PostSnapshot[]> {
    return this.http.request<PostSnapshot[]>(this.gatewayUrl, 'POST', '/sso/posts/refresh', {
      accessToken,
    });
  }

  /** forces a fresh service conntion display-name resolution for the caller */
  async refreshConnections(accessToken: string): Promise<ExpandedConnections> {
    return this.http.request<ExpandedConnections>(
      this.gatewayUrl,
      'POST',
      '/sso/connections/refresh',
      { accessToken },
    );
  }

  /** lists moderators on serverIndex, optionally filtered by Discord id or nickname substring */
  async listModerators(serverIndex: number, query?: string): Promise<Moderator[]> {
    return this.http.request<Moderator[]>(
      this.gatewayUrl,
      'GET',
      `/sso/servers/${serverIndex}/moderators`,
      { query: query ? { query } : undefined },
    );
  }

  /** returns a moderator's current linked connections on serverIndex */
  async getModeratorConnections(serverIndex: number, userID: string): Promise<Connections> {
    return this.http.request<Connections>(
      this.gatewayUrl,
      'GET',
      `/sso/servers/${serverIndex}/moderators/${userID}/connections`,
    );
  }

  /** forces a fresh connection resolution for a moderator on serverIndex */
  async refreshModeratorConnections(serverIndex: number, userID: string): Promise<Connections> {
    return this.http.request<Connections>(
      this.gatewayUrl,
      'POST',
      `/sso/servers/${serverIndex}/moderators/${userID}/connections/refresh`,
    );
  }

  /** forces a fresh role/post sync for a moderator on serverIndex */
  async refreshModeratorPosts(serverIndex: number, userID: string): Promise<PostSnapshot[]> {
    return this.http.request<PostSnapshot[]>(
      this.gatewayUrl,
      'POST',
      `/sso/servers/${serverIndex}/moderators/${userID}/posts/refresh`,
    );
  }

  /** notifies every staff member designated to receive notifications for serverIndex */
  async notifyServer(
    serverIndex: number,
    notification: NotifyRequest,
  ): Promise<NotifyServerResult> {
    return this.http.request<NotifyServerResult>(
      this.gatewayUrl,
      'POST',
      `/sso/servers/${serverIndex}/notify`,
      notifyOptions(notification),
    );
  }

  /** notifies single moderator on serverIndex */
  async notifyModerator(
    serverIndex: number,
    userID: string,
    notification: NotifyRequest,
  ): Promise<NotifyModeratorResult> {
    return this.http.request<NotifyModeratorResult>(
      this.gatewayUrl,
      'POST',
      `/sso/servers/${serverIndex}/moderators/${userID}/notify`,
      notifyOptions(notification),
    );
  }

  /**
   * sets the https url that receives a signed WebhookEvent whenever a
   * recipient runs one of this service's payload buttons; every call issues a
   * new signing secret, invalidating the previous one
   */
  async setWebhook(url: string): Promise<WebhookConfig> {
    return this.http.request<WebhookConfig>(this.gatewayUrl, 'PUT', '/sso/webhook', {
      body: { url },
    });
  }

  /** removes this service's webhook; payload buttons already sent fail until one is set again */
  async deleteWebhook(): Promise<void> {
    await this.http.request<void>(this.gatewayUrl, 'DELETE', '/sso/webhook');
  }
}

/** splits a NotifyRequest into its JSON body and Idempotency-Key header */
function notifyOptions({ idempotencyKey, ...body }: NotifyRequest): RequestOptions {
  return { body, idempotencyKey };
}
