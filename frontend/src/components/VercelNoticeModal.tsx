import React, { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

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
}) => {
  const [isVercel, setIsVercel] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setIsVercel(isVercelEnvironment());
  }, []);

  if (!isVercel || dismissed) return null;

  return (
    <div className="w-full bg-[#0d1627] border-b border-amber-500/30 text-slate-200 px-4 py-2 text-xs font-mono flex items-center justify-between gap-3 relative z-40 shadow-sm">
      <div className="flex items-center gap-2 overflow-hidden">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="leading-snug text-[11px] sm:text-xs">
          <strong className="text-amber-300">Notice:</strong> Viewing on Vercel — AI models are not supported on serverless edge, so you may encounter issues running remote models. In-browser 3D demo mode is active.
        </span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onOpenSettings && (
          <button
            type="button"
            onClick={onOpenSettings}
            className="text-[11px] text-[#00c2cb] hover:text-white underline cursor-pointer hidden sm:inline"
          >
            Settings
          </button>
        )}
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="text-slate-400 hover:text-white p-1 rounded cursor-pointer transition"
          title="Dismiss notice"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
