import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { PointerLockControls as PointerLockControlsImpl } from 'three-stdlib';
import { getAuthoritativeHeight, type HeightmapMeta } from './utils/heightmap';

interface FlyControlsProps {
  cpuHeightmap: Float32Array | null;
  meta: HeightmapMeta;
  zExag: number;
}

export function FlyControls({ cpuHeightmap, meta, zExag }: FlyControlsProps) {
  const { camera, gl } = useThree();
  const controlsRef = useRef<PointerLockControlsImpl | null>(null);

  // Key tracking
  const keys = useRef<{ [key: string]: boolean }>({
    KeyW: false,
    KeyA: false,
    KeyS: false,
    KeyD: false,
    KeyQ: false,
    KeyE: false,
    ShiftLeft: false,
    ShiftRight: false,
  });

  const widthM = (meta.width - 1) * (meta.assumed_gsd_m || 0.33);
  const depthM = (meta.height - 1) * (meta.assumed_gsd_m || 0.33);

  useEffect(() => {
    const controls = new PointerLockControlsImpl(camera, gl.domElement);
    controlsRef.current = controls;

    const onKeyDown = (e: KeyboardEvent) => {
      if (keys.current[e.code] !== undefined) {
        keys.current[e.code] = true;
      }
    };

    const onKeyUp = (e: KeyboardEvent) => {
      if (keys.current[e.code] !== undefined) {
        keys.current[e.code] = false;
      }
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      controls.dispose();
    };
  }, [camera, gl]);

  useFrame((_, delta) => {
    if (!controlsRef.current || !controlsRef.current.isLocked) return;

    const k = keys.current;
    const isSprint = k.ShiftLeft || k.ShiftRight;
    const baseSpeed = 25.0 * (isSprint ? 3.0 : 1.0); // m/s
    const moveDist = baseSpeed * delta;

    // Movement vectors
    if (k.KeyW) controlsRef.current.moveForward(moveDist);
    if (k.KeyS) controlsRef.current.moveForward(-moveDist);
    if (k.KeyA) controlsRef.current.moveRight(-moveDist);
    if (k.KeyD) controlsRef.current.moveRight(moveDist);

    // Altitude controls (Q: descend, E: ascend)
    if (k.KeyE) camera.position.y += moveDist;
    if (k.KeyQ) camera.position.y -= moveDist;

    // Terrain collision clamp: camera height >= ground_height + 2.0m
    if (cpuHeightmap && widthM > 0 && depthM > 0) {
      const u = camera.position.x / widthM;
      const v = camera.position.z / depthM;

      if (u >= 0 && u <= 1 && v >= 0 && v <= 1) {
        const groundHeightM = getAuthoritativeHeight(
          cpuHeightmap,
          meta.width,
          meta.height,
          u,
          v
        );
        const minCamY = groundHeightM * zExag + 2.0; // 2.0m collision buffer
        if (camera.position.y < minCamY) {
          camera.position.y = minCamY;
        }
      }
    }
  });

  return null;
}
