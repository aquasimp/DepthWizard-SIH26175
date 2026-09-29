import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Info,
  Server,
  ShieldAlert,
  Sparkles,
  Wrench,
  X,
  CheckCircle2,
} from 'lucide-react';

export const isVercelEnvironment = (): boolean => {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname.toLowerCase();
  return (
    host.includes('vercel.app') ||
    host.includes('depthwizardd') ||
    (window as any).__FORCE_VERCEL_NOTICE__ === true
  );
};

interface VercelNoticeModalProps {
  onOpenSettings?: () => void;
  onViewBenchmark?: () => void;
}

export const VercelNoticeModal: React.FC<VercelNoticeModalProps> = ({
  onOpenSettings,
  onViewBenchmark,
}) => {
  const [isVercel, setIsVercel] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  useEffect(() => {
    const vercelDetected = isVercelEnvironment();
    setIsVercel(vercelDetected);

    if (vercelDetected) {
      // Check if user has already acknowledged the modal this session
      const acknowledged = sessionStorage.getItem('depthwizard_vercel_acknowledged');
      if (!acknowledged) {
        setShowModal(true);
      }
    }
  }, []);

  if (!isVercel) return null;

  const handleDismissModal = () => {
    sessionStorage.setItem('depthwizard_vercel_acknowledged', 'true');
    setShowModal(false);
  };

  return (
    <>
      {/* 1. TOP PERSISTENT WARNING BANNER ON VERCEL */}
      {!bannerDismissed && (
        <div className="w-full bg-[#1c1204] border-b border-[#ff6600]/40 text-amber-200 px-3 sm:px-4 py-2 text-xs font-mono flex items-center justify-between gap-3 shadow-md z-50 relative">
          <div className="flex items-center gap-2 overflow-hidden">
            <AlertTriangle className="w-4 h-4 text-[#ff9944] shrink-0 animate-pulse" />
            <span className="truncate">
              <strong className="text-[#ff9944]">VERCEL HOSTING NOTICE:</strong> PyTorch AI Models cannot run on Vercel serverless edge. In-browser client engine &amp; 3D demo mode active.
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="px-2 py-0.5 rounded bg-[#ff6600]/20 hover:bg-[#ff6600]/40 text-[#ff9944] hover:text-white border border-[#ff6600]/50 text-[11px] font-bold transition cursor-pointer"
            >
              DETAILS &amp; WORKAROUNDS
            </button>
            <button
              type="button"
              onClick={() => setBannerDismissed(true)}
              className="text-slate-400 hover:text-white p-0.5 rounded cursor-pointer"
              title="Dismiss banner"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* 2. MANDATORY MODAL PROMPT FOR EVALUATORS & USERS */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div
            className="w-full max-w-2xl bg-[#070e1d] border-2 border-[#ff6600] rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans relative"
            style={{ boxShadow: '0 0 50px rgba(255, 102, 0, 0.35)' }}
          >
            {/* Top Warning Strip */}
            <div className="bg-gradient-to-r from-[#ff6600] via-[#e05a00] to-[#b34000] px-5 py-3 text-slate-950 flex items-center justify-between font-mono font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-slate-950" />
                <span>MANDATORY SYSTEM NOTICE · VERCEL DEPLOYMENT</span>
              </div>
              <span className="bg-slate-950/20 px-2 py-0.5 rounded text-[10px]">
                STATIC WEB TIER
              </span>
            </div>

            {/* Modal Body */}
            <div className="p-6 flex flex-col gap-4 text-slate-200">
              <div className="flex flex-col gap-1 border-b border-[#1e315b]/80 pb-3">
                <h3 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2.5 font-display">
                  <span>AI Models Not Supported on Vercel Serverless</span>
                </h3>
                <p className="text-xs text-[#ff9944] font-mono">
                  Environment: Vercel Edge (<code className="underline">{typeof window !== 'undefined' ? window.location.hostname : 'depthwizardd.vercel.app'}</code>)
                </p>
              </div>

              {/* Core Notice Box */}
              <div className="p-3.5 rounded-xl border border-amber-500/40 bg-[#161106] text-xs font-mono text-amber-200 leading-relaxed flex flex-col gap-2">
                <div className="flex items-start gap-2 text-amber-300 font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>Why you may encounter an issue triggering remote model inference:</span>
                </div>
                <p className="text-amber-200/90 text-[11px] pl-6">
                  DepthWizard's full AI architecture requires <strong>PyTorch with NVIDIA CUDA GPU acceleration</strong> to execute our <strong>35.1M-parameter multi-scale neural elevation pipeline (DINOv2-S + DPT Head + GDAL/Trimesh)</strong>. Vercel is a serverless frontend hosting tier that cannot run persistent PyTorch CUDA neural backends.
                </p>
              </div>

              {/* Functional Capabilities Grid */}
              <div className="flex flex-col gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#00c2cb] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" /> Available Operational Modes on Vercel:
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs font-mono">
                  <div className="p-3 rounded-lg border border-[#1e315b] bg-[#09152b] flex flex-col gap-1">
                    <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> 1. Interactive 3D Viewer
                    </span>
                    <p className="text-slate-300 text-[10px] leading-relaxed">
                      Pre-calculated LiDAR DSMs and 3D textured meshes load with full lighting, slope hazard shaders, and measurement tools.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#1e315b] bg-[#09152b] flex flex-col gap-1">
                    <span className="font-bold text-[#00c2cb] flex items-center gap-1.5 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#00c2cb]" /> 2. In-Browser Client Depth
                    </span>
                    <p className="text-slate-300 text-[10px] leading-relaxed">
                      If you upload custom imagery on Vercel, DepthWizard activates our client-side WebGL engine directly in your browser.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#1e315b] bg-[#09152b] flex flex-col gap-1">
                    <span className="font-bold text-indigo-300 flex items-center gap-1.5 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" /> 3. Verified LiDAR Benchmarks
                    </span>
                    <p className="text-slate-300 text-[10px] leading-relaxed">
                      Examine authentic accuracy benchmarks (RMSE 3.82m Urban, 4.47m Overall) across 1,071 LiDAR tiles.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#1e315b] bg-[#09152b] flex flex-col gap-1">
                    <span className="font-bold text-[#ff9944] flex items-center gap-1.5 text-[11px]">
                      <Server className="w-3.5 h-3.5 text-[#ff9944]" /> 4. Connect Local CUDA Server
                    </span>
                    <p className="text-slate-300 text-[10px] leading-relaxed">
                      To run the full neural model, host the Python FastAPI backend locally and connect your URL in Settings.
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#1e315b]/80">
                <div className="flex items-center gap-2">
                  {onOpenSettings && (
                    <button
                      type="button"
                      onClick={() => {
                        handleDismissModal();
                        onOpenSettings();
                      }}
                      className="px-3.5 py-2 rounded-lg bg-[#09152b] hover:bg-[#11244a] text-slate-200 hover:text-white border border-[#1e315b] hover:border-[#00c2cb] text-xs font-mono flex items-center gap-1.5 transition cursor-pointer"
                    >
                      <Wrench className="w-3.5 h-3.5 text-[#00c2cb]" />
                      <span>Configure Backend URL</span>
                    </button>
                  )}

                  {onViewBenchmark && (
                    <button
                      type="button"
                      onClick={() => {
                        handleDismissModal();
                        onViewBenchmark();
                      }}
                      className="px-3.5 py-2 rounded-lg bg-[#09152b] hover:bg-[#11244a] text-slate-200 hover:text-white border border-[#1e315b] hover:border-[#ff9944] text-xs font-mono flex items-center gap-1.5 transition cursor-pointer"
                    >
                      <Info className="w-3.5 h-3.5 text-[#ff9944]" />
                      <span>View Benchmarks</span>
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleDismissModal}
                  className="px-5 py-2 rounded-lg bg-[#ff6600] hover:bg-[#e05a00] text-slate-950 font-bold text-xs font-mono transition cursor-pointer shadow-lg shadow-[#ff6600]/25 flex items-center gap-1.5"
                >
                  <span>I UNDERSTAND &amp; ACKNOWLEDGE</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
