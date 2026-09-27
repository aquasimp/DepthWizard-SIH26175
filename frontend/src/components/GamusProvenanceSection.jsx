import React from 'react';
import { Database, ShieldCheck, CheckCircle2, MapPin, Layers, Award, FileSpreadsheet, ExternalLink } from 'lucide-react';

export default function GamusProvenanceSection() {
  const cities = [
    { name: 'Washington D.C.', trainCrops: '1,226', testCrops: '338', testPixels: '11.3M', rmse: '4.94m', pearsonR: '0.877', within25: '61.6%' },
    { name: 'New York City', trainCrops: '1,191', testCrops: '333', testPixels: '10.4M', rmse: '4.97m', pearsonR: '0.787', within25: '65.2%' },
    { name: 'Philadelphia', trainCrops: '1,400', testCrops: '400', testPixels: '13.4M', rmse: '3.54m', pearsonR: '0.712', within25: '79.8%' },
  ];

  return (
    <section className="gamus-provenance-section" id="gamus-section">
      <div className="section-header-block">
        <div className="section-title-wrap">
          <Database className="text-cyan" size={22} />
          <div>
            <h3 className="section-title-text">GAMUS Benchmark Dataset &amp; Provenance</h3>
            <p className="section-subtitle-text">
              Official Hugging Face repository <code className="font-mono bg-white/70 px-1.5 py-0.5 rounded border border-slate-200">earthflow/GAMUS</code> — 3,817 quality-controlled metropolitan crops evaluated against airborne LiDAR.
            </p>
          </div>
        </div>

        <div className="gamus-top-badges">
          <span className="eval-direction-pill higher">
            <ShieldCheck size={13} />
            <span>0 OMA / JAX Artifacts</span>
          </span>
          <span className="eval-direction-pill lower">
            <CheckCircle2 size={13} />
            <span>Bitwise Disjoint Splits</span>
          </span>
        </div>
      </div>

      {/* 4 Ingestion Stat Highlight Cards */}
      <div className="gamus-stats-grid">
        <div className="gamus-stat-card">
          <div className="gamus-stat-icon-wrap">
            <Layers size={18} className="text-blue" />
          </div>
          <div className="gamus-stat-body">
            <span className="gamus-stat-label">CANONICAL CROPS</span>
            <strong className="gamus-stat-number font-mono">3,817</strong>
            <span className="gamus-stat-sub">~95× Scale-Up vs v1.0.3 (518×518 px)</span>
          </div>
        </div>

        <div className="gamus-stat-card">
          <div className="gamus-stat-icon-wrap">
            <MapPin size={18} className="text-emerald" />
          </div>
          <div className="gamus-stat-body">
            <span className="gamus-stat-label">METROPOLITAN DIVERSITY</span>
            <strong className="gamus-stat-number font-mono">3 Cities</strong>
            <span className="gamus-stat-sub">DC (1,226), NYC (1,191), PHL (1,400)</span>
          </div>
        </div>

        <div className="gamus-stat-card">
          <div className="gamus-stat-icon-wrap">
            <Award size={18} className="text-cyan" />
          </div>
          <div className="gamus-stat-body">
            <span className="gamus-stat-label">LIDAR TRUTH EVALUATED</span>
            <strong className="gamus-stat-number font-mono">35.1 Million</strong>
            <span className="gamus-stat-sub">1,071 Held-out test crops (zero leakage)</span>
          </div>
        </div>

        <div className="gamus-stat-card">
          <div className="gamus-stat-icon-wrap">
            <ShieldCheck size={18} className="text-rose" />
          </div>
          <div className="gamus-stat-body">
            <span className="gamus-stat-label">QC REJECTION FILTER</span>
            <strong className="gamus-stat-number font-mono">544 Crops</strong>
            <span className="gamus-stat-sub">Dropped &gt;30% NaN &amp; unphysical &lt; -1.0m</span>
          </div>
        </div>
      </div>

      {/* City Breakdown Table Card */}
      <div className="dsm-card-box gamus-table-card">
        <div className="dsm-card-title-bar">
          <MapPin size={18} className="text-blue" />
          <h4>Cross-City Geographic Generalization</h4>
        </div>

        <div className="gamus-table-wrap">
          <table className="gamus-city-table">
            <thead>
              <tr>
                <th>Metropolitan Area</th>
                <th>Train Crops</th>
                <th>Held-Out Test</th>
                <th>Reference Pixels</th>
                <th>RMSE (LiDAR)</th>
                <th>Pearson r</th>
                <th>&delta; &lt; 2.5m Precision</th>
              </tr>
            </thead>
            <tbody>
              {cities.map((c) => (
                <tr key={c.name}>
                  <td><strong>{c.name}</strong></td>
                  <td className="font-mono">{c.trainCrops}</td>
                  <td className="font-mono">{c.testCrops}</td>
                  <td className="font-mono">{c.testPixels}</td>
                  <td className="font-mono text-cyan"><strong>{c.rmse}</strong></td>
                  <td className="font-mono text-emerald"><strong>{c.pearsonR}</strong></td>
                  <td className="font-mono highlight-badge"><strong>{c.within25}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="gamus-table-footer">
          <span className="gamus-footer-note">
            *Ground truth elevations sourced from airborne USGS LiDAR nDSM rasters at 0.33 m Ground Sample Distance (GSD).
          </span>
          <a
            href="https://huggingface.co/datasets/earthflow/GAMUS"
            target="_blank"
            rel="noreferrer"
            className="eval-download-pill-btn"
          >
            <ExternalLink size={13} />
            <span>Hugging Face GAMUS Dataset</span>
          </a>
        </div>
      </div>
    </section>
  );
}
