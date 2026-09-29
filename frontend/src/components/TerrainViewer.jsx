import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import sampleOpticalImg from '../assets/sample_gamus_optical.png';
import defaultTerrainMesh from '../data/default_terrain_mesh.json';
import { createTerrainGeometry, createElevationColorTexture, createSlopeColorTexture } from './TerrainMesh';
import { getApiBase } from '../utils/apiConfig';

/**
 * TerrainViewer - WebGL / Three.js 3D Terrain Viewer
 * High-performance, single-context 3D heightfield viewer.
 * Updates vertex positions, materials, and textures in-place without context loss or camera resets.
 */
export default function TerrainViewer({
  dsmData = null,
  userTextureUrl = null,
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
  const terrainMaterialRef = useRef(null);
  const markerGroupRef = useRef(null);
  const ringMeshRef = useRef(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());
  const mouseDownPosRef = useRef({ x: 0, y: 0 });

  // Texture caches to allow instantaneous mode switching without network overhead
  const colorTextureRef = useRef(null);
  const slopeTextureRef = useRef(null);
  const opticalTextureRef = useRef(null);

  // Active mesh metadata
  const [internalCameraMode, setInternalCameraMode] = useState('orbit');
  const [internalTextureMode, setInternalTextureMode] = useState(textureMode);
  const [loadedMeshMeta, setLoadedMeshMeta] = useState(dsmData || defaultTerrainMesh);
  const loadedMeshMetaRef = useRef(loadedMeshMeta);
  loadedMeshMetaRef.current = loadedMeshMeta;

  const verticalExaggerationRef = useRef(verticalExaggeration);
  verticalExaggerationRef.current = verticalExaggeration;

  const effectiveCameraMode = cameraMode || internalCameraMode;
  const effectiveTextureMode = textureMode || internalTextureMode;

  const cameraModeRef = useRef(effectiveCameraMode);
  cameraModeRef.current = effectiveCameraMode;

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

  // Keep internal mesh meta in sync with dsmData prop
  useEffect(() => {
    if (dsmData) {
      setLoadedMeshMeta(dsmData);
      return;
    }

    const apiBase = getApiBase();
    if (apiBase) {
      fetch(`${apiBase}/api/terrain/mesh?resolution=128`)
        .then((res) => {
          if (!res.ok) throw new Error('Live DSM mesh endpoint unavailable');
          return res.json();
        })
        .then((data) => {
          if (data && data.heights) {
            setLoadedMeshMeta(data);
          }
        })
        .catch((err) => {
          console.info('[DepthWizard] Using bundled pre-computed GAMUS terrain mesh:', err.message);
          setLoadedMeshMeta(defaultTerrainMesh);
        });
    }
  }, [dsmData]);

  // Resolve best available optical texture URL without making broken network calls
  const resolveOpticalTextureUrl = useCallback((meta) => {
    if (userTextureUrl) return userTextureUrl;
    if (meta?.texture_url) {
      // If it's a blob URL or base64 data URL, use directly
      if (meta.texture_url.startsWith('blob:') || meta.texture_url.startsWith('data:')) {
        return meta.texture_url;
      }
      // If it's a relative /api/ link
      if (meta.texture_url.startsWith('/api/') || meta.texture_url.includes('localhost:8000')) {
        const apiBase = getApiBase() || 'http://127.0.0.1:8000';
        const cleanPath = meta.texture_url.replace(/^.*localhost:\d+/, '');
        return `${apiBase}${cleanPath}`;
      }
      return meta.texture_url;
    }
    return sampleOpticalImg;
  }, [userTextureUrl]);

  // Helper to build or update terrain mesh geometry and textures
  const buildOrUpdateMesh = useCallback((scene, meta) => {
    if (!scene || !meta || !meta.heights || !meta.heights.length) return;

    const planeSize = 200;
    const {
      geometry,
      minElevation,
      maxElevation,
      baseOffset = 0,
      reliefMultiplier = 1.0,
      planeWidth = 200,
      planeHeight = 200,
    } = createTerrainGeometry({
      heights: meta.heights,
      rows: meta.rows,
      cols: meta.cols,
      planeSize,
      aspectRatio: meta.aspect_ratio || 1.0,
      verticalExaggeration: verticalExaggerationRef.current,
    });

    // Procedural Colormap & Slope Textures
    const colorTexture = createElevationColorTexture(
      meta.heights,
      meta.rows,
      meta.cols,
      minElevation,
      maxElevation,
      colorRamp
    );
    colorTextureRef.current = colorTexture;

    const slopeTexture = createSlopeColorTexture(
      meta.heights,
      meta.rows,
      meta.cols,
      planeSize
    );
    slopeTextureRef.current = slopeTexture;

    // Optical RGB Texture Loader
    const textureLoader = new THREE.TextureLoader();
    const opticalUrl = resolveOpticalTextureUrl(meta);

    let activeMap = colorTexture;
    if (effectiveTextureMode === 'slope') activeMap = slopeTexture;
    else if (effectiveTextureMode === 'colormap') activeMap = colorTexture;

    let terrainMaterial = terrainMaterialRef.current;
    if (!terrainMaterial) {
      terrainMaterial = new THREE.MeshStandardMaterial({
        map: effectiveTextureMode === 'wireframe' ? null : activeMap,
        wireframe: effectiveTextureMode === 'wireframe',
        roughness: 0.75,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
      terrainMaterialRef.current = terrainMaterial;
    } else {
      terrainMaterial.map = effectiveTextureMode === 'wireframe' ? null : activeMap;
      terrainMaterial.wireframe = effectiveTextureMode === 'wireframe';
      terrainMaterial.side = THREE.DoubleSide;
      terrainMaterial.needsUpdate = true;
    }

    // Load optical texture asynchronously
    textureLoader.load(
      opticalUrl,
      (loadedTex) => {
        loadedTex.wrapS = THREE.ClampToEdgeWrapping;
        loadedTex.wrapT = THREE.ClampToEdgeWrapping;
        loadedTex.needsUpdate = true;
        opticalTextureRef.current = loadedTex;
        if (effectiveTextureMode === 'rgb' && terrainMaterialRef.current) {
          terrainMaterialRef.current.map = loadedTex;
          terrainMaterialRef.current.needsUpdate = true;
        }
      },
      undefined,
      () => {
        if (opticalUrl !== sampleOpticalImg) {
          textureLoader.load(sampleOpticalImg, (fbTex) => {
            opticalTextureRef.current = fbTex;
            if (effectiveTextureMode === 'rgb' && terrainMaterialRef.current) {
              terrainMaterialRef.current.map = fbTex;
              terrainMaterialRef.current.needsUpdate = true;
            }
          });
        }
      }
    );

    // Existing mesh update vs new creation
    let mesh = terrainMeshRef.current;
    if (mesh) {
      if (mesh.geometry) mesh.geometry.dispose();
      mesh.geometry = geometry;
      mesh.material = terrainMaterial;
      if (!scene.children.includes(mesh)) {
        scene.add(mesh);
      }
    } else {
      mesh = new THREE.Mesh(geometry, terrainMaterial);
      mesh.receiveShadow = true;
      mesh.castShadow = true;
      scene.add(mesh);
      terrainMeshRef.current = mesh;
    }

    mesh.visible = true;
    mesh.userData = {
      baseOffset,
      reliefMultiplier,
      verticalExaggeration: verticalExaggerationRef.current,
      planeWidth,
      planeHeight,
      meta,
    };
  }, [colorRamp, effectiveTextureMode, resolveOpticalTextureUrl]);

  // 1. Scene & WebGLRenderer Setup (MOUNT ONCE)
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 520;

    // A. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e17);
    scene.fog = new THREE.FogExp2(0x0a0e17, 0.002);
    sceneRef.current = scene;

    // B. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 3000);
    camera.position.set(0, 90, 160);
    cameraRef.current = camera;

    // C. Renderer (single WebGL context created once)
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // D. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.minDistance = 10;
    controls.maxDistance = 600;
    controlsRef.current = controls;

    // E. Lighting
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

    // F. Base Reference Grid
    const planeSize = 200;
    const grid = new THREE.GridHelper(planeSize, 20, 0x0284c7, 0x1e293b);
    grid.position.y = -0.2;
    scene.add(grid);

    // G. 3D Measurement Marker Pin Group
    const markerGroup = new THREE.Group();
    markerGroup.visible = false;

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

    const stemGeo = new THREE.CylinderGeometry(0.2, 0.2, 4.0, 8);
    const stemMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const stemMesh = new THREE.Mesh(stemGeo, stemMat);
    stemMesh.position.y = 2.0;
    markerGroup.add(stemMesh);

    const ringGeo = new THREE.RingGeometry(1.2, 1.8, 24);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.y = 0.1;
    markerGroup.add(ringMesh);
    ringMeshRef.current = ringMesh;

    scene.add(markerGroup);
    markerGroupRef.current = markerGroup;

    // G. Build initial mesh immediately so scene is never empty
    if (loadedMeshMetaRef.current && loadedMeshMetaRef.current.heights) {
      buildOrUpdateMesh(scene, loadedMeshMetaRef.current);
    }

    // H. Continuous Animation Loop
    let animId;
    let lastTime = performance.now();

    const animate = (currentTime) => {
      animId = requestAnimationFrame(animate);
      const delta = (currentTime - lastTime) / 1000;
      lastTime = currentTime;

      if (markerGroup.visible && ringMeshRef.current) {
        const pulse = 1.0 + 0.15 * Math.sin(currentTime * 0.006);
        ringMeshRef.current.scale.set(pulse, 1, pulse);
      }

      if (cameraModeRef.current === 'fly') {
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

    // I. Click Interaction for Terrain Measurement
    const domElement = renderer.domElement;

    const handlePointerDown = (e) => {
      mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerUp = (e) => {
      const dx = Math.abs(e.clientX - mouseDownPosRef.current.x);
      const dy = Math.abs(e.clientY - mouseDownPosRef.current.y);
      if (dx > 5 || dy > 5) return;

      const rect = domElement.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const terrainMesh = terrainMeshRef.current;
      if (!terrainMesh) return;

      const intersects = raycasterRef.current.intersectObject(terrainMesh);
      if (intersects.length > 0) {
        const hit = intersects[0];
        const hitX = hit.point.x;
        const hitZ = hit.point.z;
        const meshUserData = terrainMesh.userData || {};

        const baseOffset = meshUserData.baseOffset || 0;
        const currentExag = meshUserData.verticalExaggeration || 1.0;
        const pWidth = meshUserData.planeWidth || 200;
        const pHeight = meshUserData.planeHeight || 200;
        const meta = meshUserData.meta || loadedMeshMeta;

        const cols = meta.cols || 128;
        const rows = meta.rows || 128;
        const heights = meta.heights || [];

        const colFloat = ((hitX / pWidth) + 0.5) * (cols - 1);
        const rowFloat = ((hitZ / pHeight) + 0.5) * (rows - 1);

        const c = Math.max(0, Math.min(cols - 1, Math.round(colFloat)));
        const r = Math.max(0, Math.min(rows - 1, Math.round(rowFloat)));

        // Retrieve real physical metric elevation from heightfield raster
        const rawRasterH = (heights && heights[r * cols + c] !== undefined)
          ? heights[r * cols + c]
          : null;

        const elevationM = rawRasterH !== null
          ? rawRasterH
          : (currentExag > 0.01 ? baseOffset + (hit.point.y / currentExag) : baseOffset);
        const heightM = Math.max(0.0, elevationM - baseOffset);

        const dxM = pWidth / Math.max(1, cols - 1);
        const dzM = pHeight / Math.max(1, rows - 1);

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

        markerGroup.position.copy(hit.point);
        const reliefMultiplier = meshUserData.reliefMultiplier || 1.0;
        markerGroup.userData = {
          relH: heightM * reliefMultiplier,
          hitX,
          hitZ,
          row: r,
          col: c,
        };
        markerGroup.visible = true;

        if (onSelectPoint) {
          onSelectPoint({
            height: heightM,
            elevation: elevationM,
            slope: slopeDeg,
            x: hitX,
            z: hitZ,
            row: r,
            col: c,
          });
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

    // Robust multi-phase resize handler with sub-pixel and fullscreen stabilization
    const handleResize = () => {
      const cont = mountRef.current;
      const cam = cameraRef.current;
      const rend = rendererRef.current;
      const ctrl = controlsRef.current;
      if (!cont || !cam || !rend) return;

      const w = cont.clientWidth;
      const h = cont.clientHeight;
      if (w < 10 || h < 10) return;

      cam.aspect = w / h;
      cam.updateProjectionMatrix();
      rend.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      rend.setSize(w, h, false);
      if (rend.domElement) {
        rend.domElement.style.width = '100%';
        rend.domElement.style.height = '100%';
      }
      if (ctrl) {
        ctrl.update();
      }
    };

    const resizeObserver = new ResizeObserver(() => handleResize());
    resizeObserver.observe(container);

    const handleFullscreenTransition = () => {
      handleResize();
      setTimeout(handleResize, 50);
      setTimeout(handleResize, 150);
      setTimeout(handleResize, 350);
    };

    window.addEventListener('resize', handleResize);
    document.addEventListener('fullscreenchange', handleFullscreenTransition);
    document.addEventListener('webkitfullscreenchange', handleFullscreenTransition);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('fullscreenchange', handleFullscreenTransition);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenTransition);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      domElement.removeEventListener('pointerdown', handlePointerDown);
      domElement.removeEventListener('pointerup', handlePointerUp);
      controls.dispose();
      renderer.dispose();
      if (terrainMeshRef.current && sceneRef.current) {
        sceneRef.current.remove(terrainMeshRef.current);
        if (terrainMeshRef.current.geometry) terrainMeshRef.current.geometry.dispose();
      }
      terrainMeshRef.current = null;
      terrainMaterialRef.current = null;
      sceneRef.current = null;
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []); // Run ONCE on mount

  // 2. Build or Rebuild Mesh Geometry when loadedMeshMeta changes
  useEffect(() => {
    const scene = sceneRef.current;
    if (scene && loadedMeshMeta?.heights) {
      buildOrUpdateMesh(scene, loadedMeshMeta);
    }
  }, [loadedMeshMeta, buildOrUpdateMesh]);

  // 3. Ultra-fast IN-PLACE Vertical Exaggeration update (Zero scene recreation!)
  useEffect(() => {
    const mesh = terrainMeshRef.current;
    if (!mesh || !mesh.geometry || !loadedMeshMeta?.heights) return;

    mesh.userData.verticalExaggeration = verticalExaggeration;
    const posAttr = mesh.geometry.attributes.position;
    const heights = loadedMeshMeta.heights;
    const baseOffset = mesh.userData.baseOffset || 0;
    const reliefMultiplier = mesh.userData.reliefMultiplier || 1.0;

    const rows = loadedMeshMeta.rows || 128;
    const cols = loadedMeshMeta.cols || 128;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const val = heights[i] !== undefined ? heights[i] : baseOffset;
        let effectiveH = val;

        if (r > 0 && r < rows - 1 && c > 0 && c < cols - 1) {
          const nUp = heights[(r - 1) * cols + c] ?? val;
          const nDown = heights[(r + 1) * cols + c] ?? val;
          const nLeft = heights[r * cols + (c - 1)] ?? val;
          const nRight = heights[r * cols + (c + 1)] ?? val;
          const neighborMean = (nUp + nDown + nLeft + nRight) * 0.25;
          if (val - neighborMean > 5.0) {
            effectiveH = neighborMean + 1.5;
          }
        }

        const relH = Math.max(0, (effectiveH - baseOffset) * reliefMultiplier);
        posAttr.setY(i, relH * verticalExaggeration);
      }
    }
    posAttr.needsUpdate = true;
    mesh.geometry.computeVertexNormals();

    // Dynamically update pin marker elevation so it rises/flattens smoothly with the surface!
    const marker = markerGroupRef.current;
    if (marker && marker.visible && marker.userData?.relH !== undefined) {
      marker.position.y = marker.userData.relH * verticalExaggeration;
    }
  }, [verticalExaggeration, loadedMeshMeta]);

  // 4. IN-PLACE Texture Mode Switching (RGB, Colormap, Slope, Wireframe)
  useEffect(() => {
    const mat = terrainMaterialRef.current;
    if (!mat) return;

    if (effectiveTextureMode === 'wireframe') {
      mat.wireframe = true;
      mat.map = null;
    } else if (effectiveTextureMode === 'colormap') {
      mat.wireframe = false;
      mat.map = colorTextureRef.current;
    } else if (effectiveTextureMode === 'slope') {
      mat.wireframe = false;
      mat.map = slopeTextureRef.current;
    } else if (effectiveTextureMode === 'rgb') {
      mat.wireframe = false;
      mat.map = opticalTextureRef.current || colorTextureRef.current;
    }
    mat.needsUpdate = true;
  }, [effectiveTextureMode]);

  // 5. Hide 3D marker when measurement cleared
  useEffect(() => {
    if (markerGroupRef.current && !selectedPoint) {
      markerGroupRef.current.visible = false;
    }
  }, [selectedPoint]);

  // 6. Camera reset trigger
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
    <div className="terrain-viewer-container" style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={mountRef} className="terrain-webgl-canvas" style={{ width: '100%', height: '100%', overflow: 'hidden' }} />

      {/* Floating Viewport Quick Controls */}
      <div className="terrain-viewport-overlay">
        {/* Navigation Info Pill */}
        <div className="viewport-info-pill">
          <span className="dot-live" />
          <span className="pill-text font-mono">
            {effectiveCameraMode === 'fly' ? 'Flythrough (WASD+QE)' : 'Orbit (Click-Measure Active)'}
          </span>
          {loadedMeshMeta?.is_client_side && (
            <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-cyan-900/60 text-cyan-300 border border-cyan-700 rounded font-semibold">
              Client Engine
            </span>
          )}
        </div>

        {/* Texture Mode Selector Buttons */}
        <div className="viewport-mode-pills">
          <button
            className={`pill-btn ${effectiveTextureMode === 'rgb' ? 'active' : ''}`}
            onClick={() => handleTextureChange('rgb')}
            title="Draped True-Color Satellite / Aerial Optical Texture"
          >
            RGB Optical
          </button>
          <button
            className={`pill-btn ${effectiveTextureMode === 'colormap' ? 'active' : ''}`}
            onClick={() => handleTextureChange('colormap')}
            title="Procedural Elevation Hypsometric Tint"
          >
            Colormap
          </button>
          <button
            className={`pill-btn ${effectiveTextureMode === 'slope' ? 'active' : ''}`}
            onClick={() => handleTextureChange('slope')}
            title="Topographic Slope Angle Analysis (<5° Green, 5-15° Cyan, 15-30° Yellow, >30° Red)"
          >
            Slope
          </button>
          <button
            className={`pill-btn ${effectiveTextureMode === 'wireframe' ? 'active' : ''}`}
            onClick={() => handleTextureChange('wireframe')}
            title="Structural Geometric Elevation Grid Triangulation"
          >
            Wireframe
          </button>
        </div>
      </div>
    </div>
  );
}
