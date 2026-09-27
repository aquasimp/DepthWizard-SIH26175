import React from 'react';

/**
 * ElevationProfile - Interactive height and slope transect analysis
 */
export default function ElevationProfile({ profileData }) {
  if (!profileData) {
    return (
      <div className="profile-container empty-state">
        <p>Interactive Elevation & Slope Profile: Draw a transect on the terrain to inspect cross-section metrics.</p>
      </div>
    );
  }

  const { distances, elevations, slopes, total_distance_m, max_slope_deg, avg_slope_deg } = profileData;

  // Compute SVG polyline points
  const width = 600;
  const height = 140;
  const padding = 20;

  const minE = Math.min(...elevations);
  const maxE = Math.max(...elevations);
  const rangeE = Math.max(maxE - minE, 1.0);
  const maxD = Math.max(...distances, 1.0);

  const points = distances.map((d, i) => {
    const x = padding + (d / maxD) * (width - 2 * padding);
    const y = height - padding - ((elevations[i] - minE) / rangeE) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="profile-container">
      <div className="profile-header">
        <h4>Transect Elevation Profile</h4>
        <div className="profile-stats">
          <span className="stat-item">Length: <strong>{total_distance_m.toFixed(1)}m</strong></span>
          <span className="stat-item">Elevation: <strong>{minE.toFixed(1)}m - {maxE.toFixed(1)}m</strong></span>
          <span className="stat-item">Max Slope: <strong>{max_slope_deg.toFixed(1)}°</strong></span>
          <span className="stat-item">Avg Slope: <strong>{avg_slope_deg.toFixed(1)}°</strong></span>
        </div>
      </div>

      <div className="svg-wrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="profile-svg">
          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#1e293b" strokeDasharray="3 3" />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#1e293b" strokeDasharray="3 3" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#334155" />

          {/* Elevation polygon fill */}
          <polygon
            points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`}
            fill="url(#elevationGradient)"
            opacity="0.35"
          />

          {/* Elevation line */}
          <polyline
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2.5"
            points={points}
          />

          <defs>
            <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0.0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}
