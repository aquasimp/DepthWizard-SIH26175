import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { HeightmapMeta } from './utils/heightmap';

interface DisplacedTerrainProps {
  heightmapUrl: string;
  textureUrl: string;
  meta: HeightmapMeta;
  zExag: number;
  showSlope: boolean;
  wireframe: boolean;
  resolution?: number; // plane segments, default 512
  onPointerMove?: (u: number, v: number, point: THREE.Vector3) => void;
  onClick?: (u: number, v: number, point: THREE.Vector3) => void;
}

export function DisplacedTerrain({
  heightmapUrl,
  textureUrl,
  meta,
  zExag,
  showSlope,
  wireframe,
  resolution = 512,
  onPointerMove,
  onClick,
}: DisplacedTerrainProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);

  // Physical width and depth in metres
  const widthM = (meta.width - 1) * (meta.assumed_gsd_m || 0.33);
  const depthM = (meta.height - 1) * (meta.assumed_gsd_m || 0.33);

  // Load and configure the 16-bit PNG height texture
  const heightTexture = useMemo(() => {
    const loader = new THREE.TextureLoader();
    const tex = loader.load(
      heightmapUrl,
      (t) => {
        t.needsUpdate = true;
        if (materialRef.current) {
          materialRef.current.needsUpdate = true;
        }
      },
      undefined,
      (err) => {
        console.warn('[DisplacedTerrain] Heightmap texture load warning:', err);
      }
    );
    // CRITICAL: Configure LinearFilter and NoColorSpace to prevent sRGB-decoding distortion
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.colorSpace = THREE.NoColorSpace;
    tex.wrapS = THREE.ClampToEdgeWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.generateMipmaps = false;
    return tex;
  }, [heightmapUrl]);

  // Load base-color RGB texture
  const baseTexture = useMemo(() => {
    const loader = new THREE.TextureLoader();
    const tex = loader.load(
      textureUrl,
      (t) => {
        t.needsUpdate = true;
        if (materialRef.current) {
          materialRef.current.map = t;
          materialRef.current.needsUpdate = true;
        }
      },
      undefined,
      (err) => {
        console.warn('[DisplacedTerrain] Base texture load warning:', err);
      }
    );
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.wrapS = THREE.ClampToEdgeWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, [textureUrl]);

  const uniformsRef = useRef({
    uHeightMap: { value: heightTexture },
    uHMin: { value: meta.h_min_raw },
    uHMax: { value: meta.h_max_raw },
    uZExag: { value: zExag },
    uShowSlope: { value: showSlope ? 1.0 : 0.0 },
    uGsd: { value: meta.assumed_gsd_m || 0.33 },
    uTexelSize: { value: new THREE.Vector2(1.0 / meta.width, 1.0 / meta.height) },
  });

  // Keep static inputs in sync
  useEffect(() => {
    uniformsRef.current.uHeightMap.value = heightTexture;
    uniformsRef.current.uHMin.value = meta.h_min_raw;
    uniformsRef.current.uHMax.value = meta.h_max_raw;
    uniformsRef.current.uGsd.value = meta.assumed_gsd_m || 0.33;
    uniformsRef.current.uTexelSize.value.set(1.0 / meta.width, 1.0 / meta.height);
  }, [heightTexture, meta]);

  // Update dynamic uniform values continuously
  useEffect(() => {
    uniformsRef.current.uZExag.value = zExag;
    uniformsRef.current.uShowSlope.value = showSlope ? 1.0 : 0.0;
  }, [zExag, showSlope]);

  // Sync wireframe updates to material
  useEffect(() => {
    if (materialRef.current) {
      materialRef.current.wireframe = wireframe;
      materialRef.current.needsUpdate = true;
    }
  }, [wireframe]);

  // Custom vertex displacement and procedural slope shading via onBeforeCompile
  const onBeforeCompile = useMemo(
    () => (shader: THREE.WebGLProgramParametersWithUniforms) => {
      shader.uniforms.uHeightMap = uniformsRef.current.uHeightMap;
      shader.uniforms.uHMin = uniformsRef.current.uHMin;
      shader.uniforms.uHMax = uniformsRef.current.uHMax;
      shader.uniforms.uZExag = uniformsRef.current.uZExag;
      shader.uniforms.uShowSlope = uniformsRef.current.uShowSlope;
      shader.uniforms.uGsd = uniformsRef.current.uGsd;
      shader.uniforms.uTexelSize = uniformsRef.current.uTexelSize;

      // Inject custom vertex shader displacement logic
      shader.vertexShader = `
        uniform sampler2D uHeightMap;
        uniform float uHMin;
        uniform float uHMax;
        uniform float uZExag;
        uniform float uGsd;
        uniform vec2 uTexelSize;
        varying vec2 vTerrainUv;
        varying float vSlopeDeg;

        ${shader.vertexShader}
      `;

      shader.vertexShader = shader.vertexShader.replace(
        '#include <beginnormal_vertex>',
        `
        #include <beginnormal_vertex>

        // Calculate elevation gradient for procedural slope & normals
        float hL = uHMin + texture2D(uHeightMap, uv - vec2(uTexelSize.x, 0.0)).r * (uHMax - uHMin);
        float hR = uHMin + texture2D(uHeightMap, uv + vec2(uTexelSize.x, 0.0)).r * (uHMax - uHMin);
        float hD = uHMin + texture2D(uHeightMap, uv - vec2(0.0, uTexelSize.y)).r * (uHMax - uHMin);
        float hU = uHMin + texture2D(uHeightMap, uv + vec2(0.0, uTexelSize.y)).r * (uHMax - uHMin);

        float dzDx = (hR - hL) / (2.0 * max(uGsd, 0.001));
        float dzDy = (hU - hD) / (2.0 * max(uGsd, 0.001));
        objectNormal = normalize(vec3(-dzDx * uZExag, -dzDy * uZExag, 1.0));

        // Slope calculation in degrees
        float grad = sqrt(dzDx * dzDx + dzDy * dzDy);
        vSlopeDeg = atan(grad) * 57.2957795;
        `
      );

      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        `
        #include <begin_vertex>

        vTerrainUv = uv;

        // Sample normalized height [0.0, 1.0]
        float rawNorm = texture2D(uHeightMap, uv).r;
        // Decode metric elevation via sidecar formula
        float elevM = uHMin + rawNorm * (uHMax - uHMin);

        // Displace along local +Z (which corresponds to World +Y UP after rotation -PI/2 on X)
        transformed.z = elevM * uZExag;
        `
      );

      // Inject custom fragment shader slope coloring
      shader.fragmentShader = `
        uniform float uShowSlope;
        varying vec2 vTerrainUv;
        varying float vSlopeDeg;

        vec4 getSlopeColor(float deg) {
          if (deg < 10.0) return vec4(0.133, 0.773, 0.369, 1.0); // Green
          if (deg < 25.0) return vec4(0.918, 0.702, 0.031, 1.0); // Yellow
          if (deg <= 40.0) return vec4(0.976, 0.451, 0.086, 1.0); // Orange
          return vec4(0.937, 0.267, 0.267, 1.0); // Red > 40 deg
        }

        ${shader.fragmentShader}
      `;

      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <dithering_fragment>',
        `
        #include <dithering_fragment>
        if (uShowSlope > 0.5) {
          vec4 slopeRamp = getSlopeColor(vSlopeDeg);
          gl_FragColor = mix(gl_FragColor, slopeRamp, 0.65);
        }
        `
      );
    },
    []
  );

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 2, 0, 0]} // Rotate plane to lie on XZ with Y-UP
      position={[widthM / 2, 0, depthM / 2]}
      receiveShadow
      castShadow
      onPointerMove={(e) => {
        if (!onPointerMove) return;
        e.stopPropagation();
        if (e.uv) {
          onPointerMove(e.uv.x, 1.0 - e.uv.y, e.point);
        }
      }}
      onClick={(e) => {
        if (!onClick) return;
        e.stopPropagation();
        if (e.uv) {
          onClick(e.uv.x, 1.0 - e.uv.y, e.point);
        }
      }}
    >
      <planeGeometry args={[widthM, depthM, resolution, resolution]} />
      <meshStandardMaterial
        ref={materialRef}
        map={baseTexture}
        wireframe={wireframe}
        roughness={0.8}
        metalness={0.1}
        onBeforeCompile={onBeforeCompile}
      />
    </mesh>
  );
}
