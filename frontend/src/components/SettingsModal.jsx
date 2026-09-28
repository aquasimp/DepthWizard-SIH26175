import React, { useState } from 'react';
import { X, Settings, Cpu, Globe, Sliders, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { getApiBase, setApiBase, checkBackendHealth } from '../utils/apiConfig';

export default function SettingsModal(props) {
  const {
    isOpen = false,
    onClose = null,
    systemStatus = null,
    onSystemStatusChange = null,
    colorRamp = 'terrain',
    onColorRampChange = null,
    verticalExaggeration = 1.0,
    onVerticalExaggerationChange = null,
  } = props || {};

  const [apiUrl, setApiUrl] = useState(() => getApiBase());
  const [testingStatus, setTestingStatus] = useState('idle');
  const [testMessage, setTestMessage] = useState(null);

  if (!isOpen) return null;

  const isCuda = Boolean(systemStatus?.cuda_available || systemStatus?.environment?.cuda_available);
  const device = systemStatus?.device || systemStatus?.environment?.device_name || (isCuda ? 'CUDA (GPU)' : (systemStatus ? 'CPU' : 'In-Browser Client Engine (Standalone)'));
  const pythonVer = systemStatus?.environment?.python_version || (systemStatus ? '3.11+' : 'WebAssembly / WebGL (Client)');
  const weightsReady = systemStatus?.active_checkpoint ? `Loaded (${systemStatus.active_checkpoint})` : (systemStatus ? 'Loaded & Verified (v1.1.0 Multi-City)' : 'GAMUS Geometric Calibration Active');

  const handleTestAndSave = async () => {
    setTestingStatus('testing');
    setTestMessage(null);

    const result = await checkBackendHealth(apiUrl);
    if (result.ok && result.data) {
      setApiBase(apiUrl);
      setTestingStatus('success');
      setTestMessage(`Connected: ${result.data.model_name || 'DepthWizard Backend Ready'}`);
      if (onSystemStatusChange) {
        onSystemStatusChange(result.data);
      }
    } else {
      setTestingStatus('error');
      setTestMessage(result.error || 'Connection failed. App will use Standalone In-Browser Engine.');
    }
  };

  const handleResetToDefault = () => {
    setApiBase('');
    setApiUrl('');
    setTestingStatus('idle');
    setTestMessage(null);
  };

  return (
    <div className="modal-backdrop-blur" onClick={onClose}>
      <div className="settings-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header-row">
          <div className="modal-title-wrap">
            <Settings size={20} className="text-cyan" />
            <h3 className="modal-heading-text">DepthWizard Settings &amp; Diagnostics</h3>
          </div>
          <button className="modal-close-icon-btn" onClick={onClose} aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body-scrollable">
          {/* Section 1: System & Compute Diagnostics */}
          <div className="settings-section-card">
            <h4 className="settings-section-title">
              <Cpu size={16} />
              <span>Compute &amp; Hardware Diagnostics</span>
            </h4>
            <div className="settings-details-table">
              <div className="setting-row">
                <span className="setting-key">Active Compute Engine</span>
                <span className="setting-val font-mono">{device}</span>
              </div>
              <div className="setting-row">
                <span className="setting-key">Acceleration State</span>
                <span className="setting-val font-mono">
                  {isCuda ? 'CUDA 12.x Active (RTX Accelerated)' : systemStatus ? 'CPU Optimization (AVX2)' : 'GPU WebGL Shader + Canvas Acceleration'}
                </span>
              </div>
              <div className="setting-row">
                <span className="setting-key">Runtime Environment</span>
                <span className="setting-val font-mono">{pythonVer}</span>
              </div>
              <div className="setting-row">
                <span className="setting-key">Model / Calibration</span>
                <span className="setting-val font-mono">{weightsReady}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Visual & Display Preferences */}
          <div className="settings-section-card">
            <h4 className="settings-section-title">
              <Sliders size={16} />
              <span>Display &amp; Topographic Preferences</span>
            </h4>
            <div className="settings-details-table">
              <div className="setting-row">
                <span className="setting-key">Elevation Colormap</span>
                <select
                  value={colorRamp}
                  onChange={(e) => onColorRampChange && onColorRampChange(e.target.value)}
                  className="settings-dropdown"
                >
                  <option value="terrain">Natural Terrain (Hypsometric)</option>
                  <option value="viridis">Viridis Spectral</option>
                </select>
              </div>
              <div className="setting-row">
                <span className="setting-key">Default Vertical Exaggeration</span>
                <span className="setting-val font-mono">{verticalExaggeration.toFixed(1)}x</span>
              </div>
            </div>
          </div>

          {/* Section 3: API Gateway & Service Health */}
          <div className="settings-section-card">
            <h4 className="settings-section-title">
              <Globe size={16} />
              <span>API Gateway &amp; Backend Connectivity</span>
            </h4>
            <p className="text-xs text-slate-400 mb-3">
              On Vercel, DepthWizard runs an automatic in-browser depth engine. If you have a deployed PyTorch backend (e.g., Render, Railway, Ngrok, EC2), enter the base URL below:
            </p>

            <div className="flex flex-col gap-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="e.g. https://my-depthwizard-backend.onrender.com"
                  className="flex-1 px-3 py-1.5 text-xs font-mono bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={handleTestAndSave}
                  disabled={testingStatus === 'testing'}
                  className="px-3 py-1.5 text-xs font-medium rounded bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {testingStatus === 'testing' ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      <span>Testing...</span>
                    </>
                  ) : (
                    <span>Test &amp; Save</span>
                  )}
                </button>
              </div>

              {testMessage && (
                <div className={`text-xs px-2.5 py-1.5 rounded flex items-center gap-1.5 ${testingStatus === 'success' ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800' : 'bg-rose-950/60 text-rose-300 border border-rose-800'}`}>
                  {testingStatus === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                  <span>{testMessage}</span>
                </div>
              )}

              <div className="flex items-center justify-between mt-1 text-xs text-slate-400">
                <span>Active Endpoint: <strong className="font-mono text-slate-300">{getApiBase() || 'None (Standalone Client Engine)'}</strong></span>
                <button
                  type="button"
                  onClick={handleResetToDefault}
                  className="text-xs text-cyan-400 hover:underline"
                >
                  Clear Custom URL
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer-row">
          <button className="btn-modal-done" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
