import type { Packet } from 'resol-vbus-core';
import type { LiveField, StateEntry } from './types.js';

export function decodeLivePacket(packet: Packet, fields: LiveField[]): StateEntry[] {
  const data = packet.getFrameData();
  const ts = new Date().toISOString();
  return fields.map((field) => decodeField(data, field, ts));
}

function decodeField(data: Uint8Array, field: LiveField, ts: string): StateEntry {
  let raw: number | string | boolean | null;
  let value: number | string | boolean | null;

  if (field.format === 'heat' && field.parts) {
    raw = field.parts.reduce((sum, part) => sum + readUnsigned(data, part.offset, part.bitSize) * part.factor, 0);
    value = raw;
  } else if (field.format === 'version' && field.parts) {
    const major = readUnsigned(data, field.parts[0]?.offset ?? 0, field.parts[0]?.bitSize ?? 7);
    const minor = readUnsigned(data, field.parts[1]?.offset ?? 0, field.parts[1]?.bitSize ?? 7);
    raw = `${major}.${String(minor).padStart(2, '0')}`;
    value = raw;
  } else if (field.format === 'time') {
    const minutes = readUnsigned(data, field.offset ?? 0, field.bitSize ?? 15);
    raw = minutes;
    value = `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
  } else if (field.bitSize === 1) {
    raw = ((data[field.offset ?? 0] ?? 0) >> (field.bitPos ?? 0)) & 1;
    value = Boolean(raw);
  } else {
    raw = readSignedOrUnsigned(data, field.offset ?? 0, field.bitSize ?? 8);
    value = round(Number(raw) * (field.factor ?? 1));
  }

  return {
    key: field.key,
    raw,
    value,
    text: `${value}${field.unit ? ` ${field.unit.trim()}` : ''}`,
    unit: field.unit,
    ts,
    source: 'live',
    output: field.output,
  };
}

function readSignedOrUnsigned(data: Uint8Array, offset: number, bitSize: number): number {
  if (bitSize === 15) {
    const raw = readUnsigned(data, offset, 16);
    return raw & 0x4000 ? raw - 0x8000 : raw;
  }
  return readUnsigned(data, offset, bitSize);
}

function readUnsigned(data: Uint8Array, offset: number, bitSize: number): number {
  if (bitSize <= 8) return data[offset] ?? 0;
  if (bitSize <= 16) return (data[offset] ?? 0) | ((data[offset + 1] ?? 0) << 8);
  return 0;
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
