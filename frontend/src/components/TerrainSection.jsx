import React, { useState, useRef, useEffect } from 'react';
import {
  Plane,
  Orbit,
  RotateCcw,
  Maximize2,
  Minimize2,
  Compass,
  Navigation,
  Crosshair,
  Sliders,
  Layers,
  Activity,
  Gauge,
  Radio,
  Sun,
  Eye,
  Map,
} from 'lucide-react';
import TerrainViewer from './TerrainViewer';

/**
 * Tactical 3D Cockpit & Aerial Reconnaissance Section
 * Interactive 60 FPS flight deck featuring:
 * - Full Tactical Cockpit HUD with Solar Lighting & Sun Angle simulation
 * - Autonomous Drone Reconnaissance Flythrough (Auto Tour)
 * - First-Person Manual Drone Flight Simulator (WASD + Mouse-Look)
 * - 360° Orbital Inspection and Top-Down Nadir satellite views
 * - Authoritative point measurements & surface diagnostics
 */
export default function TerrainSection(props) {
  const {
    dsmMesh,
    userTextureUrl = null,
    textureMode = 'rgb',
    onTextureModeChange,
    cameraMode = 'fly',
    onCameraModeChange,
    verticalExaggeration = 0.2,
    onVerticalExaggerationChange,
    colorRamp = 'terrain',
    selectedMeasurement,
    onSelectMeasurement,
    resetViewTrigger = 0,
    onResetView,
    onOpenCockpit,
  } = props || {};

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState('cockpit'); // 'cockpit' | 'flythrough'
  const [flightMode, setFlightMode] = useState('auto'); // 'auto' | 'manual' | 'orbit' | 'topdown'
  const [isTourPaused, setIsTourPaused] = useState(false);
  const [tourSpeed, setTourSpeed] = useState(1.0);
  const [cruiseAltitude, setCruiseAltitude] = useState(28.0);
  const containerRef = useRef(null);

  // Sync state with native browser fullscreen events
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = Boolean(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

  // Sync cameraMode prop with internal flightMode
  useEffect(() => {
    if (cameraMode === 'orbit' && flightMode !== 'orbit') {
      setFlightMode('orbit');
    } else if (cameraMode === 'fly' && flightMode === 'orbit') {
      setFlightMode('auto');
    }
  }, [cameraMode]);

  const handleFlightModeSelect = (mode) => {
    setFlightMode(mode);
    if (mode === 'orbit' || mode === 'topdown') {
      if (onCameraModeChange) onCameraModeChange('orbit');
    } else {
      if (onCameraModeChange) onCameraModeChange('fly');
    }
  };

  const toggleFullscreen = async () => {
    const el = containerRef.current;
    if (!el) return;
    try {
      const isCurrentlyFullscreen = Boolean(
        document.fullscreenElement ||
        document.webkitFullscreenElement
      );
      if (!isCurrentlyFullscreen) {
        if (el.requestFullscreen) {
          await el.requestFullscreen();
        } else if (el.webkitRequestFullscreen) {
          await el.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          await document.webkitExitFullscreen();
        }
      }
    } catch (err) {
      console.warn('[DepthWizard] Fullscreen toggle error:', err);
    }
  };

  // Real values for overlay measurement cards
  const hasPoint = selectedMeasurement && selectedMeasurement.height !== undefined;
  const heightVal = hasPoint
    ? `${selectedMeasurement.height.toFixed(1)} m`
    : dsmMesh ? `${(dsmMesh.max_height - dsmMesh.min_height).toFixed(1)} m (span)` : '--';
  const elevationVal = hasPoint
    ? `${selectedMeasurement.elevation.toFixed(1)} m`
    : dsmMesh ? `${dsmMesh.mean_height?.toFixed(1)} m (mean)` : '--';
  const slopeVal = hasPoint
    ? `${selectedMeasurement.slope.toFixed(1)}°`
    : '--';

  return (
    <section
      ref={containerRef}
      className={`terrain-section-card ${isFullscreen ? 'fullscreen-mode' : ''}`}
      id="terrain-section"
    >
      {/* Flight Deck Header Toolbar */}
      <div className="terrain-header-toolbar">
        <div className="toolbar-title-group">
          <Navigation className="text-cyan animate-pulse" size={22} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="terrain-title-text">Tactical 3D Cockpit &amp; Flythrough</h3>
              <span className="flight-live-badge">
                <span className="flight-pulse-dot" />
                <span>60 FPS Fly Engine</span>
              </span>
              <span className="hidden sm:inline-flex px-1.5 py-0.5 text-[10px] font-mono bg-sky-950/70 text-sky-300 border border-sky-800/60 rounded">
                ISRO / SAC Telemetry
              </span>
            </div>
            <span className="terrain-subtitle-text">
              Real-Time Drone Reconnaissance &amp; Metric Elevation Flight Deck ({dsmMesh ? `${dsmMesh.rows}×${dsmMesh.cols} Grid` : '128×128 Grid'} · 0.33m GSD)
            </span>
          </div>
        </div>

        {/* Controls Toolbar: View Mode, Flight Modes, Tactical Cockpit, Fullscreen */}
        <div className="toolbar-controls-group">
          {/* View Mode Toggle: Tactical Cockpit vs Flythrough */}
          <div className="flex items-center bg-slate-900 border border-slate-700/60 rounded-full p-0.5">
            <button
              type="button"
              className={`px-3 py-1 text-xs font-semibold rounded-full transition flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'cockpit'
                  ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              onClick={() => setViewMode('cockpit')}
              title="Tactical Cockpit View with Solar Lighting, HUD Avionics & Diagnostics"
            >
              <Compass size={13} />
              <span>Cockpit HUD</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 text-xs font-semibold rounded-full transition flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'flythrough'
                  ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              onClick={() => setViewMode('flythrough')}
              title="Clean 3D Flythrough View"
            >
              <Plane size={13} />
              <span>Flythrough</span>
            </button>
          </div>

          {/* Flight Modes: Auto Tour, Manual Fly, Orbit, Top-Down */}
          <div className="flight-mode-toggle-group">
            <button
              type="button"
              className={`flight-mode-btn ${flightMode === 'auto' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('auto')}
              title="Autonomous Drone Reconnaissance (Auto-gliding across terrain)"
            >
              <Navigation size={13} />
              <span>Auto Tour</span>
            </button>
            <button
              type="button"
              className={`flight-mode-btn ${flightMode === 'manual' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('manual')}
              title="Manual Drone Flight Simulator (Drag mouse to steer, WASD keys to thrust)"
            >
              <Plane size={13} />
              <span>Manual Fly</span>
            </button>
            <button
              type="button"
              className={`flight-mode-btn ${flightMode === 'orbit' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('orbit')}
              title="Orbital 360° Inspection (Drag to rotate, scroll to zoom, click to measure)"
            >
              <Orbit size={13} />
              <span>Orbit</span>
            </button>
            <button
              type="button"
              className={`flight-mode-btn ${flightMode === 'topdown' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('topdown')}
              title="Top-Down Nadir 2D/3D Map View"
            >
              <Map size={13} />
              <span>Top-Down</span>
            </button>
          </div>

          {onOpenCockpit && (
            <button
              type="button"
              className="tool-btn-accent"
              onClick={onOpenCockpit}
              title="Launch full-screen Tactical 3D Cockpit with ISRO Telemetry HUD, Solar Illumination & LOD controls"
            >
              <Compass size={15} />
              <span>Cockpit Page ↗</span>
            </button>
          )}

          <button
            type="button"
            className="tool-btn-neutral"
            onClick={onResetView}
            title="Reset flight trajectory to initial takeoff position"
          >
            <RotateCcw size={15} />
            <span>Reset View</span>
          </button>

          <button
            type="button"
            className="tool-btn-neutral"
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            <span>{isFullscreen ? 'Exit' : 'Fullscreen'}</span>
          </button>
        </div>
      </div>

      {/* 3D WebGL Canvas Container */}
      <div className="terrain-canvas-wrapper">
        <TerrainViewer
          dsmData={dsmMesh}
          userTextureUrl={userTextureUrl}
          textureMode={textureMode}
          onTextureModeChange={onTextureModeChange}
          cameraMode={cameraMode}
          onCameraModeChange={onCameraModeChange}
          flightMode={flightMode}
          onFlightModeChange={setFlightMode}
          isTourPaused={isTourPaused}
          onToggleTourPause={() => setIsTourPaused((prev) => !prev)}
          tourSpeed={tourSpeed}
          onChangeTourSpeed={setTourSpeed}
          cruiseAltitude={cruiseAltitude}
          onChangeAltitude={setCruiseAltitude}
          verticalExaggeration={verticalExaggeration}
          onVerticalExaggerationChange={onVerticalExaggerationChange}
          colorRamp={colorRamp}
          selectedPoint={selectedMeasurement}
          onSelectPoint={onSelectMeasurement}
          resetViewTrigger={resetViewTrigger}
          showCockpitHud={viewMode === 'cockpit'}
        />

        {/* Floating Overlay Point Measurement Cards */}
        <div className="floating-hud-overlay">
          <div className="hud-card">
            <span className="hud-label">HEIGHT</span>
            <span className="hud-value font-mono">{heightVal}</span>
            <span className="hud-sub">Above Ground</span>
          </div>

          <div className="hud-card">
            <span className="hud-label">ELEVATION</span>
            <span className="hud-value font-mono">{elevationVal}</span>
            <span className="hud-sub">Datum Elevation</span>
          </div>

          <div className="hud-card">
            <span className="hud-label">SLOPE</span>
            <span className="hud-value font-mono">{slopeVal}</span>
            <span className="hud-sub">Surface Angle</span>
          </div>
        </div>

        {/* Click-to-measure hint bar */}
        <div className="terrain-interaction-hint">
          <span>Click anywhere on the 3D surface to sample precise point elevation &amp; slope gradient</span>
        </div>
      </div>
    </section>
  );
}
