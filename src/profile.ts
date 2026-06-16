import { readFile } from 'node:fs/promises';
import type { ParameterDef, StationProfile } from './types.js';

export async function loadProfile(filename: string): Promise<StationProfile> {
  const raw = await readFile(filename, 'utf8');
  return JSON.parse(raw) as StationProfile;
}

export function parseIndex(input: string | number): number {
  if (typeof input === 'number') return input;
  const trimmed = input.trim();
  return trimmed.toLowerCase().startsWith('0x') ? Number.parseInt(trimmed.slice(2), 16) : Number.parseInt(trimmed, 10);
}

export function findParameter(profile: StationProfile, keyOrIndex: string | number): ParameterDef {
  const index = typeof keyOrIndex === 'number' || /^0x[0-9a-f]+$/i.test(String(keyOrIndex)) || /^\d+$/.test(String(keyOrIndex))
    ? parseIndex(keyOrIndex)
    : null;
  const found = profile.parameters.find((param) => param.key === keyOrIndex || (index != null && param.index === index));
  if (!found) {
    throw new Error(`Unknown parameter "${keyOrIndex}"`);
  }
  return found;
}

export function rawToValue(param: ParameterDef, raw: number): number {
  return round(raw * (param.factor || 1));
}

export function valueToRaw(param: ParameterDef, value: string | number | boolean): number {
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (typeof value === 'number') return Math.round(value / (param.factor || 1));

  const lowered = value.trim().toLowerCase();
  if (['true', 'on', 'ein', 'yes', 'ja'].includes(lowered)) return 1;
  if (['false', 'off', 'aus', 'no', 'nein'].includes(lowered)) return 0;

  const normalized = lowered.replace(',', '.');
  const numeric = Number(normalized);
  if (!Number.isFinite(numeric)) {
    throw new Error(`Value "${value}" is not numeric/boolean; write raw values for type ${param.type}`);
  }
  return Math.round(numeric / (param.factor || 1));
}

export function formatParameter(param: ParameterDef, raw: number): string {
  const value = rawToValue(param, raw);
  return `${value}${param.unit ? ` ${param.unit.trim()}` : ''}`;
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
