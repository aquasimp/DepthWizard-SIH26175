/**
 * Authoritative CPU-side heightmap decoding and analysis utilities.
 *
 * All height probing, slope calculations, and collision detection MUST be
 * grounded in CPU-side Float32Array values rather than GPU raycasting.
 */

export interface HeightmapMeta {
  is_absolute: boolean;
  units: string;
  h_min_raw: number;
  h_max_raw: number;
  elevation_range_m?: number;
  decode_formula: string;
  assumed_gsd_m: number;
  width: number;
  height: number;
  model_version?: string;
  calibration_status?: string;
  [key: string]: unknown;
}

/**
 * Pure function: Decode an array of 16-bit unsigned integers [0, 65535]
 * into real metric elevations using the sidecar linear formula:
 * h_real = h_min_raw + (px / 65535.0) * (h_max_raw - h_min_raw)
 */
export function decodeHeightmapFromPixels(
  u16Data: Uint16Array | number[],
  width: number,
  height: number,
  hMin: number,
  hMax: number
): Float32Array {
  const total = width * height;
  const out = new Float32Array(total);
  const range = hMax - hMin;

  for (let i = 0; i < total; i++) {
    const px = u16Data[i];
    out[i] = hMin + (px / 65535.0) * range;
  }
  return out;
}

/**
 * Sample authoritative elevation from a Float32Array heightmap at normalized UV coords (0.0 to 1.0).
 * Uses bilinear interpolation for smooth, precise readings.
 */
export function getAuthoritativeHeight(
  heightmap: Float32Array,
  width: number,
  height: number,
  u: number,
  v: number
): number {
  if (width < 1 || height < 1 || heightmap.length === 0) return 0;

  const clampedU = Math.max(0, Math.min(1, u));
  const clampedV = Math.max(0, Math.min(1, v));

  const cFloat = clampedU * (width - 1);
  const rFloat = clampedV * (height - 1);

  const c0 = Math.floor(cFloat);
  const c1 = Math.min(width - 1, c0 + 1);
  const r0 = Math.floor(rFloat);
  const r1 = Math.min(height - 1, r0 + 1);

  const fc = cFloat - c0;
  const fr = rFloat - r0;

  const h00 = heightmap[r0 * width + c0] ?? 0;
  const h01 = heightmap[r0 * width + c1] ?? 0;
  const h10 = heightmap[r1 * width + c0] ?? 0;
  const h11 = heightmap[r1 * width + c1] ?? 0;

  const top = h00 * (1 - fc) + h01 * fc;
  const bottom = h10 * (1 - fc) + h11 * fc;

  return top * (1 - fr) + bottom * fr;
}

/**
 * Compute slope in degrees across a Float32Array height grid using Sobel operators.
 * slope = arctan(sqrt(dz_dx^2 + dz_dy^2) / gsd) * (180 / pi)
 */
export function computeSlopeGrid(
  heightmap: Float32Array,
  width: number,
  height: number,
  gsdM: number
): Float32Array {
  const slopes = new Float32Array(width * height);
  const effectiveGsd = Math.max(1e-4, gsdM);
  const radToDeg = 180.0 / Math.PI;

  for (let r = 0; r < height; r++) {
    const rPrev = Math.max(0, r - 1);
    const rNext = Math.min(height - 1, r + 1);
    const dr = (rNext - rPrev) * effectiveGsd;

    for (let c = 0; c < width; c++) {
      const cPrev = Math.max(0, c - 1);
      const cNext = Math.min(width - 1, c + 1);
      const dc = (cNext - cPrev) * effectiveGsd;

      // Central difference approximation for horizontal & vertical elevation gradients
      const hL = heightmap[r * width + cPrev];
      const hR = heightmap[r * width + cNext];
      const dzDx = (hR - hL) / dc;

      const hT = heightmap[rPrev * width + c];
      const hB = heightmap[rNext * width + c];
      const dzDy = (hB - hT) / dr;

      const gradNorm = Math.sqrt(dzDx * dzDx + dzDy * dzDy);
      slopes[r * width + c] = Math.atan(gradNorm) * radToDeg;
    }
  }

  return slopes;
}

/**
 * Color ramp mapping slope angle in degrees to RGBA:
 * - 0 - 10 deg: Green (#22c55e)
 * - 10 - 25 deg: Yellow (#eab308)
 * - 25 - 40 deg: Orange (#f97316)
 * - > 40 deg: Red (#ef4444)
 */
export function getSlopeColorRamp(slopeDeg: number): [number, number, number, number] {
  if (slopeDeg < 10) {
    // Green
    return [34, 197, 94, 255];
  } else if (slopeDeg < 25) {
    // Yellow
    return [234, 179, 8, 255];
  } else if (slopeDeg <= 40) {
    // Orange
    return [249, 115, 22, 255];
  } else {
    // Red (> 40 degrees)
    return [239, 68, 68, 255];
  }
}
