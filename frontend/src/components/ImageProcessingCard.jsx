import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileImage,
  Sparkles,
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileText,
  RefreshCw,
} from 'lucide-react';

export default function ImageProcessingCard(props) {
  const {
    selectedFile,
    fileName = 'sample_gamus_optical.png',
    fileFormat = 'PNG',
    filePreviewUrl,
    fileResolution = '1024 × 1024 px',
    pipelineState = 'idle',
    pipelineResult,
    pipelineError,
    onFileSelect,
    onLoadSample,
    onRunPipeline,
  } = props || {};
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const isRunning = pipelineState === 'running';
  const isCompleted = pipelineState === 'completed';

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && onFileSelect) {
      onFileSelect(file);
    }
  };

  const handleInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file && onFileSelect) {
      onFileSelect(file);
    }
  };

  // Pipeline vertical steps:
  // RGB IMAGE -> DEPTH ESTIMATION -> SCALE CALIBRATION -> METRIC DSM -> 3D TERRAIN
  const verticalSteps = [
    { id: 'rgb', title: 'RGB IMAGE', desc: 'Optical Ingestion' },
    { id: 'depth', title: 'DEPTH ESTIMATION', desc: 'Depth Anything 3' },
    { id: 'calib', title: 'SCALE CALIBRATION', desc: 'H = a·D + b' },
    { id: 'dsm', title: 'METRIC DSM', desc: 'GeoTIFF Surface' },
    { id: 'terrain', title: '3D TERRAIN', desc: 'WebGL Heightfield' },
  ];

  return (
    <section className="image-processing-card" id="upload-section">
      <div className="card-header-bar">
        <div className="card-title-group">
          <FileImage className="card-header-icon" size={20} />
          <div>
            <h3 className="card-heading-text">Upload Remote-Sensing Image</h3>
            <p className="card-subheading-text">
              Accepts optical satellite or aerial imagery (PNG, JPG, GeoTIFF) for single-view 3D elevation extraction.
            </p>
          </div>
        </div>

        <div className="card-header-actions">
          <button
            className="btn-sample-load"
            onClick={onLoadSample}
            disabled={isRunning}
            title="Load representative GAMUS satellite optical image"
          >
            <Sparkles size={14} />
            <span>Use Sample Image (DC_02_26)</span>
          </button>
        </div>
      </div>

      <div className="upload-and-info-grid">
        {/* Left Side: Drag & Drop Upload Zone */}
        <div
          className={`dropzone-area ${isDragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.tif,.tiff"
            onChange={handleInputChange}
            style={{ display: 'none' }}
          />

          <div className="dropzone-inner-content">
            <div className="dropzone-icon-box">
              <UploadCloud size={32} />
            </div>
            <p className="dropzone-prompt">
              <strong>Click to upload</strong> or drag and drop optical image
            </p>
            <span className="dropzone-supported">
              Supports: <strong>PNG</strong>, <strong>JPG</strong>, <strong>GeoTIFF (.tif, .tiff)</strong>
            </span>
          </div>
        </div>

        {/* Right Side: File Metadata & Pipeline Progress */}
        <div className="upload-metadata-panel">
          <div className="meta-card-preview-row">
            {filePreviewUrl ? (
              <div className="preview-image-box">
                <img src={filePreviewUrl} alt="Satellite Input Preview" className="preview-thumbnail" />
              </div>
            ) : (
              <div className="preview-placeholder-box">
                <FileText size={28} />
                <span>GeoTIFF / Raster</span>
              </div>
            )}

            <div className="metadata-text-column">
              <div className="meta-field">
                <span className="meta-field-label">File Name:</span>
                <span className="meta-field-value font-mono">{fileName}</span>
              </div>
              <div className="meta-field">
                <span className="meta-field-label">Resolution:</span>
                <span className="meta-field-value font-mono">
                  {pipelineResult?.stages?.rgb_ingestion?.dimensions
                    ? `${pipelineResult.stages.rgb_ingestion.dimensions.width} × ${pipelineResult.stages.rgb_ingestion.dimensions.height} px`
                    : fileResolution}
                </span>
              </div>
              <div className="meta-field">
                <span className="meta-field-label">File Type:</span>
                <span className="format-tag">{fileFormat}</span>
              </div>
              <div className="meta-field">
                <span className="meta-field-label">Processing Status:</span>
                <span className={`status-pill-small ${isRunning ? 'running' : isCompleted ? 'completed' : 'ready'}`}>
                  {isRunning ? 'Processing...' : isCompleted ? 'Completed' : 'Ready'}
                </span>
              </div>
            </div>
          </div>

          {/* Stepper: RGB IMAGE -> DEPTH ESTIMATION -> SCALE CALIBRATION -> METRIC DSM -> 3D TERRAIN */}
          <div className="vertical-stepper-box">
            <div className="stepper-title">PIPELINE STAGES</div>
            <div className="stepper-steps-flow">
              {verticalSteps.map((s, i) => (
                <React.Fragment key={s.id}>
                  <div className={`step-badge-node ${isCompleted ? 'done' : isRunning ? 'active' : ''}`}>
                    <span className="step-node-dot" />
                    <span className="step-node-text">{s.title}</span>
                  </div>
                  {i < verticalSteps.length - 1 && <span className="step-node-arrow">↓</span>}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Primary Action Button */}
          <div className="action-button-row">
            <button
              className={`btn-primary-execute ${isRunning ? 'running' : ''}`}
              onClick={onRunPipeline}
              disabled={isRunning}
            >
              {isRunning ? (
                <>
                  <Loader2 size={16} className="spin-icon" />
                  <span>Processing Depth &amp; DSM...</span>
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  <span>▶ Run End-to-End Pipeline</span>
                </>
              )}
            </button>

            {isCompleted && (
              <span className="execution-time-label">
                ✓ Executed in {pipelineResult?.total_execution_seconds}s
              </span>
            )}
            {pipelineError && (
              <span className="execution-error-label">
                <AlertCircle size={14} /> {pipelineError}
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
