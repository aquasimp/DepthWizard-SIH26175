import { useEffect, useState } from 'react';
import { ArrowLeft, CheckCircle2, Download, Layers, Sparkles, Upload, Wrench } from 'lucide-react';

interface MetricsData {
  job_id: string;
  status: string;
  metrics_absolute?: {
    bias: number;
    mae: number;
    rmse: number;
    medae: number;
    rmse_db: number;
    std_error?: number;
    le90?: number;
    le95?: number;
    nmad?: number;
    pearson_r: number;
    delta1: number;
    delta2_5: number;
    valid_pixels: number;
  };
  terrain_tag?: string;
  shift_applied?: {
    shift_x: number;
    shift_y: number;
    shift_magnitude: number;
    shift_applied: boolean;
    warning?: string | null;
  };
  histogram?: {
    counts: number[];
    bin_edges: number[];
    bin_centers: number[];
    range_m: [number, number];
  };
  diff_artifact_url?: string;
}

interface ValidatePageProps {
  jobId: string;
  onNavigateBack: () => void;
}

export const ValidatePage: React.FC<ValidatePageProps> = ({
  jobId,
  onNavigateBack,
}) => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [refFile, setRefFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // GCP Recalibration State
  const [showGcpForm, setShowGcpForm] = useState(false);
  const [gcps, setGcps] = useState([
    { x: 50, y: 50, z_true: 120.0 },
    { x: 200, y: 150, z_true: 135.5 },
    { x: 400, y: 350, z_true: 110.2 },
  ]);
  const [isRecalibrating, setIsRecalibrating] = useState(false);
  const [recalibrateMsg, setRecalibrateMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/jobs/${jobId}/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setMetrics(data);
      })
      .catch(() => {});
  }, [jobId]);

  const handleUploadRef = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refFile) return;

    setIsUploading(true);
    setError(null);
    const fd = new FormData();
    fd.append('file', refFile);

    try {
      const res = await fetch(`/api/jobs/${jobId}/reference`, {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail?.detail || errJson.detail || 'Failed to evaluate reference DSM.');
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Error uploading reference');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRecalibrate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRecalibrating(true);
    setRecalibrateMsg(null);
    try {
      const res = await fetch(`/api/jobs/${jobId}/gcps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gcps }),
      });
      if (!res.ok) throw new Error('Recalibration failed.');
      setRecalibrateMsg('GCP Recalibration successful! Re-upload reference to verify new accuracy.');
    } catch (err: any) {
      setRecalibrateMsg(`Error: ${err.message}`);
    } finally {
      setIsRecalibrating(false);
    }
  };

  const maxHistCount = metrics?.histogram?.counts ? Math.max(...metrics.histogram.counts, 1) : 1;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-md px-8 py-4 flex items-center justify-between">
        <button
          onClick={onNavigateBack}
          className="text-xs font-mono text-slate-400 hover:text-white transition flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to 3D Viewer
        </button>
        <span className="font-mono text-xs text-cyan-400 font-bold">Elevation Validation & Accuracy Analysis</span>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto p-8 flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Elevation Model Validation</h2>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Ground truth LiDAR / Reference DEM co-registration and accuracy benchmark for Job #{jobId}
            </p>
          </div>
          <button
            onClick={() => setShowGcpForm(!showGcpForm)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-200 border border-slate-700 transition w-fit"
          >
            <Wrench className="w-3.5 h-3.5 text-amber-400" />
            {showGcpForm ? 'Hide GCP Recalibration' : 'Recalibrate with GCPs (Path B)'}
          </button>
        </div>

        {/* GCP Recalibration Form Modal / Card */}
        {showGcpForm && (
          <div className="rounded-2xl border border-amber-900/50 bg-amber-950/20 p-6 flex flex-col gap-4 font-mono text-xs">
            <h3 className="font-bold text-amber-300 flex items-center gap-2">
              <Wrench className="w-4 h-4" /> Ground Control Point (GCP) Recalibration (Path B Huber Fit)
            </h3>
            <p className="text-slate-400 text-[11px]">
              Provide at least 3 Ground Control Points with known true orthometric heights ($z_{'{true}'}$) to fit robust affine calibration.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {gcps.map((g, idx) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 flex flex-col gap-2">
                  <span className="font-bold text-cyan-400">GCP #{idx + 1}</span>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Pixel X:</span>
                    <input
                      type="number"
                      value={g.x}
                      onChange={(e) => {
                        const updated = [...gcps];
                        updated[idx].x = parseFloat(e.target.value) || 0;
                        setGcps(updated);
                      }}
                      className="w-20 bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-right"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Pixel Y:</span>
                    <input
                      type="number"
                      value={g.y}
                      onChange={(e) => {
                        const updated = [...gcps];
                        updated[idx].y = parseFloat(e.target.value) || 0;
                        setGcps(updated);
                      }}
                      className="w-20 bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-right"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">True Z (m):</span>
                    <input
                      type="number"
                      step="0.1"
                      value={g.z_true}
                      onChange={(e) => {
                        const updated = [...gcps];
                        updated[idx].z_true = parseFloat(e.target.value) || 0;
                        setGcps(updated);
                      }}
                      className="w-20 bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-right text-emerald-400 font-bold"
                    />
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={handleRecalibrate}
              disabled={isRecalibrating}
              className="mt-2 w-fit px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold disabled:opacity-50 transition"
            >
              {isRecalibrating ? 'Recalibrating...' : 'Apply GCP Huber Recalibration'}
            </button>
            {recalibrateMsg && <p className="text-xs text-amber-300">{recalibrateMsg}</p>}
          </div>
        )}

        {/* Upload Reference DSM */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-slate-200 font-mono flex items-center gap-2">
            <Upload className="w-4 h-4 text-cyan-400" /> Upload Ground Truth Reference DSM (GeoTIFF)
          </h3>

          <form onSubmit={handleUploadRef} className="flex flex-col sm:flex-row gap-3 items-center">
            <input
              type="file"
              accept=".tif,.tiff"
              onChange={(e) => e.target.files && setRefFile(e.target.files[0])}
              className="text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-cyan-500 file:text-slate-950 hover:file:bg-cyan-400 cursor-pointer"
            />
            <button
              type="submit"
              disabled={isUploading || !refFile}
              className="px-5 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-xs font-mono transition"
            >
              {isUploading ? 'Co-registering & Evaluating...' : 'Run Co-registration & Evaluate'}
            </button>
          </form>

          {error && <p className="text-xs font-mono text-rose-400">{error}</p>}
        </div>

        {/* Metrics Display */}
        {metrics?.metrics_absolute ? (
          <div className="flex flex-col gap-6">
            {/* Shift & Co-registration Banner */}
            {metrics.shift_applied && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>
                    Sub-pixel Co-registration:{' '}
                    <strong className="text-cyan-400">
                      ΔX = {metrics.shift_applied.shift_x}px, ΔY = {metrics.shift_applied.shift_y}px
                    </strong>{' '}
                    (Magnitude: {metrics.shift_applied.shift_magnitude}px)
                  </span>
                </div>
                {metrics.shift_applied.warning && (
                  <span className="text-amber-400 text-[11px] bg-amber-950/40 border border-amber-800/60 rounded px-2 py-0.5">
                    {metrics.shift_applied.warning}
                  </span>
                )}
              </div>
            )}

            {/* Metric Score Cards */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono flex items-center gap-2">
                  <Sparkles className="w-4 h-4" /> Photogrammetric Accuracy Metrics (LiDAR vs Predicted DSM)
                </span>
                <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                  TAG: {metrics.terrain_tag || 'Standard'}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">RMSE (Total Error)</span>
                  <span className="text-xl font-bold text-emerald-400">
                    {metrics.metrics_absolute.rmse.toFixed(3)} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">MAE (Mean Absolute)</span>
                  <span className="text-xl font-bold text-cyan-300">
                    {metrics.metrics_absolute.mae.toFixed(3)} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">LE90 (90% Conf)</span>
                  <span className="text-xl font-bold text-indigo-400">
                    {metrics.metrics_absolute.le90?.toFixed(3) || '—'} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">NMAD (Robust Std)</span>
                  <span className="text-xl font-bold text-amber-300">
                    {metrics.metrics_absolute.nmad?.toFixed(3) || '—'} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">Mean Bias (ME)</span>
                  <span className="text-lg font-bold text-white">
                    {metrics.metrics_absolute.bias.toFixed(3)} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">Median AE (MedAE)</span>
                  <span className="text-lg font-bold text-white">
                    {metrics.metrics_absolute.medae.toFixed(3)} m
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">Pearson r Correlation</span>
                  <span className="text-lg font-bold text-white">
                    {metrics.metrics_absolute.pearson_r.toFixed(3)}
                  </span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 flex flex-col gap-1">
                  <span className="text-slate-400 text-[11px]">δ &lt; 1.0m Inliers</span>
                  <span className="text-lg font-bold text-emerald-400">
                    {(metrics.metrics_absolute.delta1 * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Difference Map & Histogram Visualization */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Difference Heatmap */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-4 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-slate-200 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-rose-400" /> Signed Difference Map (Pred − Ref)
                  </span>
                  <a
                    href={`/api/jobs/${jobId}/artifacts/diff.tif`}
                    download="diff.tif"
                    className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300"
                  >
                    <Download className="w-3 h-3" /> diff.tif
                  </a>
                </div>

                <div className="relative aspect-square w-full rounded-xl overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center">
                  <img
                    src={`/api/jobs/${jobId}/artifacts/diff.png?t=${Date.now()}`}
                    alt="Elevation difference heatmap"
                    className="w-full h-full object-contain"
                  />
                </div>

                {/* Color Legend */}
                <div className="flex flex-col gap-1 text-[10px] text-slate-400">
                  <div className="h-3 w-full rounded bg-gradient-to-r from-blue-600 via-slate-100 to-red-600" />
                  <div className="flex justify-between font-mono">
                    <span>−15 m (Pred Lower)</span>
                    <span>0 m (Exact)</span>
                    <span>+15 m (Pred Higher)</span>
                  </div>
                </div>
              </div>

              {/* Error Distribution Histogram */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-4 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-slate-200">Error Distribution Histogram</span>
                  <span className="text-[11px] text-slate-400">
                    {metrics.metrics_absolute.valid_pixels.toLocaleString()} points
                  </span>
                </div>

                {metrics.histogram?.counts && metrics.histogram.counts.length > 0 ? (
                  <div className="flex-1 flex flex-col justify-end gap-1">
                    <div className="flex items-end h-48 gap-0.5 bg-slate-950/60 rounded-xl p-3 border border-slate-800">
                      {metrics.histogram.counts.map((count, i) => {
                        const heightPct = Math.max((count / maxHistCount) * 100, 1);
                        const center = metrics.histogram?.bin_centers[i] ?? 0;
                        const isNearZero = Math.abs(center) < 1.0;
                        return (
                          <div
                            key={i}
                            className="flex-1 rounded-t transition-all hover:opacity-80"
                            style={{
                              height: `${heightPct}%`,
                              backgroundColor: isNearZero ? '#10b981' : '#38bdf8',
                            }}
                            title={`Bin: ${center.toFixed(1)}m | Count: ${count}`}
                          />
                        );
                      })}
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500 pt-1">
                      <span>−15 m</span>
                      <span className="text-emerald-400 font-bold">0.0 m</span>
                      <span>+15 m</span>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">
                    Histogram data unavailable.
                  </div>
                )}

                <div className="text-[11px] text-slate-400 bg-slate-950/40 rounded-xl p-3 border border-slate-800/80">
                  <p>
                    <strong className="text-emerald-400">Green bars</strong> highlight error within &plusmn;1.0 m.
                    Symmetric clustering around 0.0m confirms low bias and high model accuracy.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/20 p-8 text-center text-slate-500 text-xs font-mono">
            No reference evaluation yet. Upload a ground truth GeoTIFF above to view accuracy metrics.
          </div>
        )}
      </main>
    </div>
  );
};
