import { useEffect, useState } from 'react';
import { ArrowRight, Clock, FileUp, Globe2, Sparkles, Upload } from 'lucide-react';

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
}

export const UploadPage: React.FC<UploadPageProps> = ({
  onJobSelect,
  onJobCreated,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [assumedGsd, setAssumedGsd] = useState('0.33');
  const [calibrationPath, setCalibrationPath] = useState('');
  const [modelVersion, setModelVersion] = useState('v1.1.0_best');
  const [zExag, setZExag] = useState('1.0');
  const [isSubmitting, setIsSubmitting] = useState(false);
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
            device: data.device,
            cudaAvailable: data.cuda_available,
          });
        } else {
          setBackendHealth({ online: false });
        }
      })
      .catch(() => setBackendHealth({ online: false }));
  };

  useEffect(() => {
    checkHealth();
    fetch('/api/jobs')
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setRecentJobs(data))
      .catch(() => {});
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an imagery file to upload.');
      return;
    }

    if (backendHealth?.online === false) {
      setError('Cannot submit job: Backend server is offline at port 8000. Start it with `uvicorn depthwizard.main:app --app-dir backend --port 8000`.');
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
        const msg = errJson.detail?.detail || errJson.detail || 'Upload failed.';
        throw new Error(msg);
      }

      const data = await resp.json();
      onJobCreated(data.job_id);
    } catch (err: any) {
      setError(err.message || 'An error occurred during upload.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-md px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Globe2 className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
              DepthWizard <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">SIH 26175</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/50 hidden sm:inline-flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5 text-cyan-400" /> v1.1.0 Multi-City
              </span>
            </h1>
            <p className="text-xs text-slate-400">ISRO Single-View Height Estimation & 3D Flythrough</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          {backendHealth === null ? (
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
              Connecting...
            </span>
          ) : backendHealth.online ? (
            <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2.5 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Backend Online ({backendHealth.device?.toUpperCase() || 'Ready'})
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2.5 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Backend Offline (Port 8000)
            </span>
          )}
        </div>
      </header>

      {/* Backend Offline Warning Banner */}
      {backendHealth?.online === false && (
        <div className="bg-amber-950/80 border-b border-amber-700/50 px-8 py-2.5 text-xs font-mono text-amber-200 flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>
              <strong>Backend Disconnected:</strong> Could not reach FastAPI at <code className="bg-slate-900 px-1.5 py-0.5 rounded text-amber-300">/api/health</code>. Start the backend with: <code className="bg-slate-900 px-1.5 py-0.5 rounded text-cyan-300">uvicorn depthwizard.main:app --app-dir backend --port 8000</code>
            </span>
          </div>
          <button
            onClick={checkHealth}
            className="px-2.5 py-1 rounded bg-amber-800 hover:bg-amber-700 text-amber-100 text-xs font-sans transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Upload Form */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">Reconstruct 3D Digital Surface Models</h2>
            <p className="text-sm text-slate-400 mt-1">
              Upload single optical RGB remote sensing imagery (GeoTIFF, TIFF, PNG, or JPEG) to generate metric elevation models and interactive 3D terrain meshes.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {/* Drop Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center transition cursor-pointer group ${
                selectedFile
                  ? 'border-cyan-500/70 bg-cyan-950/20'
                  : 'border-slate-800 hover:border-cyan-500/50 hover:bg-slate-900/40 bg-slate-900/20'
              }`}
            >
              <input
                type="file"
                accept=".tif,.tiff,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />

              <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-cyan-400 mb-4 group-hover:scale-105 transition shadow-inner">
                {selectedFile ? <FileUp className="w-7 h-7" /> : <Upload className="w-7 h-7" />}
              </div>

              {selectedFile ? (
                <div>
                  <p className="font-semibold text-white text-base">{selectedFile.name}</p>
                  <p className="text-xs text-cyan-400 font-mono mt-1">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for processing
                  </p>
                </div>
              ) : (
                <div>
                  <p className="font-medium text-slate-200">Drag & drop imagery or browse files</p>
                  <p className="text-xs text-slate-500 mt-1">Supports GeoTIFF (WGS84/UTM), standard TIFF, PNG, and JPEG up to 8000×8000 px</p>
                </div>
              )}
            </div>

            {/* Error banner */}
            {error && (
              <div className="p-3.5 rounded-xl border border-rose-500/40 bg-rose-950/40 text-xs font-mono text-rose-300">
                {error}
              </div>
            )}

            {/* Advanced Parameters Accordion */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5 flex flex-col gap-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Pipeline Parameters
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-slate-300">
                    Assumed GSD (m/px)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.05"
                    max="10.0"
                    value={assumedGsd}
                    onChange={(e) => setAssumedGsd(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none transition"
                    placeholder="0.33"
                  />
                  <span className="text-[10px] text-slate-500">Auto-extracted for GeoTIFF; default 0.33m for plain imagery</span>
                </div>

                <div className="flex flex-col gap-1.5 sm:col-span-2">
                  <div className="flex justify-between items-center text-xs font-medium text-slate-300">
                    <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                      Model Architecture & Weights
                    </label>
                    <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                      GAMUS 3-City Trained
                    </span>
                  </div>
                  <select
                    value={modelVersion}
                    onChange={(e) => setModelVersion(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none transition"
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
                  <span className="text-[10px] text-slate-500">
                    Trained across 35.1M LiDAR ground truth pixels over Washington D.C., New York City, and Philadelphia
                  </span>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-slate-300">
                    Calibration Mode
                  </label>
                  <select
                    value={calibrationPath}
                    onChange={(e) => setCalibrationPath(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none transition"
                  >
                    <option value="">Auto Selector (Hierarchy B → A → C → D)</option>
                    <option value="PATH_A">Path A: SRTM Bare-Earth DTM</option>
                    <option value="PATH_B">Path B: Ground Control Points</option>
                    <option value="PATH_C">Path C: RANSAC Affine Disparity</option>
                    <option value="PATH_D">Path D: Relative Stretch [0, 1]</option>
                  </select>
                  <span className="text-[10px] text-slate-500">Auto engages the optimal scale recovery path</span>
                </div>

                <div className="flex flex-col gap-1.5 sm:col-span-2">
                  <div className="flex justify-between items-center text-xs font-medium text-slate-300">
                    <span>Vertical Exaggeration</span>
                    <span className="font-mono text-cyan-400 font-bold">{zExag}x</span>
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={zExag}
                    onChange={(e) => setZExag(e.target.value)}
                    className="accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                  />
                  <span className="text-[10px] text-slate-500">Scale terrain relief in exported 3D meshes (1.0x - 5.0x)</span>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !selectedFile}
              className="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 transition cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                  Uploading & Initializing...
                </>
              ) : (
                <>
                  Reconstruct 3D Digital Surface Model <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Recent Jobs list */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" /> Recent Jobs
            </h3>
            <span className="text-xs text-slate-500 font-mono">{recentJobs.length} models</span>
          </div>

          <div className="flex flex-col gap-2.5 max-h-[600px] overflow-y-auto pr-1">
            {recentJobs.length === 0 ? (
              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/20 p-8 text-center text-slate-500 text-xs font-mono">
                No jobs registered yet. Upload an image to start!
              </div>
            ) : (
              recentJobs.map((j) => (
                <div
                  key={j.job_id}
                  onClick={() => onJobSelect(j.job_id)}
                  className="rounded-xl border border-slate-800/80 hover:border-cyan-500/40 bg-slate-900/40 hover:bg-slate-900/80 p-4 transition cursor-pointer flex flex-col gap-2 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-white group-hover:text-cyan-300 transition">
                      #{j.job_id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        j.status === 'DONE'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                          : j.status === 'FAILED'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800/50'
                          : 'bg-cyan-950 text-cyan-400 border border-cyan-800/50 animate-pulse'
                      }`}
                    >
                      {j.status}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs text-slate-400 font-mono">
                    <span>Stage: {j.stage}</span>
                    <span>{j.progress}%</span>
                  </div>

                  {j.status === 'DONE' && (
                    <div className="flex items-center gap-1 text-[11px] text-cyan-400 font-medium pt-1">
                      <span>Launch 3D Flythrough</span> →
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
