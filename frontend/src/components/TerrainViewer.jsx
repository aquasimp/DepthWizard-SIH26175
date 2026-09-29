import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Compass,
  Play,
  Pause,
  FastForward,
  RotateCcw,
  Gauge,
  Navigation,
  Crosshair,
  Sliders,
  Layers,
  Eye,
  Sun,
  Maximize2,
  Minimize2,
  ChevronDown,
  ChevronUp,
  Radio,
  Activity,
  Box,
} from 'lucide-react';
import sampleOpticalImg from '../assets/sample_gamus_optical.png';
import defaultTerrainMesh from '../data/default_terrain_mesh.json';
import { createTerrainGeometry, createElevationColorTexture, createSlopeColorTexture } from './TerrainMesh';
import { getApiBase } from '../utils/apiConfig';

/**
 * TerrainViewer - Tactical 3D Cockpit & Aerial Reconnaissance Engine
 * 60 FPS WebGL engine with automated cinematic flythrough tour,
 * manual first-person drone flight simulator, solar angle illumination,
 * surface diagnostics, and point probe measurements.
 */
export default function TerrainViewer({
  dsmData = null,
  userTextureUrl = null,
  textureMode = 'rgb', // 'rgb', 'colormap', 'slope', 'wireframe'
  onTextureModeChange = null,
  cameraMode = 'fly', // 'fly', 'orbit', 'topdown'
  onCameraModeChange = null,
  flightMode = 'auto', // 'auto' | 'manual' | 'orbit' | 'topdown'
  onFlightModeChange = null,
  isTourPaused = false,
  onToggleTourPause = null,
  tourSpeed = 1.0,
  onChangeTourSpeed = null,
  cruiseAltitude = 28.0,
  onChangeAltitude = null,
  verticalExaggeration = 0.2,
  onVerticalExaggerationChange = null,
  colorRamp = 'terrain',
  selectedPoint = null,
  onSelectPoint = null,
  resetViewTrigger = 0,
  showCockpitHud = true,
}) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainMeshRef = useRef(null);
  const terrainMaterialRef = useRef(null);
  const sunLightRef = useRef(null);
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
  const [loadedMeshMeta, setLoadedMeshMeta] = useState(dsmData || defaultTerrainMesh);
  const loadedMeshMetaRef = useRef(loadedMeshMeta);
  loadedMeshMetaRef.current = loadedMeshMeta;

  const verticalExaggerationRef = useRef(verticalExaggeration);
  verticalExaggerationRef.current = verticalExaggeration;

  const effectiveFlightMode = flightMode || (cameraMode === 'orbit' ? 'orbit' : 'auto');
  const flightModeRef = useRef(effectiveFlightMode);
  flightModeRef.current = effectiveFlightMode;

  const cameraModeRef = useRef(cameraMode);
  cameraModeRef.current = cameraMode;

  const isTourPausedRef = useRef(isTourPaused);
  isTourPausedRef.current = isTourPaused;

  const tourSpeedRef = useRef(tourSpeed);
  tourSpeedRef.current = tourSpeed;

  const cruiseAltitudeRef = useRef(cruiseAltitude);
  cruiseAltitudeRef.current = cruiseAltitude;

  // Tactical Cockpit Solar Lighting State
  const [sunAzimuth, setSunAzimuth] = useState(135); // 0-360 deg
  const [sunElevation, setSunElevation] = useState(45); // 10-90 deg
  const [lodLevel, setLodLevel] = useState('lod0'); // 'lod0' | 'lod1' | 'lod2'
  const [hudDrawerOpen, setHudDrawerOpen] = useState(true);
  const [showCrosshair, setShowCrosshair] = useState(true);

  // Fly controls movement state
  const flyStateRef = useRef({
    moveForward: false,
    moveBackward: false,
    moveLeft: false,
    moveRight: false,
    moveUp: false,
    moveDown: false,
    isSprint: false,
  });

  // Flight path & camera steering variables
  const flightTimeRef = useRef(0);
  const lookTargetRef = useRef(new THREE.Vector3(0, 15, 0));
  const isPointerDownRef = useRef(false);
  const lastPointerPosRef = useRef({ x: 0, y: 0 });
  const pitchRef = useRef(-0.16); // ~9° down-tilt towards terrain
  const yawRef = useRef(0);

  // Real-time Flight Telemetry State for HUD
  const [telemetry, setTelemetry] = useState({
    heading: 45,
    cardinal: 'NE',
    altAgl: 28.5,
    datumMsl: 39.1,
    groundElev: 10.6,
    speedKmH: 52,
    x: 0,
    z: 0,
    fps: 60,
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

  // Resolve optical texture with robust fallbacks
  const resolveOpticalTextureUrl = useCallback((meta) => {
    if (userTextureUrl) return userTextureUrl;
    if (meta?.texture_url) {
      if (meta.texture_url.startsWith('blob:') || meta.texture_url.startsWith('data:')) {
        return meta.texture_url;
      }
      if (meta.texture_url.startsWith('/api/') || meta.texture_url.includes('localhost:8000')) {
        const apiBase = getApiBase();
        if (apiBase) {
          if (typeof window !== 'undefined' && window.location.protocol === 'https:' && apiBase.startsWith('http://127.0.0.1')) {
            return sampleOpticalImg;
          }
          const cleanPath = meta.texture_url.replace(/^.*localhost:\d+/, '');
          return `${apiBase}${cleanPath}`;
        }
        return sampleOpticalImg;
      }
      return meta.texture_url;
    }
    return sampleOpticalImg;
  }, [userTextureUrl]);

  // Fast terrain height sampling function for flight navigation and collision safety
  const sampleTerrainHeight = useCallback((worldX, worldZ) => {
    const meta = loadedMeshMetaRef.current;
    if (!meta || !meta.heights || !meta.heights.length) return 0;
    const planeWidth = 200;
    const planeHeight = 200;
    const cols = meta.cols || 128;
    const rows = meta.rows || 128;

    const u = (worldX / planeWidth) + 0.5;
    const v = (worldZ / planeHeight) + 0.5;
    if (u < 0 || u > 1 || v < 0 || v > 1) return 0;

    const c = Math.max(0, Math.min(cols - 1, Math.round(u * (cols - 1))));
    const r = Math.max(0, Math.min(rows - 1, Math.round(v * (rows - 1))));
    const val = meta.heights[r * cols + c];
    if (val === undefined || val === null) return 0;

    const baseOffset = terrainMeshRef.current?.userData?.baseOffset || 0;
    const reliefMultiplier = terrainMeshRef.current?.userData?.reliefMultiplier || 1.0;
    return Math.max(0, (val - baseOffset) * reliefMultiplier);
  }, []);

  // Update dynamic sun light position based on azimuth and elevation
  useEffect(() => {
    if (!sunLightRef.current) return;
    const azRad = (sunAzimuth * Math.PI) / 180;
    const elRad = (sunElevation * Math.PI) / 180;
    const dist = 320;
    const sx = dist * Math.cos(elRad) * Math.sin(azRad);
    const sy = dist * Math.sin(elRad);
    const sz = dist * Math.cos(elRad) * Math.cos(azRad);
    sunLightRef.current.position.set(sx, sy, sz);
  }, [sunAzimuth, sunElevation]);

  // Build or update terrain mesh geometry and textures
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
    if (textureMode === 'slope') activeMap = slopeTexture;
    else if (textureMode === 'colormap') activeMap = colorTexture;
    else if (textureMode === 'rgb' && opticalTextureRef.current) activeMap = opticalTextureRef.current;

    let terrainMaterial = terrainMaterialRef.current;
    if (!terrainMaterial) {
      terrainMaterial = new THREE.MeshStandardMaterial({
        map: textureMode === 'wireframe' ? null : activeMap,
        wireframe: textureMode === 'wireframe',
        roughness: 0.72,
        metalness: 0.08,
        side: THREE.DoubleSide,
      });
      terrainMaterialRef.current = terrainMaterial;
    } else {
      terrainMaterial.map = textureMode === 'wireframe' ? null : activeMap;
      terrainMaterial.wireframe = textureMode === 'wireframe';
      terrainMaterial.side = THREE.DoubleSide;
      terrainMaterial.needsUpdate = true;
    }

    textureLoader.load(
      opticalUrl,
      (loadedTex) => {
        loadedTex.wrapS = THREE.ClampToEdgeWrapping;
        loadedTex.wrapT = THREE.ClampToEdgeWrapping;
        loadedTex.needsUpdate = true;
        opticalTextureRef.current = loadedTex;
        if (textureMode === 'rgb' && terrainMaterialRef.current) {
          terrainMaterialRef.current.map = loadedTex;
          terrainMaterialRef.current.needsUpdate = true;
        }
      },
      undefined,
      () => {
        if (opticalUrl !== sampleOpticalImg) {
          textureLoader.load(sampleOpticalImg, (fbTex) => {
            opticalTextureRef.current = fbTex;
            if (textureMode === 'rgb' && terrainMaterialRef.current) {
              terrainMaterialRef.current.map = fbTex;
              terrainMaterialRef.current.needsUpdate = true;
            }
          });
        }
      }
    );

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
  }, [colorRamp, textureMode, resolveOpticalTextureUrl]);

  // 1. Scene & WebGLRenderer Setup
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 520;

    // A. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060c18);
    scene.fog = new THREE.FogExp2(0x060c18, 0.0018);
    sceneRef.current = scene;

    // B. Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.5, 3500);
    camera.position.set(0, 36, 92);
    camera.lookAt(0, 12, 0);
    cameraRef.current = camera;

    // C. WebGL Renderer
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
    controls.enabled = effectiveFlightMode === 'orbit';
    controlsRef.current = controls;

    // E. Lighting (with Dynamic Solar Directional Light)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff5ea, 1.6);
    sunLight.position.set(130, 230, 95);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 700;
    sunLight.shadow.camera.left = -120;
    sunLight.shadow.camera.right = 120;
    sunLight.shadow.camera.top = 120;
    sunLight.shadow.camera.bottom = -120;
    scene.add(sunLight);
    sunLightRef.current = sunLight;

    const skyFill = new THREE.HemisphereLight(0x38bdf8, 0x060c18, 0.6);
    scene.add(skyFill);

    // F. Base Metric Grid
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

    // H. Build initial mesh immediately
    if (loadedMeshMetaRef.current && loadedMeshMetaRef.current.heights) {
      buildOrUpdateMesh(scene, loadedMeshMetaRef.current);
    }

    // I. 60 FPS Animation & Flight Engine Loop
    let animId;
    let lastTime = performance.now();
    let lastTelemetryUpdate = 0;
    let frameCount = 0;
    let fpsTimer = performance.now();
    let currentFps = 60;

    const animate = (currentTime) => {
      animId = requestAnimationFrame(animate);
      const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
      lastTime = currentTime;

      // Track FPS
      frameCount++;
      if (currentTime - fpsTimer >= 1000) {
        currentFps = Math.round((frameCount * 1000) / (currentTime - fpsTimer));
        frameCount = 0;
        fpsTimer = currentTime;
      }

      // Pulse pin marker
      if (markerGroup.visible && ringMeshRef.current) {
        const pulse = 1.0 + 0.15 * Math.sin(currentTime * 0.006);
        ringMeshRef.current.scale.set(pulse, 1, pulse);
      }

      const currentFlight = flightModeRef.current;
      const currentExag = verticalExaggerationRef.current || 0.2;

      if (currentFlight === 'orbit') {
        controls.enabled = true;
        controls.update();
      } else if (currentFlight === 'topdown') {
        controls.enabled = true;
        controls.update();
      } else {
        controls.enabled = false;

        if (currentFlight === 'auto') {
          // --- AUTONOMOUS RECONNAISSANCE FLYTHROUGH TOUR ---
          if (!isTourPausedRef.current) {
            flightTimeRef.current += delta * tourSpeedRef.current;
          }
          const t = flightTimeRef.current * 0.11;

          // Smooth figure-8 / panoramic sweeping reconnaissance path
          const radiusX = 66.0;
          const radiusZ = 60.0;
          const pathX = radiusX * Math.sin(t);
          const pathZ = radiusZ * Math.sin(2 * t) * 0.65;

          // Look-ahead tangent
          const dt = 0.07;
          const aheadT = t + dt;
          const aheadX = radiusX * Math.sin(aheadT);
          const aheadZ = radiusZ * Math.sin(2 * aheadT) * 0.65;

          // Dynamic AGL flight clearance
          const groundH = sampleTerrainHeight(pathX, pathZ);
          const groundY = groundH * currentExag;
          const targetCamY = groundY + cruiseAltitudeRef.current + 3.0 * Math.sin(t * 1.6);

          const lookH = sampleTerrainHeight(aheadX, aheadZ);
          const targetLookY = (lookH * currentExag) + Math.max(3.0, cruiseAltitudeRef.current * 0.35);

          // Smooth camera glide
          camera.position.x += (pathX - camera.position.x) * 0.07;
          camera.position.y += (targetCamY - camera.position.y) * 0.07;
          camera.position.z += (pathZ - camera.position.z) * 0.07;

          lookTargetRef.current.x += (aheadX - lookTargetRef.current.x) * 0.07;
          lookTargetRef.current.y += (targetLookY - lookTargetRef.current.y) * 0.07;
          lookTargetRef.current.z += (aheadZ - lookTargetRef.current.z) * 0.07;

          camera.lookAt(lookTargetRef.current);
        } else {
          // --- MANUAL FIRST-PERSON DRONE FLIGHT SIMULATOR ---
          const fly = flyStateRef.current;
          const isSprint = fly.isSprint;
          const baseSpeed = isSprint ? 68.0 : 28.0;
          const moveDist = baseSpeed * delta;

          // Direction vector from mouse-look pitch & yaw
          const forward = new THREE.Vector3(
            Math.sin(yawRef.current) * Math.cos(pitchRef.current),
            Math.sin(pitchRef.current),
            -Math.cos(yawRef.current) * Math.cos(pitchRef.current)
          ).normalize();

          const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();

          if (fly.moveForward) camera.position.addScaledVector(forward, moveDist);
          if (fly.moveBackward) camera.position.addScaledVector(forward, -moveDist);
          if (fly.moveLeft) camera.position.addScaledVector(right, -moveDist);
          if (fly.moveRight) camera.position.addScaledVector(right, moveDist);
          if (fly.moveUp) camera.position.y += moveDist;
          if (fly.moveDown) camera.position.y -= moveDist;

          // Ground collision clamp: camera height >= ground_height + 2.5m buffer
          const groundH = sampleTerrainHeight(camera.position.x, camera.position.z);
          const minCamY = (groundH * currentExag) + 2.5;
          if (camera.position.y < minCamY) {
            camera.position.y = minCamY;
          }

          camera.lookAt(camera.position.clone().add(forward));
        }
      }

      // Throttle telemetry HUD updates to ~15 Hz for peak UI performance
      if (currentTime - lastTelemetryUpdate > 66) {
        lastTelemetryUpdate = currentTime;
        const dir = new THREE.Vector3();
        camera.getWorldDirection(dir);
        const headingDeg = Math.round(((Math.atan2(dir.x, -dir.z) * 180 / Math.PI) + 360) % 360);
        const cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
        const cardIdx = Math.round(headingDeg / 22.5) % 16;
        const cardinal = cardinals[cardIdx];

        const currentGroundH = sampleTerrainHeight(camera.position.x, camera.position.z);
        const groundY = currentGroundH * currentExag;
        const altAgl = Math.max(0.5, camera.position.y - groundY);
        const baseOffset = terrainMeshRef.current?.userData?.baseOffset || 0;
        const datumMsl = baseOffset + (camera.position.y / Math.max(0.01, currentExag));

        let speedKmH = 0;
        if (currentFlight === 'auto') {
          speedKmH = isTourPausedRef.current ? 0 : Math.round(52 * tourSpeedRef.current);
        } else if (currentFlight === 'manual') {
          const isMoving = flyStateRef.current.moveForward || flyStateRef.current.moveBackward || flyStateRef.current.moveLeft || flyStateRef.current.moveRight || flyStateRef.current.moveUp || flyStateRef.current.moveDown;
          speedKmH = isMoving ? (flyStateRef.current.isSprint ? 115 : 46) : 0;
        }

        setTelemetry({
          heading: headingDeg,
          cardinal,
          altAgl: Number(altAgl.toFixed(1)),
          datumMsl: Number(datumMsl.toFixed(1)),
          groundElev: Number((baseOffset + currentGroundH).toFixed(1)),
          speedKmH,
          x: Number(camera.position.x.toFixed(1)),
          z: Number(camera.position.z.toFixed(1)),
          fps: currentFps,
        });
      }

      renderer.render(scene, camera);
    };
    animate(performance.now());

    // J. Pointer Controls: Mouse-Look in Manual Fly + Point Measurement on Click
    const domElement = renderer.domElement;

    const handlePointerDown = (e) => {
      mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
      lastPointerPosRef.current = { x: e.clientX, y: e.clientY };
      isPointerDownRef.current = true;
    };

    const handlePointerMove = (e) => {
      if (!isPointerDownRef.current) return;
      if (flightModeRef.current === 'manual') {
        const dx = e.clientX - lastPointerPosRef.current.x;
        const dy = e.clientY - lastPointerPosRef.current.y;
        lastPointerPosRef.current = { x: e.clientX, y: e.clientY };
        yawRef.current -= dx * 0.0035;
        pitchRef.current -= dy * 0.0035;
        pitchRef.current = Math.max(-1.42, Math.min(1.42, pitchRef.current));
      }
    };

    const handlePointerUp = (e) => {
      isPointerDownRef.current = false;
      const dx = Math.abs(e.clientX - mouseDownPosRef.current.x);
      const dy = Math.abs(e.clientY - mouseDownPosRef.current.y);
      if (dx > 5 || dy > 5) return; // Dragged for steering/orbiting, not a point click

      // Raycast to sample point elevation
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
        const currentExag = meshUserData.verticalExaggeration || 0.2;
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
    domElement.addEventListener('pointermove', handlePointerMove);
    domElement.addEventListener('pointerup', handlePointerUp);

    // K. Keyboard controls for Fly mode
    const handleKeyDown = (e) => {
      const fly = flyStateRef.current;
      switch (e.code) {
        case 'KeyW': fly.moveForward = true; break;
        case 'KeyS': fly.moveBackward = true; break;
        case 'KeyA': fly.moveLeft = true; break;
        case 'KeyD': fly.moveRight = true; break;
        case 'KeyQ': fly.moveDown = true; break;
        case 'KeyE': fly.moveUp = true; break;
        case 'ShiftLeft':
        case 'ShiftRight': fly.isSprint = true; break;
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
        case 'ShiftLeft':
        case 'ShiftRight': fly.isSprint = false; break;
        default: break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    // L. Resize Observer
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
      domElement.removeEventListener('pointermove', handlePointerMove);
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
  }, [buildOrUpdateMesh, sampleTerrainHeight]);

  // 2. Build or Rebuild Mesh Geometry when loadedMeshMeta changes
  useEffect(() => {
    const scene = sceneRef.current;
    if (scene && loadedMeshMeta?.heights) {
      buildOrUpdateMesh(scene, loadedMeshMeta);
    }
  }, [loadedMeshMeta, buildOrUpdateMesh]);

  // 3. Ultra-fast IN-PLACE Vertical Exaggeration update
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

    const marker = markerGroupRef.current;
    if (marker && marker.visible && marker.userData?.relH !== undefined) {
      marker.position.y = marker.userData.relH * verticalExaggeration;
    }
  }, [verticalExaggeration, loadedMeshMeta]);

  // 4. IN-PLACE Texture Mode Switching
  useEffect(() => {
    const mat = terrainMaterialRef.current;
    if (!mat) return;

    if (textureMode === 'wireframe') {
      mat.wireframe = true;
      mat.map = null;
    } else if (textureMode === 'colormap') {
      mat.wireframe = false;
      mat.map = colorTextureRef.current;
    } else if (textureMode === 'slope') {
      mat.wireframe = false;
      mat.map = slopeTextureRef.current;
    } else if (textureMode === 'rgb') {
      mat.wireframe = false;
      mat.map = opticalTextureRef.current || colorTextureRef.current;
    }
    mat.needsUpdate = true;
  }, [textureMode]);

  // 5. Hide 3D marker when measurement cleared
  useEffect(() => {
    if (markerGroupRef.current && !selectedPoint) {
      markerGroupRef.current.visible = false;
    }
  }, [selectedPoint]);

  // 6. Camera / Drone Reset Trigger
  useEffect(() => {
    if (cameraRef.current && resetViewTrigger > 0) {
      if (effectiveFlightMode === 'orbit') {
        cameraRef.current.position.set(0, 90, 160);
        if (controlsRef.current) {
          controlsRef.current.target.set(0, 0, 0);
          controlsRef.current.update();
        }
      } else if (effectiveFlightMode === 'topdown') {
        cameraRef.current.position.set(0, 200, 0.01);
        if (controlsRef.current) {
          controlsRef.current.target.set(0, 0, 0);
          controlsRef.current.update();
        }
      } else {
        flightTimeRef.current = 0;
        yawRef.current = 0;
        pitchRef.current = -0.16;
        cameraRef.current.position.set(0, 36, 92);
        lookTargetRef.current.set(0, 12, 0);
        cameraRef.current.lookAt(lookTargetRef.current);
      }
    }
  }, [resetViewTrigger, effectiveFlightMode]);

  // Handle switching to manual flight
  useEffect(() => {
    if (effectiveFlightMode === 'manual' && cameraRef.current) {
      const dir = new THREE.Vector3();
      cameraRef.current.getWorldDirection(dir);
      yawRef.current = Math.atan2(dir.x, -dir.z);
      pitchRef.current = Math.asin(Math.max(-0.95, Math.min(0.95, dir.y)));
    } else if (effectiveFlightMode === 'topdown' && cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, 210, 0.01);
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    }
  }, [effectiveFlightMode]);

  const handleTextureChange = (mode) => {
    if (onTextureModeChange) onTextureModeChange(mode);
  };

  return (
    <div className="terrain-viewer-container" style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={mountRef} className="terrain-webgl-canvas" style={{ width: '100%', height: '100%', overflow: 'hidden' }} />

      {/* ISRO Tactical Mission Banner */}
      <div className="cockpit-mission-banner">
        <Radio size={12} className="text-emerald-400 animate-pulse" />
        <span className="text-white font-bold tracking-wider">ISRO / SAC TACTICAL COCKPIT</span>
        <span className="text-slate-500">|</span>
        <span className="text-cyan-300">0.33m GSD</span>
        <span className="text-slate-500">|</span>
        <span className="text-amber-300 font-semibold">{telemetry.fps} FPS</span>
      </div>

      {/* Cockpit Reticle / Flight Crosshairs */}
      {showCrosshair && (
        <div className="cockpit-crosshair-center">
          <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="60" r="30" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
            <circle cx="60" cy="60" r="2.5" fill="#ff9944" />
            {/* Horizon pitch marks */}
            <line x1="20" y1="60" x2="45" y2="60" stroke="#38bdf8" strokeWidth="1.5" />
            <line x1="75" y1="60" x2="100" y2="60" stroke="#38bdf8" strokeWidth="1.5" />
            <line x1="60" y1="20" x2="60" y2="35" stroke="#38bdf8" strokeWidth="1.5" />
            <line x1="60" y1="85" x2="60" y2="100" stroke="#38bdf8" strokeWidth="1.5" />
          </svg>
        </div>
      )}

      {/* TOP-RIGHT: Tactical Cockpit Controls HUD Drawer */}
      {showCockpitHud && (
        <div className="tactical-cockpit-drawer">
          <div className="cockpit-drawer-header">
            <span className="cockpit-drawer-title">
              <Sliders size={13} className="text-[#ff9944]" />
              <span>COCKPIT CONTROLS HUD</span>
            </span>
            <div className="flex items-center gap-1.5">
              <span className="px-1.5 py-0.5 rounded font-mono text-[9px] font-bold bg-emerald-950/90 text-emerald-400 border border-emerald-700/60">
                {telemetry.fps} FPS
              </span>
              <button
                type="button"
                onClick={() => setHudDrawerOpen(!hudDrawerOpen)}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800/60 transition cursor-pointer"
                title={hudDrawerOpen ? 'Collapse HUD Drawer' : 'Expand HUD Drawer'}
              >
                {hudDrawerOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>
          </div>

          {hudDrawerOpen && (
            <>
              {/* Telemetry Avionics Grid */}
              <div className="cockpit-hud-section">
                <div className="cockpit-section-label">
                  <span>FLIGHT AVIONICS</span>
                  <span className="text-slate-300 font-mono text-[9.5px]">
                    {telemetry.heading.toString().padStart(3, '0')}° {telemetry.cardinal}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800">
                    <span className="text-[9px] text-slate-400 block">ALT (AGL)</span>
                    <strong className="text-emerald-400 text-xs">{telemetry.altAgl} m</strong>
                  </div>
                  <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800">
                    <span className="text-[9px] text-slate-400 block">AIRSPEED</span>
                    <strong className="text-cyan-300 text-xs">{telemetry.speedKmH} km/h</strong>
                  </div>
                  <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800">
                    <span className="text-[9px] text-slate-400 block">DATUM MSL</span>
                    <strong className="text-slate-200 text-xs">{telemetry.datumMsl} m</strong>
                  </div>
                  <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800">
                    <span className="text-[9px] text-slate-400 block">COORDS</span>
                    <strong className="text-slate-300 text-[10px] truncate block">
                      {telemetry.x > 0 ? '+' : ''}{telemetry.x}, {telemetry.z > 0 ? '+' : ''}{telemetry.z}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Solar Lighting Simulation */}
              <div className="cockpit-hud-section">
                <div className="cockpit-section-label">
                  <span className="flex items-center gap-1.5">
                    <Sun size={11} className="text-amber-400" />
                    <span>SOLAR ILLUMINATION</span>
                  </span>
                </div>
                <div className="sun-slider-wrap">
                  <div className="sun-slider-header">
                    <span>Sun Azimuth</span>
                    <span className="font-mono text-amber-400">{sunAzimuth}°</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="360"
                    step="5"
                    value={sunAzimuth}
                    onChange={(e) => setSunAzimuth(Number(e.target.value))}
                    className="sun-slider-input"
                  />
                </div>
                <div className="sun-slider-wrap mt-1">
                  <div className="sun-slider-header">
                    <span>Sun Elevation</span>
                    <span className="font-mono text-amber-400">{sunElevation}°</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="90"
                    step="5"
                    value={sunElevation}
                    onChange={(e) => setSunElevation(Number(e.target.value))}
                    className="sun-slider-input"
                  />
                </div>
              </div>

              {/* Surface Diagnostics: Slope, Wireframe, Reticle */}
              <div className="cockpit-hud-section">
                <div className="cockpit-section-label">
                  <span>SURFACE DIAGNOSTICS</span>
                </div>
                <div className="cockpit-btn-grid">
                  <button
                    type="button"
                    className={`cockpit-toggle-btn ${textureMode === 'slope' ? 'active' : ''}`}
                    onClick={() => handleTextureChange(textureMode === 'slope' ? 'rgb' : 'slope')}
                  >
                    <span>Slope Analysis</span>
                  </button>
                  <button
                    type="button"
                    className={`cockpit-toggle-btn ${textureMode === 'wireframe' ? 'active' : ''}`}
                    onClick={() => handleTextureChange(textureMode === 'wireframe' ? 'rgb' : 'wireframe')}
                  >
                    <span>Wireframe Grid</span>
                  </button>
                  <button
                    type="button"
                    className={`cockpit-toggle-btn ${textureMode === 'colormap' ? 'active' : ''}`}
                    onClick={() => handleTextureChange(textureMode === 'colormap' ? 'rgb' : 'colormap')}
                  >
                    <span>Colormap</span>
                  </button>
                  <button
                    type="button"
                    className={`cockpit-toggle-btn ${showCrosshair ? 'active' : ''}`}
                    onClick={() => setShowCrosshair(!showCrosshair)}
                  >
                    <Crosshair size={11} />
                    <span>HUD Reticle</span>
                  </button>
                </div>
              </div>

              {/* Vertical Relief Slider */}
              <div className="cockpit-hud-section">
                <div className="cockpit-section-label">
                  <span>VERTICAL RELIEF</span>
                  <span className="font-mono text-cyan-300 font-bold">{verticalExaggeration.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.1"
                  value={verticalExaggeration}
                  onChange={(e) => onVerticalExaggerationChange && onVerticalExaggerationChange(parseFloat(e.target.value))}
                  className="sun-slider-input"
                />
              </div>
            </>
          )}
        </div>
      )}

      {/* BOTTOM-BAR: Flight Controls & Mode Specific Controls */}
      <div className="flight-deck-bar">
        {effectiveFlightMode === 'auto' && (
          <div className="flight-controls-pill-group">
            <button
              className="flight-deck-btn"
              onClick={onToggleTourPause}
              title={isTourPaused ? 'Resume Autonomous Flythrough Tour' : 'Pause Flythrough Tour to Hover in Place'}
            >
              {isTourPaused ? <Play size={12} className="text-emerald-400" /> : <Pause size={12} className="text-amber-400" />}
              <span>{isTourPaused ? 'Resume Tour' : 'Hover / Pause'}</span>
            </button>

            <button
              className={`flight-deck-btn ${tourSpeed > 1 ? 'active' : ''}`}
              onClick={() => onChangeTourSpeed && onChangeTourSpeed(tourSpeed > 1 ? 1.0 : 1.75)}
              title="Toggle flythrough sweep speed"
            >
              <FastForward size={12} />
              <span>{tourSpeed > 1 ? '1.75x Fast' : '1.0x Cruise'}</span>
            </button>

            <div className="hidden sm:flex items-center gap-1 ml-1 border-l border-slate-700/60 pl-2">
              <span className="text-[10px] text-slate-400 font-medium">Altitude:</span>
              <button
                className={`flight-deck-btn text-[10.5px] px-2 py-0.5 ${cruiseAltitude < 22 ? 'active' : ''}`}
                onClick={() => onChangeAltitude && onChangeAltitude(18)}
                title="Low altitude proximity flythrough (18m AGL)"
              >
                18m
              </button>
              <button
                className={`flight-deck-btn text-[10.5px] px-2 py-0.5 ${cruiseAltitude >= 22 && cruiseAltitude <= 38 ? 'active' : ''}`}
                onClick={() => onChangeAltitude && onChangeAltitude(28)}
                title="Standard reconnaissance altitude (28m AGL)"
              >
                28m
              </button>
              <button
                className={`flight-deck-btn text-[10.5px] px-2 py-0.5 ${cruiseAltitude > 38 ? 'active' : ''}`}
                onClick={() => onChangeAltitude && onChangeAltitude(55)}
                title="High altitude tactical survey (55m AGL)"
              >
                55m
              </button>
            </div>
          </div>
        )}

        {effectiveFlightMode === 'manual' && (
          <div className="flight-hint-pill font-mono">
            <span>🖱️ Drag to Steer | WASD Thrust | Q/E Alt | Shift Boost</span>
          </div>
        )}

        {effectiveFlightMode === 'orbit' && (
          <div className="flight-hint-pill">
            <span>🖱️ Left-drag Rotate | Right-drag Pan | Scroll Zoom</span>
          </div>
        )}

        {effectiveFlightMode === 'topdown' && (
          <div className="flight-hint-pill font-mono">
            <span>🗺️ Top-Down Nadir 2D View · Drag to Pan · Scroll to Zoom</span>
          </div>
        )}

        {/* Quick Texture Mode Pills */}
        <div className="viewport-mode-pills pointer-events-auto">
          <button
            className={`pill-btn ${textureMode === 'rgb' ? 'active' : ''}`}
            onClick={() => handleTextureChange('rgb')}
            title="Draped True-Color Optical Texture"
          >
            RGB Optical
          </button>
          <button
            className={`pill-btn ${textureMode === 'colormap' ? 'active' : ''}`}
            onClick={() => handleTextureChange('colormap')}
            title="Procedural Hypsometric Elevation Colormap"
          >
            Colormap
          </button>
          <button
            className={`pill-btn ${textureMode === 'slope' ? 'active' : ''}`}
            onClick={() => handleTextureChange('slope')}
            title="Surface Slope Gradient Analysis"
          >
            Slope
          </button>
          <button
            className={`pill-btn ${textureMode === 'wireframe' ? 'active' : ''}`}
            onClick={() => handleTextureChange('wireframe')}
            title="Geometric Triangulation Mesh Wireframe"
          >
            Wireframe
          </button>
        </div>
      </div>
    </div>
  );
}
