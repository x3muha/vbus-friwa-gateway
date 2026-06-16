import type { Packet } from 'resol-vbus-core';
import type { GatewayConfig, ParameterDef, StationProfile } from './types.js';
import { decodeLivePacket } from './decoder.js';
import { rawToValue, formatParameter } from './profile.js';
import { SerialVBusConnection } from './serial-connection.js';
import { StateStore } from './state.js';

export class VBusClient {
  private readonly connection: SerialVBusConnection;
  private readonly queue: Promise<unknown> = Promise.resolve();
  private locked: Promise<unknown> = Promise.resolve();

  constructor(
    private readonly config: GatewayConfig,
    private readonly profile: StationProfile,
    private readonly state: StateStore,
  ) {
    this.connection = new SerialVBusConnection({
      path: config.serial.path,
      baudRate: config.serial.baudRate,
    });
  }

  async connect(): Promise<void> {
    this.connection.liveTransceiver.onPacket = (packet) => this.handlePacket(packet);
    await this.connection.connect();
  }

  async disconnect(): Promise<void> {
    await this.connection.disconnect();
  }

  async refreshParameters(mode = this.config.server.parameterReadMode): Promise<void> {
    if (mode === 'none') return;
    const params = this.profile.parameters.filter((param) => mode === 'all' || param.writable);
    await this.withLock(async () => {
      const tx = this.connection.liveTransceiver;
      const offer = await tx.waitForFreeBus();
      if (!offer) throw new Error('No VBus free-bus offer received');
      const peer = offer.sourceAddress;
      try {
        for (const param of params) {
          const dgram = await tx.getValueByIndex(peer, param.index, {
            tries: this.config.vbus.refreshTries,
            initialTimeoutMs: this.config.vbus.refreshTimeoutMs,
            timeoutIncrMs: 0,
          });
          if (dgram) {
            this.storeParameter(param, dgram.param32 >>> 0);
          }
        }
      } finally {
        await tx.releaseBus(peer);
      }
    });
  }

  async readParameter(param: ParameterDef): Promise<number> {
    return this.withLock(async () => {
      const tx = this.connection.liveTransceiver;
      const offer = await tx.waitForFreeBus();
      if (!offer) throw new Error('No VBus free-bus offer received');
      const peer = offer.sourceAddress;
      try {
        const dgram = await tx.getValueByIndex(peer, param.index, this.actionOptions());
        if (!dgram) throw new Error(`Read failed for ${param.indexHex}`);
        const raw = dgram.param32 >>> 0;
        this.storeParameter(param, raw, true);
        return raw;
      } finally {
        await tx.releaseBus(peer);
      }
    });
  }

  async writeParameter(param: ParameterDef, rawValue: number): Promise<{ before: number; after: number }> {
    if (!this.config.writes.enabled) throw new Error('Writes are disabled in config');
    if (this.config.writes.deny.includes(param.key) || this.config.writes.deny.includes(param.indexHex)) {
      throw new Error(`Writes are denied for ${param.key}`);
    }
    if (!param.writable) throw new Error(`${param.key} is not writable according to profile`);

    return this.withLock(async () => {
      const tx = this.connection.liveTransceiver;
      const offer = await tx.waitForFreeBus();
      if (!offer) throw new Error('No VBus free-bus offer received');
      const peer = offer.sourceAddress;
      try {
        const beforeDgram = await tx.getValueByIndex(peer, param.index, this.actionOptions());
        if (!beforeDgram) throw new Error(`Pre-read failed for ${param.indexHex}`);
        const before = beforeDgram.param32 >>> 0;
        const writeDgram = await tx.setValueByIndex(peer, param.index, rawValue, this.actionOptions());
        if (!writeDgram) throw new Error(`Write failed for ${param.indexHex}`);
        const afterDgram = await tx.getValueByIndex(peer, param.index, this.actionOptions());
        if (!afterDgram) throw new Error(`Readback failed for ${param.indexHex}`);
        const after = afterDgram.param32 >>> 0;
        this.storeParameter(param, after, true);
        return { before, after };
      } finally {
        await tx.releaseBus(peer);
      }
    });
  }

  private handlePacket(packet: Packet): void {
    if (packet.getId() !== this.profile.livePacketId) return;
    for (const entry of decodeLivePacket(packet, this.profile.live)) {
      this.state.set(entry);
    }
  }

  private storeParameter(param: ParameterDef, raw: number, force = false): void {
    this.state.set({
      key: param.key,
      raw,
      value: rawToValue(param, raw),
      text: formatParameter(param, raw),
      unit: param.unit,
      ts: new Date().toISOString(),
      source: 'parameter',
      output: param.output,
      input: param.input,
      indexHex: param.indexHex,
    }, { force });
  }

  private actionOptions() {
    return {
      tries: this.config.vbus.actionTries,
      initialTimeoutMs: this.config.vbus.actionTimeoutMs,
      timeoutIncrMs: 0,
    };
  }

  private async withLock<T>(fn: () => Promise<T>): Promise<T> {
    const previous = this.locked;
    let release!: () => void;
    this.locked = new Promise<void>((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      return await fn();
    } finally {
      release();
    }
  }
}
