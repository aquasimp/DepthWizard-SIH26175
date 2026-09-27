import React, { useEffect, useState } from 'react';
import { Satellite } from 'lucide-react';
import type { PageView } from '../App';

interface IsroHeaderProps {
  currentPage?: PageView;
  activeJobId?: string | null;
  onNavigate?: (page: PageView, jobId?: string) => void;
  backendOnline?: boolean;
  computeDevice?: string;
}

export const IsroHeader: React.FC<IsroHeaderProps> = ({
  currentPage = 'upload',
  activeJobId,
  onNavigate,
  backendOnline = true,
  computeDevice = 'CUDA (GPU)',
}) => {
  const [timeUtc, setTimeUtc] = useState('');
  const [timeIst, setTimeIst] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeUtc(
        now.toISOString().slice(11, 19) + ' UTC'
      );
      // IST is UTC + 5:30
      const istTime = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
      setTimeIst(
        istTime.toISOString().slice(11, 19) + ' IST'
      );
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-[#1e315b]/80 bg-[#070e1d]/95 backdrop-blur-md px-4 sm:px-6 py-2.5 flex flex-col gap-2 z-40 relative">
      {/* Top Institutional Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Emblem & Institutional Titles */}
        <div className="flex items-center gap-3.5">
          <div 
            onClick={() => onNavigate && onNavigate('dashboard')}
            className="w-11 h-11 rounded-lg border border-[#00c2cb]/40 bg-[#09152b] p-1 flex items-center justify-center shadow-lg shadow-[#0055a5]/20 cursor-pointer hover:border-[#ff6600]/80 transition group"
            title="Return to DepthWizard Dashboard"
          >
            <img 
              src="/isro_insignia.svg" 
              alt="ISRO Space Applications Centre" 
              className="w-9 h-9 object-contain group-hover:scale-105 transition"
            />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-slate-300 tracking-wide">
                भारतीय अंतरिक्ष अनुसंधान संगठन
              </span>
              <span className="text-slate-600">|</span>
              <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400">
                Indian Space Research Organisation
              </span>
            </div>
            
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-extrabold tracking-tight text-white flex items-center gap-1.5 font-display">
                अंतरिक्ष अनुप्रयोग केंद्र (SAC)
                <span className="text-[#00c2cb] text-xs font-normal">·</span>
                <span className="text-[#ff7700]">BHOOMI-3D</span>
                <span className="text-xs font-mono text-slate-400 font-normal">/ DepthWizard-EO</span>
              </span>
              
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#091834] text-[#00c2cb] border border-[#00c2cb]/30 flex items-center gap-1">
                <Satellite className="w-2.5 h-2.5 text-[#00c2cb]" /> SIH-26175
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1e1708] text-[#ff9944] border border-[#ff6600]/30 hidden md:inline-flex">
                EGM96 GEOID DATUM
              </span>
            </div>
          </div>
        </div>

        {/* Right: Telemetry Mission Clock & Engine Status */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Mission Digital Clock */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-md bg-[#091224] border border-[#1e315b] text-[11px] font-mono">
            <div className="flex items-center gap-1 text-slate-300">
              <span className="text-[#00c2cb]">UTC:</span>
              <span className="font-semibold text-white">{timeUtc || '--:--:--'}</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="flex items-center gap-1 text-slate-300">
              <span className="text-[#ff9944]">IST:</span>
              <span className="font-semibold text-white">{timeIst || '--:--:--'}</span>
            </div>
          </div>

          {/* Compute Engine & Device */}
          <div className="flex items-center gap-2 text-[11px] font-mono">
            {backendOnline ? (
              <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 border border-emerald-700/50 px-3 py-1 rounded-md">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-semibold">{computeDevice.toUpperCase()}</span>
                <span className="text-emerald-500/80 text-[10px] hidden sm:inline">ONLINE</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-rose-400 bg-rose-950/50 border border-rose-700/50 px-3 py-1 rounded-md">
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                <span className="font-semibold">CORE OFFLINE (PORT 8000)</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sub-Bar: Mission Navigation Tabs & Sensor Constellation Compatibility */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[#1e315b]/40 text-xs">
        {/* Navigation Tabs */}
        {onNavigate && (
          <nav className="flex items-center gap-1 font-mono text-[11px]">
            <button
              type="button"
              onClick={() => onNavigate('dashboard')}
              className={`px-3 py-1 rounded transition cursor-pointer flex items-center gap-1.5 ${
                currentPage === 'dashboard'
                  ? 'bg-[#00c2cb] text-[#070e1d] font-bold shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-[#0f1d3a]'
              }`}
            >
              <span>✦</span> DEPTHWIZARD HOME
            </button>

            <button
              type="button"
              onClick={() => onNavigate('upload')}
              className={`px-3 py-1 rounded transition cursor-pointer flex items-center gap-1.5 ${
                currentPage === 'upload'
                  ? 'bg-[#0055a5] text-white font-bold border border-[#00c2cb]/60 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-[#0f1d3a]'
              }`}
            >
              <span>01</span> INGESTION TERMINAL
            </button>

            {activeJobId && (
              <>
                <button
                  type="button"
                  onClick={() => onNavigate('status', activeJobId)}
                  className={`px-3 py-1 rounded transition cursor-pointer flex items-center gap-1.5 ${
                    currentPage === 'status'
                      ? 'bg-[#0055a5] text-white font-bold border border-[#00c2cb]/60 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-[#0f1d3a]'
                  }`}
                >
                  <span>02</span> TELEMETRY PIPELINE
                </button>

                <button
                  type="button"
                  onClick={() => onNavigate('viewer', activeJobId)}
                  className={`px-3 py-1 rounded transition cursor-pointer flex items-center gap-1.5 ${
                    currentPage === 'viewer'
                      ? 'bg-[#0055a5] text-white font-bold border border-[#00c2cb]/60 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-[#0f1d3a]'
                  }`}
                >
                  <span>03</span> 3D COCKPIT
                </button>

                <button
                  type="button"
                  onClick={() => onNavigate('validate', activeJobId)}
                  className={`px-3 py-1 rounded transition cursor-pointer flex items-center gap-1.5 ${
                    currentPage === 'validate'
                      ? 'bg-[#0055a5] text-white font-bold border border-[#00c2cb]/60 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-[#0f1d3a]'
                  }`}
                >
                  <span>04</span> LIDAR BENCHMARK
                </button>
              </>
            )}
          </nav>
        )}

        {/* Sensor Compatibility Specs */}
        <div className="hidden xl:flex items-center gap-3 text-[10px] font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ff6600]" />
            CARTOSAT-2/3 (0.28m PAN)
          </span>
          <span className="text-slate-700">/</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00c2cb]" />
            RESOURCESAT-2A (LISS-IV)
          </span>
          <span className="text-slate-700">/</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            AERIAL ORTHOPHOTO (0.33m)
          </span>
        </div>
      </div>
    </header>
  );
};
