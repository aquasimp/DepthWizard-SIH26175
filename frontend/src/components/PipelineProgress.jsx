import React from 'react';
import {
  Camera,
  Sparkles,
  Layers,
  Sliders,
  FileCheck2,
  Box,
  Check,
  Loader2,
  ArrowRight,
} from 'lucide-react';

export default function PipelineProgress({
  pipelineState = 'idle', // 'idle' | 'running' | 'completed' | 'error'
  pipelineResult = null,
}) {
  const isRunning = pipelineState === 'running';
  const isCompleted = pipelineState === 'completed';

  const stages = [
    {
      id: 'rgb',
      title: 'RGB INPUT',
      label: 'Optical Satellite',
      icon: Camera,
      detail: pipelineResult?.stages?.rgb_ingestion?.dimensions
        ? `${pipelineResult.stages.rgb_ingestion.dimensions.width}×${pipelineResult.stages.rgb_ingestion.dimensions.height}`
        : 'PNG / JPG / GeoTIFF',
    },
    {
      id: 'ai',
      title: 'DEPTH AI',
      label: 'Depth Anything 3',
      icon: Sparkles,
      detail: 'ViT-S Monocular Backbone',
    },
    {
      id: 'depth',
      title: 'RELATIVE DEPTH',
      label: 'Inverse Depth',
      icon: Layers,
      detail: pipelineResult?.stages?.relative_depth?.min_depth !== undefined
        ? `[${pipelineResult.stages.relative_depth.min_depth}, ${pipelineResult.stages.relative_depth.max_depth}]`
        : 'Unitless D',
    },
    {
      id: 'calib',
      title: 'CALIBRATION',
      label: 'Affine Fit',
      icon: Sliders,
      detail: pipelineResult?.stages?.metric_calibration?.rmse_meters !== undefined
        ? `H = a·D + b (RMSE: ${pipelineResult.stages.metric_calibration.rmse_meters.toFixed(1)}m)`
        : 'Metric Ground Datum',
    },
    {
      id: 'dsm',
      title: 'METRIC DSM',
      label: 'GeoTIFF Raster',
      icon: FileCheck2,
      detail: pipelineResult?.stages?.dsm?.minimum_elevation !== undefined && pipelineResult?.stages?.dsm?.maximum_elevation !== undefined
        ? `${pipelineResult.stages.dsm.minimum_elevation.toFixed(1)}m to ${pipelineResult.stages.dsm.maximum_elevation.toFixed(1)}m`
        : 'EPSG:3857 Grid',
    },
    {
      id: 'mesh',
      title: '3D MESH',
      label: 'WebGL Surface',
      icon: Box,
      detail: pipelineResult?.stages?.terrain_3d?.vertex_count !== undefined
        ? `${pipelineResult.stages.terrain_3d.vertex_count.toLocaleString()} Vertices`
        : '32,258 Triangles',
    },
  ];

  return (
    <section className="horizontal-pipeline-section" aria-label="End-to-End Processing Pipeline">
      <div className="pipeline-header-bar">
        <span className="pipeline-title-label">PROCESSING PIPELINE</span>
        <span className="pipeline-status-text">
          {isRunning ? 'Pipeline Running...' : isCompleted ? `✓ Finished in ${pipelineResult?.total_execution_seconds}s` : 'Ready for Ingestion'}
        </span>
      </div>

      <div className="pipeline-stages-container">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const isStageCompleted = isCompleted;
          const isStageActive = isRunning;

          return (
            <React.Fragment key={stage.id}>
              <div className={`pipeline-stage-item ${isStageCompleted ? 'completed' : isStageActive ? 'active' : ''}`}>
                <div className="stage-icon-circle">
                  {isStageCompleted ? (
                    <Check size={16} className="text-emerald" />
                  ) : isStageActive ? (
                    <Loader2 size={16} className="spin-icon" />
                  ) : (
                    <Icon size={16} />
                  )}
                </div>

                <div className="stage-text-block">
                  <span className="stage-step-title">{stage.title}</span>
                  <span className="stage-step-label">{stage.label}</span>
                  <span className="stage-step-detail font-mono">{stage.detail}</span>
                </div>
              </div>

              {idx < stages.length - 1 && (
                <div className={`pipeline-connector-line ${isStageCompleted ? 'completed' : isStageActive ? 'active' : ''}`}>
                  <ArrowRight size={14} className="connector-arrow" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}
