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
  const [loadError, setLoadError] = useState<string | null>(null);

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
    setLoadError(null);
    fetch(metaUrl)
      .then((r) => {
        if (!r.ok) {
          throw new Error(`Failed to load terrain metadata (${r.status} ${r.statusText})`);
        }
        return r.json();
      })
      .then((data: HeightmapMeta) => setMeta(data))
      .catch((err) => {
        console.error('Failed to load heightmap metadata:', err);
        setLoadError(err.message || 'Failed to connect to backend server.');
      });
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

  if (loadError) {
    return (
      <div className="relative w-screen h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-slate-200">
        <div className="max-w-md w-full bg-slate-900/90 border border-red-500/40 rounded-2xl p-6 shadow-2xl backdrop-blur-md flex flex-col items-center text-center gap-4">
          <div className="w-12 h-12 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Terrain Model Unavailable</h3>
            <p className="text-xs text-slate-400 mt-1 font-mono">Job ID: {jobId}</p>
            <p className="text-sm text-red-300/90 mt-2">{loadError}</p>
          </div>
          <p className="text-xs text-slate-400">
            Ensure the FastAPI backend server is running on port 8000 and that this job has finished processing.
          </p>
          <div className="flex gap-3 mt-2 w-full">
            <button
              onClick={onNavigateBack}
              className="flex-1 py-2 px-4 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-sm font-medium transition cursor-pointer"
            >
              Back to Home
            </button>
            <button
              onClick={() => window.location.reload()}
              className="flex-1 py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-sm font-medium transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

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
