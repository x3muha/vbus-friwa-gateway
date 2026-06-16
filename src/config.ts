import { readFile } from 'node:fs/promises';
import path from 'node:path';
import type { GatewayConfig } from './types.js';

export const defaultConfig: GatewayConfig = {
  serial: {
    path: '/dev/ttyACM0',
    baudRate: 9600,
  },
  vbus: {
    refreshTries: 1,
    refreshTimeoutMs: 200,
    actionTries: 2,
    actionTimeoutMs: 1500,
  },
  server: {
    host: '0.0.0.0',
    port: 8787,
    refreshIntervalMs: 60000,
    parameterReadMode: 'all',
  },
  auth: {
    username: 'admin',
    password: 'admin',
    token: '',
  },
  tls: {
    enabled: false,
    certFile: '',
    keyFile: '',
  },
  profile: {
    file: './profiles/friwa-0x7611.json',
  },
  writes: {
    enabled: true,
    deny: [],
  },
  logging: {
    level: 'info',
  },
};

function mergeConfig(base: GatewayConfig, extra: Partial<GatewayConfig>): GatewayConfig {
  return {
    ...base,
    ...extra,
    serial: { ...base.serial, ...extra.serial },
    vbus: { ...base.vbus, ...extra.vbus },
    server: { ...base.server, ...extra.server },
    auth: { ...base.auth, ...extra.auth },
    tls: { ...base.tls, ...extra.tls },
    profile: { ...base.profile, ...extra.profile },
    writes: { ...base.writes, ...extra.writes },
    logging: { ...base.logging, ...extra.logging },
  };
}

export async function loadConfig(configFile?: string): Promise<{ config: GatewayConfig; baseDir: string }> {
  if (!configFile) {
    return { config: defaultConfig, baseDir: process.cwd() };
  }

  const absFile = path.resolve(configFile);
  const raw = await readFile(absFile, 'utf8');
  const parsed = JSON.parse(raw) as Partial<GatewayConfig>;
  const config = mergeConfig(defaultConfig, parsed);
  return { config, baseDir: path.dirname(absFile) };
}

export function resolveFrom(baseDir: string, filename: string): string {
  if (!filename) return filename;
  return path.isAbsolute(filename) ? filename : path.resolve(baseDir, filename);
}
