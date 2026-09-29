import React, { useState } from 'react';
import {
  Camera,
  Compass,
  Download,
  Eye,
  Layers,
  Maximize2,
  Minimize2,
  Scale,
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
  isEmbedded?: boolean;
  autoTour?: boolean;
  onToggleAutoTour?: () => void;
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
  isEmbedded = false,
  autoTour = false,
  onToggleAutoTour,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      {/* Fly mode tactical instructions banner */}
      {isFlyMode && (
        <div className={`absolute ${isEmbedded ? 'top-14' : 'top-16'} left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 rounded-lg border border-[#00c2cb]/60 bg-[#061022]/95 px-5 py-2 shadow-2xl backdrop-blur-md text-xs font-mono text-slate-100 animate-pulse`}>
          <span className="font-bold text-[#ff9944]">TACTICAL FLIGHT COCKPIT:</span>
          <span>Click canvas to lock crosshair · WASD move · QE altitude · Shift 3× boost · ESC release</span>
        </div>
      )}

      {/* Floating ISRO Telemetry HUD Controls Panel */}
      <div className={`absolute ${isEmbedded ? 'top-3 right-3 max-h-[calc(100%-24px)]' : 'top-20 right-4 max-h-[calc(100vh-95px)]'} z-20 flex flex-col gap-2 min-w-[275px] max-w-[310px] pr-0.5 pointer-events-auto select-none`}>
        {/* Top Header Card */}
        <div className="rounded-lg border border-[#1e315b] bg-[#060c18]/95 backdrop-blur-xl p-3 shadow-2xl flex items-center justify-between text-slate-200">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-[#ff6600]" />
            <span className="text-xs font-bold tracking-wider uppercase font-mono text-white">
              COCKPIT CONTROLS HUD
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            {/* FPS Counter badge */}
            <div
              className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${
                fps >= 50
                  ? 'bg-emerald-950/90 text-emerald-400 border-emerald-700/60'
                  : fps >= 30
                  ? 'bg-amber-950/90 text-amber-400 border-amber-700/60'
                  : 'bg-rose-950/90 text-rose-400 border-rose-700/60'
              }`}
            >
              {fps} FPS
            </div>

            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              className="text-slate-400 hover:text-white transition p-1 cursor-pointer"
              title="Toggle HUD details"
            >
              {collapsed ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {!collapsed && (
          <div className={`rounded-lg border border-[#1e315b] bg-[#060c18]/95 backdrop-blur-xl p-3.5 shadow-2xl flex flex-col gap-3 text-xs text-slate-300 ${isEmbedded ? 'max-h-[500px]' : 'max-h-[calc(100vh-140px)]'} overflow-y-auto scrollbar-thin scrollbar-thumb-[#1e315b]`}>
            {/* Camera Mode Rig */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Camera className="w-3 h-3 text-[#00c2cb]" /> FLIGHT CAMERA RIG
                </span>
                <span className="text-slate-500">[KEY 1/2/3]</span>
              </span>
              <div className="grid grid-cols-3 gap-1 p-0.5 rounded-lg bg-[#070e1d] border border-[#1e315b]">
                {(['ORBIT', 'FLY', 'TOP'] as CameraMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => onCameraModeChange(m)}
                    className={`py-1 rounded text-[11px] font-mono font-semibold transition cursor-pointer ${
                      cameraMode === m
                        ? 'bg-[#0055a5] text-white shadow font-bold border border-[#00c2cb]/50'
                        : 'text-slate-400 hover:text-white hover:bg-[#0d1b38]'
                    }`}
                  >
                    {m === 'ORBIT' ? 'ORBIT 360' : m === 'FLY' ? 'TACTICAL' : 'NADIR 2D'}
                  </button>
                ))}
              </div>
              {onToggleAutoTour && cameraMode === 'ORBIT' && (
                <button
                  type="button"
                  onClick={onToggleAutoTour}
                  className={`mt-1 py-1 px-2.5 rounded text-[10.5px] font-mono flex items-center justify-center gap-1.5 transition cursor-pointer border ${
                    autoTour
                      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.25)]'
                      : 'bg-[#070e1d] text-slate-400 border-[#1e315b] hover:text-white'
                  }`}
                  title="Toggle automatic sweeping flythrough tour"
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${autoTour ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'}`} />
                  <span>{autoTour ? 'AUTO FLYTHROUGH: ACTIVE' : 'START AUTO TOUR (SWEEP 360°)'}</span>
                </button>
              )}
            </div>

            {/* Render Path Toggle */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Layers className="w-3 h-3 text-[#00c2cb]" /> RENDER PIPELINE
              </span>
              <div className="grid grid-cols-2 gap-1 p-0.5 rounded-lg bg-[#070e1d] border border-[#1e315b]">
                <button
                  type="button"
                  onClick={() => onRenderPathChange('DISPLACEMENT')}
                  className={`py-1 rounded text-[10px] font-mono font-semibold transition cursor-pointer ${
                    renderPath === 'DISPLACEMENT'
                      ? 'bg-[#0055a5] text-white shadow font-bold border border-[#00c2cb]/50'
                      : 'text-slate-400 hover:text-white hover:bg-[#0d1b38]'
                  }`}
                >
                  GPU Displace
                </button>
                <button
                  type="button"
                  onClick={() => onRenderPathChange('GLB')}
                  className={`py-1 rounded text-[10px] font-mono font-semibold transition cursor-pointer ${
                    renderPath === 'GLB'
                      ? 'bg-[#0055a5] text-white shadow font-bold border border-[#00c2cb]/50'
                      : 'text-slate-400 hover:text-white hover:bg-[#0d1b38]'
                  }`}
                >
                  GLB Mesh LOD
                </button>
              </div>
            </div>

            {/* LOD Level Selector */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Compass className="w-3 h-3 text-[#00c2cb]" /> MESH RESOLUTION LOD
                </span>
                <span className="text-[9px] text-slate-500">TRIANGLES</span>
              </span>
              <div className="grid grid-cols-3 gap-1 p-0.5 rounded-lg bg-[#070e1d] border border-[#1e315b] font-mono text-[10px]">
                {(
                  [
                    { id: 'lod0', label: 'LOD0 (262k)' },
                    { id: 'lod1', label: 'LOD1 (65k)' },
                    { id: 'lod2', label: 'LOD2 (16k)' },
                  ] as const
                ).map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => onLodChange(l.id)}
                    className={`py-1 rounded font-semibold transition cursor-pointer ${
                      lod === l.id
                        ? 'bg-[#0055a5] text-white shadow font-bold border border-[#00c2cb]/50'
                        : 'text-slate-400 hover:text-white hover:bg-[#0d1b38]'
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
                <span className="text-slate-300">Vertical Relief Exaggeration:</span>
                <span className="font-bold text-[#ff9944] bg-[#1a1408] px-1.5 py-0.5 rounded border border-[#ff6600]/40">
                  {zExag <= 0.02 ? '0.0× (Flat)' : `${zExag.toFixed(1)}×`}
                </span>
              </div>
              <input
                type="range"
                min="0.0"
                max="3.0"
                step="0.05"
                value={zExag}
                onChange={(e) => onZExagChange(parseFloat(e.target.value))}
                className="accent-[#ff6600] cursor-pointer h-1.5 bg-[#070e1d] rounded-lg mt-1"
              />
              <div className="flex justify-between text-[9px] text-slate-400 font-mono select-none">
                <button type="button" onClick={() => onZExagChange(0.0)} className={`hover:text-white transition cursor-pointer ${zExag <= 0.02 ? 'text-[#ff9944] font-bold underline' : ''}`}>0.0× (Flat)</button>
                <button type="button" onClick={() => onZExagChange(0.2)} className={`hover:text-white transition cursor-pointer ${Math.abs(zExag - 0.2) <= 0.04 ? 'text-[#ff9944] font-bold underline' : ''}`}>0.2× (Tactical)</button>
                <button type="button" onClick={() => onZExagChange(0.5)} className={`hover:text-white transition cursor-pointer ${Math.abs(zExag - 0.5) <= 0.04 ? 'text-[#ff9944] font-bold underline' : ''}`}>0.5×</button>
                <button type="button" onClick={() => onZExagChange(1.0)} className={`hover:text-white transition cursor-pointer ${Math.abs(zExag - 1.0) <= 0.04 ? 'text-[#ff9944] font-bold underline' : ''}`}>1.0× (True)</button>
                <button type="button" onClick={() => onZExagChange(2.0)} className={`hover:text-white transition cursor-pointer ${Math.abs(zExag - 2.0) <= 0.04 ? 'text-[#ff9944] font-bold underline' : ''}`}>2.0×</button>
                <button type="button" onClick={() => onZExagChange(3.0)} className={`hover:text-white transition cursor-pointer ${Math.abs(zExag - 3.0) <= 0.04 ? 'text-[#ff9944] font-bold underline' : ''}`}>3.0×</button>
              </div>
            </div>

            {/* Analytical Shader Overlays */}
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#1e315b]/60">
              <button
                type="button"
                onClick={onToggleSlope}
                className={`py-1.5 px-2 rounded-lg border text-[11px] font-mono font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer ${
                  showSlope
                    ? 'bg-[#2b1807] text-[#ff9944] border-[#ff6600] shadow-sm'
                    : 'bg-[#070e1d] text-slate-400 border-[#1e315b] hover:border-slate-600'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" /> Slope Hazard
              </button>

              <button
                type="button"
                onClick={onToggleWireframe}
                className={`py-1.5 px-2 rounded-lg border text-[11px] font-mono font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer ${
                  wireframe
                    ? 'bg-[#091b38] text-[#00c2cb] border-[#00c2cb] shadow-sm'
                    : 'bg-[#070e1d] text-slate-400 border-[#1e315b] hover:border-slate-600'
                }`}
              >
                <Eye className="w-3.5 h-3.5" /> Wireframe
              </button>
            </div>

            {/* Solar Illumination Vector Controls */}
            <div className="flex flex-col gap-1.5 pt-1 border-t border-[#1e315b]/60">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5 font-mono">
                <Sun className="w-3 h-3 text-[#ff9944]" /> SOLAR VECTOR (AZIMUTH &amp; ELEVATION)
              </span>
              <div className="flex flex-col gap-2 p-2.5 rounded-lg bg-[#070e1d] border border-[#1e315b] text-[11px] font-mono">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Solar Azimuth (&Phi;):</span>
                  <span className="text-[#00c2cb] font-bold bg-[#0a1a2e] px-1.5 py-0.5 rounded border border-[#00c2cb]/30">{sunAzimuth}°</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="360"
                  step="5"
                  value={sunAzimuth}
                  onChange={(e) => onSunAzimuthChange(parseInt(e.target.value, 10))}
                  className="accent-[#00c2cb] cursor-pointer h-1.5 bg-[#09152b] rounded-lg"
                />

                <div className="flex justify-between items-center mt-0.5">
                  <span className="text-slate-400">Solar Elevation (&Theta;):</span>
                  <span className="text-[#ff9944] font-bold bg-[#261505] px-1.5 py-0.5 rounded border border-[#ff6600]/30">{sunElevation}°</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="90"
                  step="5"
                  value={sunElevation}
                  onChange={(e) => onSunElevationChange(parseInt(e.target.value, 10))}
                  className="accent-[#ff6600] cursor-pointer h-1.5 bg-[#09152b] rounded-lg"
                />
              </div>
            </div>

            {/* Exports & Benchmark Actions */}
            <div className="flex flex-col gap-1.5 pt-2 border-t border-[#1e315b]/60">
              <button
                type="button"
                onClick={onDownloadDsm}
                className="w-full py-1.5 px-3 rounded-lg bg-[#09152b] hover:bg-[#11244a] text-slate-200 border border-[#1e315b] font-mono text-[11px] font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-[#00c2cb]" /> Export GeoTIFF (EGM96)
              </button>

              <button
                type="button"
                onClick={onDownloadGlb}
                className="w-full py-1.5 px-3 rounded-lg bg-[#09152b] hover:bg-[#11244a] text-slate-200 border border-[#1e315b] font-mono text-[11px] font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-[#00c2cb]" /> Export 3D Mesh (.glb)
              </button>

              <button
                type="button"
                onClick={onNavigateValidate}
                className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-[#0055a5] to-[#00c2cb] hover:from-[#004488] hover:to-[#00a2ab] text-white font-bold font-mono text-xs flex items-center justify-center gap-2 shadow-lg transition cursor-pointer mt-1 border border-[#00c2cb]/50"
              >
                <Scale className="w-3.5 h-3.5 text-[#ff9944]" />
                <span>EVALUATE LIDAR BENCHMARK →</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};
