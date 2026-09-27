import React from 'react';
import { Sparkles, ArrowRight, Play, UploadCloud, Globe, Compass, Box, FileText, Mountain, Activity, Layers } from 'lucide-react';

export default function HeroOverview({
  onUploadClick,
  onDemoClick,
  onSelectFeature,
  activeFeature = 'upload',
  isRunning = false,
}) {
  const dockFeatures = [
    { id: 'upload', icon: Box, label: 'Single-View Optical' },
    { id: 'da3', icon: Activity, label: 'Relative Depth (DA3)' },
    { id: 'dsm-analysis', icon: Mountain, label: 'Metric DSM & GeoTIFF' },
    { id: 'terrain', icon: Compass, label: '3D WebGL Flythrough' },
    { id: 'measurements', icon: Layers, label: 'Slope & Height Profile' },
  ];

  return (
    <section className="luminous-hero-container">
      {/* Background Architectural Circuit/Hairline SVGs (matching screenshot) */}
      <div className="hero-circuit-bg" aria-hidden="true">
        <svg className="circuit-lines-svg" width="100%" height="100%" viewBox="0 0 1440 600" fill="none" preserveAspectRatio="none">
          {/* Left Circuit Lines */}
          <path d="M 0 180 L 180 180 L 220 220 L 220 380 L 260 420 L 340 420" stroke="rgba(255, 255, 255, 0.45)" strokeWidth="1.2" strokeDasharray="3 3" />
          <path d="M 0 320 L 120 320 L 160 360 L 160 480" stroke="rgba(255, 255, 255, 0.35)" strokeWidth="1" />
          <circle cx="220" cy="220" r="3" fill="rgba(255, 255, 255, 0.7)" />
          <circle cx="260" cy="420" r="3" fill="rgba(255, 255, 255, 0.7)" />

          {/* Right Circuit Lines */}
          <path d="M 1440 180 L 1260 180 L 1220 220 L 1220 380 L 1180 420 L 1100 420" stroke="rgba(255, 255, 255, 0.45)" strokeWidth="1.2" strokeDasharray="3 3" />
          <path d="M 1440 320 L 1320 320 L 1280 360 L 1280 480" stroke="rgba(255, 255, 255, 0.35)" strokeWidth="1" />
          <circle cx="1220" cy="220" r="3" fill="rgba(255, 255, 255, 0.7)" />
          <circle cx="1180" cy="420" r="3" fill="rgba(255, 255, 255, 0.7)" />

          {/* Central subtle technical crosshairs */}
          <line x1="720" y1="50" x2="720" y2="70" stroke="rgba(255, 255, 255, 0.3)" strokeWidth="1" />
          <line x1="710" y1="60" x2="730" y2="60" stroke="rgba(255, 255, 255, 0.3)" strokeWidth="1" />
        </svg>
      </div>

      <div className="hero-inner-content">
        {/* Top Floating Badge Pill (matching screenshot) */}
        <div className="hero-pill-badge">
          <span className="badge-sparkle">✦</span>
          <span className="badge-text">THE AGENTIC 3D TERRAIN &amp; ELEVATION PLATFORM</span>
        </div>

        {/* Editorial Serif Hero Headline (matching screenshot) */}
        <h1 className="hero-editorial-title">
          Reconstruct 3D elevation models that <span className="title-serif-italic">convert</span> with AI intelligence
        </h1>

        {/* Subtitle (matching screenshot) */}
        <p className="hero-editorial-subtitle">
          A fast, consistent, and high-precision monocular depth &amp; DSM terrain elevation AI platform powered by Depth Anything 3.
        </p>

        {/* Dual Action Buttons (matching screenshot) */}
        <div className="hero-cta-buttons-row">
          {/* Primary Dark Button with Intense Soft Ambient Glow */}
          <button
            className="hero-btn-dark-glow"
            onClick={onDemoClick}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <span className="btn-spinner" />
                <span>Running DA3 Inference...</span>
              </>
            ) : (
              <>
                <span>Start Depth Estimation</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>

          {/* Secondary Crisp White Pill Button */}
          <button
            className="hero-btn-white-pill"
            onClick={onUploadClick}
          >
            <span>Upload Optical Imagery</span>
          </button>
        </div>

        {/* Floating Bottom Pill Dock (matching screenshot) */}
        <div className="hero-bottom-dock-wrapper">
          <div className="dock-connector-line" aria-hidden="true" />
          <div className="hero-bottom-dock">
            {dockFeatures.map((feat) => {
              const Icon = feat.icon;
              const isSelected = activeFeature === feat.id;
              return (
                <button
                  key={feat.id}
                  className={`dock-pill-chip ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectFeature?.(feat.id)}
                >
                  <Icon size={14} className="dock-chip-icon" />
                  <span>{feat.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
