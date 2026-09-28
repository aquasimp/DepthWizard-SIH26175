import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Clock,
  Database,
  Eye,
  FileCheck,
  Play,
  RotateCcw,
  Satellite,
  Scale,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { getApiBase } from '../utils/apiConfig';

interface JobSummary {
  job_id: string;
  status: string;
  stage: string;
  progress: number;
  created_at: string;
}

interface UploadPageProps {
  onJobSelect: (jobId: string) => void;
  onJobCreated: (jobId: string) => void;
  onNavigateValidate?: (jobId: string) => void;
  onNavigateHome?: () => void;
}

interface SampleTile {
  name: string;
  filename: string;
  path: string;
  gsd: string;
  desc: string;
  location: string;
  type: string;
}

const SAMPLE_TILES: SampleTile[] = [
  {
    name: 'Washington D.C. LiDAR Benchmark',
    filename: 'benchmark_optical.tif',
    path: '/samples/benchmark_optical.tif',
    gsd: '0.33',
    desc: 'GAMUS test tile with paired 0.33m USGS LiDAR ground truth GeoTIFF (WGS84 UTM 18N)',
    location: 'District 20/38, Washington D.C.',
    type: 'Benchmark Pair (Optical + LiDAR GT)',
  },
  {
    name: 'Washington D.C. Urban Core',
    filename: 'sample_georeferenced.tif',
    path: '/samples/sample_georeferenced.tif',
    gsd: '0.33',
    desc: 'High-density commercial & federal district (GeoTIFF · WGS84 UTM 18N)',
    location: 'Washington D.C., USA',
    type: 'GeoTIFF (Calibrated)',
  },
  {
    name: 'Metropolitan Geographic Tile',
    filename: 'sample_geographic.tif',
    path: '/samples/sample_geographic.tif',
    gsd: '0.33',
    desc: 'Geographic coordinate system remote sensing tile (EPSG:4326 / WGS84 Degrees)',
    location: 'Mid-Atlantic Urban Corridor',
    type: 'GeoTIFF (Geographic)',
  },
  {
    name: 'High-Resolution Aerial Ortho',
    filename: 'sample_plain.png',
    path: '/samples/sample_plain.png',
    gsd: '0.33',
    desc: 'Sub-meter optical RGB orthophoto without embedded georeference tags',
    location: 'Urban Mixed Density',
    type: 'RGB Orthophoto (PNG)',
  },
];

export const UploadPage: React.FC<UploadPageProps> = ({
  onJobSelect,
  onJobCreated,
  onNavigateValidate,
  onNavigateHome,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDetails, setFileDetails] = useState<{
    name: string;
    sizeMb: string;
    type: string;
    isGeotiff: boolean;
  } | null>(null);
  const [assumedGsd, setAssumedGsd] = useState('0.33');
  const [calibrationPath, setCalibrationPath] = useState('');
  const [modelVersion, setModelVersion] = useState('v1.1.0_best');
  const [zExag, setZExag] = useState('1.0');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingSample, setIsLoadingSample] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentJobs, setRecentJobs] = useState<JobSummary[]>([]);
  const [backendHealth, setBackendHealth] = useState<{
    online: boolean;
    device?: string;
    cudaAvailable?: boolean;
  } | null>(null);

  const checkHealth = () => {
    const apiBase = getApiBase();
    if (!apiBase) {
      setBackendHealth({ online: false, device: 'In-Browser Client Engine (Standalone)' });
      return;
    }
    fetch(`${apiBase}/api/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.status === 'healthy') {
          setBackendHealth({
            online: true,
            device: data.device || (data.cuda_available ? 'CUDA (GPU)' : 'CPU'),
            cudaAvailable: data.cuda_available,
          });
        } else {
          setBackendHealth({ online: false, device: 'In-Browser Client Engine (Standalone)' });
        }
      })
      .catch(() => setBackendHealth({ online: false, device: 'In-Browser Client Engine (Standalone)' }));
  };

  const loadRecentJobs = () => {
    const apiBase = getApiBase();
    if (!apiBase) return;
    fetch(`${apiBase}/api/jobs`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          setRecentJobs(data);
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    checkHealth();
    loadRecentJobs();
    const interval = setInterval(loadRecentJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  const inspectFile = (file: File) => {
    setSelectedFile(file);
    setError(null);
    const isGeo = file.name.toLowerCase().endsWith('.tif') || file.name.toLowerCase().endsWith('.tiff');
    setFileDetails({
      name: file.name,
      sizeMb: (file.size / (1024 * 1024)).toFixed(2),
      type: file.type || (isGeo ? 'image/tiff' : 'image/png'),
      isGeotiff: isGeo,
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      inspectFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      inspectFile(e.dataTransfer.files[0]);
    }
  };

  const handleLoadSample = async (sample: SampleTile) => {
    setIsLoadingSample(true);
    setError(null);
    try {
      const resp = await fetch(sample.path);
      if (!resp.ok) {
        throw new Error(`Failed to load benchmark tile: ${resp.statusText}`);
      }
      const blob = await resp.blob();
      const file = new File([blob], sample.filename, {
        type: sample.filename.endsWith('.tif') ? 'image/tiff' : 'image/png',
      });
      inspectFile(file);
      setAssumedGsd(sample.gsd);
    } catch (err: any) {
      setError(err.message || 'Error loading sample tile.');
    } finally {
      setIsLoadingSample(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select or load optical imagery to initiate reconstruction.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('assumed_gsd_m', assumedGsd);
    formData.append('z_exag', zExag);
    formData.append('model_version', modelVersion);
    if (calibrationPath) {
      formData.append('calibration_path', calibrationPath);
    }

    try {
      const apiBase = getApiBase();
      if (!apiBase) {
        throw new Error('A live backend endpoint is required for queued jobs. Use the main Dashboard for instant In-Browser 3D reconstruction, or configure your backend in Settings.');
      }
      const resp = await fetch(`${apiBase}/api/jobs`, {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        const msg = errJson.detail?.detail || errJson.detail || 'Reconstruction job initialization failed.';
        throw new Error(msg);
      }

      const data = await resp.json();
      onJobCreated(data.job_id);
    } catch (err: any) {
      setError(err.message || 'An error occurred during submission.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mission-portal-page">
      {/* Top Breadcrumb & Status Action Bar */}
      <div className="mission-portal-top-bar">
        <div className="mission-top-bar-left">
          {onNavigateHome && (
            <button
              type="button"
              onClick={onNavigateHome}
              className="mission-btn-back"
              title="Return to 3D Dashboard"
            >
              <ArrowLeft size={14} />
              <span>Dashboard Home</span>
            </button>
          )}
          <div className="mission-institutional-tag">
            <i className="fa-solid fa-satellite-dish text-sky-400" />
            <span>ISRO / SAC · BHOOMI-3D RECONNAISSANCE CONSOLE</span>
          </div>
        </div>

        <div className="mission-top-bar-right">
          <div className="mission-telemetry-badge">
            <span className={`telemetry-dot ${backendHealth?.online ? 'online' : 'standalone'}`} />
            <span className="font-mono text-xs">
              {backendHealth?.online ? `ENGINE: ${backendHealth.device}` : 'STANDALONE IN-BROWSER ENGINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Column Ingestion / Right Column Telemetry Queue */}
      <div className="mission-portal-layout-grid">
        {/* Left Column: Console Header, Presets & Ingestion Dropzone */}
        <div className="mission-portal-col-main">
          {/* Mission Ingestion Card */}
          <div className="mission-console-card">
            <div className="mission-console-accent-strip" />

            <div className="mission-card-header">
              <div className="mission-badge-row">
                <span className="mission-pulsing-badge">
                  <span className="pulse-dot-orange" />
                  <span>RECONNAISSANCE INGESTION CONSOLE</span>
                </span>
                <span className="mission-step-tag">STAGE 01 / 05</span>
              </div>
              <h2 className="mission-console-title">
                Single-View 3D Digital Surface Model (DSM) Reconstruction
              </h2>
              <p className="mission-console-desc">
                Ingest monocular optical satellite or aerial orthophoto imagery (GeoTIFF, standard TIFF, PNG, JPEG). The photogrammetric engine predicts dense metric relative heights, fits geodetic datum scale (EGM96 orthometric / SRTM / GCP), and generates 3D terrain meshes.
              </p>
            </div>

            {/* Quick Benchmark Preset Tiles */}
            <div className="mission-presets-section">
              <div className="mission-presets-header">
                <span className="presets-label">
                  <Database size={13} className="text-cyan-400" />
                  <span>1-Click Test Benchmarks (GAMUS Ground Truth)</span>
                </span>
                <span className="presets-tag">Instant Load</span>
              </div>

              <div className="mission-presets-grid">
                {SAMPLE_TILES.map((sample) => (
                  <button
                    key={sample.filename}
                    type="button"
                    onClick={() => handleLoadSample(sample)}
                    disabled={isLoadingSample || isSubmitting}
                    className="mission-preset-btn"
                  >
                    <div className="preset-btn-top">
                      <span className="preset-name">{sample.name}</span>
                      <span className="preset-specs">GSD: {sample.gsd}m · {sample.type.split(' ')[0]}</span>
                    </div>
                    <div className="preset-btn-bottom">
                      <span className="preset-loc">{sample.location}</span>
                      <span className="preset-action">Load →</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Ingestion Dropzone Form */}
            <form onSubmit={handleSubmit} className="mission-form-container">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className={`mission-dropzone-box ${selectedFile ? 'has-file' : ''}`}
              >
                <input
                  type="file"
                  accept=".tif,.tiff,.png,.jpg,.jpeg"
                  onChange={handleFileChange}
                  className="mission-hidden-file-input"
                />

                <div className="mission-viewfinder-reticle">
                  {selectedFile ? (
                    <FileCheck size={28} className="text-cyan-400" />
                  ) : (
                    <Upload size={28} className="text-slate-400" />
                  )}
                </div>

                {selectedFile && fileDetails ? (
                  <div className="mission-file-meta-block">
                    <div className="mission-filename-badge">
                      <Satellite size={13} className="text-amber-400" />
                      <strong>{fileDetails.name}</strong>
                    </div>
                    <div className="mission-file-stats">
                      <span>SIZE: <strong>{fileDetails.sizeMb} MB</strong></span>
                      <span>·</span>
                      <span>FORMAT: <strong className="text-cyan-400">{fileDetails.isGeotiff ? 'GeoTIFF' : 'Raster PNG/JPG'}</strong></span>
                      <span>·</span>
                      <span className="text-emerald-400 font-bold">READY FOR INFERENCE</span>
                    </div>
                  </div>
                ) : (
                  <div className="mission-dropzone-prompt">
                    <p className="dropzone-main-text">SELECT OPTICAL SATELLITE OR AERIAL ORTHOPHOTO</p>
                    <p className="dropzone-sub-text">Drag &amp; drop or click to browse GeoTIFF (WGS84 / UTM), standard TIFF, PNG, or JPEG</p>
                    <div className="dropzone-meta-chips">
                      <span>MAX RESOLUTION: 8000×8000 px</span>
                      <span>·</span>
                      <span>TILED SLIDING WINDOW</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Ingestion Parameters Grid */}
              <div className="mission-params-grid">
                <div className="mission-param-field">
                  <label className="param-label">Assumed GSD (m/px)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.05"
                    max="10.0"
                    value={assumedGsd}
                    onChange={(e) => setAssumedGsd(e.target.value)}
                    className="param-input font-mono"
                  />
                </div>

                <div className="mission-param-field">
                  <label className="param-label">Vertical Exaggeration ({zExag}x)</label>
                  <input
                    type="range"
                    min="0.5"
                    max="3.0"
                    step="0.1"
                    value={zExag}
                    onChange={(e) => setZExag(e.target.value)}
                    className="param-range-slider"
                  />
                </div>

                <div className="mission-param-field">
                  <label className="param-label">Depth Anything 3 Backbone</label>
                  <select
                    value={modelVersion}
                    onChange={(e) => setModelVersion(e.target.value)}
                    className="param-select font-mono"
                  >
                    <option value="v1.1.0_best">DA3 ViT-S Multi-City Fine-Tuned (Recommended)</option>
                    <option value="v1.0.0_base">DA3 ViT-B Zero-Shot Base</option>
                  </select>
                </div>

                <div className="mission-param-field">
                  <label className="param-label">LiDAR Ground Truth Path (Optional Calibration)</label>
                  <input
                    type="text"
                    placeholder="e.g. data/ground_truth/dsm_lidar.tif"
                    value={calibrationPath}
                    onChange={(e) => setCalibrationPath(e.target.value)}
                    className="param-input font-mono"
                  />
                </div>
              </div>

              {error && (
                <div className="mission-error-banner">
                  <AlertTriangle size={15} />
                  <span>{error}</span>
                </div>
              )}

              {/* Submit Action Row */}
              <div className="mission-submit-row">
                <button
                  type="submit"
                  disabled={isSubmitting || !selectedFile}
                  className="mission-btn-submit"
                >
                  {isSubmitting ? (
                    <>
                      <span className="btn-spinner" />
                      <span>INITIALIZING RECONSTRUCTION PIPELINE...</span>
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      <span>START 3D SURFACE MODEL RECONSTRUCTION</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Mission Telemetry Queue & Standards */}
        <div className="mission-portal-col-sidebar">
          {/* Telemetry Queue Card */}
          <div className="mission-sidebar-card">
            <div className="mission-sidebar-header">
              <div className="sidebar-title-group">
                <Clock size={16} className="text-cyan-400" />
                <h3 className="sidebar-title">Reconstruction Job Telemetry</h3>
              </div>
              <button
                type="button"
                onClick={loadRecentJobs}
                className="btn-refresh-jobs"
                title="Refresh Recent Jobs"
              >
                <RotateCcw size={12} />
              </button>
            </div>

            <div className="mission-jobs-list">
              {recentJobs.length === 0 ? (
                <div className="mission-jobs-empty">
                  <Satellite size={24} className="text-slate-500 mb-2" />
                  <p className="empty-title">No Active Server Jobs Found</p>
                  <p className="empty-desc">
                    Jobs submitted via FastAPI appear here. Or launch sample photogrammetry directly on the 3D Dashboard.
                  </p>
                  {onNavigateHome && (
                    <button
                      type="button"
                      onClick={onNavigateHome}
                      className="btn-empty-dashboard"
                    >
                      Open 3D Dashboard
                    </button>
                  )}
                </div>
              ) : (
                recentJobs.map((j) => (
                  <div key={j.job_id} className="mission-job-card">
                    <div className="job-card-top">
                      <span className="job-id-text font-mono">#{j.job_id.slice(0, 16)}</span>
                      <span className={`job-status-pill ${j.status.toLowerCase()}`}>
                        {j.status === 'DONE' ? 'REGISTERED' : j.status}
                      </span>
                    </div>

                    <div className="job-stage-row">
                      <span className="job-stage-label">STAGE: <strong>{j.stage || 'Inference'}</strong></span>
                      <span className="job-progress-num font-mono">{j.progress || 100}%</span>
                    </div>

                    <div className="job-progress-bar">
                      <div
                        className={`job-progress-fill ${j.status.toLowerCase()}`}
                        style={{ width: `${Math.max(j.progress || 100, 8)}%` }}
                      />
                    </div>

                    <div className="job-actions-row">
                      <button
                        type="button"
                        onClick={() => onJobSelect(j.job_id)}
                        className="btn-job-action primary"
                      >
                        <Eye size={12} />
                        <span>LAUNCH 3D COCKPIT</span>
                      </button>

                      {onNavigateValidate && (
                        <button
                          type="button"
                          onClick={() => onNavigateValidate(j.job_id)}
                          className="btn-job-action secondary"
                          title="Evaluate LiDAR Accuracy"
                        >
                          <Scale size={12} />
                          <span>LIDAR</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Institutional Photogrammetry Standards Card */}
          <div className="mission-sidebar-card compliance">
            <div className="compliance-header">
              <ShieldCheck size={16} className="text-emerald-400" />
              <span>NRSC &amp; ASPRS PHOTOGRAMMETRY STANDARD</span>
            </div>
            <p className="compliance-text">
              Complies with national standards for digital elevation data. Vertical accuracy benchmarked against aerial LiDAR ground truth (0.33m GSD). Outputs standard 32-bit GeoTIFF and decimation Level-of-Detail 3D GLB tiles.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
