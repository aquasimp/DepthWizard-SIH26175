import React from 'react';

export interface ProbeData {
  u: number;
  v: number;
  worldX: number;
  worldY: number;
  worldZ: number;
  elevationM: number;
  isAbsolute: boolean;
  units: string;
}

interface HeightProbeBadgeProps {
  probe: ProbeData | null;
}

export const HeightProbeBadge: React.FC<HeightProbeBadgeProps> = ({ probe }) => {
  if (!probe) return null;

  return (
    <div className="absolute top-4 left-4 z-20 pointer-events-none flex flex-col gap-1 rounded-xl border border-slate-700/60 bg-slate-900/80 p-3.5 shadow-2xl backdrop-blur-md text-xs font-mono text-slate-200 min-w-[240px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-1">
        <span className="font-semibold tracking-wider text-cyan-400 uppercase text-[10px]">
          Height Probe
        </span>
        <span
          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
            probe.isAbsolute
              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
              : 'bg-amber-950/80 text-amber-400 border border-amber-800/60'
          }`}
        >
          {probe.isAbsolute ? 'METRIC EGM96' : 'RELATIVE UNITS'}
        </span>
      </div>

      <div className="flex justify-between items-baseline py-0.5">
        <span className="text-slate-400">Elevation:</span>
        <span className="text-base font-bold text-white">
          {probe.elevationM.toFixed(2)}{' '}
          <span className="text-xs font-normal text-slate-400">{probe.units}</span>
        </span>
      </div>

      <div className="flex justify-between text-slate-400 py-0.5">
        <span>World Position:</span>
        <span className="text-slate-200">
          X: {probe.worldX.toFixed(1)}m, Z: {probe.worldZ.toFixed(1)}m
        </span>
      </div>

      <div className="flex justify-between text-slate-500 text-[10px] pt-1">
        <span>Normalized UV:</span>
        <span>
          ({probe.u.toFixed(3)}, {probe.v.toFixed(3)})
        </span>
      </div>
    </div>
  );
};
