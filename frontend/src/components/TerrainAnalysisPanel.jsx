import React from 'react';
import {
  Ruler,
  Mountain,
  Compass,
  MapPin,
  Sliders,
  Download,
  XCircle,
  Activity,
  Layers,
  Box,
  BarChart3,
} from 'lucide-react';

export default function TerrainAnalysisPanel(props) {
  const {
    selectedMeasurement = null,
    onResetMeasurement = null,
    verticalExaggeration = 1.0,
    onVerticalExaggerationChange = null,
    textureMode = 'rgb',
    onTextureModeChange = null,
    colorRamp = 'terrain',
    onColorRampChange = null,
    dsmMesh = null,
    onExportDSM = null,
    onExportGLB = null,
    onOpenCockpit = null,
  } = props || {};
  const hasMeasurement = selectedMeasurement && selectedMeasurement.elevation !== undefined;

  const heightVal = hasMeasurement ? selectedMeasurement.height.toFixed(2) : (dsmMesh ? `${(dsmMesh.max_height - dsmMesh.min_height).toFixed(2)} (span)` : '--');
  const elevationVal = hasMeasurement ? selectedMeasurement.elevation.toFixed(2) : (dsmMesh ? `${dsmMesh.mean_height?.toFixed(2)} (mean)` : '--');
  const slopeVal = hasMeasurement ? selectedMeasurement.slope.toFixed(1) : '--';
  const coordX = hasMeasurement ? selectedMeasurement.x.toFixed(1) : '--';
  const coordZ = hasMeasurement ? selectedMeasurement.z.toFixed(1) : '--';

  // Distance from center of tile
  const distVal = hasMeasurement
    ? Math.sqrt(selectedMeasurement.x ** 2 + selectedMeasurement.z ** 2).toFixed(1)
    : '--';

  let slopeTag = 'Normal';
  let slopeColorClass = 'text-cyan';
  if (hasMeasurement) {
    const s = selectedMeasurement.slope;
    if (s < 5) {
      slopeTag = 'Flat (<5°)';
      slopeColorClass = 'text-emerald';
    } else if (s < 15) {
      slopeTag = 'Gentle (5-15°)';
      slopeColorClass = 'text-cyan';
    } else if (s < 30) {
      slopeTag = 'Moderate (15-30°)';
      slopeColorClass = 'text-amber';
    } else {
      slopeTag = 'Steep (>30°)';
      slopeColorClass = 'text-rose';
    }
  }

  return (
    <aside className="terrain-analysis-sidebar" id="measurements-section">
      <div className="panel-title-header">
        <div className="panel-badge-label">TERRAIN ANALYSIS</div>
        <h3 className="panel-main-heading">Point Measurements</h3>
        <p className="panel-instruction-hint">
          {hasMeasurement ? (
            <span className="text-emerald">Active Pin at ({coordX}m, {coordZ}m)</span>
          ) : (
            <span>Click terrain to measure</span>
          )}
        </p>
      </div>

      {/* Measurement Metrics Cards: HEIGHT, ELEVATION, SLOPE, DISTANCE */}
      <div className="analysis-metrics-stack">
        {/* HEIGHT */}
        <div className="analysis-metric-box">
          <div className="metric-box-top">
            <span className="metric-box-title">HEIGHT</span>
            <span className="metric-box-subtitle">Above Local Ground</span>
          </div>
          <div className="metric-box-content">
            <span className="metric-num-lg font-mono">{heightVal}</span>
            <span className="metric-unit-text">m</span>
          </div>
          <div className="metric-box-footer">
            <span>Datum: Local Relief Baseline</span>
          </div>
        </div>

        {/* ELEVATION */}
        <div className="analysis-metric-box">
          <div className="metric-box-top">
            <span className="metric-box-title">ELEVATION</span>
            <span className="metric-box-subtitle">Calibrated Metric DSM</span>
          </div>
          <div className="metric-box-content">
            <span className="metric-num-lg font-mono">{elevationVal}</span>
            <span className="metric-unit-text">m</span>
          </div>
          <div className="metric-box-footer">
            <span>Grid Min: {dsmMesh?.min_height?.toFixed(1) || 0}m | Max: {dsmMesh?.max_height?.toFixed(1) || 0}m</span>
          </div>
        </div>

        {/* SLOPE */}
        <div className="analysis-metric-box">
          <div className="metric-box-top">
            <span className="metric-box-title">SLOPE</span>
            <span className={`metric-box-subtitle ${slopeColorClass}`}>
              {hasMeasurement ? slopeTag : 'Local Surface Gradient'}
            </span>
          </div>
          <div className="metric-box-content">
            <span className={`metric-num-lg font-mono ${slopeColorClass}`}>{slopeVal}</span>
            <span className="metric-unit-text">deg (°)</span>
          </div>
          <div className="metric-box-footer">
            <span>Gradient: arctan(|∇z|)</span>
          </div>
        </div>

        {/* DISTANCE */}
        <div className="analysis-metric-box">
          <div className="metric-box-top">
            <span className="metric-box-title">DISTANCE</span>
            <span className="metric-box-subtitle">From Center (0, 0)</span>
          </div>
          <div className="metric-box-content">
            <span className="metric-num-lg font-mono">{distVal}</span>
            <span className="metric-unit-text">m</span>
          </div>
          <div className="metric-box-footer">
            <span>Coords: ({coordX}m, {coordZ}m)</span>
          </div>
        </div>
      </div>

      {/* Surface Display Controls */}
      <div className="panel-controls-group">
        <div className="control-header-label">
          <Sliders size={14} />
          <span>Surface &amp; Exaggeration</span>
        </div>

        <div className="exaggeration-control-item">
          <div className="slider-label-row">
            <span>Vertical Exaggeration:</span>
            <span className="font-mono text-cyan font-semibold">
              {verticalExaggeration <= 0.02 ? '0.0x (Flat)' : `${verticalExaggeration.toFixed(1)}x`}
            </span>
          </div>
          <input
            type="range"
            min="0.0"
            max="3.0"
            step="0.05"
            value={verticalExaggeration}
            onChange={(e) => onVerticalExaggerationChange && onVerticalExaggerationChange(parseFloat(e.target.value))}
            className="custom-range-slider"
          />
          <div className="slider-markers">
            <span className={verticalExaggeration <= 0.02 ? 'text-cyan font-bold' : ''}>0.0x (Flat)</span>
            <span>0.5x</span>
            <span className={Math.abs(verticalExaggeration - 1.0) <= 0.04 ? 'text-cyan font-bold' : ''}>1.0x (True)</span>
            <span>2.0x</span>
            <span>3.0x</span>
          </div>
          <div className="exaggeration-preset-row">
            <button
              type="button"
              className={`exag-preset-chip ${verticalExaggeration <= 0.02 ? 'active' : ''}`}
              onClick={() => onVerticalExaggerationChange && onVerticalExaggerationChange(0.0)}
            >
              Flat (0x)
            </button>
            <button
              type="button"
              className={`exag-preset-chip ${Math.abs(verticalExaggeration - 0.5) <= 0.04 ? 'active' : ''}`}
              onClick={() => onVerticalExaggerationChange && onVerticalExaggerationChange(0.5)}
            >
              0.5x
            </button>
            <button
              type="button"
              className={`exag-preset-chip ${Math.abs(verticalExaggeration - 1.0) <= 0.04 ? 'active' : ''}`}
              onClick={() => onVerticalExaggerationChange && onVerticalExaggerationChange(1.0)}
            >
              1.0x (True)
            </button>
            <button
              type="button"
              className={`exag-preset-chip ${Math.abs(verticalExaggeration - 2.0) <= 0.04 ? 'active' : ''}`}
              onClick={() => onVerticalExaggerationChange && onVerticalExaggerationChange(2.0)}
            >
              2.0x
            </button>
          </div>
        </div>

        {/* Texture Switcher */}
        <div className="texture-switcher-row">
          <button
            className={`texture-pill-btn ${textureMode === 'rgb' ? 'active' : ''}`}
            onClick={() => onTextureModeChange && onTextureModeChange('rgb')}
          >
            RGB
          </button>
          <button
            className={`texture-pill-btn ${textureMode === 'colormap' ? 'active' : ''}`}
            onClick={() => onTextureModeChange && onTextureModeChange('colormap')}
          >
            Color
          </button>
          <button
            className={`texture-pill-btn ${textureMode === 'slope' ? 'active' : ''}`}
            onClick={() => onTextureModeChange && onTextureModeChange('slope')}
          >
            Slope
          </button>
          <button
            className={`texture-pill-btn ${textureMode === 'wireframe' ? 'active' : ''}`}
            onClick={() => onTextureModeChange && onTextureModeChange('wireframe')}
          >
            Wire
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="panel-action-buttons">
        {hasMeasurement && onResetMeasurement && (
          <button className="btn-clear-pin" onClick={onResetMeasurement}>
            <XCircle size={15} />
            <span>Reset Measurement Marker</span>
          </button>
        )}

        <button className="btn-download-dsm-direct" onClick={onExportDSM}>
          <Download size={15} />
          <span>Export Metric DSM GeoTIFF</span>
        </button>

        {onExportGLB && (
          <button className="btn-download-glb-direct" onClick={onExportGLB}>
            <Box size={15} />
            <span>Export 3D Mesh (.glb)</span>
          </button>
        )}

        {onOpenCockpit && (
          <button className="btn-launch-cockpit-direct" onClick={onOpenCockpit}>
            <Compass size={15} />
            <span>Launch Tactical Cockpit ↗</span>
          </button>
        )}

        <button
          type="button"
          className="btn-view-graphs-direct"
          onClick={() => {
            const el = document.getElementById('accuracy-section');
            if (el) {
              el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }}
          title="Scroll directly to Model Accuracy &amp; Interactive Graphs"
        >
          <BarChart3 size={15} />
          <span>Model Accuracy &amp; Graphs ↓</span>
        </button>
      </div>
    </aside>
  );
}
