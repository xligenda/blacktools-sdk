import * as http from 'node:http';
import * as https from 'node:https';

// minimal HTTP response shape the client needs
export interface HttpResponse {
  status: number;
  statusText: string;
  header(name: string): string | null;
  text: string;
}

export type Transport = (
  url: URL,
  method: string,
  headers: Record<string, string>,
  body?: string,
) => Promise<HttpResponse>;


export const nodeHttpTransport: Transport = (url, method, headers, body) => {
  return new Promise((resolve, reject) => {
    const client = url.protocol === 'https:' ? https : http;
    const requestHeaders = { ...headers };
    if (body !== undefined) {
      requestHeaders['Content-Length'] = String(Buffer.byteLength(body));
    }

    const req = client.request(url, { method, headers: requestHeaders }, (res) => {
      const chunks: Buffer[] = [];
      res.on('data', (chunk: Buffer) => chunks.push(chunk));
      res.on('end', () => {
        resolve({
          status: res.statusCode ?? 0,
          statusText: res.statusMessage ?? '',
          header: (name: string) => {
            const value = res.headers[name.toLowerCase()];
            if (Array.isArray(value)) return value[0] ?? null;
            return value ?? null;
          },
          text: Buffer.concat(chunks).toString('utf8'),
        });
      });
    });

    req.on('error', reject);
    if (body !== undefined) req.write(body);
    req.end();
  });
};
