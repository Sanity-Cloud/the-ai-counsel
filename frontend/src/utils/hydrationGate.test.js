import { describe, expect, it } from 'vitest';
import { createHydrationGate } from './hydrationGate';

describe('createHydrationGate', () => {
  it('blocks side effects until the active hydration releases', () => {
    const gate = createHydrationGate();
    const token = gate.begin();

    expect(gate.isHydrating()).toBe(true);
    expect(gate.release(token)).toBe(true);
    expect(gate.isHydrating()).toBe(false);
  });

  it('does not let a stale load release a newer hydration', () => {
    const gate = createHydrationGate();
    const staleToken = gate.begin();
    const currentToken = gate.begin();

    expect(gate.release(staleToken)).toBe(false);
    expect(gate.isHydrating()).toBe(true);
    expect(gate.release(currentToken)).toBe(true);
    expect(gate.isHydrating()).toBe(false);
  });

  it('returns to blocking state and invalidates the active token when cancelled', () => {
    const gate = createHydrationGate();
    const token = gate.begin();
    gate.release(token);
    gate.cancel();

    expect(gate.isHydrating()).toBe(true);
    expect(gate.isCurrent(token)).toBe(false);
    expect(gate.release(token)).toBe(false);
  });
});
