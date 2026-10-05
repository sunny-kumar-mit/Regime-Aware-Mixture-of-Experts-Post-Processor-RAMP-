import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

// Approximate boundary anchor coordinates for the Indian subcontinent (normalized to [-10, 10] coordinate space)
const INDIA_COORDINATES: [number, number, number][] = [
  // Northwest / Kashmir / Punjab
  [-2.2, 5.8, 0],
  [-1.2, 6.2, 0.1],
  [0.0, 5.8, 0.2],
  [1.0, 5.2, 0.2],
  // Himalayan arc / Nepal / Northeast
  [2.2, 4.8, 0.15],
  [3.6, 4.4, 0.1],
  [5.2, 4.2, 0],
  [5.8, 3.4, -0.1],
  [5.2, 2.8, -0.1],
  [3.8, 2.8, -0.05],
  // Bay of Bengal coast / Odisha / Andhra
  [3.2, 2.0, 0],
  [2.6, 0.6, 0.1],
  [2.0, -0.8, 0.2],
  [1.4, -2.4, 0.3],
  [0.8, -4.0, 0.35],
  // Southern Tip / Kanyakumari / Tamil Nadu
  [0.2, -5.2, 0.4],
  [-0.4, -5.4, 0.4],
  [-0.8, -4.2, 0.35],
  // Arabian Sea coast / Kerala / Karnataka / Goa / Maharashtra
  [-1.4, -2.8, 0.3],
  [-2.0, -1.0, 0.2],
  [-2.6, 0.4, 0.1],
  [-3.2, 1.8, 0.05],
  // Gujarat / Rann of Kutch / Rajasthan
  [-4.2, 2.2, 0],
  [-4.4, 2.8, 0.02],
  [-3.8, 3.6, 0.05],
  [-3.2, 4.8, 0.05],
  [-2.2, 5.8, 0], // close loop
];

// Operational grid stations
const GRID_STATIONS: [number, number, number, string][] = [
  [-2.6, 0.4, 0.2, 'Mumbai Coast'],
  [-1.0, 4.2, 0.15, 'Delhi NCR'],
  [3.2, 2.0, 0.1, 'Kolkata Delta'],
  [1.2, -3.2, 0.3, 'Chennai Port'],
  [0.2, -1.8, 0.25, 'Bengaluru Urban'],
  [-1.4, -2.8, 0.35, 'Kochi Coast'],
  [0.4, 1.2, 0.15, 'Nagpur Central'],
  [5.0, 3.8, 0.05, 'Guwahati Valley'],
];

export const AtmosphericHeroCanvas: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x070c18, 0.035);

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(0, -1.5, 17);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.setClearColor(0x000000, 0);
      container.appendChild(renderer.domElement);
    } catch {
      // WebGL not available - fallback gracefully
      return;
    }

    const group = new THREE.Group();
    scene.add(group);

    // 1. Curved Atmospheric Coordinate Grid
    const gridGeometry = new THREE.PlaneGeometry(26, 26, 32, 32);
    const gridPositions = gridGeometry.attributes.position;
    for (let i = 0; i < gridPositions.count; i++) {
      const x = gridPositions.getX(i);
      const y = gridPositions.getY(i);
      // Subtle spherical curvature
      const z = -(x * x + y * y) * 0.025;
      gridPositions.setZ(i, z);
    }
    gridGeometry.computeVertexNormals();

    const gridMaterial = new THREE.MeshBasicMaterial({
      color: 0x1e3a5f,
      wireframe: true,
      transparent: true,
      opacity: 0.18,
    });
    const gridMesh = new THREE.Mesh(gridGeometry, gridMaterial);
    gridMesh.position.z = -1.5;
    group.add(gridMesh);

    // 2. India Outline Polyline
    const linePoints: THREE.Vector3[] = INDIA_COORDINATES.map(
      (coord) => new THREE.Vector3(coord[0], coord[1], coord[2])
    );
    const lineGeometry = new THREE.BufferGeometry().setFromPoints(linePoints);
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.65,
      linewidth: 1.5,
    });
    const indiaOutline = new THREE.Line(lineGeometry, lineMaterial);
    group.add(indiaOutline);

    // 3. Glowing India Coordinate Nodes
    const nodesGeometry = new THREE.BufferGeometry().setFromPoints(linePoints);
    const nodesMaterial = new THREE.PointsMaterial({
      color: 0x06b6d4,
      size: 0.18,
      transparent: true,
      opacity: 0.85,
    });
    const indiaNodes = new THREE.Points(nodesGeometry, nodesMaterial);
    group.add(indiaNodes);

    // 4. Station Grid Forecast Points (Pulsing nodes)
    const stationPositions: number[] = [];
    GRID_STATIONS.forEach((st) => {
      stationPositions.push(st[0], st[1], st[2]);
    });
    const stationGeometry = new THREE.BufferGeometry();
    stationGeometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(stationPositions, 3)
    );
    const stationMaterial = new THREE.PointsMaterial({
      color: 0x10b981,
      size: 0.32,
      transparent: true,
      opacity: 0.9,
    });
    const stationPoints = new THREE.Points(stationGeometry, stationMaterial);
    group.add(stationPoints);

    // 5. Atmospheric Wind Streamlines (Monsoon Southwesterly Flow)
    const particleCount = window.innerWidth < 768 ? 450 : 1000;
    const streamPositions = new Float32Array(particleCount * 3);
    const streamVelocities: { x: number; y: number; z: number; baseSpeed: number }[] = [];

    for (let i = 0; i < particleCount; i++) {
      const x = (Math.random() - 0.5) * 22;
      const y = (Math.random() - 0.5) * 20;
      const z = (Math.random() - 0.5) * 6;

      streamPositions[i * 3] = x;
      streamPositions[i * 3 + 1] = y;
      streamPositions[i * 3 + 2] = z;

      // Southwest monsoon flow: northward and eastward with cyclonic deflection
      streamVelocities.push({
        x: 0.015 + Math.random() * 0.02,
        y: 0.02 + Math.random() * 0.025,
        z: (Math.random() - 0.5) * 0.005,
        baseSpeed: 0.8 + Math.random() * 0.5,
      });
    }

    const streamGeometry = new THREE.BufferGeometry();
    streamGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(streamPositions, 3)
    );
    const streamMaterial = new THREE.PointsMaterial({
      color: 0x60a5fa,
      size: 0.1,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending,
    });
    const streamParticles = new THREE.Points(streamGeometry, streamMaterial);
    group.add(streamParticles);

    // 6. Precipitation Rainfall Droplets
    const rainCount = window.innerWidth < 768 ? 250 : 600;
    const rainPositions = new Float32Array(rainCount * 3);
    const rainSpeeds: number[] = [];

    for (let i = 0; i < rainCount; i++) {
      rainPositions[i * 3] = (Math.random() - 0.5) * 16;
      rainPositions[i * 3 + 1] = (Math.random() - 0.5) * 14;
      rainPositions[i * 3 + 2] = (Math.random() - 0.5) * 4;
      rainSpeeds.push(0.04 + Math.random() * 0.05);
    }

    const rainGeometry = new THREE.BufferGeometry();
    rainGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(rainPositions, 3)
    );
    const rainMaterial = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.08,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
    });
    const rainParticles = new THREE.Points(rainGeometry, rainMaterial);
    group.add(rainParticles);

    // Interaction State
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const clientX = event.clientX - rect.left;
      const clientY = event.clientY - rect.top;
      mouseX = (clientX / rect.width - 0.5) * 2;
      mouseY = -(clientY / rect.height - 0.5) * 2;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Handle Resize
    const handleResize = () => {
      if (!container || !renderer) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    // Visibility Observer to pause loop when not on screen
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

    // Animation Loop
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
        // Smooth camera tilt towards mouse
        targetX += (mouseX - targetX) * 0.04;
        targetY += (mouseY - targetY) * 0.04;
        group.rotation.y = targetX * 0.18 + Math.sin(elapsedTime * 0.15) * 0.04;
        group.rotation.x = -targetY * 0.12 + Math.cos(elapsedTime * 0.12) * 0.03;

        // Animate wind particles
        const posAttr = streamGeometry.attributes.position as THREE.BufferAttribute;
        const positions = posAttr.array as Float32Array;

        for (let i = 0; i < particleCount; i++) {
          const idx = i * 3;
          const vel = streamVelocities[i];

          positions[idx] += vel.x * (delta * 60) * vel.baseSpeed;
          positions[idx + 1] += vel.y * (delta * 60) * vel.baseSpeed;
          positions[idx + 2] += vel.z * (delta * 60);

          // Loop boundaries
          if (positions[idx] > 11) positions[idx] = -11;
          if (positions[idx + 1] > 10) positions[idx + 1] = -10;
        }
        posAttr.needsUpdate = true;

        // Animate rain droplets falling downward
        const rainAttr = rainGeometry.attributes.position as THREE.BufferAttribute;
        const rPositions = rainAttr.array as Float32Array;
        for (let i = 0; i < rainCount; i++) {
          const idx = i * 3;
          rPositions[idx + 1] -= rainSpeeds[i] * (delta * 60);
          if (rPositions[idx + 1] < -8) {
            rPositions[idx + 1] = 8;
            rPositions[idx] = (Math.random() - 0.5) * 16;
          }
        }
        rainAttr.needsUpdate = true;

        // Pulsing station points
        stationMaterial.size = 0.32 + Math.sin(elapsedTime * 3) * 0.06;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Clean up
    return () => {
      observer.disconnect();
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);

      if (renderer) {
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
        renderer.dispose();
      }

      // Dispose Geometries and Materials
      gridGeometry.dispose();
      gridMaterial.dispose();
      lineGeometry.dispose();
      lineMaterial.dispose();
      nodesGeometry.dispose();
      nodesMaterial.dispose();
      stationGeometry.dispose();
      stationMaterial.dispose();
      streamGeometry.dispose();
      streamMaterial.dispose();
      rainGeometry.dispose();
      rainMaterial.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="absolute inset-0 pointer-events-none z-0 overflow-hidden opacity-80"
      aria-hidden="true"
    />
  );
};
