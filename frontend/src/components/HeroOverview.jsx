import React from 'react';

export default function HeroOverview({
  onUploadClick,
  onDemoClick,
  onSelectFeature,
  activeFeature = 'upload',
  isRunning = false,
}) {
  const dockFeatures = [
    { id: 'upload', icon: 'fa-solid fa-satellite', label: 'Single-View Optical' },
    { id: 'da3', icon: 'fa-solid fa-chart-line', label: 'Relative Depth (DA3)' },
    { id: 'dsm-analysis', icon: 'fa-solid fa-mountain-sun', label: 'Metric DSM & GeoTIFF' },
    { id: 'terrain', icon: 'fa-solid fa-cube', label: '3D WebGL Flythrough' },
    { id: 'measurements', icon: 'fa-solid fa-layer-group', label: 'Slope & Height Profile' },
    { id: 'accuracy', icon: 'fa-solid fa-chart-simple', label: 'Model Accuracy & Graphs' },
  ];

  return (
    <section className="luminous-hero-container">
      {/* Background Architectural Circuit/Hairline SVGs */}
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

        </svg>
      </div>

      <div className="hero-inner-content">
        {/* Top Floating Badge Pill with Font Awesome Icon */}
        <div className="hero-pill-badge">
          <i className="fa-solid fa-satellite-dish badge-fa-icon"></i>
          <span className="badge-text">ISRO / SAC · BHOOMI-3D ELEVATION PLATFORM</span>
        </div>

        {/* High-Impact Bold Aerospace Hero Headline (Not thin AI serif) */}
        <h1 className="hero-bold-title">
          Reconstruct <span className="hero-title-highlight">3D Elevation Models</span> <br className="hero-title-br" /> from Single Optical Satellites
        </h1>

        {/* Subheading Card with Font Awesome Icon and Illuminated Card Background */}
        <div className="hero-subheading-card">
          <div className="subheading-icon-badge">
            <i className="fa-solid fa-mountain-sun"></i>
          </div>
          <p className="hero-subheading-text">
            A fast, high-precision monocular depth &amp; DSM terrain elevation platform powered by <strong>Depth Anything 3</strong>
          </p>
          <div className="subheading-badge-tag">
            <i className="fa-solid fa-bolt"></i>
            <span>Real-Time DA3</span>
          </div>
        </div>

        {/* Dual Action CTA Buttons with Font Awesome Icons */}
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
                <i className="fa-solid fa-bolt text-sky-400"></i>
                <span>Start Depth Estimation</span>
                <i className="fa-solid fa-arrow-right"></i>
              </>
            )}
          </button>

          {/* Secondary Crisp White Pill Button */}
          <button
            className="hero-btn-white-pill"
            onClick={onUploadClick}
          >
            <i className="fa-solid fa-cloud-arrow-up text-sky-600"></i>
            <span>Upload Optical Imagery</span>
          </button>
        </div>

        {/* Floating Bottom Pill Dock with Font Awesome Icons */}
        <div className="hero-bottom-dock-wrapper">
          <div className="dock-connector-line" aria-hidden="true" />
          <div className="hero-bottom-dock">
            {dockFeatures.map((feat) => {
              const isSelected = activeFeature === feat.id;
              return (
                <button
                  key={feat.id}
                  className={`dock-pill-chip ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectFeature?.(feat.id)}
                >
                  <i className={`${feat.icon} dock-chip-icon`}></i>
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
