import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Cpu,
  Eye,
  FileCheck,
  Globe,
  Radio,
  Scale,
} from 'lucide-react';
import { IsroHeader } from '../components/IsroHeader';

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
  onNavigateValidate?: (jobId: string) => void;
}

const STAGES = [
  {
    id: 'PREPROCESS',
    code: '01',
    label: 'IMAGE INGESTION & GSD',
    icon: Globe,
    desc: 'Bilinear downscale & 0.33m/px canonical GSD normalization',
    sub: 'Tiled Window Buffer',
  },
  {
    id: 'INFER',
    code: '02',
    label: 'DINOv2 INFERENCE',
    icon: Cpu,
    desc: 'Multi-scale Vision Transformer with DPT head regression',
    sub: '3-City GAMUS Weights',
  },
  {
    id: 'CALIBRATE',
    code: '03',
    label: 'GEODETIC SCALE FITTING',
    icon: Scale,
    desc: 'EGM96 geoid vertical datum / SRTM bare-earth DTM alignment',
    sub: 'Hierarchy B → A → C',
  },
  {
    id: 'EXPORT',
    code: '04',
    label: 'RASTER REPROJECTION',
    icon: FileCheck,
    desc: 'Tiled 32-bit Float GeoTIFF & 16-bit packed PNG heightmap',
    sub: 'Deflate Compression',
  },
  {
    id: 'MESH',
    code: '05',
    label: 'SURFACE MESH LODs',
    icon: Boxes,
    desc: 'Vectorized height-field triangulation into LOD0-2 GLB meshes',
    sub: 'Delaunay Decimation',
  },
];

export const JobStatusPage: React.FC<JobStatusPageProps> = ({
  jobId,
  onOpenViewer,
  onNavigateHome,
  onNavigateValidate,
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
    <div className="min-h-screen bg-[#050811] text-slate-100 flex flex-col font-sans relative">
      <div className="absolute inset-0 bg-aerospace-grid opacity-75 pointer-events-none z-0" />

      {/* ISRO Mission Header */}
      <IsroHeader
        currentPage="status"
        activeJobId={jobId}
        onNavigate={(page, id) => {
          if (page === 'upload' || page === 'dashboard') onNavigateHome();
          else if (page === 'viewer' && id) onOpenViewer(id);
          else if (page === 'validate' && id && onNavigateValidate) onNavigateValidate(id);
        }}
      />

      {/* Main Mission Operations Dashboard */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col gap-6 relative z-10 justify-center">
        {/* Mission Status Telemetry Ribbon */}
        <div className="mission-panel rounded-xl p-5 border border-[#1e315b] relative overflow-hidden flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#ff6600] via-[#0055a5] to-[#00c2cb]" />

          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-[#00c2cb]">
              <Radio className="w-3.5 h-3.5 text-[#ff6600] animate-pulse" />
              <span>ISRO SAC GROUND STATION TELEMETRY PIPELINE</span>
            </div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl sm:text-2xl font-black text-white font-display">
                MISSION PIPELINE #{jobId}
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-0.5">
              <span>ELAPSED TIME: <strong className="text-white">{elapsedSeconds}s</strong></span>
              <span>•</span>
              <span>GEODETIC DATUM: <strong className="text-[#00c2cb]">EGM96 ORTHOMETRIC</strong></span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border tracking-wider flex items-center gap-2 ${
                job?.status === 'DONE'
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-700/60 shadow-lg shadow-emerald-950/50'
                  : job?.status === 'FAILED'
                  ? 'bg-rose-950/80 text-rose-400 border-rose-700/60'
                  : 'bg-[#091834] text-[#00c2cb] border-[#00c2cb]/50 animate-pulse'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  job?.status === 'DONE'
                    ? 'bg-emerald-400'
                    : job?.status === 'FAILED'
                    ? 'bg-rose-400'
                    : 'bg-[#00c2cb] animate-ping'
                }`}
              />
              <span>{job?.status ? `STATUS: ${job.status}` : 'INITIALIZING TELEMETRY...'}</span>
            </div>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="mission-panel rounded-xl p-5 border border-[#1e315b] flex flex-col gap-2.5">
          <div className="flex justify-between items-center text-xs font-mono text-slate-300">
            <span className="flex items-center gap-1.5 uppercase tracking-wider font-semibold">
              <Clock className="w-3.5 h-3.5 text-[#ff6600]" /> OVERALL RECONSTRUCTION PROGRESS
            </span>
            <span className="text-sm font-bold text-white font-mono">{job?.progress || 0}%</span>
          </div>

          <div className="h-3.5 w-full bg-[#070e1d] rounded-full overflow-hidden border border-[#1e315b] p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-500 shadow-md ${
                job?.status === 'DONE'
                  ? 'bg-emerald-400'
                  : job?.status === 'FAILED'
                  ? 'bg-rose-500'
                  : 'bg-gradient-to-r from-[#ff6600] via-[#0055a5] to-[#00c2cb]'
              }`}
              style={{ width: `${Math.max(job?.progress || 0, 3)}%` }}
            />
          </div>

          <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-0.5">
            <span>STAGE: {job?.stage || 'STANDBY'}</span>
            <span>VERIFICATION: AUTOMATIC (PARITY TESTED)</span>
          </div>
        </div>

        {/* 5-Stage Aerospace Sequencer Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {STAGES.map((s) => {
            const status = getStageStatus(s.id);
            const Icon = s.icon;

            return (
              <div
                key={s.id}
                className={`mission-panel rounded-xl border p-4 flex flex-col justify-between gap-3 transition relative overflow-hidden ${
                  status === 'active'
                    ? 'border-[#00c2cb] bg-[#091b38] shadow-lg shadow-[#0055a5]/30'
                    : status === 'completed'
                    ? 'border-emerald-700/60 bg-[#071922]/60'
                    : 'border-[#1e315b]/60 bg-[#091224]/50 opacity-60'
                }`}
              >
                {/* Active pulse highlight */}
                {status === 'active' && (
                  <div className="absolute top-0 left-0 right-0 h-1 bg-[#00c2cb] animate-pulse" />
                )}

                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-[#ff9944]">
                    STAGE {s.code}
                  </span>
                  {status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : status === 'active' ? (
                    <span className="w-2 h-2 rounded-full bg-[#00c2cb] animate-ping" />
                  ) : null}
                </div>

                <div className="w-10 h-10 rounded-lg flex items-center justify-center border border-[#1e315b] bg-[#070e1d]">
                  <Icon
                    className={`w-5 h-5 ${
                      status === 'active'
                        ? 'text-[#00c2cb]'
                        : status === 'completed'
                        ? 'text-emerald-400'
                        : 'text-slate-500'
                    }`}
                  />
                </div>

                <div>
                  <h4 className="font-bold text-xs text-white font-display tracking-wide">{s.label}</h4>
                  <p className="text-[10px] text-slate-400 mt-1 leading-relaxed font-sans">{s.desc}</p>
                </div>

                <div className="pt-2 border-t border-[#1e315b]/40 text-[9px] font-mono text-slate-500">
                  {s.sub}
                </div>
              </div>
            );
          })}
        </div>

        {/* Failure Report */}
        {job?.status === 'FAILED' && (
          <div className="p-4 rounded-xl border border-rose-600 bg-rose-950/50 text-xs font-mono text-rose-200 flex items-start gap-3 shadow-xl">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <p className="font-bold text-sm text-rose-100 font-display">Mission Processing Terminated</p>
              <p className="mt-1">{job.error || 'Check server logs for GPU or dataset details.'}</p>
            </div>
          </div>
        )}

        {/* Completion Launch Deck */}
        {job?.status === 'DONE' && (
          <div className="mission-panel rounded-xl p-6 border border-[#00c2cb]/50 flex flex-col items-center gap-4 text-center shadow-2xl shadow-[#0055a5]/30">
            <div className="w-12 h-12 rounded-full bg-emerald-950/80 border border-emerald-600/80 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-white font-display tracking-wide">
                Surface Reconstruction Completed &amp; Geodetically Registered
              </h3>
              <p className="text-xs text-slate-300 font-mono mt-1">
                All 3 LOD GLB meshes, 32-bit metric GeoTIFF, and 16-bit heightmap generated successfully.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => onOpenViewer(jobId)}
                className="py-3 px-6 rounded-xl bg-gradient-to-r from-[#0055a5] to-[#00c2cb] hover:from-[#004488] hover:to-[#00a2ab] text-white font-bold text-sm flex items-center gap-2.5 shadow-lg shadow-[#0055a5]/40 transition cursor-pointer font-display tracking-wider uppercase border border-[#00c2cb]/60"
              >
                <Eye className="w-4 h-4 text-white" />
                <span>LAUNCH 3D RECONNAISSANCE COCKPIT</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              {onNavigateValidate && (
                <button
                  type="button"
                  onClick={() => onNavigateValidate(jobId)}
                  className="py-3 px-5 rounded-xl bg-[#09152b] hover:bg-[#11244a] text-slate-200 font-bold text-xs flex items-center gap-2 transition cursor-pointer font-mono border border-[#1e315b]"
                >
                  <Scale className="w-4 h-4 text-[#ff9944]" />
                  <span>EVALUATE LIDAR BENCHMARK</span>
                </button>
              )}

              <button
                type="button"
                onClick={onNavigateHome}
                className="py-3 px-4 rounded-xl bg-[#070e1d] hover:bg-[#0f1d38] text-slate-400 hover:text-white text-xs font-mono flex items-center gap-1.5 transition cursor-pointer border border-[#1e315b]"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>RETURN TO INGESTION</span>
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
