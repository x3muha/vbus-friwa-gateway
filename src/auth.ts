import type { IncomingMessage } from 'node:http';
import type { GatewayConfig } from './types.js';

export function isAuthorized(req: IncomingMessage, config: GatewayConfig): boolean {
  const url = new URL(req.url || '/', 'http://localhost');
  const token = req.headers.authorization?.startsWith('Bearer ')
    ? req.headers.authorization.slice('Bearer '.length)
    : (url.searchParams.get('token') || '');
  if (config.auth.token && token === config.auth.token) return true;

  const auth = req.headers.authorization || '';
  if (!auth.startsWith('Basic ')) return false;
  const decoded = Buffer.from(auth.slice('Basic '.length), 'base64').toString('utf8');
  const [username, ...passwordParts] = decoded.split(':');
  const password = passwordParts.join(':');
  return username === config.auth.username && password === config.auth.password;
}

export function unauthorizedBody(): string {
  return JSON.stringify({ ok: false, error: 'unauthorized' });
}
