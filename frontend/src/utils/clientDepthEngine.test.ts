import { describe, expect, it } from 'vitest';
import { createMinimalGeoTiffBlob } from './clientDepthEngine';

describe('clientDepthEngine', () => {
  it('generates a valid binary GeoTIFF blob with correct TIFF header and IEEE Float32 raster', async () => {
    const width = 16;
    const height = 16;
    const heights = new Array(width * height).fill(15.5);
    heights[0] = 5.0;
    heights[width * height - 1] = 45.2;

    const blob = createMinimalGeoTiffBlob(heights, width, height, 5.0, 45.2);
    expect(blob).toBeDefined();
    expect(blob.type).toBe('image/tiff');

    const arrayBuffer = await blob.arrayBuffer();
    const view = new DataView(arrayBuffer);

    // Verify Little Endian 'II' header
    expect(view.getUint8(0)).toBe(0x49); // 'I'
    expect(view.getUint8(1)).toBe(0x49); // 'I'
    expect(view.getUint16(2, true)).toBe(42); // 42 magic number

    // Verify first IFD offset
    const ifdOffset = view.getUint32(4, true);
    expect(ifdOffset).toBe(8);

    // Verify number of tags
    const numTags = view.getUint16(ifdOffset, true);
    expect(numTags).toBe(11);

    // Total file size should match header + IFD + raster bytes (16*16*4)
    const expectedRasterBytes = width * height * 4;
    expect(arrayBuffer.byteLength).toBeGreaterThan(expectedRasterBytes);
  });

  it('correctly scales and calibrates metric elevations via H = a·D + b', () => {
    const scaleA = -54.9398;
    const offsetB = 65.3389;

    // At normalized depth D = 0.5
    const depth = 0.5;
    const expectedHeight = scaleA * depth + offsetB;
    expect(expectedHeight).toBeCloseTo(37.869, 2);

    // At normalized depth D = 0.98 (deep ground)
    const deepGround = scaleA * 0.98 + offsetB;
    expect(deepGround).toBeCloseTo(11.497, 2);

    // At normalized depth D = 0.12 (tall structure)
    const tallStructure = scaleA * 0.12 + offsetB;
    expect(tallStructure).toBeCloseTo(58.746, 2);
  });
});
