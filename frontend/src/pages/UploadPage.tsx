import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  Cpu,
  Database,
  Eye,
  FileCheck,
  Layers,
  Play,
  Radar,
  Satellite,
  Scale,
  Settings,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { IsroHeader } from '../components/IsroHeader';

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
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.status === 'healthy') {
          setBackendHealth({
            online: true,
            device: data.device || (data.cuda_available ? 'CUDA (GPU)' : 'CPU'),
            cudaAvailable: data.cuda_available,
          });
        } else {
          setBackendHealth({ online: false });
        }
      })
      .catch(() => setBackendHealth({ online: false }));
  };

  const loadRecentJobs = () => {
    fetch('/api/jobs')
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

  // 1-Click Load Pre-Bundled Benchmark Sample
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

    if (backendHealth?.online === false) {
      setError(
        'FastAPI Core Engine is offline on port 8000. Start backend with `uvicorn depthwizard.main:app --app-dir backend --port 8000`.'
      );
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
      const resp = await fetch('/api/jobs', {
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
    <div className="min-h-screen bg-[#050811] text-slate-100 flex flex-col font-sans relative">
      {/* Background Aerospace Technical Grid */}
      <div className="absolute inset-0 bg-aerospace-grid opacity-75 pointer-events-none z-0" />

      {/* ISRO / SAC Mission Header */}
      <IsroHeader
        currentPage="upload"
        backendOnline={backendHealth?.online ?? false}
        computeDevice={backendHealth?.device || 'CUDA (GPU)'}
      />

      {/* Offline Alert Bar */}
      {backendHealth?.online === false && (
        <div className="bg-[#2a0e0e] border-b border-rose-800/80 px-6 py-2 text-xs font-mono text-rose-200 flex items-center justify-between z-30 shadow-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
            <span>
              <strong>GROUND SYSTEM TELEMETRY ALERT:</strong> Backend service unreachable at{' '}
              <code className="bg-black/50 px-1 py-0.5 rounded text-rose-300">/api/health</code>. Please verify FastAPI daemon on port 8000.
            </span>
          </div>
          <button
            onClick={checkHealth}
            className="px-3 py-0.5 rounded bg-rose-900 hover:bg-rose-800 text-rose-100 text-xs font-mono transition cursor-pointer border border-rose-700"
          >
            RETRY LINK
          </button>
        </div>
      )}

      {/* Main Mission Control Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start relative z-10">
        {/* Left Column (Cols 1-7): Ingestion & Telemetry Parameters */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          {/* Mission Ingestion Card Header */}
          <div className="mission-panel rounded-xl p-5 border border-[#1e315b] relative overflow-hidden">
            {/* Top Accent Strip */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#ff6600] via-[#0055a5] to-[#00c2cb]" />

            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#ff6600] animate-pulse" />
                <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-[#ff9944]">
                  RECONNAISSANCE INGESTION CONSOLE
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 border border-[#1e315b] bg-[#091224] px-2 py-0.5 rounded">
                STAGE 01 / 05
              </span>
            </div>

            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight font-display">
              Single-View 3D Digital Surface Model (DSM) Reconstruction
            </h2>
            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed font-sans">
              Ingest monocular optical satellite or aerial orthophoto imagery (GeoTIFF, standard TIFF, PNG, JPEG). The photogrammetric engine predicts dense metric relative heights, fits geodetic datum scale (EGM96 orthometric / SRTM / GCP), and generates 3D terrain meshes.
            </p>

            {/* Quick Benchmark Preset Tiles */}
            <div className="mt-4 pt-3 border-t border-[#1e315b]/80">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Database className="w-3 h-3 text-[#00c2cb]" /> 1-Click Test Benchmarks (GAMUS Ground Truth)
                </span>
                <span className="text-[9px] font-mono text-[#00c2cb]">INSTANT LOAD</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {SAMPLE_TILES.map((sample) => (
                  <button
                    key={sample.filename}
                    type="button"
                    onClick={() => handleLoadSample(sample)}
                    disabled={isLoadingSample || isSubmitting}
                    className="text-left p-2.5 rounded-lg bg-[#091224] hover:bg-[#11203f] border border-[#1e315b] hover:border-[#00c2cb]/60 transition cursor-pointer group flex flex-col justify-between"
                  >
                    <div>
                      <div className="text-[11px] font-bold text-white group-hover:text-[#00c2cb] transition line-clamp-1">
                        {sample.name}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                        GSD: {sample.gsd}m · {sample.type.split(' ')[0]}
                      </div>
                    </div>
                    <div className="text-[9px] text-slate-500 font-mono mt-2 flex items-center justify-between">
                      <span>{sample.location}</span>
                      <span className="text-[#ff6600] group-hover:translate-x-0.5 transition font-bold">LOAD →</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Ingestion Dropzone & Parameters Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Tactical Optical Ingestion Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`tactical-frame mission-panel rounded-xl p-6 sm:p-8 flex flex-col items-center justify-center text-center transition cursor-pointer border relative overflow-hidden group ${
                selectedFile
                  ? 'border-[#00c2cb] bg-[#07162e]/90 shadow-lg shadow-[#0055a5]/20'
                  : 'border-[#1e315b] hover:border-[#00c2cb]/70 bg-[#091224]/80'
              }`}
            >
              <input
                type="file"
                accept=".tif,.tiff,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer z-20"
              />

              {/* Optical Viewfinder Target Reticle */}
              <div className="w-16 h-16 rounded-full border border-[#00c2cb]/40 flex items-center justify-center text-[#00c2cb] mb-3 bg-[#061022] group-hover:scale-105 group-hover:border-[#ff6600] group-hover:text-[#ff6600] transition relative">
                <div className="absolute inset-0 rounded-full border border-dashed border-[#00c2cb]/30 animate-spin" style={{ animationDuration: '20s' }} />
                {selectedFile ? (
                  <FileCheck className="w-8 h-8 text-[#00c2cb]" />
                ) : (
                  <Upload className="w-7 h-7" />
                )}
              </div>

              {selectedFile && fileDetails ? (
                <div className="flex flex-col items-center">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-[#091834] border border-[#00c2cb]/50 text-xs font-mono text-white mb-1">
                    <Satellite className="w-3.5 h-3.5 text-[#ff6600]" />
                    <span className="font-bold">{fileDetails.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400 mt-1">
                    <span>SIZE: <strong className="text-white">{fileDetails.sizeMb} MB</strong></span>
                    <span>•</span>
                    <span>FORMAT: <strong className="text-[#00c2cb]">{fileDetails.isGeotiff ? 'GeoTIFF' : 'Plain Raster'}</strong></span>
                    <span>•</span>
                    <span className="text-emerald-400 font-bold">READY FOR INFERENCE</span>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="font-bold text-sm text-slate-100 font-display tracking-wide">
                    SELECT OPTICAL SATELLITE OR AERIAL ORTHOPHOTO
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Drag & drop or click to browse GeoTIFF (WGS84 / UTM), standard TIFF, PNG, or JPEG
                  </p>
                  <div className="flex items-center justify-center gap-3 text-[10px] font-mono text-slate-500 mt-3">
                    <span>MAX DIMENSIONS: 8000×8000 px</span>
                    <span>|</span>
                    <span>TILED SLIDING WINDOW INFERENCE</span>
                  </div>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3.5 rounded-lg border border-rose-600/80 bg-rose-950/60 text-xs font-mono text-rose-200 flex items-center gap-2 shadow-lg">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Photogrammetric & Model Parameters Grid */}
            <div className="mission-panel rounded-xl border border-[#1e315b] p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-[#1e315b]/60 pb-2.5">
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4 text-[#ff6600]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200 font-mono">
                    PHOTOGRAMMETRIC &amp; INFERENCE PARAMETERS
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">ISRO SAC SPECIFICATION</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* 1. Assumed GSD */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                    <span>Ground Sampling Distance (GSD)</span>
                    <span className="font-mono text-[#00c2cb] text-[11px] font-bold">{assumedGsd} m/px</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.05"
                    max="10.0"
                    value={assumedGsd}
                    onChange={(e) => setAssumedGsd(e.target.value)}
                    className="w-full rounded-lg border border-[#1e315b] bg-[#070e1d] px-3 py-2 text-xs text-white font-mono focus:border-[#00c2cb] focus:outline-none transition"
                    placeholder="0.33"
                  />
                  <span className="text-[10px] text-slate-400">
                    Auto-parsed for GeoTIFF metadata; default 0.33m for sub-meter high-res aerial imagery
                  </span>
                </div>

                {/* 2. Geodetic Vertical Datum Hierarchy */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                    <span>Calibration Scale Hierarchy</span>
                    <span className="text-[10px] font-mono text-[#ff9944]">EGM96 GEOID</span>
                  </label>
                  <select
                    value={calibrationPath}
                    onChange={(e) => setCalibrationPath(e.target.value)}
                    className="w-full rounded-lg border border-[#1e315b] bg-[#070e1d] px-3 py-2 text-xs text-white font-mono focus:border-[#00c2cb] focus:outline-none transition"
                  >
                    <option value="">Auto Selector (Hierarchy B → A → C → D)</option>
                    <option value="PATH_A">Path A: SRTM Bare-Earth DTM (EGM96)</option>
                    <option value="PATH_B">Path B: Ground Control Points (GCP RANSAC)</option>
                    <option value="PATH_C">Path C: RANSAC Affine Disparity Alignment</option>
                    <option value="PATH_D">Path D: Normalized Metric Stretch [0, 1]</option>
                  </select>
                  <span className="text-[10px] text-slate-400">
                    Determines vertical scale factor $s$ and translation $t$ to ground truth elevation
                  </span>
                </div>

                {/* 3. Model Architecture & Weights */}
                <div className="flex flex-col gap-1.5 sm:col-span-2">
                  <div className="flex justify-between items-center text-xs font-semibold text-slate-200">
                    <label className="flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-[#00c2cb]" />
                      Deep Learning Model Weights
                    </label>
                    <span className="text-[10px] font-mono text-[#00c2cb] bg-[#091834] px-2 py-0.5 rounded border border-[#00c2cb]/30">
                      GAMUS 3-CITY TRAINED (35.1M LiDAR Px)
                    </span>
                  </div>
                  <select
                    value={modelVersion}
                    onChange={(e) => setModelVersion(e.target.value)}
                    className="w-full rounded-lg border border-[#1e315b] bg-[#070e1d] px-3 py-2 text-xs text-white font-mono focus:border-[#00c2cb] focus:outline-none transition"
                  >
                    <option value="v1.1.0_best">
                      DepthWizard v1.1.0 Multi-City (Recommended — 3,817 Crops, MedAE 0.71m, LiDAR Calibrated)
                    </option>
                    <option value="ensemble">
                      Adaptive Dual-Head Ensemble (Terrain + Tall Structure Specialist Fusion)
                    </option>
                    <option value="v1.1.0_tall">
                      DepthWizard v1.1.0 Tall Specialist (Optimized for High-Rise Skylines &gt; 15m)
                    </option>
                    <option value="base">
                      Zero-Shot Baseline (Depth Anything V2 Small Foundation)
                    </option>
                  </select>
                  <span className="text-[10px] text-slate-400">
                    Trained across 35.1M LiDAR ground truth pixels over Washington D.C., New York City, and Philadelphia (Xiong et al. 2023)
                  </span>
                </div>

                {/* 4. Vertical Exaggeration Slider */}
                <div className="flex flex-col gap-1.5 sm:col-span-2 pt-1 border-t border-[#1e315b]/40">
                  <div className="flex justify-between items-center text-xs font-semibold text-slate-200">
                    <span className="flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-[#ff6600]" /> 3D Cartographic Vertical Exaggeration
                    </span>
                    <span className="font-mono text-[#ff9944] font-bold bg-[#1b1509] px-2 py-0.5 rounded border border-[#ff6600]/30">
                      {zExag}× RELIEF
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={zExag}
                    onChange={(e) => setZExag(e.target.value)}
                    className="accent-[#ff6600] cursor-pointer h-1.5 bg-[#091224] rounded-lg mt-1"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span>1.0× (True Metric 1:1)</span>
                    <span>2.5× (Enhanced Urban Relief)</span>
                    <span>5.0× (Maximum Topographic Contrast)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Launch Ingestion Pipeline Button */}
            <button
              type="submit"
              disabled={isSubmitting || !selectedFile}
              className="w-full py-4 px-6 rounded-xl bg-gradient-to-r from-[#0055a5] via-[#0077d4] to-[#00c2cb] hover:from-[#004488] hover:to-[#00a2ab] disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-sm flex items-center justify-center gap-2.5 shadow-xl shadow-[#0055a5]/30 transition cursor-pointer border border-[#00c2cb]/40 font-display tracking-wider uppercase"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>INITIALIZING RECONNAISSANCE PIPELINE...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current text-[#ff9944]" />
                  <span>INITIALIZE 3D SURFACE RECONSTRUCTION PIPELINE</span>
                  <ArrowRight className="w-4 h-4 text-white" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column (Cols 8-12): Recent Mission Reconstructions Log */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="mission-panel rounded-xl p-4 border border-[#1e315b] flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-[#1e315b]/60 pb-2">
              <div className="flex items-center gap-2">
                <Radar className="w-4 h-4 text-[#00c2cb] animate-pulse" />
                <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
                  MISSION RECONSTRUCTION LOG / अभिलेख
                </h3>
              </div>
              <span className="text-[10px] font-mono text-[#00c2cb] bg-[#091834] px-2 py-0.5 rounded border border-[#00c2cb]/30">
                {recentJobs.length} MISSIONS
              </span>
            </div>

            {/* Mission Log Stream */}
            <div className="flex flex-col gap-2.5 max-h-[640px] overflow-y-auto pr-1">
              {recentJobs.length === 0 ? (
                <div className="rounded-lg border border-[#1e315b] bg-[#091224] p-8 text-center text-slate-400 text-xs font-mono">
                  No mission records logged yet. Ingest imagery to begin surface reconstruction.
                </div>
              ) : (
                recentJobs.map((j) => (
                  <div
                    key={j.job_id}
                    className="rounded-lg border border-[#1e315b] hover:border-[#00c2cb]/70 bg-[#091224] hover:bg-[#0d1b38] p-3.5 transition flex flex-col gap-2.5 group"
                  >
                    {/* Header: ID + Status badge */}
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-200 group-hover:text-[#00c2cb] transition">
                        #{j.job_id}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wider ${
                          j.status === 'DONE'
                            ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-700/60'
                            : j.status === 'FAILED'
                            ? 'bg-rose-950/80 text-rose-400 border border-rose-700/60'
                            : 'bg-[#091834] text-[#00c2cb] border border-[#00c2cb]/40 animate-pulse'
                        }`}
                      >
                        {j.status === 'DONE' ? 'REGISTERED' : j.status}
                      </span>
                    </div>

                    {/* Progress Bar & Stage */}
                    <div className="flex flex-col gap-1">
                      <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                        <span>STAGE: <strong className="text-white">{j.stage}</strong></span>
                        <span className="text-[#ff9944]">{j.progress}%</span>
                      </div>
                      <div className="w-full h-1 bg-[#050811] rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            j.status === 'DONE'
                              ? 'bg-emerald-400'
                              : j.status === 'FAILED'
                              ? 'bg-rose-500'
                              : 'bg-gradient-to-r from-[#ff6600] to-[#00c2cb]'
                          }`}
                          style={{ width: `${Math.max(j.progress, 5)}%` }}
                        />
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1 border-t border-[#1e315b]/40">
                      {j.status === 'DONE' ? (
                        <>
                          <button
                            type="button"
                            onClick={() => onJobSelect(j.job_id)}
                            className="flex-1 py-1 px-2.5 rounded bg-[#0055a5] hover:bg-[#004488] text-white text-[11px] font-mono font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer border border-[#00c2cb]/40"
                          >
                            <Eye className="w-3 h-3 text-[#00c2cb]" />
                            <span>LAUNCH 3D COCKPIT</span>
                          </button>

                          {onNavigateValidate && (
                            <button
                              type="button"
                              onClick={() => onNavigateValidate(j.job_id)}
                              className="py-1 px-2 rounded bg-[#09152b] hover:bg-[#11244a] text-slate-300 hover:text-white text-[11px] font-mono flex items-center justify-center gap-1 transition cursor-pointer border border-[#1e315b]"
                              title="Evaluate LiDAR Accuracy"
                            >
                              <Scale className="w-3 h-3 text-[#ff9944]" />
                              <span>LIDAR</span>
                            </button>
                          )}
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => onJobSelect(j.job_id)}
                          className="w-full py-1 px-2 rounded bg-[#091224] hover:bg-[#11203f] text-slate-300 text-[11px] font-mono flex items-center justify-center gap-1.5 transition cursor-pointer border border-[#1e315b]"
                        >
                          <Clock className="w-3 h-3 text-[#00c2cb]" />
                          <span>VIEW PIPELINE TELEMETRY</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Institutional Compliance Card */}
          <div className="mission-panel rounded-xl p-4 border border-[#1e315b] text-[11px] font-mono text-slate-400 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-slate-300 font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>NRSC &amp; ASPRS PHOTOGRAMMETRY STANDARD</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed font-sans">
              Complies with national standards for digital elevation data. Vertical accuracy benchmarked against aerial LiDAR ground truth (0.33m GSD). Outputs standard 32-bit GeoTIFF and decimation Level-of-Detail 3D GLB tiles.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};
