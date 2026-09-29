import React, { useState, useRef, useEffect } from 'react';
import {
  Navigation,
  Compass,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import ViewerPage from '../pages/ViewerPage';
import ErrorBoundary from './ErrorBoundary';

/**
 * Tactical 3D Cockpit & Aerial Flythrough Section
 * Direct 112 FPS high-fidelity WebGL GPU vertex displacement flight deck
 * Identical quality, tactical HUD, probe diagnostics & 360° reconnaissance sweep.
 */
export default function TerrainSection(props) {
  const {
    dsmMesh,
    userTextureUrl = null,
    selectedMeasurement,
    onSelectMeasurement,
    onOpenCockpit,
  } = props || {};

  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  // Sync state with native browser fullscreen events
  useEffect(() => {
    const triggerLayoutRecalculation = () => {
      window.dispatchEvent(new Event('resize'));
    };

    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = Boolean(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);

      // Staggered layout resize triggers to allow browser DOM transition to finish
      triggerLayoutRecalculation();
      requestAnimationFrame(triggerLayoutRecalculation);
      setTimeout(triggerLayoutRecalculation, 50);
      setTimeout(triggerLayoutRecalculation, 150);
      setTimeout(triggerLayoutRecalculation, 300);
      setTimeout(triggerLayoutRecalculation, 500);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

  const toggleFullscreen = async () => {
    const el = containerRef.current;
    if (!el) return;
    try {
      const isCurrentlyFullscreen = Boolean(
        document.fullscreenElement ||
        document.webkitFullscreenElement
      );
      if (!isCurrentlyFullscreen) {
        if (el.requestFullscreen) {
          await el.requestFullscreen();
        } else if (el.webkitRequestFullscreen) {
          await el.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          await document.webkitExitFullscreen();
        }
      }
    } catch (err) {
      console.warn('[DepthWizard] Fullscreen toggle error:', err);
    } finally {
      requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
      setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
    }
  };


  return (
    <section
      ref={containerRef}
      className={`terrain-section-card ${isFullscreen ? 'fullscreen-mode' : ''}`}
      id="terrain-section"
    >
      {/* Flight Deck Header Toolbar */}
      <div className="terrain-header-toolbar">
        <div className="toolbar-title-group">
          <Navigation className="text-cyan animate-pulse" size={22} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="terrain-title-text">Tactical 3D Cockpit &amp; Flythrough</h3>
              <span className="flight-live-badge">
                <span className="flight-pulse-dot" />
                <span>112 FPS Fly Engine</span>
              </span>
              <span className="hidden sm:inline-flex px-1.5 py-0.5 text-[10px] font-mono bg-sky-950/70 text-sky-300 border border-sky-800/60 rounded">
                ISRO / SAC Telemetry
              </span>
            </div>
            <span className="terrain-subtitle-text">
              Real-Time Drone Reconnaissance &amp; Metric Elevation Flight Deck ({dsmMesh ? `${dsmMesh.rows || 1024}×${dsmMesh.cols || 612} Grid` : '1024×612 Grid'} · 0.33m GSD)
            </span>
          </div>
        </div>

        {/* Clean, sleek aerospace action buttons */}
        <div className="toolbar-controls-group">
          {onOpenCockpit && (
            <button
              type="button"
              className="tool-btn-cockpit-link"
              onClick={onOpenCockpit}
              title="Launch dedicated full-screen Tactical 3D Cockpit workstation"
            >
              <Compass size={14} />
              <span>Full Cockpit ↗</span>
            </button>
          )}

          <button
            type="button"
            className="tool-btn-neutral"
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            <span>{isFullscreen ? 'Exit' : 'Fullscreen'}</span>
          </button>
        </div>
      </div>

      {/* 3D WebGL Canvas Container with high-fidelity Cockpit View */}
      <div className="terrain-embedded-wrapper">
        <ErrorBoundary>
          <ViewerPage
            jobId={dsmMesh?.job_id || 'demo'}
            userTextureUrl={userTextureUrl || dsmMesh?.texture_url}
            isEmbedded={true}
            onOpenCockpit={onOpenCockpit}
            onSelectPoint={onSelectMeasurement}
          />
        </ErrorBoundary>
      </div>
    </section>
  );
}
