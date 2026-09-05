import { useEffect, useState } from 'react';
import { ArrowLeft, Sparkles, Upload } from 'lucide-react';

interface MetricsData {
  job_id: string;
  status: string;
  metrics_absolute?: {
    bias: number;
    mae: number;
    rmse: number;
    medae: number;
    rmse_db: number;
    pearson_r: number;
    delta1: number;
    delta2_5: number;
    valid_pixels: number;
  };
  terrain_tag?: string;
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
        throw new Error('Failed to evaluate reference DSM.');
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Error uploading reference');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-md px-8 py-4 flex items-center justify-between">
        <button
          onClick={onNavigateBack}
          className="text-xs font-mono text-slate-400 hover:text-white transition flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to 3D Viewer
        </button>
        <span className="font-mono text-xs text-cyan-400 font-bold">Validation & Accuracy Report</span>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto p-8 flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Elevation Model Accuracy Verification</h2>
          <p className="text-xs text-slate-400 mt-1">
            Compare predicted DSM elevations against ground truth LiDAR / reference DEM for Job #{jobId}
          </p>
        </div>

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
              {isUploading ? 'Evaluating...' : 'Compute Validation Metrics'}
            </button>
          </form>

          {error && <p className="text-xs font-mono text-rose-400">{error}</p>}
        </div>

        {/* Metrics Display */}
        {metrics?.metrics_absolute ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Validation Metrics (LiDAR vs Predicted DSM)
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                STATUS: {metrics.status}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">Mean Bias (ME)</span>
                <span className="text-lg font-bold text-white">{metrics.metrics_absolute.bias.toFixed(3)} m</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">MAE</span>
                <span className="text-lg font-bold text-cyan-300">{metrics.metrics_absolute.mae.toFixed(3)} m</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">RMSE</span>
                <span className="text-lg font-bold text-emerald-400">{metrics.metrics_absolute.rmse.toFixed(3)} m</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">Pearson r</span>
                <span className="text-lg font-bold text-amber-300">{metrics.metrics_absolute.pearson_r.toFixed(3)}</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">Median AE (MedAE)</span>
                <span className="text-lg font-bold text-white">{metrics.metrics_absolute.medae.toFixed(3)} m</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">RMSE_db (De-biased)</span>
                <span className="text-lg font-bold text-white">{metrics.metrics_absolute.rmse_db.toFixed(3)} m</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">δ &lt; 1.0 m</span>
                <span className="text-lg font-bold text-emerald-400">{(metrics.metrics_absolute.delta1 * 100).toFixed(1)}%</span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 flex flex-col gap-1">
                <span className="text-slate-400 text-[11px]">δ &lt; 2.5 m</span>
                <span className="text-lg font-bold text-emerald-400">{(metrics.metrics_absolute.delta2_5 * 100).toFixed(1)}%</span>
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
