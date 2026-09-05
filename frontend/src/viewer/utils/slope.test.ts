import { describe, expect, it } from 'vitest';
import { computeSlopeGrid, getSlopeColorRamp } from './heightmap';

describe('Slope Overlay and Analysis', () => {
  it('correctly computes 0 degrees on a flat plain', () => {
    const width = 20;
    const height = 20;
    const flatGrid = new Float32Array(width * height).fill(42.0);

    const slopes = computeSlopeGrid(flatGrid, width, height, 1.0);
    for (let i = 0; i < slopes.length; i++) {
      expect(slopes[i]).toBeCloseTo(0.0, 4);
    }
  });

  it('measures a 45-degree ramp at 45.0 ± 0.5 degrees and maps to the red/orange color band', () => {
    // 45 degrees slope means elevation rises 1 metre for every 1 metre horizontal
    // dz / dx = tan(45 deg) = 1.0. With gsd = 1.0 m, H(r, c) = c * 1.0
    const width = 50;
    const height = 50;
    const gsdM = 1.0;
    const rampGrid = new Float32Array(width * height);

    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        rampGrid[r * width + c] = c * gsdM;
      }
    }

    const slopes = computeSlopeGrid(rampGrid, width, height, gsdM);

    // Check interior cells (avoiding boundary edge artifacts)
    for (let r = 5; r < height - 5; r++) {
      for (let c = 5; c < width - 5; c++) {
        const slopeDeg = slopes[r * width + c];
        expect(slopeDeg).toBeGreaterThanOrEqual(44.5);
        expect(slopeDeg).toBeLessThanOrEqual(45.5);

        // 45 degrees should map to the red colour band (> 40 degrees)
        const [red, green, blue] = getSlopeColorRamp(slopeDeg);
        expect(red).toBe(239);
        expect(green).toBe(68);
        expect(blue).toBe(68);
      }
    }
  });

  it('maps slopes into appropriate color bands', () => {
    // Green band (< 10 deg)
    const [r1, g1, b1] = getSlopeColorRamp(5.0);
    expect(r1).toBe(34);
    expect(g1).toBe(197);
    expect(b1).toBe(94);

    // Yellow band (10 - 25 deg)
    const [r2, g2, b2] = getSlopeColorRamp(18.0);
    expect(r2).toBe(234);
    expect(g2).toBe(179);
    expect(b2).toBe(8);

    // Orange band (25 - 40 deg)
    const [r3, g3, b3] = getSlopeColorRamp(32.0);
    expect(r3).toBe(249);
    expect(g3).toBe(115);
    expect(b3).toBe(22);

    // Red band (> 40 deg)
    const [r4, g4, b4] = getSlopeColorRamp(55.0);
    expect(r4).toBe(239);
    expect(g4).toBe(68);
    expect(b4).toBe(68);
  });
});
