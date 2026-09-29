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
} from 'lucide-react';
import TerrainViewer from './TerrainViewer';

/**
 * 3D Flythrough Section
 * Interactive 60 FPS drone flight deck featuring autonomous aerial reconnaissance,
 * first-person pilot simulator, real-time metric elevation telemetry, and point measurements.
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
    colorRamp = 'terrain',
    selectedMeasurement,
    onSelectMeasurement,
    resetViewTrigger = 0,
    onResetView,
    onOpenCockpit,
  } = props || {};

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [flightMode, setFlightMode] = useState('auto'); // 'auto' | 'manual' | 'orbit'
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
    if (mode === 'orbit') {
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
          <Plane className="text-cyan animate-pulse" size={21} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="terrain-title-text">3D Flythrough</h3>
              <span className="flight-live-badge">
                <span className="flight-pulse-dot" />
                <span>60 FPS Fly Engine</span>
              </span>
            </div>
            <span className="terrain-subtitle-text">
              Real-Time Drone Reconnaissance &amp; Metric Flight Deck ({dsmMesh ? `${dsmMesh.rows}×${dsmMesh.cols} Grid` : '128×128 Grid'})
            </span>
          </div>
        </div>

        {/* Controls Toolbar: Flight Modes, Tactical Cockpit, Reset View, Fullscreen */}
        <div className="toolbar-controls-group">
          {/* Mode Switcher: Auto Tour, Manual Fly, Orbit */}
          <div className="flight-mode-toggle-group">
            <button
              className={`flight-mode-btn ${flightMode === 'auto' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('auto')}
              title="Cinematic Autonomous Drone Reconnaissance Flight (Auto-gliding across terrain)"
            >
              <Navigation size={14} />
              <span>Auto Tour</span>
            </button>
            <button
              className={`flight-mode-btn ${flightMode === 'manual' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('manual')}
              title="Manual First-Person Drone Flight (Drag mouse to steer, WASD keys to thrust)"
            >
              <Plane size={14} />
              <span>Manual Fly</span>
            </button>
            <button
              className={`flight-mode-btn ${flightMode === 'orbit' ? 'active' : ''}`}
              onClick={() => handleFlightModeSelect('orbit')}
              title="Orbital Inspection (Drag to rotate 360°, scroll to zoom, click to measure)"
            >
              <Orbit size={14} />
              <span>Orbit</span>
            </button>
          </div>

          {onOpenCockpit && (
            <button
              className="tool-btn-accent"
              onClick={onOpenCockpit}
              title="Launch full-screen Tactical 3D Cockpit with ISRO Telemetry HUD, Solar Illumination & LOD controls"
            >
              <Compass size={15} />
              <span>Tactical Cockpit ↗</span>
            </button>
          )}

          <button
            className="tool-btn-neutral"
            onClick={onResetView}
            title="Reset flight trajectory to initial takeoff position"
          >
            <RotateCcw size={15} />
            <span>Reset View</span>
          </button>

          <button
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
          colorRamp={colorRamp}
          selectedPoint={selectedMeasurement}
          onSelectPoint={onSelectMeasurement}
          resetViewTrigger={resetViewTrigger}
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
