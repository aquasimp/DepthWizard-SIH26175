import React, { useState, useEffect } from 'react';
import { Sparkles, Settings as SettingsIcon, Menu, X, ChevronRight, Moon, Sun } from 'lucide-react';

export default function FloatingNavbar({
  activeNav = 'dashboard',
  onSelectNav,
  onOpenSettings,
  onRunDemo,
  isRunning = false,
  systemStatus = null,
  isDark = true,
  onToggleTheme,
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
    { id: 'terrain', label: '3D Flythrough' },
    { id: 'accuracy', label: '📊 Accuracy & Graphs' },
    { id: 'dsm-analysis', label: 'DSM & GeoTIFF' },
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
        {/* Geometric Hexagon / Satellite Emblem Logo */}
        <div className="nav-logo-group" onClick={() => handleNavClick('dashboard')} title="Return to Dashboard Home">
          <div className="nav-geom-icon">
            <svg width="26" height="26" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="18" cy="18" r="4" fill="currentColor" />
              <circle cx="18" cy="8" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <circle cx="26.66" cy="13" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <circle cx="26.66" cy="23" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <circle cx="18" cy="28" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <circle cx="9.34" cy="23" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <circle cx="9.34" cy="13" r="3.2" stroke="currentColor" strokeWidth="2" fill="none" />
              <line x1="18" y1="14" x2="18" y2="11.2" stroke="currentColor" strokeWidth="1.5" />
              <line x1="21.5" y1="16" x2="23.9" y2="14.6" stroke="currentColor" strokeWidth="1.5" />
              <line x1="21.5" y1="20" x2="23.9" y2="21.4" stroke="currentColor" strokeWidth="1.5" />
              <line x1="18" y1="22" x2="18" y2="24.8" stroke="currentColor" strokeWidth="1.5" />
              <line x1="14.5" y1="20" x2="12.1" y2="21.4" stroke="currentColor" strokeWidth="1.5" />
              <line x1="14.5" y1="16" x2="12.1" y2="14.6" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </div>
          <div className="nav-brand-title">
            <span className="brand-name">DepthWizard</span>
            <span className="brand-badge-ai">DA3</span>
          </div>
        </div>

        {/* Center: Navigation Links (unconstrained and non-colliding) */}
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
        </div>

        {/* Right: Actions Group (Live Demo + Theme Mode Toggle + Settings + Mobile Toggle) */}
        <div className="nav-actions-group">
          {/* Quick Demo Pill Button */}
          <button
            className="nav-demo-pill-btn"
            onClick={onRunDemo}
            disabled={isRunning}
            title="Execute End-to-End DA3 Pipeline with Sample Optical Imagery"
            aria-label="Run Live Demo"
          >
            {isRunning ? (
              <>
                <span className="nav-spinner" />
                <span className="nav-demo-text">Processing...</span>
                <span className="nav-demo-text-short">...</span>
              </>
            ) : (
              <>
                <Sparkles size={13} className="text-cyan-400" />
                <span className="nav-demo-text">Live Demo</span>
                <span className="nav-demo-text-short">Demo</span>
              </>
            )}
          </button>

          {/* Quick Theme Toggle Button */}
          {onToggleTheme && (
            <button
              className="nav-icon-btn theme-toggle-btn"
              onClick={onToggleTheme}
              title={isDark ? 'Switch to Luminous Light Mode' : 'Switch to Cyber Aerospace Dark Mode'}
              aria-label="Toggle Theme Mode"
            >
              {isDark ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-indigo-500" />}
            </button>
          )}

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
              {onToggleTheme && (
                <button
                  className="mobile-theme-btn"
                  onClick={() => {
                    onToggleTheme();
                  }}
                >
                  {isDark ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} />}
                  <span>{isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}</span>
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </header>
  );
}
