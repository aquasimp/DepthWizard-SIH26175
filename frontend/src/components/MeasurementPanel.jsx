import React from 'react';

/**
 * MeasurementPanel - Dedicated Right Panel for Terrain Analysis.
 *
 * Cards:
 * - HEIGHT: Measured relative height above local terrain baseline
 * - ELEVATION: Calibrated metric elevation in meters from DSM
 * - SLOPE: Calculated local surface gradient in degrees
 *
 * Controls:
 * - Navigate: Orbit vs. Fly mode & Camera reset
 * - Height: Vertical Exaggeration slider
 * - Elevation: Optical RGB, Elevation Colormap, Wireframe toggles
 * - Slope: Slope Heatmap visualization & Topographic classification
 */
export default function MeasurementPanel({
  measurement = null,
  onResetMeasurement = null,
  // Navigation control
  cameraMode = 'orbit',
  onCameraModeChange = null,
  onResetCamera = null,
  // Height control
  verticalExaggeration = 1.0,
  onVerticalExaggerationChange = null,
  // Elevation control
  textureMode = 'rgb',
  onTextureModeChange = null,
  colorRamp = 'terrain',
  onColorRampChange = null,
  // Mesh summary from active DSM
  dsmSummary = null,
  onExportDSM = null,
}) {
  const hasMeasurement = measurement && measurement.elevation !== undefined;

  const heightVal = hasMeasurement ? measurement.height.toFixed(2) : (dsmSummary ? `${(dsmSummary.max_height - dsmSummary.min_height).toFixed(2)} (span)` : '--');
  const elevationVal = hasMeasurement ? measurement.elevation.toFixed(2) : (dsmSummary ? `${dsmSummary.mean_height.toFixed(2)} (mean)` : '--');
  const slopeVal = hasMeasurement ? measurement.slope.toFixed(1) : '--';
  const coordX = hasMeasurement ? measurement.x.toFixed(1) : '--';
  const coordZ = hasMeasurement ? measurement.z.toFixed(1) : '--';

  // Topographic slope classification
  let slopeTag = 'Normal';
  let slopeColor = '#38bdf8';
  if (hasMeasurement) {
    const s = measurement.slope;
    if (s < 5) {
      slopeTag = 'Flat';
      slopeColor = '#4ade80';
    } else if (s < 15) {
      slopeTag = 'Gentle';
      slopeColor = '#38bdf8';
    } else if (s < 30) {
      slopeTag = 'Moderate';
      slopeColor = '#fbbf24';
    } else {
      slopeTag = 'Steep';
      slopeColor = '#f87171';
    }
  }

  return (
    <aside className="terrain-analysis-panel">
      {/* Panel Header */}
      <div className="panel-header-simple">
        <div className="panel-badge-simple">RIGHT PANEL</div>
        <h2 className="analysis-title">Terrain Analysis</h2>
        <p className="panel-hint">
          {hasMeasurement ? (
            <span className="active-hit-indicator">🟢 Sampled at ({coordX}m, {coordZ}m)</span>
          ) : (
            <span>🖱️ Click anywhere on 3D terrain to measure</span>
          )}
        </p>
      </div>

      {/* Measurement Cards: HEIGHT, ELEVATION, SLOPE */}
      <div className="measurement-results-column">
        {/* HEIGHT CARD */}
        <div className="measure-metric-card height-card">
          <div className="measure-metric-header">
            <span className="measure-metric-label">HEIGHT</span>
            <span className="measure-metric-sublabel">Above Local Ground</span>
          </div>
          <div className="measure-metric-body">
            <span className="measure-metric-value">{heightVal}</span>
            <span className="measure-metric-unit">m</span>
          </div>
          {dsmSummary && (
            <div className="measure-card-footer">
              <span>Grid Min: {dsmSummary.min_height?.toFixed(1)}m</span>
              <span>Max: {dsmSummary.max_height?.toFixed(1)}m</span>
            </div>
          )}
        </div>

        {/* ELEVATION CARD */}
        <div className="measure-metric-card elevation-card">
          <div className="measure-metric-header">
            <span className="measure-metric-label">ELEVATION</span>
            <span className="measure-metric-sublabel">Metric DSM Datum</span>
          </div>
          <div className="measure-metric-body">
            <span className="measure-metric-value">{elevationVal}</span>
            <span className="measure-metric-unit">m</span>
          </div>
          {dsmSummary && (
            <div className="measure-card-footer">
              <span>Datum: Georeferenced DSM</span>
              <span>Mean: {dsmSummary.mean_height?.toFixed(1)}m</span>
            </div>
          )}
        </div>

        {/* SLOPE CARD */}
        <div className="measure-metric-card slope-card">
          <div className="measure-metric-header">
            <span className="measure-metric-label">SLOPE</span>
            <span className="measure-metric-sublabel" style={{ color: slopeColor }}>
              {hasMeasurement ? `${slopeTag} Topography` : 'Local Surface Gradient'}
            </span>
          </div>
          <div className="measure-metric-body">
            <span className="measure-metric-value" style={{ color: slopeColor }}>
              {slopeVal}
            </span>
            <span className="measure-metric-unit">deg</span>
          </div>
          <div className="measure-card-footer">
            <span>Formula: arctan(|∇z|)</span>
            <span>Unit: Degrees (°)</span>
          </div>
        </div>
      </div>

      {/* Controls Section */}
      <div className="analysis-controls-section">
        <h3 className="controls-heading">Controls</h3>

        {/* 1. Navigate Control */}
        <div className="control-group-box">
          <div className="control-label-row">
            <span className="control-label-title">Navigate</span>
            <span className="control-current-val">{cameraMode === 'fly' ? 'Fly (WASD)' : 'Orbit'}</span>
          </div>
          <div className="control-buttons-row">
            <button
              className={`ctrl-btn ${cameraMode === 'orbit' ? 'active' : ''}`}
              onClick={() => onCameraModeChange && onCameraModeChange('orbit')}
              title="Orbital inspection camera (Left click rotate, right click pan, scroll zoom)"
            >
              🛰️ Orbit
            </button>
            <button
              className={`ctrl-btn ${cameraMode === 'fly' ? 'active' : ''}`}
              onClick={() => onCameraModeChange && onCameraModeChange('fly')}
              title="First-person flythrough mode (W/A/S/D to move, Q/E for altitude)"
            >
              ✈️ Fly
            </button>
            <button
              className="ctrl-btn-action"
              onClick={() => onResetCamera && onResetCamera()}
              title="Reset camera view to default orientation"
            >
              ↺ Reset
            </button>
          </div>
        </div>

        {/* 2. Height Control */}
        <div className="control-group-box">
          <div className="control-label-row">
            <span className="control-label-title">Height</span>
            <span className="control-current-val">{verticalExaggeration.toFixed(1)}x Exaggeration</span>
          </div>
          <div className="slider-container">
            <input
              type="range"
              min="0.5"
              max="4.0"
              step="0.1"
              value={verticalExaggeration}
              onChange={(e) => onVerticalExaggerationChange && onVerticalExaggerationChange(parseFloat(e.target.value))}
              className="exaggeration-slider"
            />
            <div className="slider-ticks">
              <span>0.5x</span>
              <span>1.0x (True)</span>
              <span>2.5x</span>
              <span>4.0x</span>
            </div>
          </div>
        </div>

        {/* 3. Elevation Control */}
        <div className="control-group-box">
          <div className="control-label-row">
            <span className="control-label-title">Elevation</span>
            <span className="control-current-val">{textureMode === 'rgb' ? 'Optical RGB' : textureMode === 'colormap' ? 'Hypsometric' : 'Wireframe'}</span>
          </div>
          <div className="control-buttons-row">
            <button
              className={`ctrl-btn ${textureMode === 'rgb' ? 'active' : ''}`}
              onClick={() => onTextureModeChange && onTextureModeChange('rgb')}
              title="Drape original satellite optical image"
            >
              🛰️ Optical
            </button>
            <button
              className={`ctrl-btn ${textureMode === 'colormap' ? 'active' : ''}`}
              onClick={() => onTextureModeChange && onTextureModeChange('colormap')}
              title="Color-code by metric elevation height"
            >
              🏔️ Color
            </button>
            <button
              className={`ctrl-btn ${textureMode === 'wireframe' ? 'active' : ''}`}
              onClick={() => onTextureModeChange && onTextureModeChange('wireframe')}
              title="Show topographic triangulated wireframe mesh"
            >
              🕸️ Wire
            </button>
          </div>
          {textureMode === 'colormap' && onColorRampChange && (
            <div className="color-ramp-selector">
              <label>Palette:</label>
              <select value={colorRamp} onChange={(e) => onColorRampChange(e.target.value)}>
                <option value="terrain">Natural Terrain</option>
                <option value="viridis">Viridis Hypsometric</option>
              </select>
            </div>
          )}
        </div>

        {/* 4. Slope Control */}
        <div className="control-group-box">
          <div className="control-label-row">
            <span className="control-label-title">Slope</span>
            <span className="control-current-val">{textureMode === 'slope' ? 'Slope Map Active' : 'Off'}</span>
          </div>
          <div className="control-buttons-row">
            <button
              className={`ctrl-btn slope-mode-btn ${textureMode === 'slope' ? 'active' : ''}`}
              onClick={() => onTextureModeChange && onTextureModeChange(textureMode === 'slope' ? 'rgb' : 'slope')}
              title="Toggle topographic slope gradient colormap"
            >
              📐 {textureMode === 'slope' ? 'Hide Slope Map' : 'Show Slope Map'}
            </button>
          </div>
          <div className="slope-legend-row">
            <span className="slope-tag-pill flat">● &lt;5° Flat</span>
            <span className="slope-tag-pill gentle">● 5-15° Gentle</span>
            <span className="slope-tag-pill moderate">● 15-30° Mod</span>
            <span className="slope-tag-pill steep">● &gt;30° Steep</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="panel-actions-section">
        {hasMeasurement && onResetMeasurement && (
          <button className="btn-clear-measure" onClick={onResetMeasurement}>
            ✕ Clear Measurement Marker
          </button>
        )}
        <button
          className="btn-export-dsm-direct"
          onClick={onExportDSM}
          title="Download the georeferenced metric DSM GeoTIFF (outputs/dsm/dsm.tif)"
        >
          📥 Export Metric DSM GeoTIFF
        </button>
      </div>
    </aside>
  );
}
