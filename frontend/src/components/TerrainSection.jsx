import React, { useState, useRef } from 'react';
import {
  Mountain,
  Orbit,
  Plane,
  RotateCcw,
  Maximize2,
  Minimize2,
  Layers,
  Activity,
  Compass,
} from 'lucide-react';
import TerrainViewer from './TerrainViewer';

export default function TerrainSection(props) {
  const {
    dsmMesh,
    userTextureUrl = null,
    textureMode = 'rgb',
    onTextureModeChange,
    cameraMode = 'orbit',
    onCameraModeChange,
    verticalExaggeration = 1.0,
    colorRamp = 'terrain',
    selectedMeasurement,
    onSelectMeasurement,
    resetViewTrigger = 0,
    onResetView,
    onOpenCockpit,
  } = props || {};
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  // Sync state with native browser fullscreen events (e.g. when user presses ESC key)
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

  // Real values for overlay measurement cards (NO FAKE / FABRICATED NUMBERS)
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
      {/* Card Header with Controls */}
      <div className="terrain-header-toolbar">
        <div className="toolbar-title-group">
          <Mountain className="text-cyan" size={20} />
          <div>
            <h3 className="terrain-title-text">3D Terrain</h3>
            <span className="terrain-subtitle-text">
              WebGL Metric Heightfield ({dsmMesh ? `${dsmMesh.rows}×${dsmMesh.cols} Grid` : '128×128 Grid'})
            </span>
          </div>
        </div>

        {/* Controls Toolbar: Orbit, Fly, Reset View, Fullscreen */}
        <div className="toolbar-controls-group">
          <div className="camera-mode-toggle-group">
            <button
              className={`tool-btn ${cameraMode === 'orbit' ? 'active' : ''}`}
              onClick={() => onCameraModeChange && onCameraModeChange('orbit')}
              title="Orbital inspection camera (Left click drag to rotate, right click to pan, scroll to zoom)"
            >
              <Orbit size={15} />
              <span>Orbit</span>
            </button>
            <button
              className={`tool-btn ${cameraMode === 'fly' ? 'active' : ''}`}
              onClick={() => onCameraModeChange && onCameraModeChange('fly')}
              title="First-person drone flythrough mode (WASD keys to fly, Q/E for elevation)"
            >
              <Plane size={15} />
              <span>Fly</span>
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
            title="Reset camera view to default orientation"
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
          verticalExaggeration={verticalExaggeration}
          colorRamp={colorRamp}
          selectedPoint={selectedMeasurement}
          onSelectPoint={onSelectMeasurement}
          resetViewTrigger={resetViewTrigger}
        />

        {/* Floating Overlay Measurement Cards */}
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
          <span>🖱️ Click anywhere on the 3D surface to sample precise point elevation &amp; slope gradient</span>
        </div>
      </div>
    </section>
  );
}
