import React, { useMemo } from 'react';
import * as THREE from 'three';

export interface MeasurePoint {
  u: number;
  v: number;
  worldPoint: THREE.Vector3;
  elevationM: number;
}

interface MeasureToolVisualizerProps {
  pointA: MeasurePoint | null;
  pointB: MeasurePoint | null;
}

export const MeasureToolVisualizer: React.FC<MeasureToolVisualizerProps> = ({
  pointA,
  pointB,
}) => {
  const lineGeometry = useMemo(() => {
    if (!pointA || !pointB) return null;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array([
      pointA.worldPoint.x,
      pointA.worldPoint.y + 0.5,
      pointA.worldPoint.z,
      pointB.worldPoint.x,
      pointB.worldPoint.y + 0.5,
      pointB.worldPoint.z,
    ]);
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geom;
  }, [pointA, pointB]);

  return (
    <group>
      {pointA && (
        <mesh position={[pointA.worldPoint.x, pointA.worldPoint.y + 0.5, pointA.worldPoint.z]}>
          <sphereGeometry args={[0.8, 16, 16]} />
          <meshBasicMaterial color="#38bdf8" />
        </mesh>
      )}

      {pointB && (
        <mesh position={[pointB.worldPoint.x, pointB.worldPoint.y + 0.5, pointB.worldPoint.z]}>
          <sphereGeometry args={[0.8, 16, 16]} />
          <meshBasicMaterial color="#f43f5e" />
        </mesh>
      )}

      {lineGeometry && (
        <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color: '#38bdf8', linewidth: 3 }))} />
      )}
    </group>
  );
};

interface MeasureToolCardProps {
  pointA: MeasurePoint | null;
  pointB: MeasurePoint | null;
  onClear: () => void;
  active: boolean;
  onToggleActive: () => void;
}

export const MeasureToolCard: React.FC<MeasureToolCardProps> = ({
  pointA,
  pointB,
  onClear,
  active,
  onToggleActive,
}) => {
  const stats = useMemo(() => {
    if (!pointA || !pointB) return null;

    const dx = pointB.worldPoint.x - pointA.worldPoint.x;
    const dz = pointB.worldPoint.z - pointA.worldPoint.z;
    const dy = pointB.elevationM - pointA.elevationM;

    const horizontalDistM = Math.sqrt(dx * dx + dz * dz);
    const straightDistM = Math.sqrt(horizontalDistM * horizontalDistM + dy * dy);
    const slopePercent =
      horizontalDistM > 1e-4 ? (Math.abs(dy) / horizontalDistM) * 100 : 0.0;

    return {
      horizontalDistM,
      verticalDeltaM: dy,
      straightDistM,
      slopePercent,
    };
  }, [pointA, pointB]);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-700/60 bg-slate-900/90 p-3 shadow-xl backdrop-blur-md text-xs font-mono text-slate-200 min-w-[260px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-semibold text-cyan-400 uppercase tracking-wider text-[11px]">
          3D Measure Tool
        </span>
        <div className="flex gap-1.5">
          <button
            onClick={onToggleActive}
            className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
              active
                ? 'bg-cyan-500 text-slate-950 font-bold'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {active ? 'ACTIVE' : 'START'}
          </button>
          {pointA && (
            <button
              onClick={onClear}
              className="px-2 py-0.5 rounded text-[10px] bg-rose-950/80 text-rose-300 border border-rose-800/50 hover:bg-rose-900"
            >
              CLEAR
            </button>
          )}
        </div>
      </div>

      {active && !pointA && (
        <p className="text-slate-400 text-[11px] italic py-1">Click Point A on terrain to begin...</p>
      )}

      {active && pointA && !pointB && (
        <p className="text-cyan-300 text-[11px] italic py-1">Point A set! Click Point B on terrain...</p>
      )}

      {stats && (
        <div className="flex flex-col gap-1.5 pt-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-400">Horizontal Ground:</span>
            <span className="font-bold text-white">{stats.horizontalDistM.toFixed(2)} m</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Vertical Delta (ΔY):</span>
            <span className={`font-bold ${stats.verticalDeltaM >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {stats.verticalDeltaM >= 0 ? '+' : ''}
              {stats.verticalDeltaM.toFixed(2)} m
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">3D Straight Line:</span>
            <span className="font-bold text-cyan-300">{stats.straightDistM.toFixed(2)} m</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Slope Gradient:</span>
            <span className="font-bold text-amber-300">{stats.slopePercent.toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
};
