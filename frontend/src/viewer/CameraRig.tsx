import { useEffect } from 'react';
import * as THREE from 'three';
import { OrbitControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { FlyControls } from './FlyControls';
import type { HeightmapMeta } from './utils/heightmap';

export type CameraMode = 'ORBIT' | 'FLY' | 'TOP';

interface CameraRigProps {
  mode: CameraMode;
  onModeChange: (mode: CameraMode) => void;
  meta: HeightmapMeta;
  zExag: number;
  cpuHeightmap: Float32Array | null;
}

export function CameraRig({
  mode,
  onModeChange,
  meta,
  zExag,
  cpuHeightmap,
}: CameraRigProps) {
  const { camera } = useThree();
  const widthM = (meta.width - 1) * (meta.assumed_gsd_m || 0.33);
  const depthM = (meta.height - 1) * (meta.assumed_gsd_m || 0.33);
  const centerX = widthM / 2;
  const centerZ = depthM / 2;
  const maxDim = Math.max(widthM, depthM, 100);

  // Number keys (1, 2, 3) toggle camera mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === '1') onModeChange('ORBIT');
      if (e.key === '2') onModeChange('FLY');
      if (e.key === '3') onModeChange('TOP');
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onModeChange]);

  // Adjust camera position when switching modes
  useEffect(() => {
    if (mode === 'ORBIT') {
      camera.position.set(centerX, maxDim * 0.6, depthM * 1.2);
      camera.lookAt(centerX, 0, centerZ);
      camera.up.set(0, 1, 0);
    } else if (mode === 'FLY') {
      camera.position.set(centerX, maxDim * 0.2, centerZ);
      camera.lookAt(centerX, maxDim * 0.1, centerZ - 50);
      camera.up.set(0, 1, 0);
    } else if (mode === 'TOP') {
      // Direct nadir orthographic look looking down from +Y
      camera.position.set(centerX, maxDim * 1.5, centerZ);
      camera.lookAt(centerX, 0, centerZ);
      // In satellite imaging, North (top of image) corresponds to -Z (r=0)
      camera.up.set(0, 0, -1);
    }
    camera.updateProjectionMatrix();
  }, [mode, centerX, centerZ, depthM, maxDim, camera]);

  if (mode === 'ORBIT') {
    return (
      <OrbitControls
        target={[centerX, 0, centerZ]}
        maxPolarAngle={Math.PI / 2 - 0.05} // Clamp polar angle to prevent camera going below terrain
        minDistance={5}
        maxDistance={maxDim * 3.5}
        enableDamping
        dampingFactor={0.05}
      />
    );
  }

  if (mode === 'FLY') {
    return <FlyControls cpuHeightmap={cpuHeightmap} meta={meta} zExag={zExag} />;
  }

  if (mode === 'TOP') {
    return (
      <OrbitControls
        target={[centerX, 0, centerZ]}
        enableRotate={false} // Lock rotation in TOP mode for perfect nadir alignment
        enablePan
        enableZoom
        mouseButtons={{
          LEFT: THREE.MOUSE.PAN,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.PAN,
        }}
      />
    );
  }

  return null;
}
