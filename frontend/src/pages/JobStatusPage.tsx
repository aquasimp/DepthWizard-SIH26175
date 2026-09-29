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
import { getApiBase } from '../utils/apiConfig';

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
  isDark?: boolean;
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
      if (jobId.startsWith('client_') || jobId === 'demo') {
        setJob({
          job_id: jobId,
          status: 'DONE',
          stage: 'COMPLETE',
          progress: 100,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        clearInterval(pollInterval);
        clearInterval(timer);
        return;
      }

      try {
        const apiBase = getApiBase();
        const resp = await fetch(apiBase ? `${apiBase}/api/jobs/${jobId}` : `/api/jobs/${jobId}`);
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
            <Radio className="w-3.5 h-3.5 text-[#ff6600] animate-pulse" />
            <span>ISRO SAC GROUND STATION TELEMETRY PIPELINE</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div
            className={`status-badge ${
              job?.status === 'DONE'
                ? 'done'
                : job?.status === 'FAILED'
                ? 'failed'
                : 'active'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                job?.status === 'DONE'
                  ? 'bg-emerald-500'
                  : job?.status === 'FAILED'
                  ? 'bg-rose-500'
                  : 'bg-[#0284c7] animate-ping'
              }`}
            />
            <span>{job?.status ? `STATUS: ${job.status}` : 'INITIALIZING TELEMETRY...'}</span>
          </div>
        </div>
      </div>

      {/* Mission Status Telemetry Ribbon */}
      <div className="status-telemetry-card">
        <div className="status-accent-bar" />

        <div className="status-header-content">
          <div className="status-tag">
            <Radio className="w-3.5 h-3.5 text-[#ff6600]" />
            <span>TELEMETRY STREAM ACTIVE • REAL-TIME FEED</span>
          </div>
          <h2 className="status-job-title">
            MISSION PIPELINE #{jobId}
          </h2>
          <div className="status-meta-row">
            <span>
              ELAPSED TIME: <strong>{elapsedSeconds}s</strong>
            </span>
            <span>•</span>
            <span>
              GEODETIC DATUM: <strong className="text-[#0284c7]">EGM96 ORTHOMETRIC</strong>
            </span>
            <span>•</span>
            <span>
              AI BACKBONE: <strong className="text-[#ff6600]">DINOv2-ViT-L/14</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`status-badge ${
              job?.status === 'DONE'
                ? 'done'
                : job?.status === 'FAILED'
                ? 'failed'
                : 'active'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                job?.status === 'DONE'
                  ? 'bg-emerald-500'
                  : job?.status === 'FAILED'
                  ? 'bg-rose-500'
                  : 'bg-[#0284c7] animate-ping'
              }`}
            />
            <span>{job?.status ? `PIPELINE ${job.status}` : 'PROCESSING...'}</span>
          </div>
        </div>
      </div>

      {/* Global Progress Bar */}
      <div className="status-progress-card">
        <div className="status-progress-header">
          <span className="status-progress-title-group">
            <Clock className="w-4 h-4 text-[#ff6600]" />
            <span>OVERALL RECONSTRUCTION PROGRESS</span>
          </span>
          <span className="status-progress-percent">{job?.progress || 0}%</span>
        </div>

        <div className="status-progress-track">
          <div
            className="status-progress-fill"
            style={{ width: `${Math.max(job?.progress || 0, 3)}%` }}
          />
        </div>

        <div className="status-progress-footer">
          <span>STAGE: <strong>{job?.stage || 'STANDBY'}</strong></span>
          <span>VERIFICATION: AUTOMATIC (PARITY TESTED)</span>
        </div>
      </div>

      {/* 5-Stage Aerospace Sequencer Grid */}
      <div className="status-stages-grid">
        {STAGES.map((s) => {
          const status = getStageStatus(s.id);
          const Icon = s.icon;

          return (
            <div
              key={s.id}
              className={`status-stage-card ${
                status === 'active'
                  ? 'status-active'
                  : status === 'completed'
                  ? 'status-completed'
                  : ''
              }`}
            >
              <div className="status-stage-top">
                <span className="status-stage-code">STAGE {s.code}</span>
                {status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : status === 'active' ? (
                  <span className="w-2.5 h-2.5 rounded-full bg-[#0284c7] animate-ping" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full border border-[var(--border-subtle)]" />
                )}
              </div>

              <div className="status-stage-icon-box">
                <Icon
                  className={`w-5 h-5 ${
                    status === 'active'
                      ? 'text-[#0284c7]'
                      : status === 'completed'
                      ? 'text-emerald-500'
                      : 'text-slate-400'
                  }`}
                />
              </div>

              <div className="flex-1 flex flex-col justify-start">
                <h4 className="status-stage-title">{s.label}</h4>
                <p className="status-stage-desc">{s.desc}</p>
              </div>

              <div className="status-stage-sub">
                <span className="status-sub-dot" />
                <span>{s.sub}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Failure Report */}
      {job?.status === 'FAILED' && (
        <div className="status-telemetry-card" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(239, 68, 68, 0.05)' }}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-rose-600 font-display">Mission Processing Terminated</p>
              <p className="text-xs text-rose-500 mt-1">{job.error || 'Check server logs for GPU or dataset details.'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Completion Launch Deck */}
      {job?.status === 'DONE' && (
        <div className="status-completion-deck">
          <div className="status-completion-icon-ring">
            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
          </div>

          <div>
            <h3 className="status-completion-title">
              Surface Reconstruction Completed &amp; Geodetically Registered
            </h3>
            <p className="status-completion-desc">
              All 3 LOD GLB meshes, 32-bit metric GeoTIFF, and 16-bit heightmap generated successfully.
            </p>
          </div>

          <div className="status-completion-actions">
            <button
              type="button"
              onClick={() => onOpenViewer(jobId)}
              className="btn-launch-cockpit"
            >
              <Eye className="w-4 h-4 text-white" />
              <span>LAUNCH 3D RECONNAISSANCE COCKPIT</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {onNavigateValidate && (
              <button
                type="button"
                onClick={() => onNavigateValidate(jobId)}
                className="btn-validate-benchmark"
              >
                <Scale className="w-4 h-4 text-[#ff6600]" />
                <span>EVALUATE LIDAR BENCHMARK</span>
              </button>
            )}

            <button
              type="button"
              onClick={onNavigateHome}
              className="btn-return-ingestion"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>RETURN TO INGESTION</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

