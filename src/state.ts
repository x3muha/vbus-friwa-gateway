import { EventEmitter } from 'node:events';
import type { StateEntry } from './types.js';

export class StateStore extends EventEmitter {
  private readonly entries = new Map<string, StateEntry>();

  set(entry: StateEntry, options: { force?: boolean } = {}): boolean {
    const previous = this.entries.get(entry.key);
    const changed = options.force || !previous || previous.raw !== entry.raw || previous.text !== entry.text;
    this.entries.set(entry.key, entry);
    if (changed) {
      this.emit('change', entry);
    }
    return changed;
  }

  get(key: string): StateEntry | undefined {
    return this.entries.get(key);
  }

  snapshot(): StateEntry[] {
    return [...this.entries.values()].sort((a, b) => (a.output ?? 9999) - (b.output ?? 9999) || a.key.localeCompare(b.key));
  }
}
