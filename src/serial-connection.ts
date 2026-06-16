import { LiveTransceiver } from 'resol-vbus-core';
import { SerialPort } from 'serialport';

export class SerialVBusConnection {
  readonly serialPort: SerialPort;
  readonly liveTransceiver: LiveTransceiver;

  constructor(options: { path: string; baudRate: number }) {
    this.serialPort = new SerialPort({
      path: options.path,
      baudRate: options.baudRate,
      autoOpen: false,
    });

    this.liveTransceiver = new LiveTransceiver({
      baudrate: options.baudRate,
      onTransmit: (buffer) => {
        this.serialPort.write(buffer);
      },
    });

    this.serialPort.on('data', (chunk: Buffer) => {
      this.liveTransceiver.decode(chunk);
    });
  }

  async connect(): Promise<void> {
    if (this.serialPort.isOpen) return;
    await new Promise<void>((resolve, reject) => {
      this.serialPort.open((err) => (err ? reject(err) : resolve()));
    });
  }

  async disconnect(): Promise<void> {
    if (!this.serialPort.isOpen) return;
    await new Promise<void>((resolve, reject) => {
      this.serialPort.close((err) => (err ? reject(err) : resolve()));
    });
  }
}
