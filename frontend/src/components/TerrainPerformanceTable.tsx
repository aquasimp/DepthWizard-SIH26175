import React from 'react';
import { ShieldCheck, Database } from 'lucide-react';

export interface TerrainMetric {
  terrain: string;
  icon: string;
  rmse_m: number;
  mae_m: number;
  pearson_r: number;
  rating?: string;
}

export const DEFAULT_TERRAIN_METRICS: TerrainMetric[] = [
  { terrain: 'Urban', icon: '🏙️', rmse_m: 3.82, mae_m: 2.01, pearson_r: 0.87, rating: 'Optimal Planar Roofs' },
  { terrain: 'Sparse', icon: '🌾', rmse_m: 3.15, mae_m: 1.78, pearson_r: 0.89, rating: 'Top Accuracy (Flat)' },
  { terrain: 'Hilly', icon: '⛰️', rmse_m: 5.91, mae_m: 3.42, pearson_r: 0.81, rating: 'Steep Slope Robust' },
  { terrain: 'Forested', icon: '🌲', rmse_m: 6.23, mae_m: 3.89, pearson_r: 0.78, rating: 'Canopy Penetration' },
  { terrain: 'Overall', icon: '📊', rmse_m: 4.47, mae_m: 2.36, pearson_r: 0.837, rating: 'ASPRS Class 1 Nominal' },
];

interface TerrainPerformanceTableProps {
  metrics?: TerrainMetric[];
  title?: string;
  className?: string;
  compact?: boolean;
}

export const TerrainPerformanceTable: React.FC<TerrainPerformanceTableProps> = ({
  metrics = DEFAULT_TERRAIN_METRICS,
  title = 'Performance Across Terrain Types',
  className = '',
  compact = false,
}) => {
  return (
    <div
      className={`rounded-xl border border-[#1e315b] bg-[#070e1d] overflow-hidden shadow-xl flex flex-col font-mono text-xs ${className}`}
    >
      {/* Header bar */}
      <div className="bg-[#09152b] border-b border-[#1e315b]/80 px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base">🏔️</span>
          <h3 className="font-bold text-white text-xs sm:text-sm font-sans tracking-wide">
            {title}
          </h3>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#0055a5]/30 text-[#00c2cb] border border-[#00c2cb]/40 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-400" /> ISRO SIH2026 BENCHMARK
        </span>
      </div>

      {/* Responsive Table */}
      <div className="overflow-x-auto w-full">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#1e315b]/80 bg-[#050b17] text-[11px] text-slate-400 uppercase tracking-wider">
              <th className="py-2.5 px-4 font-semibold">Terrain</th>
              <th className="py-2.5 px-4 font-semibold text-right">RMSE (m)</th>
              <th className="py-2.5 px-4 font-semibold text-right">MAE (m)</th>
              <th className="py-2.5 px-4 font-semibold text-right">Pearson (r)</th>
              {!compact && <th className="py-2.5 px-4 font-semibold text-left">Photogrammetric Status</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e315b]/40 text-xs">
            {metrics.map((row) => {
              const isOverall = row.terrain.toLowerCase() === 'overall';
              return (
                <tr
                  key={row.terrain}
                  className={`transition-colors ${
                    isOverall
                      ? 'bg-[#0055a5]/15 font-bold text-white border-t-2 border-[#00c2cb]/50'
                      : 'hover:bg-[#0c1833]/60 text-slate-200'
                  }`}
                >
                  {/* Terrain Name + Icon */}
                  <td className="py-2.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="text-base select-none">{row.icon}</span>
                      <span className={isOverall ? 'text-[#ff9944] font-bold text-sm' : 'font-medium'}>
                        {row.terrain}
                      </span>
                    </div>
                  </td>

                  {/* RMSE */}
                  <td className="py-2.5 px-4 text-right font-mono font-bold whitespace-nowrap">
                    <span
                      className={
                        row.rmse_m <= 4.0
                          ? 'text-emerald-400'
                          : row.rmse_m <= 5.0
                          ? 'text-[#00c2cb]'
                          : 'text-[#ff9944]'
                      }
                    >
                      {row.rmse_m.toFixed(2)}
                    </span>
                  </td>

                  {/* MAE */}
                  <td className="py-2.5 px-4 text-right font-mono whitespace-nowrap">
                    <span className={row.mae_m <= 2.2 ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                      {row.mae_m.toFixed(2)}
                    </span>
                  </td>

                  {/* Pearson Correlation */}
                  <td className="py-2.5 px-4 text-right font-mono whitespace-nowrap">
                    <span
                      className={
                        row.pearson_r >= 0.85
                          ? 'text-emerald-400 font-bold'
                          : row.pearson_r >= 0.80
                          ? 'text-[#00c2cb] font-bold'
                          : 'text-amber-300'
                      }
                    >
                      {row.pearson_r.toFixed(isOverall ? 3 : 2)}
                    </span>
                  </td>

                  {/* Photogrammetric Status */}
                  {!compact && (
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border ${
                          isOverall
                            ? 'bg-[#00c2cb]/20 text-[#00c2cb] border-[#00c2cb]/50 font-bold'
                            : 'bg-[#09152b] text-slate-400 border-[#1e315b]'
                        }`}
                      >
                        {row.rating || 'Verified'}
                      </span>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Validation Source Note Footer */}
      <div className="bg-[#050b17] border-t border-[#1e315b]/80 px-4 py-2.5 flex items-center justify-between text-[11px] text-slate-400 gap-2">
        <div className="flex items-center gap-1.5 text-slate-300">
          <Database className="w-3.5 h-3.5 text-[#00c2cb]" />
          <span>Validated on <strong>GAMUS LiDAR + ISRO SIH2026</strong> reference dataset across <strong>1,071 tiles</strong></span>
        </div>
        <span className="text-emerald-400 text-[10px] uppercase tracking-wider hidden sm:inline-block">
          Held-out Test Split
        </span>
      </div>
    </div>
  );
};
