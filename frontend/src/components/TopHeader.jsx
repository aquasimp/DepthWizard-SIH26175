import React from 'react';
import {
  Menu,
  Cpu,
  Settings as SettingsIcon,
  User,
  Activity,
  CheckCircle2,
  Loader2,
  Layers,
} from 'lucide-react';

export default function TopHeader({
  pipelineState = 'idle', // 'idle' | 'running' | 'completed' | 'error'
  systemStatus = null,
  onOpenSettings = null,
  onToggleMobileMenu = null,
}) {
  const isOnline = systemStatus?.status === 'healthy';
  const deviceName = systemStatus?.environment?.device_name || 'CPU';
  const isGPU = systemStatus?.environment?.cuda_available || false;

  let statusBadge = (
    <div className="header-status-badge idle">
      <span className="badge-dot idle" />
      <span>Standby</span>
    </div>
  );

  if (pipelineState === 'running') {
    statusBadge = (
      <div className="header-status-badge running">
        <Loader2 className="spin-icon" size={13} />
        <span>Processing Pipeline...</span>
      </div>
    );
  } else if (pipelineState === 'completed') {
    statusBadge = (
      <div className="header-status-badge completed">
        <CheckCircle2 size={13} className="text-emerald" />
        <span>Terrain Generated</span>
      </div>
    );
  } else if (pipelineState === 'error') {
    statusBadge = (
      <div className="header-status-badge error">
        <span className="badge-dot error" />
        <span>Pipeline Error</span>
      </div>
    );
  }

  return (
    <header className="top-header">
      <div className="header-left">
        {onToggleMobileMenu && (
          <button
            className="mobile-hamburger-btn"
            onClick={onToggleMobileMenu}
            aria-label="Toggle navigation menu"
          >
            <Menu size={20} />
          </button>
        )}
        <div className="header-title-block">
          <div className="title-row">
            <h1 className="header-app-title">DepthWizard</h1>
            <span className="version-pill">v0.1.0-MVP</span>
          </div>
          <p className="header-app-subtitle">
            Single-View Height Estimation &amp; 3D Flythrough
          </p>
        </div>
      </div>

      <div className="header-right">
        {/* Processing Status Badge */}
        {statusBadge}

        {/* Compute Device Status */}
        <div className={`compute-device-badge ${isGPU ? 'gpu' : 'cpu'}`} title="Active Compute Device">
          <Cpu size={14} className="compute-icon" />
          <span>{deviceName}</span>
        </div>

        {/* Settings Action Button */}
        <button
          className="header-icon-btn"
          onClick={onOpenSettings}
          title="Open Application Settings & Diagnostic Info"
          aria-label="Settings"
        >
          <SettingsIcon size={18} />
        </button>

        {/* User / Profile Icon */}
        <div className="header-user-avatar" title="ISRO SIH Technical Demonstration">
          <div className="avatar-circle">
            <User size={16} />
          </div>
          <span className="user-role-label">DEMO</span>
        </div>
      </div>
    </header>
  );
}
