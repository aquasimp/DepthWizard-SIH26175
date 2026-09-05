import React, { useState } from 'react';
import {
  Camera,
  Compass,
  Download,
  Eye,
  Layers,
  Maximize2,
  Sliders,
  Sun,
  TrendingUp,
} from 'lucide-react';
import type { CameraMode } from '../viewer/CameraRig';

export type LodLevel = 'lod0' | 'lod1' | 'lod2';
export type RenderPath = 'DISPLACEMENT' | 'GLB';

interface ControlHudProps {
  cameraMode: CameraMode;
  onCameraModeChange: (mode: CameraMode) => void;
  renderPath: RenderPath;
  onRenderPathChange: (path: RenderPath) => void;
  lod: LodLevel;
  onLodChange: (lod: LodLevel) => void;
  zExag: number;
  onZExagChange: (val: number) => void;
  showSlope: boolean;
  onToggleSlope: () => void;
  wireframe: boolean;
  onToggleWireframe: () => void;
  sunAzimuth: number;
  onSunAzimuthChange: (val: number) => void;
  sunElevation: number;
  onSunElevationChange: (val: number) => void;
  fps: number;
  onDownloadDsm: () => void;
  onDownloadGlb: () => void;
  onNavigateValidate: () => void;
  isFlyMode: boolean;
}

export const ControlHud: React.FC<ControlHudProps> = ({
  cameraMode,
  onCameraModeChange,
  renderPath,
  onRenderPathChange,
  lod,
  onLodChange,
  zExag,
  onZExagChange,
  showSlope,
  onToggleSlope,
  wireframe,
  onToggleWireframe,
  sunAzimuth,
  onSunAzimuthChange,
  sunElevation,
  onSunElevationChange,
  fps,
  onDownloadDsm,
  onDownloadGlb,
  onNavigateValidate,
  isFlyMode,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      {/* Fly mode instructions banner */}
      {isFlyMode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 rounded-full border border-cyan-500/40 bg-slate-950/90 px-5 py-2 shadow-2xl backdrop-blur-md text-xs font-mono text-cyan-200 animate-pulse">
          <span className="font-bold text-cyan-400">FLY MODE:</span>
          <span>Click canvas to lock cursor | WASD to move | QE for altitude | Shift for 3x boost | ESC to release</span>
        </div>
      )}

      {/* Floating HUD Controls Panel */}
      <div className="absolute top-4 right-4 z-20 flex flex-col gap-2 min-w-[280px] max-w-[320px]">
        {/* Top Header Card */}
        <div className="flex items-center justify-between rounded-xl border border-slate-700/60 bg-slate-900/90 p-3 shadow-xl backdrop-blur-md text-slate-200">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold tracking-wider uppercase font-mono">
              Viewer HUD
            </span>
          </div>
          <div className="flex items-center gap-3">
            {/* FPS Counter badge */}
            <div
              className={`px-2 py-0.5 rounded font-mono text-[11px] font-bold border ${
                fps >= 50
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-700/60'
                  : fps >= 30
                  ? 'bg-amber-950/80 text-amber-400 border-amber-700/60'
                  : 'bg-rose-950/80 text-rose-400 border-rose-700/60'
              }`}
            >
              {fps} FPS
            </div>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="text-slate-400 hover:text-white transition p-1"
              title="Toggle HUD details"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {!collapsed && (
          <div className="flex flex-col gap-3 rounded-xl border border-slate-700/60 bg-slate-900/90 p-3.5 shadow-2xl backdrop-blur-md text-xs text-slate-300 max-h-[calc(100vh-100px)] overflow-y-auto">
            {/* Camera Mode Toggle */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Camera className="w-3 h-3 text-cyan-400" /> Camera Rig (1 / 2 / 3)
              </span>
              <div className="grid grid-cols-3 gap-1 p-0.5 rounded-lg bg-slate-950/60 border border-slate-800">
                {(['ORBIT', 'FLY', 'TOP'] as CameraMode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => onCameraModeChange(m)}
                    className={`py-1 rounded text-[11px] font-mono font-semibold transition ${
                      cameraMode === m
                        ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* Render Path Toggle */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Layers className="w-3 h-3 text-cyan-400" /> Render Path
              </span>
              <div className="grid grid-cols-2 gap-1 p-0.5 rounded-lg bg-slate-950/60 border border-slate-800">
                <button
                  onClick={() => onRenderPathChange('DISPLACEMENT')}
                  className={`py-1 rounded text-[10px] font-mono font-semibold transition ${
                    renderPath === 'DISPLACEMENT'
                      ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Shader Displace
                </button>
                <button
                  onClick={() => onRenderPathChange('GLB')}
                  className={`py-1 rounded text-[10px] font-mono font-semibold transition ${
                    renderPath === 'GLB'
                      ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  GLB Mesh LOD
                </button>
              </div>
            </div>

            {/* LOD Level Selector (active in GLB mode or mesh) */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Compass className="w-3 h-3 text-cyan-400" /> Mesh Resolution / LOD
              </span>
              <div className="grid grid-cols-3 gap-1 p-0.5 rounded-lg bg-slate-950/60 border border-slate-800 font-mono text-[11px]">
                {(
                  [
                    { id: 'lod0', label: 'LOD0 (512)' },
                    { id: 'lod1', label: 'LOD1 (256)' },
                    { id: 'lod2', label: 'LOD2 (128)' },
                  ] as const
                ).map((l) => (
                  <button
                    key={l.id}
                    onClick={() => onLodChange(l.id)}
                    className={`py-1 rounded font-semibold transition ${
                      lod === l.id
                        ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Vertical Exaggeration Slider */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-slate-400">Vertical Exaggeration:</span>
                <span className="font-bold text-cyan-400">{zExag.toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="5.0"
                step="0.1"
                value={zExag}
                onChange={(e) => onZExagChange(parseFloat(e.target.value))}
                className="accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
            </div>

            {/* Toggles: Slope Overlay & Wireframe */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={onToggleSlope}
                className={`py-1.5 px-2 rounded-lg border text-[11px] font-mono font-semibold flex items-center justify-center gap-1.5 transition ${
                  showSlope
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm'
                    : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" /> Slope Map
              </button>

              <button
                onClick={onToggleWireframe}
                className={`py-1.5 px-2 rounded-lg border text-[11px] font-mono font-semibold flex items-center justify-center gap-1.5 transition ${
                  wireframe
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-sm'
                    : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                <Eye className="w-3.5 h-3.5" /> Wireframe
              </button>
            </div>

            {/* Sun Lighting Controls */}
            <div className="flex flex-col gap-2 pt-1 border-t border-slate-800">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Sun className="w-3 h-3 text-amber-400" /> Sun Angle & Elevation
              </span>
              <div className="flex flex-col gap-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Azimuth:</span>
                  <span className="text-amber-300">{sunAzimuth}°</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="360"
                  step="5"
                  value={sunAzimuth}
                  onChange={(e) => onSunAzimuthChange(parseInt(e.target.value, 10))}
                  className="accent-amber-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              <div className="flex flex-col gap-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Elevation:</span>
                  <span className="text-amber-300">{sunElevation}°</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="90"
                  step="5"
                  value={sunElevation}
                  onChange={(e) => onSunElevationChange(parseInt(e.target.value, 10))}
                  className="accent-amber-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>
            </div>

            {/* Download and Navigation Action Buttons */}
            <div className="flex flex-col gap-1.5 pt-2 border-t border-slate-800">
              <button
                onClick={onDownloadDsm}
                className="w-full py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 font-mono text-[11px] font-semibold flex items-center justify-center gap-2 transition"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" /> Download DSM (GeoTIFF)
              </button>

              <button
                onClick={onDownloadGlb}
                className="w-full py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 font-mono text-[11px] font-semibold flex items-center justify-center gap-2 transition"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" /> Download 3D Mesh (.glb)
              </button>

              <button
                onClick={onNavigateValidate}
                className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold font-mono text-xs flex items-center justify-center gap-2 shadow-lg transition mt-1"
              >
                Validate Accuracy & Split-Screen →
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};
