import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Cpu,
  FileCheck,
  Globe,
  Scale,
} from 'lucide-react';

interface JobStatus {
  job_id: string;
  status: string;
  stage: string;
  progress: number;
  error?: string;
  created_at: string;
  updated_at: string;
  metadata?: {
    is_georeferenced?: boolean;
    gsd_m?: number;
    width?: number;
    height?: number;
    infer_time_seconds?: number;
    artifacts?: string[];
  };
}

interface JobStatusPageProps {
  jobId: string;
  onOpenViewer: (jobId: string) => void;
  onNavigateHome: () => void;
}

const STAGES = [
  { id: 'PREPROCESS', label: 'Preprocess', icon: Globe, desc: 'Image normalization & GSD canonicalization' },
  { id: 'INFER', label: 'Inference', icon: Cpu, desc: 'Native DINOv2 + DPTHead sliding tile inference' },
  { id: 'CALIBRATE', label: 'Calibration', icon: Scale, desc: 'SRTM bare-earth DTM / GCP scale fitting' },
  { id: 'EXPORT', label: 'Export', icon: FileCheck, desc: 'Tiled GeoTIFF (EGM96) & 16-bit heightmap' },
  { id: 'MESH', label: 'Mesh LODs', icon: Boxes, desc: 'Vectorized triangulation & GLB generation' },
];

export const JobStatusPage: React.FC<JobStatusPageProps> = ({
  jobId,
  onOpenViewer,
  onNavigateHome,
}) => {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let timer: any;
    let pollInterval: any;

    const poll = async () => {
      try {
        const resp = await fetch(`/api/jobs/${jobId}`);
        if (resp.ok) {
          const data: JobStatus = await resp.json();
          setJob(data);
          if (data.status === 'DONE' || data.status === 'FAILED') {
            clearInterval(pollInterval);
            clearInterval(timer);
          }
        }
      } catch (err) {
        console.error('Failed to fetch job status:', err);
      }
    };

    poll();
    pollInterval = setInterval(poll, 1000);
    timer = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timer);
    };
  }, [jobId]);

  const getStageStatus = (stageId: string) => {
    if (!job) return 'pending';
    if (job.status === 'FAILED') return 'failed';
    if (job.status === 'DONE') return 'completed';

    const stageOrder = ['PREPROCESS', 'INFER', 'CALIBRATE', 'EXPORT', 'MESH', 'DONE'];
    const currentIdx = stageOrder.indexOf(job.stage);
    const thisIdx = stageOrder.indexOf(stageId);

    if (thisIdx < currentIdx) return 'completed';
    if (thisIdx === currentIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-md px-8 py-4 flex items-center justify-between">
        <button
          onClick={onNavigateHome}
          className="text-xs font-mono text-slate-400 hover:text-white transition flex items-center gap-1.5"
        >
          ← Back to Upload
        </button>
        <span className="font-mono text-xs text-cyan-400 font-bold">Job #{jobId}</span>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-8 flex flex-col gap-8 justify-center">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Processing Pipeline</h2>
            <p className="text-xs font-mono text-slate-400 mt-1">
              Elapsed Time: {elapsedSeconds}s • Status: {job?.status || 'INITIALIZING'}
            </p>
          </div>

          <div
            className={`px-3 py-1 rounded-full text-xs font-mono font-bold border ${
              job?.status === 'DONE'
                ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
                : job?.status === 'FAILED'
                ? 'bg-rose-950/80 text-rose-400 border-rose-800/60'
                : 'bg-cyan-950/80 text-cyan-400 border-cyan-800/60 animate-pulse'
            }`}
          >
            {job?.status || 'PENDING'}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs font-mono text-slate-400">
            <span>Overall Progress</span>
            <span className="font-bold text-white">{job?.progress || 0}%</span>
          </div>
          <div className="h-3 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full transition-all duration-500 shadow-lg shadow-cyan-500/20"
              style={{ width: `${job?.progress || 0}%` }}
            />
          </div>
        </div>

        {/* Pipeline Stage Diagram */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {STAGES.map((s) => {
            const status = getStageStatus(s.id);
            const Icon = s.icon;

            return (
              <div
                key={s.id}
                className={`rounded-2xl border p-4 flex flex-col gap-3 transition ${
                  status === 'active'
                    ? 'border-cyan-500/70 bg-cyan-950/30 shadow-lg shadow-cyan-500/10'
                    : status === 'completed'
                    ? 'border-emerald-500/50 bg-emerald-950/10'
                    : 'border-slate-800 bg-slate-900/20 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                      status === 'active'
                        ? 'bg-cyan-500 text-slate-950 animate-bounce'
                        : status === 'completed'
                        ? 'bg-emerald-500 text-slate-950'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  {status === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                </div>

                <div>
                  <h4 className="font-bold text-sm text-white">{s.label}</h4>
                  <p className="text-[11px] text-slate-400 mt-1 leading-snug">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Error message banner */}
        {job?.status === 'FAILED' && (
          <div className="p-4 rounded-2xl border border-rose-500/50 bg-rose-950/40 text-xs font-mono text-rose-300 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <p className="font-bold text-sm text-rose-200">Processing Failed</p>
              <p className="mt-1">{job.error || 'An unexpected error occurred.'}</p>
            </div>
          </div>
        )}

        {/* Action Button: Open 3D Viewer */}
        {job?.status === 'DONE' && (
          <div className="flex flex-col items-center gap-3 pt-4">
            <button
              onClick={() => onOpenViewer(jobId)}
              className="py-4 px-8 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold text-base flex items-center gap-3 shadow-xl shadow-cyan-500/25 transition cursor-pointer"
            >
              Launch Interactive 3D Flythrough Viewer <ArrowRight className="w-5 h-5" />
            </button>
            <p className="text-xs text-slate-400 font-mono">Elevation model and 3 LOD meshes ready for exploration</p>
          </div>
        )}
      </main>
    </div>
  );
};
