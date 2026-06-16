#!/usr/bin/env node
import { loadConfig, resolveFrom } from './config.js';
import { existsSync } from 'node:fs';
import { loadProfile, findParameter, valueToRaw, formatParameter } from './profile.js';
import { StateStore } from './state.js';
import { VBusClient } from './vbus-client.js';

interface CliOptions {
  config?: string;
  read?: string;
  readAll: boolean;
  write?: string;
  value?: string;
  raw: boolean;
  direct: boolean;
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  const { config, baseDir } = await loadConfig(options.config);
  const configRelativeProfile = resolveFrom(baseDir, config.profile.file);
  const cwdRelativeProfile = resolveFrom(process.cwd(), config.profile.file);
  const profile = await loadProfile(existsSync(configRelativeProfile) ? configRelativeProfile : cwdRelativeProfile);

  if (!options.direct) {
    await runApiMode(options, config);
    return;
  }

  const state = new StateStore();
  const vbus = new VBusClient(config, profile, state);
  await vbus.connect();
  try {
    if (options.readAll) {
      await vbus.refreshParameters('all');
      for (const entry of state.snapshot()) {
        if (entry.source === 'parameter') {
          console.log(`${entry.indexHex}\t${entry.key}\traw=${entry.raw}\tvalue=${entry.text}`);
        }
      }
      return;
    }

    if (options.read) {
      const param = findParameter(profile, options.read);
      const raw = await vbus.readParameter(param);
      console.log(`${param.indexHex}\t${param.key}\traw=${raw}\tvalue=${formatParameter(param, raw)}`);
      return;
    }

    if (options.write) {
      if (options.value == null) throw new Error('--write needs a value');
      const param = findParameter(profile, options.write);
      const raw = options.raw ? Number(options.value) : valueToRaw(param, options.value);
      const result = await vbus.writeParameter(param, raw);
      const after = state.get(param.key);
      console.log(`${param.indexHex}\t${param.key}\tbefore=${result.before}\trequested=${raw}\tafter=${result.after}\tvalue=${after?.text ?? ''}`);
      return;
    }

    printUsage();
  } finally {
    await vbus.disconnect();
  }
}

function parseArgs(args: string[]): CliOptions {
  const options: CliOptions = { readAll: false, raw: false, direct: false };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--config' || arg === '-c') options.config = args[++i];
    else if (arg === '--read') {
      const next = args[i + 1];
      if (next === '--all' || next === 'all') {
        options.readAll = true;
        i += 1;
      } else {
        options.read = args[++i];
      }
    }
    else if (arg === '--all') options.readAll = true;
    else if (arg === '--write') {
      options.write = args[++i];
      options.value = args[++i];
    } else if (arg === '--raw') options.raw = true;
    else if (arg === '--direct') options.direct = true;
    else if (arg === '--help' || arg === '-h') {
      printUsage();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

function printUsage(): void {
  console.log(`Usage:
  vbus-test --config /etc/vbus-friwa-gateway/config.json --read --all
  vbus-test --config /etc/vbus-friwa-gateway/config.json --read 0x0130
  vbus-test --config /etc/vbus-friwa-gateway/config.json --write 0x0130 65
  vbus-test --config /etc/vbus-friwa-gateway/config.json --write 0x0130 650 --raw

Default talks to the running gateway service over HTTP.
Add --direct to access the serial VBus interface directly.
`);
}

async function runApiMode(options: CliOptions, config: Awaited<ReturnType<typeof loadConfig>>['config']): Promise<void> {
  if (options.readAll) {
    const data = await apiRequest(config, '/api/read', { all: true });
    const values = Array.isArray(data.values) ? data.values : [];
    for (const entry of values.filter((item: any) => item.source === 'parameter')) {
      console.log(`${entry.indexHex ?? ''}\t${entry.key}\traw=${entry.raw}\tvalue=${entry.text}`);
    }
    return;
  }

  if (options.read) {
    const data = await apiRequest(config, '/api/read', { index: options.read });
    const value = data.value;
    if (value && typeof value === 'object') {
      console.log(`${data.index}\t${data.key}\traw=${data.raw}\tvalue=${value.text ?? value.value}`);
    } else {
      console.log(JSON.stringify(data));
    }
    return;
  }

  if (options.write) {
    if (options.value == null) throw new Error('--write needs a value');
    const data = await apiRequest(config, '/api/write', {
      index: options.write,
      value: options.value,
      raw: options.raw,
    });
    const value = data.value;
    const text = value && typeof value === 'object' ? (value.text ?? value.value ?? '') : '';
    console.log(`${data.index}\t${data.key}\tbefore=${data.before}\trequested=${data.requestedRaw}\tafter=${data.after}\tvalue=${text}`);
    return;
  }

  printUsage();
}

async function apiRequest(config: Awaited<ReturnType<typeof loadConfig>>['config'], path: string, body: unknown): Promise<any> {
  const host = config.server.host === '0.0.0.0' || config.server.host === '::' ? '127.0.0.1' : config.server.host;
  const scheme = config.tls.enabled ? 'https' : 'http';
  const url = `${scheme}://${host}:${config.server.port}${path}`;
  const headers: Record<string, string> = {
    'content-type': 'application/json',
    accept: 'application/json',
  };
  if (config.auth.token) {
    headers.authorization = `Bearer ${config.auth.token}`;
  } else {
    headers.authorization = `Basic ${Buffer.from(`${config.auth.username}:${config.auth.password}`).toString('base64')}`;
  }
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let data: any;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON from ${url}: ${text}`);
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
