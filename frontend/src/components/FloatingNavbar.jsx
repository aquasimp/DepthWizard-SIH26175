import React, { useState, useEffect } from 'react';
import { Layers, Activity, Sparkles, Settings as SettingsIcon, Play, CheckCircle2, ChevronRight, Menu, X } from 'lucide-react';

export default function FloatingNavbar({
  activeNav = 'dashboard',
  onSelectNav,
  onOpenSettings,
  onRunDemo,
  isRunning = false,
  systemStatus = null,
}) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Home' },
    { id: 'upload', label: 'Mission Portal' },
    { id: 'da3', label: 'DA3 Engine' },
    { id: 'terrain', label: '3D Flythrough' },
    { id: 'dsm-analysis', label: 'DSM & GeoTIFF' },
    { id: 'accuracy', label: 'Accuracy' },
    { id: 'measurements', label: 'Terrain Analysis' },
    { id: 'gamus', label: 'GAMUS Data' },
  ];

  const handleNavClick = (id) => {
    setMobileMenuOpen(false);
    onSelectNav?.(id);
  };

  return (
    <header className={`floating-nav-wrapper ${scrolled ? 'nav-scrolled' : ''}`}>
      <div className="floating-nav-pill">
        {/* Geometric Hexagon / Flower Logo (matching screenshot) */}
        <div className="nav-logo-group" onClick={() => handleNavClick('dashboard')}>
          <div className="nav-geom-icon">
            <svg width="26" height="26" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Central node */}
              <circle cx="18" cy="18" r="4" fill="#0f172a" />
              {/* 6 surrounding nodes with connection geometry */}
              <circle cx="18" cy="8" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              <circle cx="26.66" cy="13" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              <circle cx="26.66" cy="23" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              <circle cx="18" cy="28" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              <circle cx="9.34" cy="23" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              <circle cx="9.34" cy="13" r="3.2" stroke="#0f172a" strokeWidth="2" fill="white" />
              {/* Subtle spoke lines */}
              <line x1="18" y1="14" x2="18" y2="11.2" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="21.5" y1="16" x2="23.9" y2="14.6" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="21.5" y1="20" x2="23.9" y2="21.4" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="18" y1="22" x2="18" y2="24.8" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="14.5" y1="20" x2="12.1" y2="21.4" stroke="#0f172a" strokeWidth="1.5" />
              <line x1="14.5" y1="16" x2="12.1" y2="14.6" stroke="#0f172a" strokeWidth="1.5" />
            </svg>
          </div>
          <div className="nav-brand-title">
            <span className="brand-name">DepthWizard</span>
            <span className="brand-badge-ai">DA3</span>
          </div>
        </div>

        {/* Center: Navigation Links and Centered Action Button */}
        <div className="nav-center-container">
          <nav className="nav-center-links">
            {navItems.map((item) => (
              <button
                key={item.id}
                className={`nav-link-btn ${activeNav === item.id ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* Centered Quick Demo / Processing Button */}
          <div className="nav-center-action-wrapper">
            <button
              className="nav-demo-pill-btn centered"
              onClick={onRunDemo}
              disabled={isRunning}
              title="Execute End-to-End DA3 Pipeline with Sample Optical Imagery"
              aria-label="Run Live Demo"
            >
              {isRunning ? (
                <>
                  <span className="nav-spinner" />
                  <span className="nav-demo-text">Processing...</span>
                  <span className="nav-demo-text-short">Processing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} className="text-blue-500" />
                  <span className="nav-demo-text">Live Demo</span>
                  <span className="nav-demo-text-short">Demo</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Action Icons (Corner) */}
        <div className="nav-actions-group">
          {/* Settings / Diagnostics */}
          <button
            className="nav-icon-btn"
            onClick={onOpenSettings}
            title="System Diagnostics & Settings"
            aria-label="Settings"
          >
            <SettingsIcon size={16} />
          </button>

          {/* Mobile Menu Toggle */}
          <button
            className="nav-mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <>
          <div className="mobile-nav-backdrop" onClick={() => setMobileMenuOpen(false)} />
          <div className="mobile-nav-dropdown">
            <div className="mobile-nav-links-list">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  className={`mobile-nav-link ${activeNav === item.id ? 'active' : ''}`}
                  onClick={() => handleNavClick(item.id)}
                >
                  <span>{item.label}</span>
                  <ChevronRight size={14} />
                </button>
              ))}
            </div>
            <div className="mobile-nav-actions">
              <button
                className="mobile-demo-btn"
                onClick={() => {
                  setMobileMenuOpen(false);
                  onRunDemo?.();
                }}
                disabled={isRunning}
              >
                <Sparkles size={15} />
                <span>{isRunning ? 'Running DA3 Demo...' : 'Run Live DA3 Demo'}</span>
              </button>
            </div>
          </div>
        </>
      )}
    </header>
  );
}
