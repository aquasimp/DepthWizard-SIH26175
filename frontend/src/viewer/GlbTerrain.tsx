import { useEffect } from 'react';
import * as THREE from 'three';
import { useGLTF } from '@react-three/drei';

interface GlbTerrainProps {
  glbUrl: string;
  zExag: number;
  wireframe: boolean;
  onPointerMove?: (u: number, v: number, point: THREE.Vector3) => void;
  onClick?: (u: number, v: number, point: THREE.Vector3) => void;
}

export function GlbTerrain({
  glbUrl,
  zExag,
  wireframe,
  onPointerMove,
  onClick,
}: GlbTerrainProps) {
  const { scene } = useGLTF(glbUrl);

  // Apply wireframe and vertical exaggeration
  useEffect(() => {
    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        if (mesh.material) {
          const mat = mesh.material as THREE.MeshStandardMaterial;
          mat.wireframe = wireframe;
          mat.needsUpdate = true;
        }
      }
    });
  }, [scene, wireframe]);

  return (
    <primitive
      object={scene}
      scale={[1.0, zExag, 1.0]}
      onPointerMove={(e: any) => {
        if (!onPointerMove) return;
        e.stopPropagation();
        if (e.uv) {
          onPointerMove(e.uv.x, e.uv.y, e.point);
        }
      }}
      onClick={(e: any) => {
        if (!onClick) return;
        e.stopPropagation();
        if (e.uv) {
          onClick(e.uv.x, e.uv.y, e.point);
        }
      }}
    />
  );
}
