import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  Mountain,
  Ruler,
  BarChart3,
  Settings,
  Cpu,
  Radio,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

export default function Sidebar({
  activeNav = 'dashboard',
  onSelectNav = null,
  systemStatus = null,
  isMobileOpen = false,
  onCloseMobile = null,
}) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Image', icon: UploadCloud },
    { id: 'terrain', label: '3D Terrain', icon: Mountain },
    { id: 'measurements', label: 'Measurements', icon: Ruler },
    { id: 'dsm-analysis', label: 'DSM Analysis', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const handleNavClick = (id) => {
    if (onSelectNav) onSelectNav(id);
    if (onCloseMobile) onCloseMobile();
  };

  const isOnline = systemStatus?.status === 'healthy';
  const deviceName = systemStatus?.environment?.device_name || 'CPU';

  return (
    <aside className={`app-sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon-box">
          <svg className="brand-svg-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="16,3 29,27 3,27" stroke="url(#logo-grad)" strokeWidth="2.5" fill="rgba(56, 189, 248, 0.15)" />
            <polygon points="16,11 23,24 9,24" fill="url(#logo-grad-inner)" opacity="0.8" />
            <circle cx="16" cy="11" r="2.5" fill="#38bdf8" />
            <defs>
              <linearGradient id="logo-grad" x1="3" y1="3" x2="29" y2="27" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38bdf8" />
                <stop offset="1" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="logo-grad-inner" x1="9" y1="11" x2="23" y2="24" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38bdf8" stopOpacity="0.8" />
                <stop offset="1" stopColor="#1d4ed8" stopOpacity="0.4" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="brand-text-container">
          <span className="brand-main-title">DEPTHWIZARD</span>
          <span className="brand-tagline">Single-View Terrain Intelligence</span>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="sidebar-nav">
        <div className="nav-group-label">NAVIGATION</div>
        <ul className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeNav === item.id;
            return (
              <li key={item.id}>
                <button
                  className={`nav-item-btn ${isActive ? 'active' : ''}`}
                  onClick={() => handleNavClick(item.id)}
                >
                  <Icon className="nav-icon" size={18} />
                  <span className="nav-label">{item.label}</span>
                  {isActive && <ChevronRight className="nav-active-arrow" size={15} />}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* SIH Recognition Tag */}
      <div className="sidebar-badge-box">
        <div className="sih-indicator">
          <ShieldCheck size={14} className="sih-check-icon" />
          <span>ISRO SIH 2026 #26175</span>
        </div>
      </div>

      {/* Bottom Status Section */}
      <div className="sidebar-footer">
        <div className="system-status-box">
          <div className="status-row">
            <span className="status-text-label">System Status</span>
            <div className="status-indicator-badge">
              <span className={`status-pulse-dot ${isOnline ? 'online' : 'offline'}`} />
              <span className="status-state-text">{isOnline ? 'Online' : 'Connecting'}</span>
            </div>
          </div>
          <div className="model-info-row">
            <span className="model-label">Model</span>
            <span className="model-name">Depth Anything 3</span>
          </div>
          <div className="device-info-row">
            <span className="device-label">Compute</span>
            <span className="device-name">
              <Cpu size={12} className="device-icon" /> {deviceName}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
