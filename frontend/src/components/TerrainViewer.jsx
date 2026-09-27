import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import sampleOpticalImg from '../assets/sample_gamus_optical.png';
import defaultTerrainMesh from '../data/default_terrain_mesh.json';
import { createTerrainGeometry, createElevationColorTexture, createSlopeColorTexture } from './TerrainMesh';

/**
 * TerrainViewer - WebGL / Three.js 3D Terrain Viewer
 * Implements click-to-measure for HEIGHT, ELEVATION, and SLOPE from actual DSM mesh.
 */
export default function TerrainViewer({
  dsmData = null,
  textureMode = 'rgb', // 'rgb', 'colormap', 'slope', 'wireframe'
  onTextureModeChange = null,
  cameraMode = 'orbit', // 'orbit' or 'fly'
  onCameraModeChange = null,
  verticalExaggeration = 1.0,
  colorRamp = 'terrain',
  selectedPoint = null,
  onSelectPoint = null,
  resetViewTrigger = 0,
}) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainMeshRef = useRef(null);
  const markerGroupRef = useRef(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());
  const mouseDownPosRef = useRef({ x: 0, y: 0 });

  // State (pre-populated with bundled defaultTerrainMesh for 100% instant render)
  const [internalCameraMode, setInternalCameraMode] = useState('orbit');
  const [internalTextureMode, setInternalTextureMode] = useState(textureMode);
  const [loadedMeshMeta, setLoadedMeshMeta] = useState(dsmData || defaultTerrainMesh);
  const [isLoading, setIsLoading] = useState(!dsmData && !defaultTerrainMesh);

  const effectiveCameraMode = cameraMode || internalCameraMode;
  const effectiveTextureMode = textureMode || internalTextureMode;

  // Fly controls movement state
  const flyStateRef = useRef({
    moveForward: false,
    moveBackward: false,
    moveLeft: false,
    moveRight: false,
    moveUp: false,
    moveDown: false,
    speed: 40.0,
  });


  // Fetch real metric DSM from backend if not provided via props
  useEffect(() => {
    if (dsmData) {
      setLoadedMeshMeta(dsmData);
      setIsLoading(false);
      return;
    }

    const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');
    fetch(`${API_BASE}/api/terrain/mesh?resolution=128`)
      .then((res) => {
        if (!res.ok) throw new Error('Live DSM mesh endpoint unavailable');
        return res.json();
      })
      .then((data) => {
        setLoadedMeshMeta(data);
        setIsLoading(false);
      })
      .catch((err) => {
        console.info('[DepthWizard] Using bundled pre-computed GAMUS terrain mesh:', err.message);
        setLoadedMeshMeta(defaultTerrainMesh);
        setIsLoading(false);
      });
  }, [dsmData]);

  // Main Three.js Scene Setup & Render Loop
  useEffect(() => {
    const container = mountRef.current;
    if (!container || !loadedMeshMeta) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 520;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e17);
    scene.fog = new THREE.FogExp2(0x0a0e17, 0.002);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 3000);
    camera.position.set(0, 90, 160);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.minDistance = 10;
    controls.maxDistance = 600;
    controlsRef.current = controls;

    // 5. Lighting (bright, natural lighting for clear 3D visibility from all camera angles)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff8ed, 1.5);
    sunLight.position.set(120, 220, 90);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    scene.add(sunLight);

    const skyFill = new THREE.HemisphereLight(0x38bdf8, 0x0f172a, 0.55);
    scene.add(skyFill);

    // 6. Build Real 3D Terrain Mesh from Metric DSM
    const planeSize = 200;
    const {
      geometry,
      minElevation,
      maxElevation,
      baseOffset = 0,
      planeWidth = 200,
      planeHeight = 200,
    } = createTerrainGeometry({
      heights: loadedMeshMeta.heights,
      rows: loadedMeshMeta.rows,
      cols: loadedMeshMeta.cols,
      planeSize: planeSize,
      aspectRatio: loadedMeshMeta.aspect_ratio || 1.0,
      verticalExaggeration: verticalExaggeration,
    });

    // 7. Textures (Elevation Colormap, Slope, & Optical Satellite)
    const colorTexture = createElevationColorTexture(
      loadedMeshMeta.heights,
      loadedMeshMeta.rows,
      loadedMeshMeta.cols,
      minElevation,
      maxElevation,
      colorRamp
    );

    const slopeTexture = createSlopeColorTexture(
      loadedMeshMeta.heights,
      loadedMeshMeta.rows,
      loadedMeshMeta.cols,
      planeSize
    );

    // Default to color elevation ramp while optical texture loads to prevent any black render
    let initialTexture = colorTexture;
    if (effectiveTextureMode === 'slope') {
      initialTexture = slopeTexture;
    } else if (effectiveTextureMode === 'colormap') {
      initialTexture = colorTexture;
    }

    const terrainMaterial = new THREE.MeshStandardMaterial({
      map: effectiveTextureMode === 'wireframe' ? null : initialTexture,
      wireframe: effectiveTextureMode === 'wireframe',
      roughness: 0.75,
      metalness: 0.05,
      flatShading: false,
    });

    // Asynchronously load RGB optical texture with bundled fallback
    const textureLoader = new THREE.TextureLoader();
    const primaryTextureUrl = loadedMeshMeta.texture_url || sampleOpticalImg;

    const loadTextureWithFallback = (url, isFallback = false) => {
      textureLoader.load(
        url,
        (loadedTex) => {
          loadedTex.wrapS = THREE.ClampToEdgeWrapping;
          loadedTex.wrapT = THREE.ClampToEdgeWrapping;
          loadedTex.needsUpdate = true;
          if (effectiveTextureMode === 'rgb') {
            terrainMaterial.map = loadedTex;
            terrainMaterial.needsUpdate = true;
            if (rendererRef.current && sceneRef.current && cameraRef.current) {
              rendererRef.current.render(sceneRef.current, cameraRef.current);
            }
          }
        },
        undefined,
        (err) => {
          console.warn('[DepthWizard] Optical texture failed to load, falling back:', err);
          if (!isFallback && url !== sampleOpticalImg) {
            loadTextureWithFallback(sampleOpticalImg, true);
          } else {
            // Keep procedural elevation color texture active
            if (effectiveTextureMode === 'rgb') {
              terrainMaterial.map = colorTexture;
              terrainMaterial.needsUpdate = true;
            }
          }
        }
      );
    };

    if (effectiveTextureMode === 'rgb') {
      loadTextureWithFallback(primaryTextureUrl);
    }

    const terrainMesh = new THREE.Mesh(geometry, terrainMaterial);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = true;
    scene.add(terrainMesh);
    terrainMeshRef.current = terrainMesh;

    // Base plate & Reference Grid
    const grid = new THREE.GridHelper(planeSize, 20, 0x0284c7, 0x1e293b);
    grid.position.y = -0.2;
    scene.add(grid);

    // 8. 3D Measurement Marker Pin Group
    const markerGroup = new THREE.Group();
    markerGroup.visible = false;

    // Pin head sphere
    const sphereGeo = new THREE.SphereGeometry(1.6, 16, 16);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xff0000,
      emissiveIntensity: 0.5,
      roughness: 0.3,
    });
    const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
    sphereMesh.position.y = 4.0;
    markerGroup.add(sphereMesh);

    // Pin stem cylinder
    const stemGeo = new THREE.CylinderGeometry(0.2, 0.2, 4.0, 8);
    const stemMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const stemMesh = new THREE.Mesh(stemGeo, stemMat);
    stemMesh.position.y = 2.0;
    markerGroup.add(stemMesh);

    // Ground target ring
    const ringGeo = new THREE.RingGeometry(1.2, 1.8, 24);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.y = 0.1;
    markerGroup.add(ringMesh);

    scene.add(markerGroup);
    markerGroupRef.current = markerGroup;

    // 9. Animation & Render Loop
    let animId;
    let lastTime = performance.now();

    const animate = (currentTime) => {
      animId = requestAnimationFrame(animate);
      const delta = (currentTime - lastTime) / 1000;
      lastTime = currentTime;

      // Pulse ring marker animation
      if (markerGroup.visible) {
        const pulse = 1.0 + 0.15 * Math.sin(currentTime * 0.006);
        ringMesh.scale.set(pulse, 1, pulse);
      }

      // Fly navigation mode
      if (effectiveCameraMode === 'fly') {
        const fly = flyStateRef.current;
        const moveDist = fly.speed * delta;
        const dir = new THREE.Vector3();
        camera.getWorldDirection(dir);
        const side = new THREE.Vector3().crossVectors(dir, camera.up).normalize();

        if (fly.moveForward) camera.position.addScaledVector(dir, moveDist);
        if (fly.moveBackward) camera.position.addScaledVector(dir, -moveDist);
        if (fly.moveLeft) camera.position.addScaledVector(side, -moveDist);
        if (fly.moveRight) camera.position.addScaledVector(side, moveDist);
        if (fly.moveUp) camera.position.y += moveDist;
        if (fly.moveDown) camera.position.y = Math.max(1.0, camera.position.y - moveDist);
      } else {
        controls.update();
      }

      renderer.render(scene, camera);
    };
    animate(performance.now());

    // 10. Click Interaction for Terrain Measurement
    const domElement = renderer.domElement;

    const handlePointerDown = (e) => {
      mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerUp = (e) => {
      const dx = Math.abs(e.clientX - mouseDownPosRef.current.x);
      const dy = Math.abs(e.clientY - mouseDownPosRef.current.y);
      // Ignore if user was dragging the orbit camera
      if (dx > 4 || dy > 4) return;

      const rect = domElement.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const intersects = raycasterRef.current.intersectObject(terrainMesh);

      if (intersects.length > 0) {
        const hit = intersects[0];
        const hitX = hit.point.x;
        const hitZ = hit.point.z;

        // 1. HEIGHT & ELEVATION:
        // hit.point.y is scaled relative height above baseOffset
        const heightM = Math.max(0.0, hit.point.y / Math.max(verticalExaggeration, 0.001));
        const elevationM = baseOffset + heightM;

        // 2. Local grid indices on the actual DSM grid (rows x cols)
        const cols = loadedMeshMeta.cols;
        const rows = loadedMeshMeta.rows;
        const heights = loadedMeshMeta.heights;

        const colFloat = ((hitX / planeWidth) + 0.5) * (cols - 1);
        const rowFloat = ((hitZ / planeHeight) + 0.5) * (rows - 1);

        const c = Math.max(0, Math.min(cols - 1, Math.round(colFloat)));
        const r = Math.max(0, Math.min(rows - 1, Math.round(rowFloat)));

        // 3. SLOPE: Calculate local slope from surrounding elevation gradient
        // Cell spacing in physical coordinates
        const dxM = planeWidth / Math.max(1, cols - 1);
        const dzM = planeHeight / Math.max(1, rows - 1);

        const cPrev = Math.max(0, c - 1);
        const cNext = Math.min(cols - 1, c + 1);
        const rPrev = Math.max(0, r - 1);
        const rNext = Math.min(rows - 1, r + 1);

        const zLeft = heights[r * cols + cPrev] ?? elevationM;
        const zRight = heights[r * cols + cNext] ?? elevationM;
        const zUp = heights[rPrev * cols + c] ?? elevationM;
        const zDown = heights[rNext * cols + c] ?? elevationM;

        const dz_dx = (zRight - zLeft) / Math.max(1e-4, (cNext - cPrev) * dxM);
        const dz_dz = (zDown - zUp) / Math.max(1e-4, (rNext - rPrev) * dzM);

        const gradientMag = Math.sqrt(dz_dx * dz_dx + dz_dz * dz_dz);
        const slopeDeg = Math.atan(gradientMag) * (180.0 / Math.PI);

        // Position 3D marker
        markerGroup.position.copy(hit.point);
        markerGroup.visible = true;

        const measurementResult = {
          height: heightM,
          elevation: elevationM,
          slope: slopeDeg,
          x: hitX,
          z: hitZ,
          row: r,
          col: c,
        };

        if (onSelectPoint) {
          onSelectPoint(measurementResult);
        }
      }
    };

    domElement.addEventListener('pointerdown', handlePointerDown);
    domElement.addEventListener('pointerup', handlePointerUp);

    // Keyboard handlers for Fly mode
    const handleKeyDown = (e) => {
      const fly = flyStateRef.current;
      switch (e.code) {
        case 'KeyW': fly.moveForward = true; break;
        case 'KeyS': fly.moveBackward = true; break;
        case 'KeyA': fly.moveLeft = true; break;
        case 'KeyD': fly.moveRight = true; break;
        case 'KeyQ': fly.moveDown = true; break;
        case 'KeyE': fly.moveUp = true; break;
        default: break;
      }
    };

    const handleKeyUp = (e) => {
      const fly = flyStateRef.current;
      switch (e.code) {
        case 'KeyW': fly.moveForward = false; break;
        case 'KeyS': fly.moveBackward = false; break;
        case 'KeyA': fly.moveLeft = false; break;
        case 'KeyD': fly.moveRight = false; break;
        case 'KeyQ': fly.moveDown = false; break;
        case 'KeyE': fly.moveUp = false; break;
        default: break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      domElement.removeEventListener('pointerdown', handlePointerDown);
      domElement.removeEventListener('pointerup', handlePointerUp);
      controls.dispose();
      geometry.dispose();
      terrainMaterial.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [loadedMeshMeta, effectiveTextureMode, verticalExaggeration, colorRamp, effectiveCameraMode]);

  // Synchronize marker visibility if selectedPoint cleared
  useEffect(() => {
    if (markerGroupRef.current && !selectedPoint) {
      markerGroupRef.current.visible = false;
    }
  }, [selectedPoint]);

  // Handle camera reset trigger
  useEffect(() => {
    if (cameraRef.current && controlsRef.current && resetViewTrigger > 0) {
      cameraRef.current.position.set(0, 90, 160);
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    }
  }, [resetViewTrigger]);

  const handleTextureChange = (mode) => {
    setInternalTextureMode(mode);
    if (onTextureModeChange) onTextureModeChange(mode);
  };

  const toggleCameraMode = () => {
    const next = effectiveCameraMode === 'orbit' ? 'fly' : 'orbit';
    setInternalCameraMode(next);
    if (onCameraModeChange) onCameraModeChange(next);
  };

  return (
    <div className="terrain-viewer-wrapper">
      <div className="terrain-canvas-box" ref={mountRef}>
        {isLoading && (
          <div className="terrain-loader-overlay">
            <div className="loading-orbit" />
            <p>Constructing 3D Metric Terrain Mesh from DSM...</p>
            <span>Connecting DSM vertices and mapping RGB texture</span>
          </div>
        )}

        {/* Floating Overlay Measurement HUD Cards */}
        <div className="terrain-overlay-hud">
          <div className="hud-metric-pill">
            <span className="hud-metric-title">HEIGHT</span>
            <span className="hud-metric-number">
              {selectedPoint ? `${selectedPoint.height.toFixed(1)} m` : (loadedMeshMeta ? `${(loadedMeshMeta.max_height - loadedMeshMeta.min_height).toFixed(1)} m` : '--')}
            </span>
          </div>
          <div className="hud-metric-pill">
            <span className="hud-metric-title">ELEVATION</span>
            <span className="hud-metric-number">
              {selectedPoint ? `${selectedPoint.elevation.toFixed(1)} m` : (loadedMeshMeta ? `${loadedMeshMeta.mean_height?.toFixed(1)} m` : '--')}
            </span>
          </div>
          <div className="hud-metric-pill">
            <span className="hud-metric-title">SLOPE</span>
            <span className="hud-metric-number">
              {selectedPoint ? `${selectedPoint.slope.toFixed(1)}°` : '--'}
            </span>
          </div>
        </div>

        <div className="terrain-quick-controls">
          <div className="view-mode-pills">
            <button
              className={`pill-btn ${effectiveTextureMode === 'rgb' ? 'active' : ''}`}
              onClick={() => handleTextureChange('rgb')}
              title="Drape original high-res optical satellite image"
            >
              🛰️ Optical RGB
            </button>
            <button
              className={`pill-btn ${effectiveTextureMode === 'colormap' ? 'active' : ''}`}
              onClick={() => handleTextureChange('colormap')}
              title="Color-code terrain by metric elevation in meters"
            >
              🏔️ Elevation Color
            </button>
            <button
              className={`pill-btn ${effectiveTextureMode === 'slope' ? 'active' : ''}`}
              onClick={() => handleTextureChange('slope')}
              title="Color-code terrain by surface slope gradient in degrees"
            >
              📐 Slope Map
            </button>
            <button
              className={`pill-btn ${effectiveTextureMode === 'wireframe' ? 'active' : ''}`}
              onClick={() => handleTextureChange('wireframe')}
              title="Show topographic triangulated wireframe mesh"
            >
              🕸️ Wireframe
            </button>
          </div>

          <button
            className={`btn-camera-toggle ${effectiveCameraMode === 'fly' ? 'active' : ''}`}
            onClick={toggleCameraMode}
            title="Toggle between orbital camera and flythrough mode (WASD + QE)"
          >
            {effectiveCameraMode === 'fly' ? '✈️ Fly Mode (WASD)' : '🛰️ Orbit Camera'}
          </button>
        </div>
      </div>
    </div>
  );
}
