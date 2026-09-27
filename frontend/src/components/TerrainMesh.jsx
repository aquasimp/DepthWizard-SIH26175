import React, { useMemo } from 'react';
import * as THREE from 'three';

/**
 * TerrainMesh: Converts metric DSM elevation grid into 3D vertices, triangles, and textures.
 * Formula: Each vertex (x, y, z) corresponds to real-world coordinates:
 * x = (col / (cols - 1) - 0.5) * width_meters
 * z = (row / (rows - 1) - 0.5) * length_meters
 * y = elevation_meters * verticalExaggeration
 */
export function createTerrainGeometry({
  heights,
  rows,
  cols,
  planeSize = 200,
  aspectRatio = 1.0,
  verticalExaggeration = 1.0,
}) {
  const ar = Math.max(0.2, Math.min(5.0, Number(aspectRatio) || 1.0));
  const planeWidth = ar >= 1.0 ? planeSize : planeSize * ar;
  const planeHeight = ar >= 1.0 ? planeSize / ar : planeSize;

  const geometry = new THREE.PlaneGeometry(
    planeWidth,
    planeHeight,
    cols - 1,
    rows - 1
  );
  geometry.rotateX(-Math.PI / 2); // Orient horizontal (XZ plane)

  const posAttr = geometry.attributes.position;
  const numVertices = posAttr.count;

  let minElev = Infinity;
  let maxElev = -Infinity;

  for (let i = 0; i < numVertices; i++) {
    const h = (heights && i < heights.length) ? heights[i] : 0;
    if (h < minElev) minElev = h;
    if (h > maxElev) maxElev = h;
  }

  if (minElev === Infinity) minElev = 0;
  if (maxElev === -Infinity) maxElev = 0;

  // Offset base by minElev so that terrain datum sits cleanly on ground grid (Y >= 0)
  const baseOffset = minElev;

  for (let i = 0; i < numVertices; i++) {
    const h = (heights && i < heights.length) ? heights[i] : 0;
    const relH = Math.max(0, h - baseOffset);
    posAttr.setY(i, relH * verticalExaggeration);
  }

  geometry.computeVertexNormals();

  // Create UV texture coordinates matching satellite image mapping
  const uvAttr = geometry.attributes.uv;
  for (let i = 0; i < uvAttr.count; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const u = col / (cols - 1);
    const v = 1.0 - (row / (rows - 1)); // Flip vertical to match optical image raster order
    uvAttr.setXY(i, u, v);
  }

  return {
    geometry,
    minElevation: minElev,
    maxElevation: maxElev,
    baseOffset,
    planeWidth,
    planeHeight,
  };
}

export function createElevationColorTexture(heights, rows, cols, minH, maxH, colormap = 'terrain') {
  const canvas = document.createElement('canvas');
  canvas.width = cols;
  canvas.height = rows;
  const ctx = canvas.getContext('2d');
  const imgData = ctx.createImageData(cols, rows);
  const data = imgData.data;

  const range = Math.max(maxH - minH, 0.001);

  for (let i = 0; i < heights.length; i++) {
    const h = heights[i];
    const norm = Math.max(0, Math.min(1, (h - minH) / range));

    // Color ramp
    let r = 0, g = 0, b = 0;
    if (colormap === 'terrain') {
      // Natural terrain: blue/deep valley -> green lowlands -> yellow midlands -> brown hills -> white peaks
      if (norm < 0.2) {
        r = 50 + norm * 250; g = 120 + norm * 400; b = 70;
      } else if (norm < 0.5) {
        r = 100 + (norm - 0.2) * 400; g = 200 + (norm - 0.2) * 100; b = 80;
      } else if (norm < 0.8) {
        r = 220 + (norm - 0.5) * 100; g = 200 - (norm - 0.5) * 200; b = 80;
      } else {
        r = 240 + (norm - 0.8) * 75; g = 240 + (norm - 0.8) * 75; b = 250;
      }
    } else {
      // Viridis-style
      r = Math.floor(norm * 255);
      g = Math.floor((1 - Math.abs(norm - 0.5) * 2) * 255);
      b = Math.floor((1 - norm) * 255);
    }

    const idx = i * 4;
    data[idx] = Math.min(255, Math.max(0, Math.floor(r)));
    data[idx + 1] = Math.min(255, Math.max(0, Math.floor(g)));
    data[idx + 2] = Math.min(255, Math.max(0, Math.floor(b)));
    data[idx + 3] = 255;
  }

  ctx.putImageData(imgData, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return texture;
}

export function createSlopeColorTexture(heights, rows, cols, planeSize = 200) {
  const canvas = document.createElement('canvas');
  canvas.width = cols;
  canvas.height = rows;
  const ctx = canvas.getContext('2d');
  const imgData = ctx.createImageData(cols, rows);
  const data = imgData.data;

  const dxM = planeSize / Math.max(1, cols - 1);
  const dzM = planeSize / Math.max(1, rows - 1);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const cPrev = Math.max(0, c - 1);
      const cNext = Math.min(cols - 1, c + 1);
      const rPrev = Math.max(0, r - 1);
      const rNext = Math.min(rows - 1, r + 1);

      const zLeft = heights[r * cols + cPrev];
      const zRight = heights[r * cols + cNext];
      const zUp = heights[rPrev * cols + c];
      const zDown = heights[rNext * cols + c];

      const dz_dx = (zRight - zLeft) / Math.max(1e-4, (cNext - cPrev) * dxM);
      const dz_dz = (zDown - zUp) / Math.max(1e-4, (rNext - rPrev) * dzM);

      const gradientMag = Math.sqrt(dz_dx * dz_dx + dz_dz * dz_dz);
      const slopeDeg = Math.atan(gradientMag) * (180.0 / Math.PI);

      // Color mapping:
      // < 5 deg: Flat (Green)
      // 5-15 deg: Gentle (Cyan/Teal)
      // 15-30 deg: Moderate (Amber/Yellow)
      // > 30 deg: Steep (Red)
      let red = 34, green = 197, blue = 94;
      if (slopeDeg < 5) {
        red = 34; green = 197; blue = 94; // Flat: green
      } else if (slopeDeg < 15) {
        red = 56; green = 189; blue = 248; // Gentle: cyan
      } else if (slopeDeg < 30) {
        red = 245; green = 158; blue = 11; // Moderate: amber
      } else {
        red = 239; green = 68; blue = 68; // Steep: red
      }

      const pIdx = idx * 4;
      data[pIdx] = red;
      data[pIdx + 1] = green;
      data[pIdx + 2] = blue;
      data[pIdx + 3] = 255;
    }
  }

  ctx.putImageData(imgData, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return texture;
}

