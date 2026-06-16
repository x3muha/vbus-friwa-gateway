import { readFileSync } from 'node:fs';
import http, { type IncomingMessage, type ServerResponse } from 'node:http';
import https from 'node:https';
import { WebSocketServer, type WebSocket } from 'ws';
import { isAuthorized, unauthorizedBody } from './auth.js';
import { findParameter, valueToRaw } from './profile.js';
import type { GatewayConfig, ParameterReadMode, StationProfile, WsEvent } from './types.js';
import type { VBusClient } from './vbus-client.js';
import { StateStore } from './state.js';

export class GatewayHttpServer {
  private server?: http.Server | https.Server;
  private wss?: WebSocketServer;
  private readonly sockets = new Set<WebSocket>();

  constructor(
    private readonly config: GatewayConfig,
    private readonly profile: StationProfile,
    private readonly state: StateStore,
    private readonly vbus: VBusClient,
  ) {}

  async listen(): Promise<void> {
    this.server = this.createServer();
    this.wss = new WebSocketServer({
      server: this.server,
      path: '/ws',
      verifyClient: (info, done) => {
        done(isAuthorized(info.req, this.config), 401, 'Unauthorized');
      },
    });

    this.wss.on('connection', (socket) => {
      this.sockets.add(socket);
      socket.on('close', () => this.sockets.delete(socket));
      this.send(socket, 'hello', {
        name: this.profile.name,
        profile: this.profile.id,
        tls: this.config.tls.enabled,
      });
      this.send(socket, 'snapshot', this.state.snapshot());
    });

    this.state.on('change', (entry) => {
      this.broadcast('change', entry);
    });

    await new Promise<void>((resolve) => {
      this.server!.listen(this.config.server.port, this.config.server.host, resolve);
    });
  }

  async close(): Promise<void> {
    for (const socket of this.sockets) socket.close();
    this.wss?.close();
    if (this.server) {
      await new Promise<void>((resolve) => this.server!.close(() => resolve()));
    }
  }

  private createServer(): http.Server | https.Server {
    const handler = (req: IncomingMessage, res: ServerResponse) => {
      this.handleRequest(req, res).catch((err) => this.json(res, 500, { ok: false, error: String(err.message || err) }));
    };

    if (!this.config.tls.enabled) {
      return http.createServer(handler);
    }
    return https.createServer({
      cert: readFileSync(this.config.tls.certFile),
      key: readFileSync(this.config.tls.keyFile),
    }, handler);
  }

  private async handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    if (url.pathname === '/health') {
      this.json(res, 200, { ok: true, ts: new Date().toISOString() });
      return;
    }

    if (!isAuthorized(req, this.config)) {
      res.setHeader('WWW-Authenticate', 'Basic realm="vbus-friwa-gateway"');
      this.jsonRaw(res, 401, unauthorizedBody());
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/profile') {
      this.json(res, 200, { ok: true, profile: this.profile });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/state') {
      this.json(res, 200, { ok: true, values: this.state.snapshot() });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/read') {
      const body = await readJson(req);
      if (body.all) {
        await this.vbus.refreshParameters((body.mode as ParameterReadMode | undefined) || this.config.server.parameterReadMode);
        this.json(res, 200, { ok: true, values: this.state.snapshot() });
        return;
      }
      const param = findParameter(this.profile, String(body.key ?? body.index));
      const raw = await this.vbus.readParameter(param);
      this.json(res, 200, { ok: true, key: param.key, index: param.indexHex, raw, value: this.state.get(param.key) });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/write') {
      const body = await readJson(req);
      const param = findParameter(this.profile, String(body.key ?? body.index));
      const value = body.value as string | number | boolean;
      const raw = body.raw === true ? Number(value) : valueToRaw(param, value);
      const result = await this.vbus.writeParameter(param, raw);
      const payload = { ok: true, key: param.key, index: param.indexHex, requestedRaw: raw, ...result, value: this.state.get(param.key) };
      this.broadcast('writeResult', payload);
      this.json(res, 200, payload);
      return;
    }

    this.json(res, 404, { ok: false, error: 'not_found' });
  }

  private broadcast(type: WsEvent['type'], data: unknown): void {
    for (const socket of this.sockets) this.send(socket, type, data);
  }

  private send(socket: WebSocket, type: WsEvent['type'], data: unknown): void {
    const event: WsEvent = { type, ts: new Date().toISOString(), data };
    socket.send(JSON.stringify(event));
  }

  private json(res: ServerResponse, status: number, body: unknown): void {
    this.jsonRaw(res, status, JSON.stringify(body));
  }

  private jsonRaw(res: ServerResponse, status: number, body: string): void {
    res.statusCode = status;
    res.setHeader('content-type', 'application/json; charset=utf-8');
    res.end(body);
  }
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk as Buffer));
  if (chunks.length === 0) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as Record<string, unknown>;
}
