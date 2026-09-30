import { ExternalServiceApiError } from './errors.js';
import { nodeHttpTransport, type HttpResponse, type Transport } from './transport.js';

export interface HttpClientOptions {
  serviceToken: string;
  /**
   * override for testing
   * defaults to nodeHttpTransport
   * */
  transport?: Transport;
}

export interface RequestOptions {
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  accessToken?: string;
  idempotencyKey?: string;
}

export class HttpClient {
  private readonly serviceToken: string;
  private readonly transport: Transport;

  constructor(options: HttpClientOptions) {
    this.serviceToken = options.serviceToken;
    this.transport = options.transport ?? nodeHttpTransport;
  }

  async request<T>(
    baseUrl: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const url = new URL(baseUrl + path);
    if (options.query) {
      for (const [key, value] of Object.entries(options.query)) {
        if (value !== undefined) url.searchParams.set(key, String(value));
      }
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.serviceToken}`,
    };
    if (options.accessToken) headers['X-Access-Token'] = options.accessToken;
    if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey;

    let body: string | undefined;
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(options.body);
    }

    const response = await this.transport(url, method, headers, body);

    if (response.status < 200 || response.status >= 300) {
      throw buildError(response);
    }

    return response.text.length === 0 ? (undefined as T) : (JSON.parse(response.text) as T);
  }
}

function buildError(response: HttpResponse): ExternalServiceApiError {
  let message = response.statusText;
  try {
    const parsed = JSON.parse(response.text) as { error?: string };
    if (parsed.error) message = parsed.error;
  } catch {
    // non-json body - fall back to statusText
  }

  const retryAfterHeader = response.header('Retry-After');
  const limitHeader = response.header('X-RateLimit-Limit');
  const remainingHeader = response.header('X-RateLimit-Remaining');

  return new ExternalServiceApiError(response.status, message, response.text, {
    retryAfterSeconds: retryAfterHeader ? Number(retryAfterHeader) : undefined,
    rateLimitLimit: limitHeader ? Number(limitHeader) : undefined,
    rateLimitRemaining: remainingHeader ? Number(remainingHeader) : undefined,
  });
}
