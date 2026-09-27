import React from 'react';
import { Layers, FileCheck2, Mountain, Compass, CheckCircle2, Clock } from 'lucide-react';

export default function AnalyticsCards({
  pipelineResult = null,
  dsmMesh = null,
  selectedMeasurement = null,
  pipelineState = 'idle',
}) {
  const isCompleted = pipelineResult !== null;
  const isRunning = pipelineState === 'running';
  const isError = pipelineState === 'error';

  // 1. RELATIVE DEPTH
  const stage2 = pipelineResult?.stages?.relative_depth;
  const relDepthStatus = isCompleted ? 'Generated' : isRunning ? 'Estimating...' : isError ? 'Error' : 'Standby';
  const relDepthValue = stage2
    ? `[${stage2.min_depth}, ${stage2.max_depth}]`
    : isRunning
    ? 'Inference...'
    : isError
    ? 'Depth Failed'
    : 'Standby';
  const relDepthSub = stage2 ? 'Relative Ray Depth Range' : isError ? 'Inference Error' : 'Depth Anything 3';

  // 2. METRIC DSM
  const stage4 = pipelineResult?.stages?.dsm;
  const dsmStatus = isCompleted ? 'Ready' : isRunning ? 'Calibrating...' : isError ? 'Error' : dsmMesh ? 'Ready' : 'Standby';
  const dsmValue = stage4?.minimum_elevation !== undefined && stage4?.maximum_elevation !== undefined
    ? `${stage4.minimum_elevation.toFixed(1)}m – ${stage4.maximum_elevation.toFixed(1)}m`
    : isRunning
    ? 'Generating...'
    : isError
    ? 'DSM Failed'
    : dsmMesh?.min_height !== undefined && dsmMesh?.max_height !== undefined
    ? `${dsmMesh.min_height.toFixed(1)}m – ${dsmMesh.max_height.toFixed(1)}m`
    : 'outputs/dsm.tif';
  const dsmSub = stage4?.mean_elevation !== undefined
    ? `Mean: ${stage4.mean_elevation.toFixed(1)}m`
    : dsmMesh?.mean_height !== undefined
    ? `Mean: ${dsmMesh.mean_height.toFixed(1)}m`
    : 'GeoTIFF Surface Raster';

  // 3. TERRAIN HEIGHT
  const hasSelectedPoint = selectedMeasurement && selectedMeasurement.height !== undefined;
  const heightValue = hasSelectedPoint
    ? `${selectedMeasurement.height.toFixed(2)} m`
    : dsmMesh ? `${(dsmMesh.max_height - dsmMesh.min_height).toFixed(2)} m` : '--';
  const heightSub = hasSelectedPoint ? 'Selected Point Above Ground' : 'Total Relief Span';

  // 4. SLOPE
  const hasSelectedSlope = selectedMeasurement && selectedMeasurement.slope !== undefined;
  const slopeValue = hasSelectedSlope
    ? `${selectedMeasurement.slope.toFixed(1)}°`
    : '--';
  
  let slopeSub = 'Click terrain to calculate';
  if (hasSelectedSlope) {
    const s = selectedMeasurement.slope;
    if (s < 5) slopeSub = 'Flat Surface (<5°)';
    else if (s < 15) slopeSub = 'Gentle Gradient (5-15°)';
    else if (s < 30) slopeSub = 'Moderate Incline (15-30°)';
    else slopeSub = 'Steep Topography (>30°)';
  }

  return (
    <section className="analytics-cards-grid">
      {/* CARD 1: RELATIVE DEPTH */}
      <div className="analytics-card">
        <div className="card-top-row">
          <div className="card-icon-wrapper cyan">
            <Layers size={20} />
          </div>
          <div className={`card-status-pill ${isCompleted ? 'success' : 'neutral'}`}>
            {isCompleted ? <CheckCircle2 size={12} /> : <Clock size={12} />}
            <span>{relDepthStatus}</span>
          </div>
        </div>
        <div className="card-body">
          <span className="card-metric-title">RELATIVE DEPTH</span>
          <div className="card-metric-number font-mono">{relDepthValue}</div>
          <span className="card-metric-sub">{relDepthSub}</span>
        </div>
      </div>

      {/* CARD 2: METRIC DSM */}
      <div className="analytics-card">
        <div className="card-top-row">
          <div className="card-icon-wrapper emerald">
            <FileCheck2 size={20} />
          </div>
          <div className={`card-status-pill ${isCompleted || dsmMesh ? 'success' : 'neutral'}`}>
            {isCompleted || dsmMesh ? <CheckCircle2 size={12} /> : <Clock size={12} />}
            <span>{dsmStatus}</span>
          </div>
        </div>
        <div className="card-body">
          <span className="card-metric-title">METRIC DSM</span>
          <div className="card-metric-number font-mono">{dsmValue}</div>
          <span className="card-metric-sub">{dsmSub}</span>
        </div>
      </div>

      {/* CARD 3: TERRAIN HEIGHT */}
      <div className="analytics-card">
        <div className="card-top-row">
          <div className="card-icon-wrapper blue">
            <Mountain size={20} />
          </div>
          <div className={`card-status-pill ${hasSelectedPoint ? 'active' : 'neutral'}`}>
            <span>{hasSelectedPoint ? 'Point Sampled' : 'Relief Max'}</span>
          </div>
        </div>
        <div className="card-body">
          <span className="card-metric-title">TERRAIN HEIGHT</span>
          <div className="card-metric-number font-mono">{heightValue}</div>
          <span className="card-metric-sub">{heightSub}</span>
        </div>
      </div>

      {/* CARD 4: SLOPE */}
      <div className="analytics-card">
        <div className="card-top-row">
          <div className="card-icon-wrapper amber">
            <Compass size={20} />
          </div>
          <div className={`card-status-pill ${hasSelectedSlope ? 'active' : 'neutral'}`}>
            <span>{hasSelectedSlope ? 'Calculated' : 'Standby'}</span>
          </div>
        </div>
        <div className="card-body">
          <span className="card-metric-title">SLOPE</span>
          <div className="card-metric-number font-mono">{slopeValue}</div>
          <span className="card-metric-sub">{slopeSub}</span>
        </div>
      </div>
    </section>
  );
}
