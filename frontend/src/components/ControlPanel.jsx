import React from 'react';

export default function ControlPanel({
  minElev,
  setMinElev,
  maxElev,
  setMaxElev,
  gsd,
  setGsd,
  verticalExaggeration,
  setVerticalExaggeration,
  wireframe,
  setWireframe,
  colorRamp,
  setColorRamp,
  onCalibrate,
  onExportDSM,
  isProcessing,
  systemStatus,
}) {
  return (
    <div className="control-panel">
      <div className="panel-header">
        <h3>Terrain & Elevation Controls</h3>
        <span className={`badge ${systemStatus?.environment?.cuda_available ? 'badge-cuda' : 'badge-cpu'}`}>
          {systemStatus?.environment?.cuda_available ? 'CUDA GPU' : 'CPU Mode'}
        </span>
      </div>

      {/* Metric Elevation Bounds */}
      <div className="control-group">
        <label className="group-label">Metric Elevation Range (Meters)</label>
        <div className="input-row">
          <div className="input-field">
            <span className="field-tag">Min</span>
            <input
              type="number"
              value={minElev}
              onChange={(e) => setMinElev(parseFloat(e.target.value) || 0)}
              step="5"
            />
            <span className="unit">m</span>
          </div>
          <div className="input-field">
            <span className="field-tag">Max</span>
            <input
              type="number"
              value={maxElev}
              onChange={(e) => setMaxElev(parseFloat(e.target.value) || 100)}
              step="5"
            />
            <span className="unit">m</span>
          </div>
        </div>
      </div>

      {/* Ground Sampling Distance */}
      <div className="control-group">
        <div className="slider-header">
          <label>Spatial Resolution (GSD)</label>
          <span className="value-label">{gsd.toFixed(2)} m/px</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="5.0"
          step="0.1"
          value={gsd}
          onChange={(e) => setGsd(parseFloat(e.target.value))}
        />
      </div>

      {/* 3D Vertical Exaggeration */}
      <div className="control-group">
        <div className="slider-header">
          <label>Vertical Exaggeration</label>
          <span className="value-label">{verticalExaggeration.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="5.0"
          step="0.1"
          value={verticalExaggeration}
          onChange={(e) => setVerticalExaggeration(parseFloat(e.target.value))}
        />
      </div>

      {/* Color Ramp and Wireframe */}
      <div className="control-group">
        <label className="group-label">Visualization Style</label>
        <div className="toggle-row">
          <select
            value={colorRamp}
            onChange={(e) => setColorRamp(e.target.value)}
            className="select-style"
          >
            <option value="terrain">Natural Hypsometric Tint</option>
            <option value="spectral">Spectral Elevation (Jet)</option>
          </select>

          <button
            type="button"
            className={`btn-toggle ${wireframe ? 'active' : ''}`}
            onClick={() => setWireframe(!wireframe)}
          >
            Wireframe: {wireframe ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="button-group">
        <button
          className="btn btn-primary"
          onClick={onCalibrate}
          disabled={isProcessing}
        >
          {isProcessing ? 'Processing Pipeline...' : 'Calibrate Metric DSM'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={onExportDSM}
        >
          Export GeoTIFF DSM
        </button>
      </div>

      {/* System Status info */}
      <div className="system-specs">
        <div className="spec-row">
          <span>AI Backbone:</span>
          <strong>Depth Anything 3</strong>
        </div>
        <div className="spec-row">
          <span>Backend:</span>
          <span>FastAPI ({systemStatus?.environment?.python_version || 'Python 3'})</span>
        </div>
        <div className="spec-row">
          <span>GAMUS Dataset:</span>
          <span>{systemStatus?.dataset?.gamus_ready ? 'Loaded' : 'Pending (Modular Slot)'}</span>
        </div>
      </div>
    </div>
  );
}
