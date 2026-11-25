/**
 * PROJECT W.A.L.L. — HYPER-ACTUATOR Mk-1 Innovation & Live Physics Simulator Engine
 * 1. Full-fidelity interactive 3D WebGL CAD inspection with exploded views.
 * 2. High-speed microfluidic droplet physics simulation (DoD ejection, flight, Stokes drag, splatting, UV pinning, gravity sagging).
 */

export class ActuatorStudioApp {
  constructor() {
    this.currentMode = 'cad'; // 'cad' or 'sim'
    this.currentModelId = '00_assembly';
    this.renderMode = 'solid'; // 'solid', 'wire', 'xray'
    this.isAutoRotate = false;
    this.explodePercent = 0.0;

    // Simulation State
    this.isContinuousPrinting = false;
    this.isUvPinningActive = true;
    this.selectedColor = '#00e5ff';
    this.dropletVolumePL = 12; // 6, 12, 24 pL
    this.timeScale = 1.0; // 1.0, 0.1, 0.02
    this.totalDropletsFired = 0;
    this.totalInkVolumeUL = 0.0;
    this.carriageSweepX = 0.0;
    this.carriageSweepDir = 1;

    // Micro-droplets in flight
    this.droplets = [];
    this.splats = [];
    this.saggingRuns = [];

    // DOM Elements
    this.container = document.getElementById('webgl-canvas-container');
    this.modelListContainer = document.getElementById('model-list-container');
    this.specDwg = document.getElementById('spec-dwg');
    this.specTitle = document.getElementById('spec-title');
    this.specDesc = document.getElementById('spec-desc');
    this.specDims = document.getElementById('spec-dims');
    this.specMass = document.getElementById('spec-mass');
    this.specMat = document.getElementById('spec-mat');
    this.specTol = document.getElementById('spec-tol');
    this.specFeatures = document.getElementById('spec-features');
    this.btnDlStl = document.getElementById('btn-dl-stl');
    this.btnDlScad = document.getElementById('btn-dl-scad');
    this.explodeSlider = document.getElementById('explode-slider');
    this.explodeVal = document.getElementById('explode-val');
    this.explodeBox = document.getElementById('explode-control-box');

    // Sim UI Elements
    this.physicsHud = document.getElementById('physics-hud-panel');
    this.simDock = document.getElementById('sim-dock-overlay');
    this.cadStyleGroup = document.getElementById('cad-style-group');
    this.cadBottomOverlay = document.getElementById('cad-bottom-overlay');
    this.btnModeCad = document.getElementById('btn-mode-cad');
    this.btnModeSim = document.getElementById('btn-mode-sim');
    this.btnFireBurst = document.getElementById('btn-fire-burst');
    this.btnContinuous = document.getElementById('btn-continuous-print');
    this.btnPurge = document.getElementById('btn-purge-nozzles');
    this.btnClearWall = document.getElementById('btn-clear-wall');
    this.btnToggleUv = document.getElementById('btn-toggle-uv');
    this.hudDroplets = document.getElementById('hud-droplet-count');
    this.hudVolume = document.getElementById('hud-volume');
    this.hudUv = document.getElementById('hud-uv');
    this.hudMeniscus = document.getElementById('hud-meniscus');

    // 1. Setup Data Registry
    this.initModelRegistry();

    // 2. Initialize Three.js Viewport
    this.initThree();

    // 3. Setup Wall Canvas & Dynamic Texture
    this.initWallCanvas();

    // 4. Setup UI Listeners & Render Sidebar
    this.renderModelList();
    this.initListeners();

    // 5. Load Initial Master Assembly
    this.loadModel('00_assembly');
  }

  initModelRegistry() {
    this.models = {
      '00_assembly': {
        id: '00',
        name: 'HYPER-ACTUATOR Mk-1 Assembly',
        subtext: 'Complete 7-Module Mechatronic Engine',
        dwg: 'DWG-WALL-HACT-000',
        dims: '98.0 x 78.0 x 56.0 mm',
        mass: '420 grams',
        mat: '6061-T6 / Silicon / Fused Quartz',
        tol: '±0.005 mm (ISO 2768-mK)',
        stlFile: 'hyper_actuator_assembly.stl',
        scadFile: 'hyper_actuator_standalone.scad',
        canExplode: true,
        features: [
          'Zero Wall Contact: 1.50 mm non-contact closed-loop standoff prevents platform yaw tilt.',
          'In-Situ 395nm UV Pinning: Freezes 6-24 pL droplets in <50ms (Zero vertical drip).',
          'Active Meniscus Regulation: -1.45 kPa vacuum prevents nozzle drool under motion.',
          'Dual-Stage Micro-Z Guideway: 100 Hz voice-coil cancels cable vibration.'
        ]
      },
      '01_adapter': {
        id: '01',
        name: 'CDPR Interface Adapter Plate',
        subtext: 'Structural Carriage Bed & Grommets',
        dwg: 'DWG-WALL-HACT-001',
        dims: '98.0 x 78.0 x 6.0 mm',
        mass: '68 grams',
        mat: '6061-T6 Aluminum / Carbon Plate',
        tol: '±0.02 mm (Rail Bed Parallelism)',
        stlFile: 'cdpr_interface_adapter.stl',
        scadFile: 'cdpr_interface_adapter.scad',
        canExplode: false,
        features: [
          'Precision CNC slot for MGN7C stainless linear rail locating.',
          '4x Elastomer vibration-damping grommet bores to isolate motor stepper pulses.',
          'Central 22mm clear aperture for micro-piezo nozzle array projection.'
        ]
      },
      '02_z_stage': {
        id: '02',
        name: 'Active Moving Z-Stage Carriage',
        subtext: 'VCA Bobbin & Micro-LiDAR Eye',
        dwg: 'DWG-WALL-HACT-002',
        dims: '64.0 x 56.0 x 12.0 mm',
        mass: '38 grams (Moving Mass)',
        mat: 'Carbon-Reinforced PETG / Alum',
        tol: '±0.01 mm (MGN7C C-Block Bores)',
        stlFile: 'active_z_stage_carriage.stl',
        scadFile: 'active_z_stage_carriage.scad',
        canExplode: false,
        features: [
          'Ultra-low moving mass (<40g) allows 100 Hz closed-loop position bandwidth.',
          'Recessed pocket for VCA-15 moving copper coil with center ventilation bore.',
          'Integrated optical sight cones for ST VL53L4CD micro-LiDAR ToF distance sensor.'
        ]
      },
      '03_printhead': {
        id: '03',
        name: '128-Nozzle MEMS Printhead Dock',
        subtext: 'Micro-Piezo 300 DPI Fluidic Manifold',
        dwg: 'DWG-WALL-HACT-003',
        dims: '34.0 x 48.0 x 32.0 mm',
        mass: '82 grams',
        mat: 'Anodized 6061-T6 & Silicon MEMS',
        tol: '±0.002 mm (21.5 µm Nozzle Orifice)',
        stlFile: 'mems_128_printhead_dock.stl',
        scadFile: 'mems_128_printhead_dock.scad',
        canExplode: false,
        features: [
          '128 MEMS Micro-Nozzles arranged in dual staggered rows (Native 300 DPI).',
          'Variable 3-level grayscale droplet volume (6.0 pL, 12.0 pL, 24.0 pL).',
          'Self-centering 45° quick-release dovetail slide with lateral M3 cam clamp.'
        ]
      },
      '04_uv_wing': {
        id: '04',
        name: 'In-Situ 395nm UV Pinning Wing',
        subtext: 'Dual-Wing Heatsink & Quartz Lens',
        dwg: 'DWG-WALL-HACT-004',
        dims: '18.0 x 44.0 x 28.0 mm',
        mass: '26 grams each',
        mat: '6061-T6 Aluminum & Fused Quartz',
        tol: '±0.05 mm (Collimator Lens Alignment)',
        stlFile: 'uv_pinning_wing.stl',
        scadFile: 'uv_pinning_wing.scad',
        canExplode: false,
        features: [
          'High-intensity 395nm UV-A optical array delivering 2.8 W/cm² focal power.',
          '6mm Cylindrical quartz rod collimating lens focusing UV curtain 1.5mm from wall.',
          'Convective heat-sink flutes dissipate LED thermal load away from piezo nozzles.'
        ]
      },
      '05_damper': {
        id: '05',
        name: 'Meniscus Fluidic Damper Tank',
        subtext: 'Constant -1.45 kPa Vacuum Reservoir',
        dwg: 'DWG-WALL-HACT-005',
        dims: '26.0 dia x 42.0 mm',
        mass: '34 grams',
        mat: 'Chemical-Inert POM & PTFE',
        tol: '±0.05 mm (Sensor Tap Bore)',
        stlFile: 'meniscus_fluidic_damper.stl',
        scadFile: 'meniscus_fluidic_damper.scad',
        canExplode: false,
        features: [
          'Maintains continuous -1.45 kPa ±0.05 kPa meniscus back-pressure via PWM diaphragm pump.',
          'Direct mount boss for NXP MPXV5004DP differential pressure transducer.',
          'Eliminates vertical fluid column hydrostatic head pressure spikes during robot motion.'
        ]
      },
      '06_capping': {
        id: '06',
        name: 'Motorized Auto-Capping Dock',
        subtext: '9g Servo & Platinum Silicone Boot',
        dwg: 'DWG-WALL-HACT-006',
        dims: '38.0 x 14.0 x 12.0 mm',
        mass: '18 grams',
        mat: 'PETG Arm & Platinum Silicone (40A)',
        tol: '±0.05 mm (Servo Spline Fit)',
        stlFile: 'auto_capping_station.stl',
        scadFile: 'auto_capping_station.scad',
        canExplode: false,
        features: [
          'Articulated swing-arm driven by metal-gear digital 9g micro-servo.',
          'Perimeter sealing lip creates airtight chamber over 128 nozzles during idle pauses.',
          'Prevents volatile solvent evaporation and nozzle crusting without user intervention.'
        ]
      }
    };
  }

  initThree() {
    this.width = this.container.clientWidth || 800;
    this.height = this.container.clientHeight || 600;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x06080d);

    // Camera
    this.camera = new THREE.PerspectiveCamera(36, this.width / this.height, 0.1, 2000);
    this.camera.position.set(110, 95, 140);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    // Orbit Controls
    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.target.set(0, 0, 0);

    // Lighting
    this.ambLight = new THREE.AmbientLight(0xffffff, 0.95);
    this.scene.add(this.ambLight);

    this.dirLight1 = new THREE.DirectionalLight(0xffffff, 1.25);
    this.dirLight1.position.set(120, 150, 100);
    this.scene.add(this.dirLight1);

    this.dirLight2 = new THREE.DirectionalLight(0x93c5fd, 0.55);
    this.dirLight2.position.set(-100, -80, -60);
    this.scene.add(this.dirLight2);

    // UV Flash Spotlights (Dynamic Luminescence during Curing)
    this.uvFlashLeft = new THREE.PointLight(0x8b5cf6, 0.0, 45);
    this.uvFlashLeft.position.set(-27, 0, -26);
    this.scene.add(this.uvFlashLeft);

    this.uvFlashRight = new THREE.PointLight(0x8b5cf6, 0.0, 45);
    this.uvFlashRight.position.set(27, 0, -26);
    this.scene.add(this.uvFlashRight);

    // Grid Floor
    this.grid = new THREE.GridHelper(300, 30, 0x1f293d, 0x111624);
    this.grid.position.y = -50;
    this.scene.add(this.grid);

    // Master Group for Actuator Model
    this.modelGroup = new THREE.Group();
    this.scene.add(this.modelGroup);

    // Group for Physical Micro-Droplets
    this.dropletGroup = new THREE.Group();
    this.scene.add(this.dropletGroup);

    // Exploded parts reference map
    this.explodableMeshes = [];

    // Resize Handler
    window.addEventListener('resize', () => {
      this.width = this.container.clientWidth;
      this.height = this.container.clientHeight;
      this.camera.aspect = this.width / this.height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(this.width, this.height);
    });

    // Clock
    this.clock = new THREE.Clock();

    // Main Physics & Render Animation Loop
    const animate = () => {
      requestAnimationFrame(animate);
      const delta = this.clock.getDelta();

      if (this.isAutoRotate && this.currentMode === 'cad') {
        this.modelGroup.rotation.z += 0.005;
      }

      // Step Physical Particle Engine
      this.updatePhysicsDroplets(delta * this.timeScale);

      // Continuous Printing Sweeper
      if (this.isContinuousPrinting && this.currentMode === 'sim') {
        this.stepContinuousPrint(delta * this.timeScale);
      }

      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    };
    animate();
  }

  initWallCanvas() {
    // 2D Dynamic Wall Surface Canvas (1024 x 1024 for sharp paint accumulation)
    this.wallCanvas = document.createElement('canvas');
    this.wallCanvas.width = 1024;
    this.wallCanvas.height = 1024;
    this.wallCtx = this.wallCanvas.getContext('2d');

    // Primed Wall Base (Smooth Matte White Architectural Panel with Subtle Texture)
    this.resetWallCanvas();

    // Three.js Texture mapped to the Wall Surface Plane
    this.wallTexture = new THREE.CanvasTexture(this.wallCanvas);
    this.wallTexture.anisotropy = 8;
    this.wallTexture.minFilter = THREE.LinearMipmapLinearFilter;
    this.wallTexture.magFilter = THREE.LinearFilter;

    // Wall Surface Plane Mesh (160 x 160 mm in real-world dimensions, placed at exact z = -28.5mm)
    const wallGeo = new THREE.PlaneGeometry(160, 160);
    const wallMat = new THREE.MeshStandardMaterial({
      map: this.wallTexture,
      roughness: 0.88,
      metalness: 0.02
    });
    this.wallMesh = new THREE.Mesh(wallGeo, wallMat);
    this.wallMesh.position.set(0, 0, -28.5); // Exactly 1.50mm standoff from orifice plate (-27.0)
    this.scene.add(this.wallMesh);

    // Wall Perimeter Aluminum Frame Trim
    const frameGeo = new THREE.BoxGeometry(164, 164, 4);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.5, metalness: 0.7 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    frame.position.set(0, 0, -30.6);
    this.scene.add(frame);
  }

  resetWallCanvas() {
    this.wallCtx.fillStyle = '#f8fafc';
    this.wallCtx.fillRect(0, 0, this.wallCanvas.width, this.wallCanvas.height);

    // Light subtle grid lines on the wall panel (5mm scale)
    this.wallCtx.strokeStyle = '#e2e8f0';
    this.wallCtx.lineWidth = 1;
    for (let x = 0; x < 1024; x += 32) {
      this.wallCtx.beginPath();
      this.wallCtx.moveTo(x, 0);
      this.wallCtx.lineTo(x, 1024);
      this.wallCtx.stroke();
    }
    for (let y = 0; y < 1024; y += 32) {
      this.wallCtx.beginPath();
      this.wallCtx.moveTo(0, y);
      this.wallCtx.lineTo(1024, y);
      this.wallCtx.stroke();
    }

    if (this.wallTexture) this.wallTexture.needsUpdate = true;
    this.saggingRuns = [];
  }

  renderModelList() {
    this.modelListContainer.innerHTML = '';
    Object.keys(this.models).forEach(key => {
      const m = this.models[key];
      const item = document.createElement('div');
      item.className = `model-item ${key === this.currentModelId ? 'active' : ''}`;
      item.setAttribute('data-model-id', key);
      item.innerHTML = `
        <div class="model-item-header">
          <span class="model-id">[MODEL ${m.id}]</span>
          <span class="model-tag">${m.dwg}</span>
        </div>
        <div class="model-name">${m.name}</div>
        <div class="model-subtext">${m.subtext}</div>
      `;
      item.addEventListener('click', () => {
        if (this.currentMode === 'sim') this.switchMode('cad');
        this.loadModel(key);
      });
      this.modelListContainer.appendChild(item);
    });
  }

  loadModel(modelId) {
    this.currentModelId = modelId;
    const m = this.models[modelId];
    if (!m) return;

    // Update Sidebar Selection State
    document.querySelectorAll('.model-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-model-id') === modelId);
    });

    // Update Specs & Download Links
    this.specDwg.textContent = m.dwg;
    this.specTitle.textContent = m.name;
    this.specDesc.textContent = m.subtext;
    this.specDims.textContent = m.dims;
    this.specMass.textContent = m.mass;
    this.specMat.textContent = m.mat;
    this.specTol.textContent = m.tol;

    // Features
    this.specFeatures.innerHTML = m.features.map(f => `
      <div class="feature-item">
        <span class="feature-icon">&bull;</span>
        <span>${f}</span>
      </div>
    `).join('');

    // Download Links
    this.btnDlStl.href = `exports/novel_actuator/${m.stlFile}`;
    this.btnDlStl.download = m.stlFile;
    this.btnDlScad.href = `exports/novel_actuator/${m.scadFile}`;
    this.btnDlScad.download = m.scadFile;

    // Explode Control Visibility
    this.explodeBox.style.display = (m.canExplode && this.currentMode === 'cad') ? 'flex' : 'none';
    this.explodeSlider.value = 0;
    this.explodeVal.textContent = '0%';
    this.explodePercent = 0.0;

    // Build 3D Mesh
    this.clearModelGroup();
    this.buildGeometryForModel(modelId);
    this.applyRenderMode();

    if (this.currentMode === 'cad') {
      this.wallMesh.visible = false;
      this.resetCamera();
    } else {
      this.wallMesh.visible = true;
      this.setupSimulationCamera();
    }
  }

  clearModelGroup() {
    this.explodableMeshes = [];
    while (this.modelGroup.children.length > 0) {
      const obj = this.modelGroup.children[0];
      this.modelGroup.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(mat => mat.dispose());
        else obj.material.dispose();
      }
    }
    this.modelGroup.rotation.set(0, 0, 0);
    this.modelGroup.position.set(0, 0, 0);
  }

  buildGeometryForModel(modelId) {
    switch (modelId) {
      case '00_assembly':
        this.buildMasterAssembly3D();
        break;
      case '01_adapter':
        this.buildAdapterPlate3D();
        break;
      case '02_z_stage':
        this.buildZStageCarriage3D();
        break;
      case '03_printhead':
        this.buildPrinthead3D();
        break;
      case '04_uv_wing':
        this.buildUvWing3D();
        break;
      case '05_damper':
        this.buildFluidicDamper3D();
        break;
      case '06_capping':
        this.buildCappingStation3D();
        break;
    }
  }

  buildMasterAssembly3D() {
    // 1. CDPR Base Adapter
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(98, 78, 6),
      new THREE.MeshStandardMaterial({ color: 0x22262d, roughness: 0.45, metalness: 0.65 })
    );
    this.modelGroup.add(base);
    this.explodableMeshes.push({ mesh: base, basePos: new THREE.Vector3(0, 0, 0), dir: new THREE.Vector3(0, 0, -25) });

    // 2. Linear Rail
    const rail = new THREE.Mesh(
      new THREE.BoxGeometry(7, 60, 4.8),
      new THREE.MeshStandardMaterial({ color: 0xd8dde4, roughness: 0.25, metalness: 0.90 })
    );
    rail.position.set(0, 0, 5.4);
    this.modelGroup.add(rail);
    this.explodableMeshes.push({ mesh: rail, basePos: new THREE.Vector3(0, 0, 5.4), dir: new THREE.Vector3(0, 0, -15) });

    // 3. VCA Stator
    const vcaStator = new THREE.Mesh(
      new THREE.CylinderGeometry(12, 12, 14, 24),
      new THREE.MeshStandardMaterial({ color: 0xb58900, roughness: 0.35, metalness: 0.75 })
    );
    vcaStator.position.set(0, 24, 10);
    this.modelGroup.add(vcaStator);
    this.explodableMeshes.push({ mesh: vcaStator, basePos: new THREE.Vector3(0, 24, 10), dir: new THREE.Vector3(0, 30, -5) });

    // 4. Moving Z-Carriage
    this.zCarriageGrp = new THREE.Group();
    const zCarriage = new THREE.Mesh(
      new THREE.BoxGeometry(64, 56, 12),
      new THREE.MeshStandardMaterial({ color: 0x303642, roughness: 0.50, metalness: 0.50 })
    );
    this.zCarriageGrp.add(zCarriage);

    const coil = new THREE.Mesh(
      new THREE.CylinderGeometry(10, 10, 8, 24),
      new THREE.MeshStandardMaterial({ color: 0xc86420, roughness: 0.30, metalness: 0.80 })
    );
    coil.position.set(0, 18, -4);
    this.zCarriageGrp.add(coil);

    const lidar = new THREE.Mesh(
      new THREE.BoxGeometry(12, 8, 2.5),
      new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.20, metalness: 0.30 })
    );
    lidar.position.set(22, 0, 7);
    this.zCarriageGrp.add(lidar);

    this.zCarriageGrp.position.set(0, 0, 16.5);
    this.modelGroup.add(this.zCarriageGrp);
    this.explodableMeshes.push({ mesh: this.zCarriageGrp, basePos: new THREE.Vector3(0, 0, 16.5), dir: new THREE.Vector3(0, 0, 20) });

    // 5. 128-Nozzle Printhead
    const headGrp = new THREE.Group();
    const head = new THREE.Mesh(
      new THREE.BoxGeometry(34, 48, 30),
      new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.40, metalness: 0.60 })
    );
    headGrp.add(head);

    // Silicon Orifice Plate with 128 micro-nozzle orifices
    const plate = new THREE.Mesh(
      new THREE.BoxGeometry(12, 28, 2),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.10, metalness: 0.95 })
    );
    plate.position.set(0, 0, -16);
    headGrp.add(plate);

    // Orifice holes visible on bottom plate face
    for (let r = 0; r < 16; r++) {
      [-1.2, 1.2].forEach(col => {
        const hole = new THREE.Mesh(
          new THREE.CircleGeometry(0.35, 8),
          new THREE.MeshBasicMaterial({ color: 0x000000 })
        );
        hole.rotation.x = Math.PI;
        hole.position.set(col, (r - 7.5) * 1.5, -17.05);
        headGrp.add(hole);
      });
    }

    headGrp.position.set(0, 0, -10);
    this.modelGroup.add(headGrp);
    this.explodableMeshes.push({ mesh: headGrp, basePos: new THREE.Vector3(0, 0, -10), dir: new THREE.Vector3(0, 0, 50) });

    // 6. Dual UV Wings
    this.uvWings = [];
    [-27, 27].forEach((x, idx) => {
      const wingGrp = new THREE.Group();
      const wing = new THREE.Mesh(
        new THREE.BoxGeometry(16, 44, 26),
        new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.35, metalness: 0.70 })
      );
      wingGrp.add(wing);

      // Quartz Lens
      const lens = new THREE.Mesh(
        new THREE.CylinderGeometry(3, 3, 36, 20),
        new THREE.MeshPhysicalMaterial({ color: 0xffffff, transmission: 0.92, opacity: 0.95, transparent: true, roughness: 0.05, ior: 1.46 })
      );
      lens.rotation.x = Math.PI / 2;
      lens.position.set(0, 0, -13);
      wingGrp.add(lens);

      // Violet UV Pinning Light Cone
      const uvCone = new THREE.Mesh(
        new THREE.ConeGeometry(8, 14, 16),
        new THREE.MeshBasicMaterial({ color: 0x8b5cf6, transparent: true, opacity: 0.35 })
      );
      uvCone.rotation.x = Math.PI;
      uvCone.position.set(0, 0, -20);
      wingGrp.add(uvCone);

      wingGrp.position.set(x, 0, -6);
      this.modelGroup.add(wingGrp);
      this.uvWings.push(uvCone);
      this.explodableMeshes.push({
        mesh: wingGrp,
        basePos: new THREE.Vector3(x, 0, -6),
        dir: new THREE.Vector3(x < 0 ? -40 : 40, 0, 15)
      });
    });

    // 7. Meniscus Damper Tank
    const tank = new THREE.Mesh(
      new THREE.CylinderGeometry(13, 13, 40, 24),
      new THREE.MeshPhysicalMaterial({ color: 0x38bdf8, transmission: 0.75, opacity: 0.85, transparent: true, roughness: 0.2 })
    );
    tank.position.set(34, 0, 14);
    this.modelGroup.add(tank);
    this.explodableMeshes.push({ mesh: tank, basePos: new THREE.Vector3(34, 0, 14), dir: new THREE.Vector3(45, 0, -10) });

    // 8. Auto-Capping Servo Dock
    const cappingGrp = new THREE.Group();
    const servo = new THREE.Mesh(
      new THREE.BoxGeometry(12, 22, 22),
      new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.6 })
    );
    cappingGrp.add(servo);

    const arm = new THREE.Mesh(
      new THREE.BoxGeometry(32, 10, 4),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 })
    );
    arm.position.set(16, 0, 13);
    cappingGrp.add(arm);

    cappingGrp.position.set(-32, -10, 12);
    this.modelGroup.add(cappingGrp);
    this.explodableMeshes.push({ mesh: cappingGrp, basePos: new THREE.Vector3(-32, -10, 12), dir: new THREE.Vector3(-45, -20, -10) });
  }

  buildAdapterPlate3D() {
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(98, 78, 6),
      new THREE.MeshStandardMaterial({ color: 0x2b313d, roughness: 0.45, metalness: 0.70 })
    );
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(11, 14, 32),
      new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide })
    );
    ring.position.set(0, 0, 3.1);
    base.add(ring);
    this.modelGroup.add(base);
  }

  buildZStageCarriage3D() {
    const grp = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(64, 56, 12),
      new THREE.MeshStandardMaterial({ color: 0x333b47, roughness: 0.40, metalness: 0.60 })
    );
    grp.add(body);

    const coil = new THREE.Mesh(
      new THREE.CylinderGeometry(11, 11, 8, 32),
      new THREE.MeshStandardMaterial({ color: 0xc86420, roughness: 0.30, metalness: 0.85 })
    );
    coil.position.set(0, 14, 8);
    grp.add(coil);

    const lidar = new THREE.Mesh(
      new THREE.BoxGeometry(14, 9, 3),
      new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.20, metalness: 0.40 })
    );
    lidar.position.set(20, 0, 7.5);
    grp.add(lidar);

    this.modelGroup.add(grp);
  }

  buildPrinthead3D() {
    const grp = new THREE.Group();
    const head = new THREE.Mesh(
      new THREE.BoxGeometry(34, 48, 32),
      new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.35, metalness: 0.70 })
    );
    grp.add(head);

    const plate = new THREE.Mesh(
      new THREE.BoxGeometry(12, 28, 2),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.05, metalness: 0.98 })
    );
    plate.position.set(0, 0, -17);
    grp.add(plate);

    [-7, 7].forEach(x => {
      const luer = new THREE.Mesh(
        new THREE.CylinderGeometry(2.2, 2.2, 8, 16),
        new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.2, metalness: 0.8 })
      );
      luer.position.set(x, 0, 18);
      grp.add(luer);
    });

    this.modelGroup.add(grp);
  }

  buildUvWing3D() {
    const grp = new THREE.Group();
    const wing = new THREE.Mesh(
      new THREE.BoxGeometry(18, 44, 28),
      new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.35, metalness: 0.75 })
    );
    grp.add(wing);

    const lens = new THREE.Mesh(
      new THREE.CylinderGeometry(3, 3, 36, 24),
      new THREE.MeshPhysicalMaterial({ color: 0xffffff, transmission: 0.95, opacity: 0.9, transparent: true, roughness: 0.05, ior: 1.46 })
    );
    lens.rotation.x = Math.PI / 2;
    lens.position.set(0, 0, -13);
    grp.add(lens);

    const uvCone = new THREE.Mesh(
      new THREE.ConeGeometry(9, 18, 24),
      new THREE.MeshBasicMaterial({ color: 0x8b5cf6, transparent: true, opacity: 0.40 })
    );
    uvCone.rotation.x = Math.PI;
    uvCone.position.set(0, 0, -22);
    grp.add(uvCone);

    this.modelGroup.add(grp);
  }

  buildFluidicDamper3D() {
    const grp = new THREE.Group();
    const tank = new THREE.Mesh(
      new THREE.CylinderGeometry(13, 13, 42, 32),
      new THREE.MeshPhysicalMaterial({ color: 0x38bdf8, transmission: 0.80, opacity: 0.88, transparent: true, roughness: 0.15 })
    );
    grp.add(tank);

    const sensor = new THREE.Mesh(
      new THREE.BoxGeometry(8, 14, 16),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.5 })
    );
    sensor.position.set(14, 0, 5);
    grp.add(sensor);

    this.modelGroup.add(grp);
  }

  buildCappingStation3D() {
    const grp = new THREE.Group();
    const servo = new THREE.Mesh(
      new THREE.BoxGeometry(12, 22, 22),
      new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.6 })
    );
    grp.add(servo);

    const arm = new THREE.Mesh(
      new THREE.BoxGeometry(38, 12, 6),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 })
    );
    arm.position.set(19, 0, 12);
    grp.add(arm);

    const boot = new THREE.Mesh(
      new THREE.BoxGeometry(32, 16, 6),
      new THREE.MeshStandardMaterial({ color: 0x06b6d4, roughness: 0.8 })
    );
    boot.position.set(38, 0, 16);
    grp.add(boot);

    this.modelGroup.add(grp);
  }

  // ====================================================================
  // MICROFLUIDIC DROPLET EJECTION & IMPACT PHYSICS ENGINE
  // ====================================================================

  fireDropletStream(patternType = 'burst') {
    // Orifice plate is at z = -27.0 mm (world coords). Wall surface is at z = -28.5 mm.
    // Standoff gap is exactly 1.50 mm!
    const numNozzles = (patternType === 'purge') ? 32 : (patternType === 'single') ? 1 : 16;
    const dropRadius = (this.dropletVolumePL === 6) ? 0.35 : (this.dropletVolumePL === 12) ? 0.48 : 0.65;
    const ejectVelZ = -75.0; // Scaled physics flight velocity (75 mm/s visual)

    const colorHex = parseInt(this.selectedColor.replace('#', '0x'), 16);
    const dropMat = new THREE.MeshStandardMaterial({
      color: colorHex,
      roughness: 0.1,
      metalness: 0.8,
      emissive: colorHex,
      emissiveIntensity: 0.2
    });

    for (let i = 0; i < numNozzles; i++) {
      // Calculate origin nozzle on the 128-orifice array
      const row = (i % 16) - 7.5;
      const col = (i % 2 === 0) ? -1.2 : 1.2;

      const originX = this.modelGroup.position.x + col + (Math.random() - 0.5) * 0.1;
      const originY = this.modelGroup.position.y + row * 1.5 + (Math.random() - 0.5) * 0.1;
      const originZ = -27.05; // Just exiting the orifice plate

      const dropGeo = new THREE.SphereGeometry(dropRadius, 12, 12);
      const dropMesh = new THREE.Mesh(dropGeo, dropMat);
      dropMesh.position.set(originX, originY, originZ);
      this.dropletGroup.add(dropMesh);

      this.droplets.push({
        mesh: dropMesh,
        x: originX,
        y: originY,
        z: originZ,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        vz: ejectVelZ,
        life: 0.0,
        maxLife: 0.15, // Reaches wall in ~200 µs
        color: this.selectedColor,
        radius: dropRadius,
        impacted: false
      });

      this.totalDropletsFired++;
      this.totalInkVolumeUL += (this.dropletVolumePL * 1e-6);
    }

    // Update Telemetry HUD
    this.hudDroplets.textContent = this.totalDropletsFired.toLocaleString();
    this.hudVolume.textContent = `${this.totalInkVolumeUL.toFixed(3)} \u00B5L`;

    // Trigger UV Flash if Pinning is Active
    if (this.isUvPinningActive) {
      this.uvFlashLeft.intensity = 2.5;
      this.uvFlashRight.intensity = 2.5;
      setTimeout(() => {
        this.uvFlashLeft.intensity = 0.0;
        this.uvFlashRight.intensity = 0.0;
      }, 60);
    }
  }

  updatePhysicsDroplets(dt) {
    const wallImpactZ = -28.5; // Exact wall coordinate

    for (let i = this.droplets.length - 1; i >= 0; i--) {
      const d = this.droplets[i];
      d.life += dt;

      // Newtonian integration with Stokes air resistance
      d.vz *= 0.992; // Air drag
      d.x += d.vx * dt;
      d.y += d.vy * dt;
      d.z += d.vz * dt;

      d.mesh.position.set(d.x, d.y, d.z);

      // Check impact with Wall Surface
      if (d.z <= wallImpactZ && !d.impacted) {
        d.impacted = true;
        this.handleWallImpact(d);

        // Remove in-flight droplet mesh
        this.dropletGroup.remove(d.mesh);
        d.mesh.geometry.dispose();
        this.droplets.splice(i, 1);
      } else if (d.life > 0.4) {
        // Timeout
        this.dropletGroup.remove(d.mesh);
        d.mesh.geometry.dispose();
        this.droplets.splice(i, 1);
      }
    }

    // Update Gravity Sagging Runs on Wall (when UV Pinning is OFF)
    if (!this.isUvPinningActive && this.saggingRuns.length > 0) {
      this.updateSaggingDrips(dt);
    }
  }

  handleWallImpact(droplet) {
    // Map 3D world (x, y) [-80..80 mm] to 2D Wall Canvas [0..1024 px]
    const canvasX = ((droplet.x + 80.0) / 160.0) * 1024.0;
    const canvasY = ((-droplet.y + 80.0) / 160.0) * 1024.0;

    // Splat diameter calculated via Kurabayashi-Chandra relation (beta = 2.2)
    const splatRadiusPx = (droplet.radius * 2.2) * (1024.0 / 160.0) * 1.5;

    this.wallCtx.save();
    this.wallCtx.beginPath();
    this.wallCtx.arc(canvasX, canvasY, splatRadiusPx, 0, Math.PI * 2);
    this.wallCtx.fillStyle = droplet.color;
    this.wallCtx.shadowColor = droplet.color;
    this.wallCtx.shadowBlur = this.isUvPinningActive ? 2 : 5;
    this.wallCtx.fill();
    this.wallCtx.restore();

    this.wallTexture.needsUpdate = true;

    // If UV Pinning is OFF: Register a gravity sagging run!
    if (!this.isUvPinningActive) {
      this.saggingRuns.push({
        x: canvasX,
        y: canvasY,
        color: droplet.color,
        speed: 12.0 + Math.random() * 18.0, // Pixels per second downward
        length: 0.0,
        maxLength: 35.0 + Math.random() * 50.0 // Unsightly drip length
      });
    }
  }

  updateSaggingDrips(dt) {
    let needsUpdate = false;
    for (let i = this.saggingRuns.length - 1; i >= 0; i--) {
      const run = this.saggingRuns[i];
      if (run.length < run.maxLength) {
        const step = run.speed * dt;
        run.length += step;
        run.y += step; // Run down vertical wall under gravity

        this.wallCtx.beginPath();
        this.wallCtx.arc(run.x + (Math.random() - 0.5) * 0.5, run.y, 1.8, 0, Math.PI * 2);
        this.wallCtx.fillStyle = run.color;
        this.wallCtx.fill();
        needsUpdate = true;
      }
    }
    if (needsUpdate) {
      this.wallTexture.needsUpdate = true;
    }
  }

  stepContinuousPrint(dt) {
    // Sweeps the HYPER-ACTUATOR carriage horizontally across the wall in an S-curve path
    const sweepSpeed = 45.0; // mm/s
    this.carriageSweepX += this.carriageSweepDir * sweepSpeed * dt;

    if (this.carriageSweepX > 40.0) {
      this.carriageSweepX = 40.0;
      this.carriageSweepDir = -1;
    } else if (this.carriageSweepX < -40.0) {
      this.carriageSweepX = -40.0;
      this.carriageSweepDir = 1;
    }

    this.modelGroup.position.x = this.carriageSweepX;

    // Micro-vibrations on Meniscus Vacuum Gauge
    const microJitter = (Math.random() - 0.5) * 0.04;
    this.hudMeniscus.textContent = `${(-1.45 + microJitter).toFixed(2)} kPa (STABLE)`;

    // Fire continuous high-frequency droplet bursts
    if (Math.random() < 0.45) {
      this.fireDropletStream('burst');
    }
  }

  // ====================================================================
  // MODE & VIEW CONTROLS
  // ====================================================================

  switchMode(mode) {
    this.currentMode = mode;
    if (mode === 'sim') {
      this.btnModeSim.classList.add('btn-mode-active');
      this.btnModeCad.classList.remove('active');
      this.physicsHud.style.display = 'flex';
      this.simDock.style.display = 'flex';
      this.cadBottomOverlay.style.display = 'none';
      this.cadStyleGroup.style.display = 'none';
      this.wallMesh.visible = true;

      // Ensure Master Assembly is loaded for printing
      if (this.currentModelId !== '00_assembly') {
        this.loadModel('00_assembly');
      }
      this.setupSimulationCamera();
    } else {
      this.btnModeCad.classList.add('active');
      this.btnModeSim.classList.remove('btn-mode-active');
      this.physicsHud.style.display = 'none';
      this.simDock.style.display = 'none';
      this.cadBottomOverlay.style.display = 'flex';
      this.cadStyleGroup.style.display = 'flex';
      this.wallMesh.visible = false;
      this.isContinuousPrinting = false;
      this.btnContinuous.classList.remove('running');
      this.btnContinuous.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
        CONTINUOUS PRINT
      `;
      this.resetCamera();
    }
  }

  setupSimulationCamera() {
    // Macro Close-Up Angle looking directly into the 1.50 mm Standoff Gap
    this.camera.position.set(45, -10, -5);
    this.controls.target.set(0, 0, -26);
    this.controls.update();
  }

  applyRenderMode() {
    this.modelGroup.traverse(child => {
      if (child.isMesh) {
        if (!child.userData.origMat) child.userData.origMat = child.material;

        if (this.renderMode === 'wire') {
          child.material = new THREE.MeshBasicMaterial({ color: 0x00ff88, wireframe: true });
        } else if (this.renderMode === 'xray') {
          child.material = new THREE.MeshStandardMaterial({
            color: child.userData.origMat.color || 0x60a5fa,
            roughness: 0.2,
            metalness: 0.1,
            transparent: true,
            opacity: 0.35,
            wireframe: false
          });
        } else {
          child.material = child.userData.origMat;
        }
      }
    });
  }

  updateExplode(factor) {
    this.explodePercent = factor;
    this.explodableMeshes.forEach(item => {
      const targetPos = item.basePos.clone().add(item.dir.clone().multiplyScalar(factor));
      item.mesh.position.copy(targetPos);
    });
  }

  resetCamera() {
    this.camera.position.set(110, 95, 140);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  initListeners() {
    // Mode Switch: CAD vs Simulator
    this.btnModeCad.addEventListener('click', () => this.switchMode('cad'));
    this.btnModeSim.addEventListener('click', () => this.switchMode('sim'));

    // Render Mode Toggles (Solid / Wireframe / X-Ray)
    document.getElementById('btn-render-solid').addEventListener('click', e => {
      this.renderMode = 'solid';
      this.updateToolButtons(e.target);
      this.applyRenderMode();
    });

    document.getElementById('btn-render-wire').addEventListener('click', e => {
      this.renderMode = 'wire';
      this.updateToolButtons(e.target);
      this.applyRenderMode();
    });

    document.getElementById('btn-render-xray').addEventListener('click', e => {
      this.renderMode = 'xray';
      this.updateToolButtons(e.target);
      this.applyRenderMode();
    });

    // Auto-Rotate & Reset
    const autoRotBtn = document.getElementById('btn-auto-rotate');
    autoRotBtn.addEventListener('click', () => {
      this.isAutoRotate = !this.isAutoRotate;
      autoRotBtn.classList.toggle('active', this.isAutoRotate);
    });

    document.getElementById('btn-reset-cam').addEventListener('click', () => {
      if (this.currentMode === 'sim') this.setupSimulationCamera();
      else this.resetCamera();
    });

    // Explode Slider
    this.explodeSlider.addEventListener('input', e => {
      const val = parseFloat(e.target.value) / 100.0;
      this.explodeVal.textContent = `${e.target.value}%`;
      this.updateExplode(val);
    });

    // Simulation Trigger Buttons
    this.btnFireBurst.addEventListener('click', () => {
      this.fireDropletStream('burst');
    });

    this.btnContinuous.addEventListener('click', () => {
      this.isContinuousPrinting = !this.isContinuousPrinting;
      this.btnContinuous.classList.toggle('running', this.isContinuousPrinting);
      this.btnContinuous.innerHTML = this.isContinuousPrinting
        ? `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> PAUSE PRINT`
        : `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg> CONTINUOUS PRINT`;
    });

    this.btnPurge.addEventListener('click', () => {
      this.fireDropletStream('purge');
    });

    this.btnClearWall.addEventListener('click', () => {
      this.resetWallCanvas();
    });

    // Color Swatch Selection
    document.querySelectorAll('.color-swatch').forEach(swatch => {
      swatch.addEventListener('click', e => {
        document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
        e.target.classList.add('active');
        this.selectedColor = e.target.getAttribute('data-color');
      });
    });

    // Droplet Volume Selector
    document.getElementById('select-drop-size').addEventListener('change', e => {
      this.dropletVolumePL = parseInt(e.target.value);
    });

    // Time Dilation Selector
    document.getElementById('select-time-scale').addEventListener('change', e => {
      this.timeScale = parseFloat(e.target.value);
    });

    // UV Pinning Toggle
    this.btnToggleUv.addEventListener('click', () => {
      this.isUvPinningActive = !this.isUvPinningActive;
      this.btnToggleUv.classList.toggle('active', this.isUvPinningActive);
      this.btnToggleUv.textContent = `UV PINNING: ${this.isUvPinningActive ? 'ON' : 'OFF'}`;
      this.btnToggleUv.style.color = this.isUvPinningActive ? '#c084fc' : '#f87171';
      this.btnToggleUv.style.borderColor = this.isUvPinningActive ? 'var(--accent-purple)' : '#f87171';
      this.hudUv.textContent = this.isUvPinningActive ? 'ACTIVE (<38 ms GEL)' : 'DISABLED (SAG RISK)';
      this.hudUv.className = `hud-val ${this.isUvPinningActive ? 'purple' : 'alert'}`;
    });
  }

  updateToolButtons(activeBtn) {
    ['btn-render-solid', 'btn-render-wire', 'btn-render-xray'].forEach(id => {
      document.getElementById(id).classList.remove('active');
    });
    activeBtn.classList.add('active');
  }
}

// Instantiate Studio Engine
window.addEventListener('DOMContentLoaded', () => {
  window.actuatorStudioApp = new ActuatorStudioApp();
});
