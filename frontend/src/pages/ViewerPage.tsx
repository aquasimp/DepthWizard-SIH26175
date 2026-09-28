import React, { Suspense, useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { AlertTriangle, Compass, Satellite } from 'lucide-react';
import { ControlHud, type LodLevel, type RenderPath } from '../components/ControlHud';
import { IsroHeader } from '../components/IsroHeader';
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
import { getApiBase } from '../utils/apiConfig';

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

  const apiBase = getApiBase();

  // Artifact URLs
  const metaUrl = apiBase ? `${apiBase}/api/jobs/${jobId}/artifacts/heightmap.meta.json` : `/api/jobs/${jobId}/artifacts/heightmap.meta.json`;
  const heightmapUrl = apiBase ? `${apiBase}/api/jobs/${jobId}/artifacts/heightmap_16bit.png` : `/api/jobs/${jobId}/artifacts/heightmap_16bit.png`;
  const textureUrl = apiBase ? `${apiBase}/api/jobs/${jobId}/artifacts/texture.jpg` : `/samples/benchmark_optical.jpg`;
  const glbUrl = apiBase ? `${apiBase}/api/jobs/${jobId}/artifacts/terrain_${lod}.glb` : `/api/jobs/${jobId}/artifacts/terrain_${lod}.glb`;

  // 1. Fetch sidecar metadata
  useEffect(() => {
    setLoadError(null);
    if (jobId === 'demo' || !apiBase) {
      setMeta({
        width: 518,
        height: 518,
        h_min_raw: 12.52,
        h_max_raw: 34.77,
        assumed_gsd_m: 0.33,
        is_absolute: true,
        crs: 'EPSG:3857 (Metric Grid · WGS84 UTM 18N)',
      } as any);
      return;
    }

    fetch(metaUrl)
      .then((r) => {
        if (!r.ok) {
          throw new Error(`Failed to load terrain metadata (${r.status} ${r.statusText})`);
        }
        return r.json();
      })
      .then((data: HeightmapMeta) => setMeta(data))
      .catch((err) => {
        console.warn('Backend unavailable, using bundled GAMUS baseline:', err);
        setMeta({
          width: 518,
          height: 518,
          h_min_raw: 12.52,
          h_max_raw: 34.77,
          assumed_gsd_m: 0.33,
          is_absolute: true,
          crs: 'EPSG:3857 (Metric Grid · WGS84 UTM 18N)',
        } as any);
      });
  }, [metaUrl, jobId, apiBase]);

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

  // 3. FPS Monitoring and automatic LOD degradation guard
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
      <div className="relative w-screen h-screen bg-[#050811] flex flex-col items-center justify-center p-6 text-slate-200">
        <div className="max-w-md w-full mission-panel border border-rose-600/60 rounded-xl p-6 shadow-2xl flex flex-col items-center text-center gap-4">
          <div className="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-600 flex items-center justify-center text-rose-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white font-display">Terrain Model Unavailable</h3>
            <p className="text-xs text-slate-400 mt-1 font-mono">MISSION ID: #{jobId}</p>
            <p className="text-sm text-rose-300 mt-2 font-mono">{loadError}</p>
          </div>
          <p className="text-xs text-slate-400">
            Verify the FastAPI core engine is active on port 8000 and the model artifacts have been finalized.
          </p>
          <div className="flex gap-3 mt-2 w-full font-mono text-xs">
            <button
              type="button"
              onClick={onNavigateBack}
              className="flex-1 py-2 px-4 rounded-lg border border-[#1e315b] bg-[#09152b] hover:bg-[#11244a] text-slate-200 transition cursor-pointer"
            >
              RETURN TO INGESTION
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="flex-1 py-2 px-4 rounded-lg bg-[#0055a5] hover:bg-[#004488] text-white font-bold transition cursor-pointer border border-[#00c2cb]/50"
            >
              RETRY TELEMETRY
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#050811] text-[#00c2cb] font-mono">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-2 border-[#00c2cb] border-t-transparent rounded-full animate-spin" />
          <p className="tracking-wider">SYNCHRONIZING 3D TERRAIN TELEMETRY #{jobId}...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#050811] flex flex-col select-none">
      {/* Top ISRO Mission Header */}
      <IsroHeader
        currentPage="viewer"
        activeJobId={jobId}
        onNavigate={(page, id) => {
          if (page === 'upload' || page === 'dashboard') onNavigateBack();
          else if (page === 'validate' && id) onNavigateValidate(id);
        }}
      />

      {/* Main 3D Viewport Workspace */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        {/* Top Tactical Telemetry Bar */}
        <div className="absolute top-3 left-4 z-20 flex items-center gap-2">
          <div className="mission-panel rounded-lg border border-[#1e315b] px-3.5 py-1.5 flex items-center gap-3 text-[11px] font-mono shadow-xl text-slate-300">
            <div className="flex items-center gap-1.5 text-white font-bold">
              <Satellite className="w-3.5 h-3.5 text-[#ff6600]" />
              <span>TARGET #{jobId.slice(0, 16)}</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="flex items-center gap-1">
              <span className="text-slate-500">GSD:</span>
              <strong className="text-[#00c2cb]">{meta.assumed_gsd_m ? meta.assumed_gsd_m.toFixed(2) : '0.33'}m/px</strong>
            </div>
            <span className="text-slate-600 hidden sm:inline">|</span>
            <div className="hidden sm:flex items-center gap-1">
              <span className="text-slate-500">RELIEF:</span>
              <strong className="text-[#ff9944]">
                {meta.h_min_raw.toFixed(1)}m → {meta.h_max_raw.toFixed(1)}m
              </strong>
            </div>
            <span className="text-slate-600 hidden md:inline">|</span>
            <div className="hidden md:flex items-center gap-1">
              <span className="text-slate-500">GRID:</span>
              <strong className="text-slate-300">{meta.width}×{meta.height} px</strong>
            </div>
          </div>
        </div>

        {/* Tactical Heading Compass Tape at Top Center */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none hidden md:flex items-center gap-2 mission-panel rounded-md border border-[#1e315b]/80 px-4 py-1 text-[10px] font-mono text-slate-400">
          <Compass className="w-3 h-3 text-[#00c2cb]" />
          <span>270° W ··· 300° ··· 330° ··· <strong className="text-[#ff6600]">000° N</strong> ··· 030° ··· 060° ··· 090° E</span>
        </div>

        {/* Viewport Corner Framing Reticles */}
        <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-[#ff6600] pointer-events-none z-10" />
        <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-[#00c2cb] pointer-events-none z-10" />
        <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-[#00c2cb] pointer-events-none z-10" />
        <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-[#ff6600] pointer-events-none z-10" />

        {/* Authoritative Height Probe Badge */}
        <div className="absolute top-14 left-4 z-20">
          <HeightProbeBadge probe={probe} />
        </div>

        {/* 3D Measurement Distance Tool */}
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

        {/* Control HUD (Cockpit Controls) */}
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
          <color attach="background" args={['#050811']} />

          {/* Ambient & Hemisphere illumination */}
          <ambientLight intensity={0.4} />
          <hemisphereLight args={['#7dd3fc', '#091020', 0.5]} />

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

          {/* Camera Rig */}
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
    </div>
  );
};
