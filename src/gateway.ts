import { resolveFrom } from './config.js';
import { existsSync } from 'node:fs';
import { loadProfile } from './profile.js';
import { StateStore } from './state.js';
import type { GatewayConfig } from './types.js';
import { VBusClient } from './vbus-client.js';
import { GatewayHttpServer } from './http-server.js';

export async function runGateway(config: GatewayConfig, baseDir: string): Promise<void> {
  const configRelativeProfile = resolveFrom(baseDir, config.profile.file);
  const cwdRelativeProfile = resolveFrom(process.cwd(), config.profile.file);
  const profile = await loadProfile(existsSync(configRelativeProfile) ? configRelativeProfile : cwdRelativeProfile);
  if (config.tls.enabled) {
    config.tls.certFile = resolveFrom(baseDir, config.tls.certFile);
    config.tls.keyFile = resolveFrom(baseDir, config.tls.keyFile);
  }

  const state = new StateStore();
  const vbus = new VBusClient(config, profile, state);
  const server = new GatewayHttpServer(config, profile, state, vbus);

  await vbus.connect();
  await server.listen();
  console.log(`vbus-friwa-gateway listening on ${config.tls.enabled ? 'https/wss' : 'http/ws'}://${config.server.host}:${config.server.port}`);

  let refreshRunning = false;
  const refresh = async () => {
    if (refreshRunning) return;
    refreshRunning = true;
    try {
      await vbus.refreshParameters();
    } catch (err) {
      console.error(`[refresh] ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      refreshRunning = false;
    }
  };

  await refresh();
  const timer = setInterval(refresh, config.server.refreshIntervalMs);

  const shutdown = async () => {
    clearInterval(timer);
    await server.close();
    await vbus.disconnect();
    process.exit(0);
  };
  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);
}
