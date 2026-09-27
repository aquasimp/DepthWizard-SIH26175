import React, { useState } from 'react';

export default function DepthInferenceTest() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [colormap, setColormap] = useState('plasma');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [inferenceResult, setInferenceResult] = useState(null);
  const [inferenceDuration, setInferenceDuration] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setErrorMsg(null);
      setInferenceResult(null);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const handleRunInference = async () => {
    if (!selectedFile) {
      setErrorMsg('Please select an RGB image first (PNG or JPG).');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    const startTime = performance.now();

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_BASE}/api/depth?colormap=${colormap}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const endTime = performance.now();
      setInferenceDuration(((endTime - startTime) / 1000).toFixed(2));
      setInferenceResult(data);
    } catch (err) {
      console.error('Inference error:', err);
      setErrorMsg(err.message || 'Failed to connect to backend inference server.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="depth-test-container">
      {/* Header */}
      <div className="test-header">
        <div className="test-badge">Depth Anything 3 | Real Inference Pipeline</div>
        <h2>Single-View Monocular Relative Depth Estimation</h2>
        <p className="test-desc">
          Upload an optical satellite or aerial RGB image. Depth Anything 3 infers affine-invariant relative depth maps in real-time.
        </p>
      </div>

      {/* Control Bar */}
      <div className="test-control-bar">
        <div className="upload-input-group">
          <label className="btn-file-select" htmlFor="rgb-file-input">
            📂 Choose RGB Image
          </label>
          <input
            id="rgb-file-input"
            type="file"
            accept="image/png, image/jpeg, image/jpg"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <span className="file-name-label">
            {selectedFile ? selectedFile.name : 'No image chosen (supports PNG / JPG)'}
          </span>
        </div>

        <div className="colormap-group">
          <label htmlFor="colormap-select">Colormap:</label>
          <select
            id="colormap-select"
            value={colormap}
            onChange={(e) => setColormap(e.target.value)}
            disabled={isLoading}
          >
            <option value="plasma">Plasma (Standard)</option>
            <option value="viridis">Viridis</option>
            <option value="inferno">Inferno</option>
            <option value="cividis">Cividis</option>
            <option value="gray">Grayscale</option>
          </select>
        </div>

        <button
          className="btn-run-inference"
          onClick={handleRunInference}
          disabled={!selectedFile || isLoading}
        >
          {isLoading ? (
            <span className="btn-spinner-text">
              <span className="spinner-dot" /> Inferring Depth...
            </span>
          ) : (
            '⚡ Estimate Relative Depth'
          )}
        </button>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="test-error-banner">
          ⚠️ <strong>Error:</strong> {errorMsg}
        </div>
      )}

      {/* Side-by-Side Comparison Workspace */}
      <div className="comparison-grid">
        {/* Left: Original RGB */}
        <div className="view-panel card">
          <div className="view-panel-header">
            <h4>1. Original RGB Input</h4>
            {selectedFile && <span className="panel-badge">Input Image</span>}
          </div>
          <div className="view-image-container">
            {previewUrl ? (
              <img src={previewUrl} alt="Original Optical RGB" className="view-img" />
            ) : (
              <div className="placeholder-box">
                <span className="placeholder-icon">🖼️</span>
                <p>Upload an RGB image to preview</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Relative Depth Map */}
        <div className="view-panel card">
          <div className="view-panel-header">
            <h4>2. Relative Depth Map (Depth Anything 3)</h4>
            {inferenceResult && (
              <span className="panel-badge badge-success">
                {inferenceDuration}s ({inferenceResult.device})
              </span>
            )}
          </div>
          <div className="view-image-container">
            {isLoading ? (
              <div className="placeholder-box loading-box">
                <div className="loading-orbit" />
                <p className="loading-title">Depth Anything 3 Inference</p>
                <span className="loading-subtitle">
                  Computing relative inverse depth matrix across receptive fields...
                </span>
              </div>
            ) : inferenceResult ? (
              <img
                src={inferenceResult.depth_image_base64 || `http://localhost:8000${inferenceResult.depth_image_url}`}
                alt="Generated Relative Depth"
                className="view-img"
              />
            ) : (
              <div className="placeholder-box">
                <span className="placeholder-icon">🌐</span>
                <p>Run inference to generate the relative depth map</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Statistics & Calibration Warning */}
      {inferenceResult && (
        <div className="stats-results-panel card">
          <div className="stats-header">
            <h4>📊 Inference Verification & Depth Statistics</h4>
            <div className="stats-actions">
              <a
                href={inferenceResult.depth_image_base64}
                download={`${selectedFile?.name?.replace(/\.[^/.]+$/, '')}_depth_${colormap}.png`}
                className="btn-download"
              >
                💾 Save Depth PNG
              </a>
              <a
                href={`http://localhost:8000${inferenceResult.depth_array_url}`}
                download
                className="btn-download btn-secondary"
              >
                🔢 Download .npy Matrix
              </a>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Input Shape</span>
              <span className="stat-value">
                {inferenceResult.statistics.input_dimensions.width} × {inferenceResult.statistics.input_dimensions.height}
              </span>
              <span className="stat-unit">3 Channels (RGB)</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Output Shape</span>
              <span className="stat-value">
                {inferenceResult.statistics.output_dimensions.width} × {inferenceResult.statistics.output_dimensions.height}
              </span>
              <span className="stat-unit">1 Channel (2D Float32)</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Min Relative Depth</span>
              <span className="stat-value">{inferenceResult.statistics.min_depth}</span>
              <span className="stat-unit">Dimensionless</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Max Relative Depth</span>
              <span className="stat-value">{inferenceResult.statistics.max_depth}</span>
              <span className="stat-unit">Dimensionless</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Mean Relative Depth</span>
              <span className="stat-value">{inferenceResult.statistics.mean_depth}</span>
              <span className="stat-unit">Std: {inferenceResult.statistics.std_depth}</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Inference Time</span>
              <span className="stat-value">{inferenceDuration}s</span>
              <span className="stat-unit">{inferenceResult.device.toUpperCase()} Device</span>
            </div>
          </div>

          <div className="notice-banner">
            <span className="notice-icon">ℹ️</span>
            <div>
              <strong>Relative Depth Notice:</strong> The values above represent monocular affine-invariant inverse depth.
              They indicate relative proximity/topography and are <strong>NOT metric height/elevation in metres</strong>.
              Metric elevation calibration will be performed in downstream pipeline stages.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
