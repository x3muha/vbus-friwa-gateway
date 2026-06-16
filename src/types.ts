export type ParameterReadMode = 'writable' | 'light' | 'all' | 'none';

export interface GatewayConfig {
  serial: {
    path: string;
    baudRate: number;
  };
  vbus: {
    refreshTries: number;
    refreshTimeoutMs: number;
    actionTries: number;
    actionTimeoutMs: number;
  };
  server: {
    host: string;
    port: number;
    refreshIntervalMs: number;
    parameterReadMode: ParameterReadMode;
    restartAfterRefreshFailures: number;
  };
  auth: {
    username: string;
    password: string;
    token: string;
  };
  tls: {
    enabled: boolean;
    certFile: string;
    keyFile: string;
  };
  profile: {
    file: string;
  };
  writes: {
    enabled: boolean;
    deny: string[];
  };
  logging: {
    level: 'debug' | 'info' | 'warn' | 'error';
  };
}

export interface LiveField {
  key: string;
  label: string;
  output: number;
  offset?: number;
  bitSize?: number;
  bitPos?: number;
  factor?: number;
  unit?: string;
  format?: 'time' | 'version' | 'heat' | 'number' | 'boolean';
  parts?: Array<{ offset: number; bitSize: number; factor: number }>;
}

export interface ParameterDef {
  key: string;
  index: number;
  indexHex: string;
  label: string;
  menu: string;
  type: string;
  unit?: string;
  factor: number;
  min?: string;
  max?: string;
  default?: string;
  writable: boolean;
  output?: number;
  input?: number;
  edomi?: {
    full?: EdomiMapping;
    light?: EdomiMapping;
  };
}

export interface EdomiMapping {
  output?: number;
  input?: number;
  label?: string;
  note?: string;
  reuseOutput?: boolean;
}

export interface StationProfile {
  id: string;
  name: string;
  peerAddress: number;
  peerAddressHex: string;
  livePacketId: string;
  live: LiveField[];
  parameters: ParameterDef[];
}

export interface StateEntry {
  key: string;
  raw: number | string | boolean | null;
  value: number | string | boolean | null;
  text: string;
  unit?: string;
  ts: string;
  source: 'live' | 'parameter';
  output?: number;
  input?: number;
  indexHex?: string;
}

export interface WsEvent {
  type: 'hello' | 'snapshot' | 'change' | 'writeResult' | 'error';
  ts: string;
  data: unknown;
}
