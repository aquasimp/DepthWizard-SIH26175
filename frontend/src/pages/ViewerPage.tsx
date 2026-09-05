import { Suspense, useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { ControlHud, type LodLevel, type RenderPath } from '../components/ControlHud';
import { CameraRig, type CameraMode } from '../viewer/CameraRig';
import { DisplacedTerrain } from '../viewer/DisplacedTerrain';
import { GlbTerrain } from '../viewer/GlbTerrain';
import { HeightProbeBadge, type ProbeData } from '../viewer/HeightProbe';
import { type MeasurePoint, MeasureToolCard, MeasureToolVisualizer } from '../viewer/MeasureTool';
import {
  decodeHeightmapFromPixels,
  getAuthoritativeHeight,
  type HeightmapMeta,
} from '../viewer/utils/heightmap';

interface ViewerPageProps {
  jobId: string;
  onNavigateBack: () => void;
  onNavigateValidate: (jobId: string) => void;
}

export const ViewerPage: React.FC<ViewerPageProps> = ({
  jobId,
  onNavigateBack,
  onNavigateValidate,
}) => {
  // State
  const [meta, setMeta] = useState<HeightmapMeta | null>(null);
  const [cpuHeightmap, setCpuHeightmap] = useState<Float32Array | null>(null);
  const [cameraMode, setCameraMode] = useState<CameraMode>('ORBIT');
  const [renderPath, setRenderPath] = useState<RenderPath>('DISPLACEMENT');
  const [lod, setLod] = useState<LodLevel>('lod0');
  const [zExag, setZExag] = useState(1.0);
  const [showSlope, setShowSlope] = useState(false);
  const [wireframe, setWireframe] = useState(false);
  const [sunAzimuth, setSunAzimuth] = useState(135);
  const [sunElevation, setSunElevation] = useState(45);
  const [fps, setFps] = useState(60);

  // Height Probe & Measure Tool states
  const [probe, setProbe] = useState<ProbeData | null>(null);
  const [measureActive, setMeasureActive] = useState(false);
  const [pointA, setPointA] = useState<MeasurePoint | null>(null);
  const [pointB, setPointB] = useState<MeasurePoint | null>(null);

  // Artifact URLs
  const metaUrl = `/api/jobs/${jobId}/artifacts/heightmap.meta.json`;
  const heightmapUrl = `/api/jobs/${jobId}/artifacts/heightmap_16bit.png`;
  const textureUrl = `/api/jobs/${jobId}/artifacts/texture.jpg`;
  const glbUrl = `/api/jobs/${jobId}/artifacts/terrain_${lod}.glb`;

  // 1. Fetch sidecar metadata
  useEffect(() => {
    fetch(metaUrl)
      .then((r) => r.json())
      .then((data: HeightmapMeta) => setMeta(data))
      .catch((err) => console.error('Failed to load heightmap metadata:', err));
  }, [metaUrl]);

  // 2. Decode authoritative CPU Float32Array from 16-bit PNG via hidden 2D canvas
  useEffect(() => {
    if (!meta) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.drawImage(img, 0, 0);
      const imgData = ctx.getImageData(0, 0, img.width, img.height);
      const data = imgData.data; // RGBA uint8
      const totalPx = img.width * img.height;
      const u16Array = new Uint16Array(totalPx);

      // In PNG 16-bit, Red & Green channels contain the high and low 8 bits
      for (let i = 0; i < totalPx; i++) {
        const r = data[i * 4];
        const g = data[i * 4 + 1];
        u16Array[i] = (r << 8) | g;
      }

      const decoded = decodeHeightmapFromPixels(
        u16Array,
        img.width,
        img.height,
        meta.h_min_raw,
        meta.h_max_raw
      );
      setCpuHeightmap(decoded);
    };
    img.src = heightmapUrl;
  }, [meta, heightmapUrl]);

  // 3. FPS Monitoring and automatic LOD degradation guard (< 30 FPS for > 2s downgrades to LOD1)
  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let lowFpsDuration = 0;

    const loop = () => {
      frameCount++;
      const now = performance.now();
      const elapsed = now - lastTime;

      if (elapsed >= 1000) {
        const currentFps = Math.round((frameCount * 1000) / elapsed);
        setFps(currentFps);
        frameCount = 0;
        lastTime = now;

        if (currentFps < 30) {
          lowFpsDuration += 1;
          if (lowFpsDuration >= 2 && lod === 'lod0') {
            console.warn('FPS dropped below 30 for >2s. Auto-downgrading to LOD1 for smooth performance.');
            setLod('lod1');
            lowFpsDuration = 0;
          }
        } else {
          lowFpsDuration = 0;
        }
      }
      requestAnimationFrame(loop);
    };

    const id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [lod]);

  // Calculate sun light position from azimuth and elevation
  const sunPosition = useMemo(() => {
    const azRad = (sunAzimuth * Math.PI) / 180;
    const elRad = (sunElevation * Math.PI) / 180;
    const dist = 500;
    const x = dist * Math.cos(elRad) * Math.sin(azRad);
    const y = dist * Math.sin(elRad);
    const z = dist * Math.cos(elRad) * Math.cos(azRad);
    return [x, y, z] as [number, number, number];
  }, [sunAzimuth, sunElevation]);

  // Handle pointer interactions on terrain
  const handlePointerMove = (u: number, v: number, point: THREE.Vector3) => {
    if (!cpuHeightmap || !meta) return;
    const elev = getAuthoritativeHeight(cpuHeightmap, meta.width, meta.height, u, v);
    setProbe({
      u,
      v,
      worldX: point.x,
      worldY: point.y,
      worldZ: point.z,
      elevationM: elev,
      isAbsolute: meta.is_absolute ?? true,
      units: meta.units ?? 'metres',
    });
  };

  const handleClick = (u: number, v: number, point: THREE.Vector3) => {
    if (!measureActive || !cpuHeightmap || !meta) return;
    const elev = getAuthoritativeHeight(cpuHeightmap, meta.width, meta.height, u, v);
    const mp: MeasurePoint = {
      u,
      v,
      worldPoint: point.clone(),
      elevationM: elev,
    };

    if (!pointA) {
      setPointA(mp);
    } else if (!pointB) {
      setPointB(mp);
    } else {
      // Reset and set point A
      setPointA(mp);
      setPointB(null);
    }
  };

  const handleDownloadDsm = () => {
    const a = document.createElement('a');
    a.href = `/api/jobs/${jobId}/artifacts/dsm.tif`;
    a.download = `dsm_${jobId}.tif`;
    a.click();
  };

  const handleDownloadGlb = () => {
    const a = document.createElement('a');
    a.href = `/api/jobs/${jobId}/artifacts/terrain_${lod}.glb`;
    a.download = `terrain_${jobId}_${lod}.glb`;
    a.click();
  };

  if (!meta) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950 text-cyan-400 font-mono">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <p>Loading Terrain Model #{jobId}...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-slate-950 select-none">
      {/* Back button */}
      <button
        onClick={onNavigateBack}
        className="absolute top-4 left-4 z-20 px-3 py-1.5 rounded-lg border border-slate-700/60 bg-slate-900/80 text-xs font-mono text-slate-300 hover:text-white backdrop-blur-md transition shadow-lg flex items-center gap-1.5"
      >
        ← Jobs Overview
      </button>

      {/* Authoritative Height Probe Badge */}
      <div className="absolute top-16 left-4 z-20">
        <HeightProbeBadge probe={probe} />
      </div>

      {/* Measure Tool Card */}
      <div className="absolute bottom-4 left-4 z-20">
        <MeasureToolCard
          pointA={pointA}
          pointB={pointB}
          active={measureActive}
          onToggleActive={() => {
            setMeasureActive(!measureActive);
            if (measureActive) {
              setPointA(null);
              setPointB(null);
            }
          }}
          onClear={() => {
            setPointA(null);
            setPointB(null);
          }}
        />
      </div>

      {/* Control HUD */}
      <ControlHud
        cameraMode={cameraMode}
        onCameraModeChange={setCameraMode}
        renderPath={renderPath}
        onRenderPathChange={setRenderPath}
        lod={lod}
        onLodChange={setLod}
        zExag={zExag}
        onZExagChange={setZExag}
        showSlope={showSlope}
        onToggleSlope={() => setShowSlope(!showSlope)}
        wireframe={wireframe}
        onToggleWireframe={() => setWireframe(!wireframe)}
        sunAzimuth={sunAzimuth}
        onSunAzimuthChange={setSunAzimuth}
        sunElevation={sunElevation}
        onSunElevationChange={setSunElevation}
        fps={fps}
        onDownloadDsm={handleDownloadDsm}
        onDownloadGlb={handleDownloadGlb}
        onNavigateValidate={() => onNavigateValidate(jobId)}
        isFlyMode={cameraMode === 'FLY'}
      />

      {/* 3D WebGL Canvas */}
      <Canvas
        shadows
        camera={{ position: [200, 150, 200], fov: 45, near: 0.5, far: 5000 }}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <color attach="background" args={['#020617']} />

        {/* Ambient & Hemisphere illumination */}
        <ambientLight intensity={0.4} />
        <hemisphereLight
          args={['#bae6fd', '#0f172a', 0.5]}
        />

        {/* Dynamic Sun Lighting with Real-time Shadows */}
        <directionalLight
          position={sunPosition}
          intensity={1.5}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-near={10}
          shadow-camera-far={2000}
          shadow-camera-left={-400}
          shadow-camera-right={400}
          shadow-camera-top={400}
          shadow-camera-bottom={-400}
        />

        {/* Camera Rig (ORBIT, FLY with collision, TOP with nadir) */}
        <CameraRig
          mode={cameraMode}
          onModeChange={setCameraMode}
          meta={meta}
          zExag={zExag}
          cpuHeightmap={cpuHeightmap}
        />

        {/* 3D Terrain Render Pathways */}
        <Suspense fallback={null}>
          {renderPath === 'DISPLACEMENT' ? (
            <DisplacedTerrain
              heightmapUrl={heightmapUrl}
              textureUrl={textureUrl}
              meta={meta}
              zExag={zExag}
              showSlope={showSlope}
              wireframe={wireframe}
              onPointerMove={handlePointerMove}
              onClick={handleClick}
            />
          ) : (
            <GlbTerrain
              glbUrl={glbUrl}
              zExag={zExag}
              wireframe={wireframe}
              onPointerMove={handlePointerMove}
              onClick={handleClick}
            />
          )}

          {/* 3D Measurement line visualization */}
          <MeasureToolVisualizer pointA={pointA} pointB={pointB} />
        </Suspense>
      </Canvas>
    </div>
  );
};
