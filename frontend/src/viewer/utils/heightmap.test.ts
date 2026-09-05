import { describe, expect, it } from 'vitest';
import {
  decodeHeightmapFromPixels,
  getAuthoritativeHeight,
} from './heightmap';

describe('Heightmap CPU Utilities', () => {
  it('decodes 16-bit integer values to exact metric elevations', () => {
    const width = 4;
    const height = 4;
    const hMin = 10.0;
    const hMax = 110.0;
    const u16 = new Uint16Array(width * height);

    // 0 -> 10.0m, 65535 -> 110.0m, 32767.5 -> 60.0m
    u16[0] = 0;
    u16[1] = 65535;
    u16[2] = Math.round(65535 / 2);

    const decoded = decodeHeightmapFromPixels(u16, width, height, hMin, hMax);

    expect(decoded[0]).toBeCloseTo(10.0, 3);
    expect(decoded[1]).toBeCloseTo(110.0, 3);
    expect(decoded[2]).toBeCloseTo(60.0, 2);
  });

  it('samples synthetic elevation ramp matching analytic formula within 0.1m', () => {
    // Synthetic linear ramp: H(u, v) = 15.0 + 35.0 * v (from 15m to 50m)
    const width = 100;
    const height = 100;
    const heightmap = new Float32Array(width * height);

    for (let r = 0; r < height; r++) {
      const v = r / (height - 1);
      const hVal = 15.0 + 35.0 * v;
      for (let c = 0; c < width; c++) {
        heightmap[r * width + c] = hVal;
      }
    }

    // Query arbitrary continuous points
    const testPoints = [
      { u: 0.25, v: 0.0, expected: 15.0 },
      { u: 0.5, v: 0.5, expected: 32.5 },
      { u: 0.8, v: 0.75, expected: 41.25 },
      { u: 0.1, v: 1.0, expected: 50.0 },
    ];

    for (const pt of testPoints) {
      const sampled = getAuthoritativeHeight(heightmap, width, height, pt.u, pt.v);
      expect(Math.abs(sampled - pt.expected)).toBeLessThanOrEqual(0.1);
    }
  });

  it('clamps coordinates safely outside [0, 1] range', () => {
    const width = 2;
    const height = 2;
    const heightmap = new Float32Array([10, 20, 30, 40]);

    const clampedLow = getAuthoritativeHeight(heightmap, width, height, -0.5, -0.5);
    expect(clampedLow).toBeCloseTo(10, 3);

    const clampedHigh = getAuthoritativeHeight(heightmap, width, height, 1.5, 1.5);
    expect(clampedHigh).toBeCloseTo(40, 3);
  });
});
