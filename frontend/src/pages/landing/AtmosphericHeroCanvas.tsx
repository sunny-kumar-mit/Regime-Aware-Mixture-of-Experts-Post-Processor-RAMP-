import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

// Accurate geographical anchor coordinates for the Indian subcontinent (mapped to [-6, 6] 3D coordinates)
// Lon: 68E to 97E -> X: -5.0 to 5.0 | Lat: 8N to 36N -> Y: -5.5 to 5.5
const INDIA_GEO_POINTS: [number, number][] = [
  // Northern frontiers (Kashmir, Ladakh, Himachal, Uttarakhand)
  [-1.2, 5.2],
  [-0.4, 5.5],
  [0.6, 5.2],
  [1.4, 4.4],
  [2.4, 4.0],
  // Himalayan Arc / Nepal Border / Sikkim / Bhutan
  [3.2, 3.8],
  [3.8, 3.6],
  [4.6, 3.7],
  // Northeast (Assam, Arunachal, Nagaland, Meghalaya)
  [5.4, 3.8],
  [5.6, 3.1],
  [5.0, 2.4],
  [4.4, 2.2],
  [3.8, 2.0],
  // Bengal Delta / Odisha Coast
  [3.2, 1.4],
  [2.6, 0.4],
  [2.0, -0.6],
  [1.5, -1.8],
  // Andhra Coast / Coromandel / Tamil Nadu
  [1.0, -3.2],
  [0.6, -4.4],
  [0.2, -5.2],
  // Kanyakumari (Southern Tip)
  [-0.2, -5.4],
  [-0.6, -4.8],
  // Malabar Coast (Kerala)
  [-1.2, -3.8],
  [-1.6, -2.4],
  // Konkan / Goa / Maharashtra Coast
  [-2.2, -0.8],
  [-2.8, 0.4],
  // Gujarat / Kathiawar Peninsula / Rann of Kutch
  [-3.8, 0.8],
  [-4.6, 1.4],
  [-4.2, 2.2],
  [-3.6, 2.6],
  // Rajasthan / Punjab / Northwest Border
  [-3.0, 3.6],
  [-2.2, 4.4],
  [-1.2, 5.2], // close loop
];

// Operational NCMRWF NWP forecast stations
const OPERATIONAL_FORECAST_STATIONS: { name: string; x: number; y: number }[] = [
  { name: 'Western Ghats / Mumbai', x: -2.6, y: 0.2 },
  { name: 'Northern Plains / Delhi', x: -1.0, y: 3.4 },
  { name: 'Bengal Delta / Kolkata', x: 3.2, y: 1.5 },
  { name: 'Southern Peninsular / Chennai', x: 0.8, y: -3.4 },
  { name: 'Plateau / Bengaluru', x: -0.2, y: -3.2 },
  { name: 'Central Trough / Nagpur', x: 0.4, y: 0.8 },
  { name: 'Coastal SW / Kochi', x: -1.1, y: -4.4 },
  { name: 'Brahmaputra / Guwahati', x: 4.8, y: 2.8 },
];

export const AtmosphericHeroCanvas: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webGLSupported, setWebGLSupported] = useState<boolean>(true);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isMobile = window.innerWidth < 768;

    // Scene & Camera setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x070c18, 0.022);

    const camera = new THREE.PerspectiveCamera(
      42,
      container.clientWidth / container.clientHeight,
      0.1,
      120
    );
    // Tilted satellite perspective viewing India from south-southwest looking northeast
    camera.position.set(0, -9.5, 14.5);
    camera.lookAt(0, 0.5, 0);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: !isMobile,
        alpha: true,
        powerPreference: 'high-performance',
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.setClearColor(0x000000, 0);
      container.appendChild(renderer.domElement);
    } catch {
      setWebGLSupported(false);
      return;
    }

    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // =========================================================================
    // 1. ATMOSPHERIC ELEVATION & PRECIPITATION FIELD (Scalar Surface Z(x, y))
    // =========================================================================
    // A high-resolution curved 3D surface representing geopotential height & atmospheric waves
    const fieldWidth = 26;
    const fieldHeight = 26;
    const gridRes = isMobile ? 40 : 80;
    const surfaceGeometry = new THREE.PlaneGeometry(fieldWidth, fieldHeight, gridRes, gridRes);

    // Vertex colors for atmospheric temperature/precipitation intensity
    const posAttribute = surfaceGeometry.attributes.position;
    const count = posAttribute.count;
    const colors = new Float32Array(count * 3);

    // Store base vertices for procedural wave animation
    const basePositions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      basePositions[i * 3] = posAttribute.getX(i);
      basePositions[i * 3 + 1] = posAttribute.getY(i);
      basePositions[i * 3 + 2] = posAttribute.getZ(i);
    }

    surfaceGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Semi-translucent glowing atmospheric surface material
    const surfaceMaterial = new THREE.MeshBasicMaterial({
      vertexColors: true,
      wireframe: false,
      transparent: true,
      opacity: 0.65,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const surfaceMesh = new THREE.Mesh(surfaceGeometry, surfaceMaterial);
    surfaceMesh.position.z = -0.3;
    rootGroup.add(surfaceMesh);

    // Atmospheric Isobar Wireframe Overlay (Subtle scientific contour grid)
    const contourMaterial = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      wireframe: true,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    });
    const contourMesh = new THREE.Mesh(surfaceGeometry, contourMaterial);
    contourMesh.position.z = -0.28;
    rootGroup.add(contourMesh);

    // =========================================================================
    // 2. INDIA REGION SILHOUETTE (Subtle Geopolitical Land Mask)
    // =========================================================================
    const indiaPoints3D: THREE.Vector3[] = INDIA_GEO_POINTS.map(
      ([x, y]) => new THREE.Vector3(x, y, 0.05)
    );
    const indiaLineGeom = new THREE.BufferGeometry().setFromPoints(indiaPoints3D);
    const indiaLineMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.85,
      linewidth: 2,
    });
    const indiaOutline = new THREE.Line(indiaLineGeom, indiaLineMaterial);
    rootGroup.add(indiaOutline);

    // Glowing border vertices on India outline
    const indiaPointsGeom = new THREE.BufferGeometry().setFromPoints(indiaPoints3D);
    const indiaPointsMaterial = new THREE.PointsMaterial({
      color: 0x06b6d4,
      size: isMobile ? 0.12 : 0.16,
      transparent: true,
      opacity: 0.9,
    });
    const indiaNodes = new THREE.Points(indiaPointsGeom, indiaPointsMaterial);
    rootGroup.add(indiaNodes);

    // =========================================================================
    // 3. OPERATIONAL NWP FORECAST STATIONS (Pulsing Grid Nodes)
    // =========================================================================
    const stationPositions: number[] = [];
    OPERATIONAL_FORECAST_STATIONS.forEach((st) => {
      stationPositions.push(st.x, st.y, 0.2);
    });
    const stationGeom = new THREE.BufferGeometry();
    stationGeom.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(stationPositions, 3)
    );
    const stationMaterial = new THREE.PointsMaterial({
      color: 0x10b981,
      size: 0.35,
      transparent: true,
      opacity: 0.95,
    });
    const stationPoints = new THREE.Points(stationGeom, stationMaterial);
    rootGroup.add(stationPoints);

    // =========================================================================
    // 4. FLOWING MONSOON WIND STREAMLINES (Vector Atmospheric Dynamics)
    // =========================================================================
    // Particles flowing in southwesterly trajectories across Arabian Sea into the Gangetic Trough
    const windCount = isMobile ? 220 : 650;
    const windPositions = new Float32Array(windCount * 3);
    const windColors = new Float32Array(windCount * 3);
    const windVelocities: { x: number; y: number; z: number; speed: number; life: number }[] = [];

    for (let i = 0; i < windCount; i++) {
      // Initialize around Arabian Sea / Indian Ocean boundary
      const startX = -8 + Math.random() * 12;
      const startY = -7 + Math.random() * 12;
      const startZ = 0.4 + Math.random() * 1.5;

      windPositions[i * 3] = startX;
      windPositions[i * 3 + 1] = startY;
      windPositions[i * 3 + 2] = startZ;

      // Soft tropical wind blue/cyan color
      windColors[i * 3] = 0.22;
      windColors[i * 3 + 1] = 0.74;
      windColors[i * 3 + 2] = 0.98;

      windVelocities.push({
        x: 0.025 + Math.random() * 0.035, // Strong eastward push
        y: 0.035 + Math.random() * 0.045, // Strong northward push
        z: (Math.random() - 0.5) * 0.01,
        speed: 0.8 + Math.random() * 0.6,
        life: Math.random(),
      });
    }

    const windGeom = new THREE.BufferGeometry();
    windGeom.setAttribute('position', new THREE.BufferAttribute(windPositions, 3));
    windGeom.setAttribute('color', new THREE.BufferAttribute(windColors, 3));

    const windMaterial = new THREE.PointsMaterial({
      size: isMobile ? 0.12 : 0.16,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const windField = new THREE.Points(windGeom, windMaterial);
    rootGroup.add(windField);

    // =========================================================================
    // 5. ANIMATED PRECIPITATION RAINFALL PARTICLES (Vertical Rain Downpour)
    // =========================================================================
    const rainCount = isMobile ? 180 : 500;
    const rainPositions = new Float32Array(rainCount * 3);
    const rainSpeeds: number[] = [];

    for (let i = 0; i < rainCount; i++) {
      // Concentrated over Western Ghats & Central Monsoon Belt
      const rx = (Math.random() - 0.35) * 8;
      const ry = (Math.random() - 0.3) * 8;
      const rz = 0.8 + Math.random() * 3.5;

      rainPositions[i * 3] = rx;
      rainPositions[i * 3 + 1] = ry;
      rainPositions[i * 3 + 2] = rz;

      rainSpeeds.push(0.06 + Math.random() * 0.07);
    }

    const rainGeom = new THREE.BufferGeometry();
    rainGeom.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3));

    const rainMaterial = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.09,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const rainParticles = new THREE.Points(rainGeom, rainMaterial);
    rootGroup.add(rainParticles);

    // =========================================================================
    // 6. SYNOPTIC LOW-PRESSURE / MONSOON TROUGH INTENSITY VORTEX
    // =========================================================================
    // Glowing cyclonic halo marking localized extreme precipitation cluster
    const vortexRingGeom = new THREE.RingGeometry(0.8, 1.4, 32);
    const vortexRingMat = new THREE.MeshBasicMaterial({
      color: 0x7c3aed,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const vortexRing = new THREE.Mesh(vortexRingGeom, vortexRingMat);
    vortexRing.position.set(1.5, 0.4, 0.3); // Bay of Bengal depression entry path
    rootGroup.add(vortexRing);

    // Core extreme cell node (Amber warning highlight)
    const corePointGeom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(1.5, 0.4, 0.4)]);
    const corePointMat = new THREE.PointsMaterial({
      color: 0xf59e0b,
      size: 0.45,
      transparent: true,
      opacity: 0.9,
    });
    const corePoint = new THREE.Points(corePointGeom, corePointMat);
    rootGroup.add(corePoint);

    // =========================================================================
    // 7. INTERACTIVE DAMPED PARALLAX & SCROLL BEHAVIOR
    // =========================================================================
    let mouseX = 0;
    let mouseY = 0;
    let targetRotY = 0;
    let targetRotX = 0;
    let scrollYOffset = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const cx = (event.clientX - rect.left) / rect.width - 0.5;
      const cy = (event.clientY - rect.top) / rect.height - 0.5;
      mouseX = cx * 2;
      mouseY = -cy * 2;
    };

    const handleScroll = () => {
      scrollYOffset = window.scrollY;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });

    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // Visibility Observer to pause when scrolled out of view
    let isVisible = true;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible = entry.isIntersecting;
        });
      },
      { threshold: 0.05 }
    );
    observer.observe(container);

    // =========================================================================
    // 8. CONTINUOUS ATMOSPHERIC MODEL EVOLUTION LOOP
    // =========================================================================
    let animationFrameId: number;
    let lastTime = performance.now();
    const startTime = performance.now();

    const animate = (currentTime: number = performance.now()) => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isVisible || !renderer) return;

      const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
      lastTime = currentTime;
      const elapsedTime = (currentTime - startTime) / 1000;

      if (!prefersReducedMotion) {
        // Damped smooth camera parallax
        targetRotY += (mouseX * 0.12 - targetRotY) * 0.04;
        targetRotX += (-mouseY * 0.08 - targetRotX) * 0.04;

        // Subtle scroll reaction: gentle tilt and field deepening as user scrolls
        const scrollProgress = Math.min(scrollYOffset / 800, 1.0);
        rootGroup.rotation.y = targetRotY + Math.sin(elapsedTime * 0.25) * 0.02;
        rootGroup.rotation.x = targetRotX - scrollProgress * 0.15;
        rootGroup.position.z = -scrollProgress * 1.5;

        // ---------------------------------------------------------------------
        // A. Evolve 3D Atmospheric Surface Z(x, y) & Vertex Color Ramp
        // ---------------------------------------------------------------------
        const posArr = surfaceGeometry.attributes.position.array as Float32Array;
        const colArr = surfaceGeometry.attributes.color.array as Float32Array;

        // Synoptic Weather Regime Cycle (18s period)
        // 0-7s: Active Monsoon | 7-14s: Monsoon Low-Pressure Vortex | 14-18s: Calibrated Post-Processed Field
        const regimePhase = (elapsedTime % 18) / 18;
        const isDepressionActive = regimePhase > 0.35 && regimePhase < 0.75;
        const vortexIntensity = isDepressionActive ? 1.4 : 0.6;

        // Vortex moves west-northwest into Odisha/Chhattisgarh
        const vortexX = 2.0 - Math.sin(elapsedTime * 0.35) * 1.5;
        const vortexY = 0.5 + Math.cos(elapsedTime * 0.3) * 0.8;

        vortexRing.position.set(vortexX, vortexY, 0.35);
        corePoint.position.set(vortexX, vortexY, 0.45);
        vortexRing.rotation.z += 0.015;

        for (let i = 0; i < count; i++) {
          const idx = i * 3;
          const bx = basePositions[idx];
          const by = basePositions[idx + 1];

          // Atmospheric Rossby waves + monsoon trough deflection
          const troughWave = Math.sin(bx * 0.4 + by * 0.3 - elapsedTime * 0.8) * 0.45;
          const highFrequencyTurbulence = Math.cos(bx * 0.8 - by * 0.6 + elapsedTime * 1.2) * 0.18;

          // Localized cyclonic depression vortex depression
          const distToVortex = Math.sqrt((bx - vortexX) ** 2 + (by - vortexY) ** 2);
          const vortexDip = -Math.exp(-(distToVortex ** 2) / 4.5) * (1.2 * vortexIntensity);

          // Western Ghats orographic barrier uplift
          const isGhats = bx > -2.8 && bx < -1.0 && by > -4.5 && by < 0.5;
          const orographicUplift = isGhats ? 0.35 : 0;

          const totalZ = troughWave + highFrequencyTurbulence + vortexDip + orographicUplift;
          posArr[idx + 2] = totalZ;

          // Dynamic Color Mapping based on atmospheric moisture & convective rainfall:
          // Navy baseline -> Cyan moisture -> Violet intense convection -> Amber peak risk
          if (distToVortex < 1.2 && isDepressionActive) {
            // Extreme convective core
            colArr[idx] = 0.95; // R
            colArr[idx + 1] = 0.45; // G
            colArr[idx + 2] = 0.15; // B (Amber-orange core)
          } else if (distToVortex < 2.8) {
            // Heavy rainfall envelope (Violet/Magenta)
            colArr[idx] = 0.48;
            colArr[idx + 1] = 0.18;
            colArr[idx + 2] = 0.88;
          } else if (isGhats || totalZ > 0.2) {
            // Orographic & active monsoon stream (Cyan/Sky blue)
            colArr[idx] = 0.06;
            colArr[idx + 1] = 0.65;
            colArr[idx + 2] = 0.92;
          } else {
            // Ambient calm atmosphere (Deep Navy)
            colArr[idx] = 0.04;
            colArr[idx + 1] = 0.09;
            colArr[idx + 2] = 0.18;
          }
        }
        surfaceGeometry.attributes.position.needsUpdate = true;
        surfaceGeometry.attributes.color.needsUpdate = true;

        // ---------------------------------------------------------------------
        // B. Animate Monsoon Wind Streamlines
        // ---------------------------------------------------------------------
        const windPosArr = windGeom.attributes.position.array as Float32Array;
        for (let i = 0; i < windCount; i++) {
          const idx = i * 3;
          const vel = windVelocities[i];

          // Vector curvature towards cyclonic center
          const wx = windPosArr[idx];

          // Southwesterly wind field bending cyclonically towards Gangetic Trough
          windPosArr[idx] += vel.x * (delta * 60) * vel.speed;
          windPosArr[idx + 1] += (vel.y + (wx > 0 ? 0.015 : 0.005)) * (delta * 60) * vel.speed;
          windPosArr[idx + 2] += vel.z * (delta * 60);

          // Recycle wind particle once it traverses past northern boundary
          if (windPosArr[idx] > 8 || windPosArr[idx + 1] > 7) {
            windPosArr[idx] = -8 + Math.random() * 4;
            windPosArr[idx + 1] = -7 + Math.random() * 4;
            windPosArr[idx + 2] = 0.4 + Math.random() * 1.5;
          }
        }
        windGeom.attributes.position.needsUpdate = true;

        // ---------------------------------------------------------------------
        // C. Animate Rainfall Droplets
        // ---------------------------------------------------------------------
        const rainPosArr = rainGeom.attributes.position.array as Float32Array;
        for (let i = 0; i < rainCount; i++) {
          const idx = i * 3;
          rainPosArr[idx + 2] -= rainSpeeds[i] * (delta * 60);

          // Reset droplet once it impacts surface
          if (rainPosArr[idx + 2] < -0.2) {
            rainPosArr[idx + 2] = 2.5 + Math.random() * 1.5;
            rainPosArr[idx] = (Math.random() - 0.35) * 8;
            rainPosArr[idx + 1] = (Math.random() - 0.3) * 8;
          }
        }
        rainGeom.attributes.position.needsUpdate = true;

        // ---------------------------------------------------------------------
        // D. Pulsing Operational Forecast Station Nodes
        // ---------------------------------------------------------------------
        stationMaterial.size = 0.35 + Math.sin(elapsedTime * 2.8) * 0.08;
      }

      renderer.render(scene, camera);
    };

    animate();

    // =========================================================================
    // CLEANUP & DISPOSAL
    // =========================================================================
    return () => {
      observer.disconnect();
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);

      if (renderer) {
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
        renderer.dispose();
      }

      surfaceGeometry.dispose();
      surfaceMaterial.dispose();
      contourMaterial.dispose();
      indiaLineGeom.dispose();
      indiaLineMaterial.dispose();
      indiaPointsGeom.dispose();
      indiaPointsMaterial.dispose();
      stationGeom.dispose();
      stationMaterial.dispose();
      windGeom.dispose();
      windMaterial.dispose();
      rainGeom.dispose();
      rainMaterial.dispose();
      vortexRingGeom.dispose();
      vortexRingMat.dispose();
      corePointGeom.dispose();
      corePointMat.dispose();
    };
  }, []);

  if (!webGLSupported) {
    // Elegant static fallback if WebGL is disabled or unsupported
    return (
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden bg-gradient-to-br from-[#060D1E] via-[#09152B] to-[#050914] flex items-center justify-center opacity-60">
        <div className="w-[500px] h-[500px] rounded-full bg-cyan-600/10 blur-[120px]" />
      </div>
    );
  }

  return (
    <div
      ref={mountRef}
      className="absolute inset-0 pointer-events-none z-0 overflow-hidden"
      aria-hidden="true"
    />
  );
};

export default AtmosphericHeroCanvas;
