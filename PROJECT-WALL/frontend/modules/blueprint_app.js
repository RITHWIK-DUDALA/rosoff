/**
 * PROJECT W.A.L.L. — High-Fidelity Engineering Blueprint Suite Engine
 * Multi-Sheet 2D Technical Blueprints + Interactive 3D CAD Part Inspection
 */

// Custom Parametric Spring Curve for isolated 3D inspection
class HelixSpringCurve extends THREE.Curve {
  constructor(radius = 8.5, height = 34.0, coils = 7.5) {
    super();
    this.radius = radius;
    this.height = height;
    this.coils = coils;
  }
  getPoint(t) {
    const angle = 2.0 * Math.PI * this.coils * t;
    const x = this.radius * Math.cos(angle);
    const y = this.radius * Math.sin(angle);
    const z = this.height * (t - 0.5);
    return new THREE.Vector3(x, y, z);
  }
}

export class BlueprintApp {
  constructor() {
    this.activeSheet = '01';
    this.renderMode = 'solid'; // 'solid', 'wire', 'xray'
    this.theme = 'classic'; // 'classic' (blue) or 'graphite'

    // DOM Elements
    this.svgContentGroup = document.getElementById('sheet-content-group');
    this.tbTitle = document.getElementById('tb-drawing-title');
    this.tbNumber = document.getElementById('tb-drawing-number');
    this.tbMaterial = document.getElementById('tb-material');
    this.tbScale = document.getElementById('tb-scale');
    this.tbSheetNum = document.getElementById('tb-sheet-num');
    this.cadPartLabel = document.getElementById('cad-part-label');
    this.specMass = document.getElementById('spec-mass');
    this.specMat = document.getElementById('spec-mat');
    this.specFab = document.getElementById('spec-fab');
    this.specTol = document.getElementById('spec-tol');

    // 1. Initialize Interactive 3D CAD Viewport
    this.initThreeViewport();

    // 2. Setup Sheet Data Registry
    this.initSheetRegistry();

    // 3. Event Listeners
    this.initListeners();

    // 4. Render Sheet 01 initially
    this.loadSheet('01');
  }

  initThreeViewport() {
    const container = document.getElementById('cad-viewport-3d');
    this.width = container.clientWidth || 500;
    this.height = container.clientHeight || 450;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x071e36);

    // Camera
    this.camera = new THREE.PerspectiveCamera(35, this.width / this.height, 0.1, 5000);
    this.camera.position.set(120, 100, 160);

    // WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    container.appendChild(this.renderer.domElement);

    // Orbit Controls
    if (window.THREE && window.THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
    }

    // Lighting
    const amb = new THREE.AmbientLight(0xffffff, 0.85);
    this.scene.add(amb);

    const dir1 = new THREE.DirectionalLight(0xffffff, 0.9);
    dir1.position.set(150, 200, 250);
    this.scene.add(dir1);

    const dir2 = new THREE.DirectionalLight(0x93c5fd, 0.4);
    dir2.position.set(-150, -100, -100);
    this.scene.add(dir2);

    // CAD Model Container Group
    this.cadModelGroup = new THREE.Group();
    this.scene.add(this.cadModelGroup);

    // Coordinate Grid Helper
    this.gridHelper = new THREE.GridHelper(200, 20, 0x60a5fa, 0x1e3a5f);
    this.gridHelper.position.y = -40;
    this.scene.add(this.gridHelper);

    // Loop
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);

    window.addEventListener('resize', () => {
      if (!container) return;
      this.width = container.clientWidth || 500;
      this.height = container.clientHeight || 450;
      this.camera.aspect = this.width / this.height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(this.width, this.height);
    });
  }

  initSheetRegistry() {
    this.sheets = {
      '01': {
        title: 'CDPR FULL SYSTEM ASSEMBLY',
        number: 'DWG-WALL-CAD-000',
        material: '6061-T6 / UHMWPE / STRUCTURAL STEEL',
        scale: '1:10 FULL VIEW',
        sheet: 'SHEET 01 OF 08',
        label: '4-Cable CDPR Planar System',
        mass: '4.85 kg (Complete System)',
        mat: 'Aluminum 6061-T6 & Dyneema SK78',
        fab: 'Modular Assembly / Perimeter Mount',
        tol: '±0.50 mm (Anchor Coordinates)',
        stlFile: 'platform_chassis.stl',
        builder3D: () => this.build3DSystemAssembly(),
        svgDraw: () => this.drawSvgSheet01()
      },
      '02': {
        title: 'NEMA 17 WINCH STATION (A1..A4)',
        number: 'DWG-WALL-CAD-001',
        material: '17HS4401 / 6061-T6 / NITRILE',
        scale: '1:1 ORTHOGRAPHIC',
        sheet: 'SHEET 02 OF 08',
        label: 'Corner Winch Mechanism',
        mass: '0.52 kg (Single Station)',
        mat: 'Stator Steel & Die-Cast Aluminum',
        fab: 'CNC Turning & 3-Axis Milling',
        tol: '±0.02 mm (Shaft Bore / Bearing Fits)',
        stlFile: 'nema17_winch_bracket.stl',
        builder3D: () => this.build3DWinchStation(),
        svgDraw: () => this.drawSvgSheet02()
      },
      '03': {
        title: 'HELICAL GROOVED WINCH SPOOL DRUM',
        number: 'DWG-WALL-CAD-002',
        material: '6061-T6 ALUMINUM BILLET',
        scale: '2:1 DETAIL SECTION',
        sheet: 'SHEET 03 OF 08',
        label: 'Helical Cable Drum Spool',
        mass: '0.085 kg',
        mat: '6061-T6 / Ra 0.8 Helical Grooving',
        fab: 'CNC Lathe Threading + 4-Axis Mill',
        tol: '±0.015 mm (Groove Pitch 1.25mm)',
        stlFile: 'winch_drum.stl',
        builder3D: () => this.build3DDrum(),
        svgDraw: () => this.drawSvgSheet03()
      },
      '04': {
        title: 'SUSPENDED 2-DOF PLATFORM CHASSIS',
        number: 'DWG-WALL-CAD-003',
        material: '6061-T6 AIRCRAFT ALUMINUM',
        scale: '1:1 ORTHOGRAPHIC',
        sheet: 'SHEET 04 OF 08',
        label: '2-DOF Suspended Chassis',
        mass: '0.28 kg (Bare Pocketed Plate)',
        mat: '6061-T6 / Type II Anodized',
        fab: 'High-Speed CNC Pocketed Milling',
        tol: '±0.05 mm (Eyelet Bores 94x69mm)',
        stlFile: 'platform_chassis.stl',
        builder3D: () => this.build3DPlatform(),
        svgDraw: () => this.drawSvgSheet04()
      },
      '05': {
        title: '1.2N HELICAL COMPLIANCE SPRING',
        number: 'DWG-WALL-CAD-004',
        material: 'ASTM A228 MUSIC WIRE (SPRING STEEL)',
        scale: '5:1 DETAIL',
        sheet: 'SHEET 05 OF 08',
        label: '1.2N Standoff Compliance Spring',
        mass: '0.014 kg',
        mat: 'ASTM A228 / Shot-Peened & Tempered',
        fab: 'CNC Spring Coiling (Squared Ends)',
        tol: 'k = 0.141 ± 0.008 N/mm',
        stlFile: 'compliance_spring.stl',
        builder3D: () => this.build3DSpring(),
        svgDraw: () => this.drawSvgSheet05()
      },
      '06': {
        title: 'MODULE A: PIEZO INKJET PRINTHEAD',
        number: 'DWG-WALL-CAD-005',
        material: 'ANODIZED ALUM / SILICON / GOLD FPC',
        scale: '2:1 ELEVATION',
        sheet: 'SHEET 06 OF 08',
        label: '48-Nozzle Drop-on-Demand Printhead',
        mass: '0.125 kg',
        mat: 'Micro-Piezo Manifold & Gold FPC',
        fab: 'MEMS Silicon Etching + Precision EDM',
        tol: '±0.002 mm (21.5µm Nozzle Orifice)',
        stlFile: 'piezo_printhead.stl',
        builder3D: () => this.build3DPiezoModule(),
        svgDraw: () => this.drawSvgSheet06()
      },
      '07': {
        title: 'MODULE B: PAINT MARKER ACTUATOR',
        number: 'DWG-WALL-CAD-006',
        material: '6061-T6 / ACRYLIC NIB / OMRON D2F',
        scale: '1:1 ELEVATION',
        sheet: 'SHEET 07 OF 08',
        label: 'Spring-Compliant Marker Clamp',
        mass: '0.110 kg',
        mat: 'Machined Aluminum Split Collet',
        fab: 'CNC Turning & Thread Milling',
        tol: '±0.05 mm (Marker Barrel Fit)',
        stlFile: 'paint_marker_sleeve.stl',
        builder3D: () => this.build3DMarkerModule(),
        svgDraw: () => this.drawSvgSheet07()
      },
      '08': {
        title: 'ELECTRICAL & UMBILICAL SCHEMATIC',
        number: 'DWG-WALL-CAD-007',
        material: 'SHIELDED COPPER / PTFE TUBING',
        scale: 'SCHEMATIC 1:1',
        sheet: 'SHEET 08 OF 08',
        label: 'Multi-Line Umbilical Drag Harness',
        mass: '0.24 kg / meter',
        mat: 'High-Flex Silicone & PTFE Chemical Line',
        fab: 'Braided Multi-Conductor Loom',
        tol: '26-Pin FPC + 16-Lead Stepper/Encoder',
        stlFile: 'platform_chassis.stl',
        builder3D: () => this.build3DUmbilical(),
        svgDraw: () => this.drawSvgSheet08()
      },
      '09': {
        title: 'HYPER-ACTUATOR MK-1: ACTIVE SURFACE-FOLLOWING UV-PIEZO ENGINE',
        number: 'DWG-WALL-HACT-000',
        material: '6061-T6 / MEMS SILICON / N52 VCA / FUSED QUARTZ',
        scale: '1:1 FULL ELEVATION',
        sheet: 'SHEET 09 OF 09 (INNOVATION)',
        label: 'Non-Contact Dual-Stage Active Standoff & In-Situ UV Curing',
        mass: '0.42 kg (Complete Mechatronic Engine)',
        mat: 'Skeletonized 6061-T6, Carbon Fiber & Delrin',
        fab: '5-Axis Micro-CNC & Precision Micro-Molding',
        tol: '±0.005 mm (VCA Guideway & Standoff Precision)',
        stlFile: 'novel_actuator/hyper_actuator_assembly.stl',
        builder3D: () => this.build3DHyperActuator(),
        svgDraw: () => this.drawSvgSheet09()
      }
    };
  }

  loadSheet(sheetId) {
    this.activeSheet = sheetId;
    const cfg = this.sheets[sheetId];
    if (!cfg) return;

    // Update Download STL Link
    const dlBtn = document.getElementById('btn-cad-download-stl');
    if (dlBtn && cfg.stlFile) {
      dlBtn.href = `exports/${cfg.stlFile}`;
      dlBtn.download = cfg.stlFile;
      dlBtn.style.display = 'inline-block';
    }

    // 1. Update Title Block Metadata
    this.tbTitle.textContent = cfg.title;
    this.tbNumber.textContent = cfg.number;
    this.tbMaterial.textContent = cfg.material;
    this.tbScale.textContent = cfg.scale;
    this.tbSheetNum.textContent = cfg.sheet;

    // 2. Update Spec Card
    this.cadPartLabel.textContent = cfg.label;
    this.specMass.textContent = cfg.mass;
    this.specMat.textContent = cfg.mat;
    this.specFab.textContent = cfg.fab;
    this.specTol.textContent = cfg.tol;

    // 3. Update Sheet Navigation UI Tabs
    document.querySelectorAll('.sheet-tab').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-sheet') === sheetId);
    });

    // 4. Render 2D SVG Blueprint
    this.svgContentGroup.innerHTML = '';
    cfg.svgDraw();

    // 5. Build Isolated 3D CAD Model
    this.clear3DModel();
    cfg.builder3D();
    this.applyRenderMode();
  }

  clear3DModel() {
    while (this.cadModelGroup.children.length > 0) {
      const obj = this.cadModelGroup.children[0];
      this.cadModelGroup.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
        else obj.material.dispose();
      }
    }
  }

  setTheme(themeName) {
    this.theme = themeName;
    document.body.className = (themeName === 'classic') ? 'blueprint-theme-classic' : 'blueprint-theme-graphite';
    const bgColor = (themeName === 'classic') ? 0x071e36 : 0x0b0d12;
    this.scene.background.setHex(bgColor);
    const gridColor = (themeName === 'classic') ? 0x60a5fa : 0xf59e0b;
    const gridDiv = (themeName === 'classic') ? 0x1e3a5f : 0x22262e;
    this.gridHelper.material.color.setHex(gridColor);
    this.gridHelper.material.opacity = 0.4;
  }

  setRenderMode(mode) {
    this.renderMode = mode;
    this.applyRenderMode();
    document.getElementById('btn-cad-solid').classList.toggle('active', mode === 'solid');
    document.getElementById('btn-cad-wire').classList.toggle('active', mode === 'wire');
    document.getElementById('btn-cad-xray').classList.toggle('active', mode === 'xray');
  }

  applyRenderMode() {
    this.cadModelGroup.traverse(child => {
      if (child.isMesh && child.material) {
        if (this.renderMode === 'wire') {
          child.material.wireframe = true;
          child.material.transparent = false;
          child.material.opacity = 1.0;
        } else if (this.renderMode === 'xray') {
          child.material.wireframe = false;
          child.material.transparent = true;
          child.material.opacity = 0.38;
        } else {
          child.material.wireframe = false;
          child.material.transparent = false;
          child.material.opacity = 1.0;
        }
      }
    });
  }

  initListeners() {
    // Sheet tabs
    document.querySelectorAll('.sheet-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const sid = tab.getAttribute('data-sheet');
        this.loadSheet(sid);
      });
    });

    // Theme toggles
    document.getElementById('btn-theme-cyan').addEventListener('click', () => {
      document.getElementById('btn-theme-cyan').classList.add('active');
      document.getElementById('btn-theme-dark').classList.remove('active');
      this.setTheme('classic');
    });

    document.getElementById('btn-theme-dark').addEventListener('click', () => {
      document.getElementById('btn-theme-dark').classList.add('active');
      document.getElementById('btn-theme-cyan').classList.remove('active');
      this.setTheme('graphite');
    });

    // 3D Render modes
    document.getElementById('btn-cad-solid').addEventListener('click', () => this.setRenderMode('solid'));
    document.getElementById('btn-cad-wire').addEventListener('click', () => this.setRenderMode('wire'));
    document.getElementById('btn-cad-xray').addEventListener('click', () => this.setRenderMode('xray'));
    document.getElementById('btn-cad-reset').addEventListener('click', () => {
      this.camera.position.set(120, 100, 160);
      if (this.controls) this.controls.target.set(0, 0, 0);
    });
  }

  animate() {
    requestAnimationFrame(this.animate);
    if (this.controls) this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  /* =========================================================================
     3D ISOLATED CAD MODEL BUILDERS (Parametric Mesh Assembly)
     ========================================================================= */

  // CAD Helper: DIN 912 / ISO 4762 Socket Head Cap Screw
  createSocketHeadCapScrew(headDia = 5.5, headH = 3.0, hexSize = 2.5, shankLen = 6.0) {
    const group = new THREE.Group();
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.12 });
    const hexMat = new THREE.MeshBasicMaterial({ color: 0x0a0a0c });

    const head = new THREE.Mesh(new THREE.CylinderGeometry(headDia / 2, headDia / 2, headH, 20), steel);
    head.rotation.x = Math.PI / 2;
    group.add(head);

    const hex = new THREE.Mesh(new THREE.CylinderGeometry(hexSize / 2, hexSize / 2, 0.4, 6), hexMat);
    hex.rotation.x = Math.PI / 2;
    hex.position.z = headH / 2 + 0.05;
    group.add(hex);

    if (shankLen > 0) {
      const shank = new THREE.Mesh(new THREE.CylinderGeometry(headDia * 0.55 / 2, headDia * 0.55 / 2, shankLen, 16), steel);
      shank.rotation.x = Math.PI / 2;
      shank.position.z = -shankLen / 2;
      group.add(shank);
    }
    return group;
  }

  // CAD Helper: F688ZZ Flanged Ball Bearing
  createFlangedBearing(id = 8.0, od = 16.0, flangeOd = 18.0, width = 5.0) {
    const group = new THREE.Group();
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.12 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x242830, metalness: 0.8, roughness: 0.3 });

    const outer = new THREE.Mesh(new THREE.CylinderGeometry(od / 2, od / 2, width, 32), steel);
    outer.rotation.x = Math.PI / 2;
    group.add(outer);

    const flange = new THREE.Mesh(new THREE.CylinderGeometry(flangeOd / 2, flangeOd / 2, 1.0, 32), steel);
    flange.rotation.x = Math.PI / 2;
    flange.position.z = -width / 2 + 0.5;
    group.add(flange);

    const inner = new THREE.Mesh(new THREE.CylinderGeometry(id / 2 + 1.2, id / 2 + 1.2, width + 0.2, 24), steel);
    inner.rotation.x = Math.PI / 2;
    group.add(inner);

    const shield = new THREE.Mesh(new THREE.RingGeometry(id / 2 + 1.4, od / 2 - 1.0, 24), dark);
    shield.position.z = width / 2 + 0.05;
    group.add(shield);

    return group;
  }

  // CAD Helper: Heim Joint / Spherical Rod End (PHS4)
  createSphericalRodEnd(ballDia = 8.0, boreDia = 4.0, shankLen = 14.0) {
    const group = new THREE.Group();
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.12 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x242830, metalness: 0.8, roughness: 0.3 });

    const eye = new THREE.Mesh(new THREE.CylinderGeometry(ballDia / 2 + 2.5, ballDia / 2 + 2.5, 5.0, 24), dark);
    eye.rotation.x = Math.PI / 2;
    group.add(eye);

    const ball = new THREE.Mesh(new THREE.SphereGeometry(ballDia / 2, 24, 24), steel);
    group.add(ball);

    const bore = new THREE.Mesh(new THREE.CylinderGeometry(boreDia / 2, boreDia / 2, 6.2, 16), steel);
    bore.rotation.x = Math.PI / 2;
    group.add(bore);

    const shank = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, shankLen, 16), steel);
    shank.position.y = -shankLen / 2 - ballDia / 2 + 1.0;
    group.add(shank);

    return group;
  }

  build3DSystemAssembly() {
    this.camera.position.set(0, 50, 480);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const alum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.85, roughness: 0.25 });
    const steel = new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.95, roughness: 0.15 });
    const board = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 });

    // Surface Board (800 x 600 mm scaled down for viewport)
    const bMesh = new THREE.Mesh(new THREE.BoxGeometry(240, 180, 4), board);
    this.cadModelGroup.add(bMesh);

    // 4 Corner Winches
    const wGeo = new THREE.BoxGeometry(22, 22, 18);
    [[-120, 90], [120, 90], [-120, -90], [120, -90]].forEach(([wx, wy]) => {
      const wm = new THREE.Mesh(wGeo, alum);
      wm.position.set(wx, wy, 8);
      this.cadModelGroup.add(wm);
    });

    // Central Platform
    const pMesh = new THREE.Mesh(new THREE.BoxGeometry(38, 30, 4), alum);
    pMesh.position.set(0, 0, 8);
    this.cadModelGroup.add(pMesh);

    // 4 Cables
    [[-120, 90, -19, 15], [120, 90, 19, 15], [-120, -90, -19, -15], [120, -90, 19, -15]].forEach(([x1, y1, x2, y2]) => {
      const pts = [new THREE.Vector3(x1, y1, 8), new THREE.Vector3(x2, y2, 8)];
      const cGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const cLine = new THREE.Line(cGeo, new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 }));
      this.cadModelGroup.add(cLine);
    });
  }

  build3DWinchStation() {
    this.camera.position.set(65, 55, 85);
    if (this.controls) this.controls.target.set(0, 0, 10);

    const darkAlum = new THREE.MeshStandardMaterial({ color: 0x1b1f24, metalness: 0.82, roughness: 0.32 });
    const silverAlum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.88, roughness: 0.24 });
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.12 });
    const brass = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.92, roughness: 0.22 });

    // Mounting L-Plate (75x75x6 mm 6061-T6)
    const base = new THREE.Mesh(new THREE.BoxGeometry(75, 75, 6), darkAlum);
    base.position.set(0, 0, -8);
    this.cadModelGroup.add(base);

    // 4x Counterbored Corner Mounting Screws (M5 DIN 912)
    [[-28, -28], [28, -28], [-28, 28], [28, 28]].forEach(([hx, hy]) => {
      const screw = this.createSocketHeadCapScrew(8.5, 4.0, 4.0, 10.0);
      screw.position.set(hx, hy, -7);
      this.cadModelGroup.add(screw);
    });

    // 2x Suction Cups with Brass Barbs
    [-22, 22].forEach(cx => {
      const cup = new THREE.Mesh(new THREE.CylinderGeometry(18, 22, 8, 24), darkAlum);
      cup.rotation.x = Math.PI / 2;
      cup.position.set(cx, 0, -15);
      this.cadModelGroup.add(cup);

      const barb = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 8, 16), brass);
      barb.rotation.x = Math.PI / 2;
      barb.position.set(cx, 0, -22);
      this.cadModelGroup.add(barb);
    });

    // 8-Sided Chamfered Stator Body (Stacked Silicon Steel Laminations)
    const statorShape = new THREE.Shape();
    const halfW = 21.15;
    const ch = 4.0;
    statorShape.moveTo(-halfW + ch, -halfW);
    statorShape.lineTo( halfW - ch, -halfW);
    statorShape.lineTo( halfW, -halfW + ch);
    statorShape.lineTo( halfW,  halfW - ch);
    statorShape.lineTo( halfW - ch,  halfW);
    statorShape.lineTo(-halfW + ch,  halfW);
    statorShape.lineTo(-halfW,  halfW - ch);
    statorShape.lineTo(-halfW, -halfW + ch);
    statorShape.closePath();

    const extrudeSettings = { depth: 34, bevelEnabled: false };
    const statorGeo = new THREE.ExtrudeGeometry(statorShape, extrudeSettings);
    statorGeo.translate(0, 0, -17);
    const stator = new THREE.Mesh(statorGeo, new THREE.MeshStandardMaterial({ color: 0x16181d, metalness: 0.75, roughness: 0.45 }));
    stator.position.set(0, 0, 10);
    this.cadModelGroup.add(stator);

    // Front & Rear Die-Cast Plates
    const fPlate = new THREE.Mesh(new THREE.BoxGeometry(42.3, 42.3, 4), silverAlum);
    fPlate.position.set(0, 0, 29);
    this.cadModelGroup.add(fPlate);

    const pilotBoss = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 2.5, 32), silverAlum);
    pilotBoss.rotation.x = Math.PI / 2;
    pilotBoss.position.set(0, 0, 31.5);
    this.cadModelGroup.add(pilotBoss);

    const rPlate = new THREE.Mesh(new THREE.BoxGeometry(42.3, 42.3, 4), silverAlum);
    rPlate.position.set(0, 0, -9);
    this.cadModelGroup.add(rPlate);

    // 4 Corner M3 Hex Socket Assembly Tie Screws (DIN 912)
    [[-15.5, -15.5], [15.5, -15.5], [-15.5, 15.5], [15.5, 15.5]].forEach(([sx, sy]) => {
      const screw = this.createSocketHeadCapScrew(5.2, 2.8, 2.5, 4.0);
      screw.position.set(sx, sy, 31.0);
      this.cadModelGroup.add(screw);
    });

    // 4-Wire Stepper Harness (Red, Green, Yellow, Black)
    const wCols = [0xef4444, 0x10b981, 0xf59e0b, 0x050505];
    [-4.5, -1.5, 1.5, 4.5].forEach((wx, i) => {
      const wire = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 24, 8), new THREE.MeshBasicMaterial({ color: wCols[i] }));
      wire.rotation.x = Math.PI / 2;
      wire.position.set(wx, -22, -20);
      this.cadModelGroup.add(wire);
    });

    // 5mm Shaft & Beam Coupler
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 26, 20), steel);
    shaft.rotation.x = Math.PI / 2;
    shaft.position.set(0, 0, 42);
    this.cadModelGroup.add(shaft);

    const coupler = new THREE.Mesh(new THREE.CylinderGeometry(9.5, 9.5, 20, 24), silverAlum);
    coupler.rotation.x = Math.PI / 2;
    coupler.position.set(0, 0, 52);
    this.cadModelGroup.add(coupler);

    // Helical Winch Drum
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, 22, 32), silverAlum);
    drum.rotation.x = Math.PI / 2;
    drum.position.set(0, 0, 76);
    this.cadModelGroup.add(drum);

    const flange1 = new THREE.Mesh(new THREE.CylinderGeometry(22, 22, 2.5, 32), silverAlum);
    flange1.rotation.x = Math.PI / 2;
    flange1.position.set(0, 0, 64);
    this.cadModelGroup.add(flange1);

    const flange2 = new THREE.Mesh(new THREE.CylinderGeometry(22, 22, 2.5, 32), silverAlum);
    flange2.rotation.x = Math.PI / 2;
    flange2.position.set(0, 0, 88);
    this.cadModelGroup.add(flange2);

    // Dual F688ZZ Flanged Ball Bearings
    const b1 = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
    b1.position.set(0, 0, 60);
    this.cadModelGroup.add(b1);

    const b2 = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
    b2.position.set(0, 0, 94);
    this.cadModelGroup.add(b2);

    // Fairlead Brass Roller
    const pulley = new THREE.Mesh(new THREE.CylinderGeometry(6.5, 6.5, 8, 24), brass);
    pulley.rotation.x = Math.PI / 2;
    pulley.position.set(18, 18, 76);
    this.cadModelGroup.add(pulley);
  }

  build3DDrum() {
    this.camera.position.set(40, 35, 60);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const alum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 });

    // Drum Barrel
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, 22, 48), alum);
    this.cadModelGroup.add(barrel);

    // Flanges with 6 Lightening Holes
    [-11, 11].forEach(fz => {
      const flange = new THREE.Mesh(new THREE.CylinderGeometry(22, 22, 2.5, 48), alum);
      flange.position.y = fz;
      this.cadModelGroup.add(flange);
    });

    // Dual F688ZZ Flanged Bearings on both ends
    const b1 = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
    b1.rotation.y = Math.PI / 2;
    b1.position.y = -13;
    this.cadModelGroup.add(b1);

    const b2 = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
    b2.rotation.y = Math.PI / 2;
    b2.position.y = 13;
    this.cadModelGroup.add(b2);
  }

  build3DPlatform() {
    this.camera.position.set(90, 70, 110);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const alum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.88, roughness: 0.25 });
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.15 });

    // 110x85x8 mm CNC Pocketed Chassis Plate
    const plate = new THREE.Mesh(new THREE.BoxGeometry(110, 85, 8), alum);
    this.cadModelGroup.add(plate);

    // 4 Corner Swiveling Heim Joint Spherical Rod Ends (B1..B4)
    [[-47, 34.5], [47, 34.5], [-47, -34.5], [47, -34.5]].forEach(([ex, ey]) => {
      const rodEnd = this.createSphericalRodEnd(8.0, 4.0, 12.0);
      rodEnd.position.set(ex, ey, 5);
      this.cadModelGroup.add(rodEnd);
    });

    // 3 POM Ball Transfer Units
    [[-42, 0], [42, 28], [42, -28]].forEach(([bx, by]) => {
      const ball = new THREE.Mesh(new THREE.SphereGeometry(4.5, 20, 20), steel);
      ball.position.set(bx, by, -5);
      this.cadModelGroup.add(ball);
    });

    // Dual 4mm Ground Guide Rods
    [-18, 18].forEach(gx => {
      const rod = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 44, 20), steel);
      rod.position.set(gx, 0, 16);
      this.cadModelGroup.add(rod);
    });
  }

  build3DSpring() {
    this.camera.position.set(30, 25, 45);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const springMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.92, roughness: 0.18 });
    const curve = new HelixSpringCurve(8.5, 34.0, 7.5);
    const geo = new THREE.TubeGeometry(curve, 120, 1.6, 14, false);
    const springMesh = new THREE.Mesh(geo, springMat);
    this.cadModelGroup.add(springMesh);

    // Ground Flat End Rings
    const ringMat = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.9, roughness: 0.2 });
    [-17, 17].forEach(zy => {
      const endRing = new THREE.Mesh(new THREE.TorusGeometry(8.5, 1.6, 16, 32), ringMat);
      endRing.rotation.x = Math.PI / 2;
      endRing.position.z = zy;
      this.cadModelGroup.add(endRing);
    });
  }

  build3DPiezoModule() {
    this.camera.position.set(35, 30, 50);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const dark = new THREE.MeshStandardMaterial({ color: 0x1b1f24, metalness: 0.8, roughness: 0.3 });
    const steel = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.95, roughness: 0.1 });
    const gold = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.6, roughness: 0.3 });

    // Printhead Manifold Body
    const body = new THREE.Mesh(new THREE.BoxGeometry(26, 30, 36), dark);
    this.cadModelGroup.add(body);

    // Silicon Orifice Plate with 48 Micro-Nozzles
    const plate = new THREE.Mesh(new THREE.BoxGeometry(18, 22, 2), steel);
    plate.position.set(0, 0, -19);
    this.cadModelGroup.add(plate);

    // 26-Pin FPC Gold Flex Ribbon
    const fpc = new THREE.Mesh(new THREE.BoxGeometry(16, 1, 40), gold);
    fpc.position.set(0, 16, 8);
    this.cadModelGroup.add(fpc);

    // Dual PTFE Luer Lock Tubes
    [-6, 6].forEach(tx => {
      const tube = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 24, 16), steel);
      tube.position.set(tx, -12, 24);
      this.cadModelGroup.add(tube);
    });
  }

  build3DMarkerModule() {
    this.camera.position.set(40, 35, 55);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const alum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.88, roughness: 0.25 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x181a1f, roughness: 0.8 });
    const nibMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.9 });
    const brass = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.9, roughness: 0.2 });

    // Marker Sleeve Clamp
    const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 32, 32), alum);
    this.cadModelGroup.add(sleeve);

    // Knurled Locking Ring
    const ring = new THREE.Mesh(new THREE.CylinderGeometry(13, 13, 6, 24), brass);
    ring.position.y = 8;
    this.cadModelGroup.add(ring);

    // Marker Body
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(8.5, 8.5, 48, 32), dark);
    barrel.position.y = -6;
    this.cadModelGroup.add(barrel);

    // 6mm Chisel Felt Nib
    const nib = new THREE.Mesh(new THREE.BoxGeometry(6, 4, 12), nibMat);
    nib.position.y = -34;
    this.cadModelGroup.add(nib);
  }

  build3DUmbilical() {
    this.camera.position.set(60, 45, 75);
    if (this.controls) this.controls.target.set(0, 0, 0);

    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(-40, -30, 0),
      new THREE.Vector3(0, 45, 20),
      new THREE.Vector3(40, -30, 0)
    );
    const geo = new THREE.TubeGeometry(curve, 32, 4.2, 16, false);
    const mat = new THREE.MeshStandardMaterial({ color: 0x1b1f24, roughness: 0.85 });
    const mesh = new THREE.Mesh(geo, mat);
    this.cadModelGroup.add(mesh);

    // Aluminum Strain Relief Bracket
    const alum = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 });
    const bracket = new THREE.Mesh(new THREE.BoxGeometry(18, 14, 10), alum);
    bracket.position.set(-40, -30, 0);
    this.cadModelGroup.add(bracket);
  }

  /* =========================================================================
     2D VECTOR BLUEPRINT DRAWING PROCEDURES (Exact Dimensions & Leaders)
     ========================================================================= */

  drawSvgSheet01() {
    // Sheet 01: Full CDPR System Assembly
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 01 &bull; 4-CABLE CDPR UNIVERSAL PLANAR SYSTEM ASSEMBLY</text>
      
      <!-- Surface Board Envelope (800 x 600 mm Scaled: 640 x 480 px) -->
      <rect x="180" y="100" width="640" height="480" class="outline-solid"/>
      
      <!-- Printable Margin Line (100mm Margin Scaled: 80px) -->
      <rect x="260" y="180" width="480" height="320" class="outline-hidden"/>
      <text x="500" y="200" class="callout-text" text-anchor="middle">PRINTABLE BOUNDARY (600 x 400 mm / 100mm MARGIN)</text>
      
      <!-- 4 Corner Winch Mechanisms (A1..A4) -->
      <rect x="140" y="60" width="40" height="40" class="outline-solid"/>
      <circle cx="160" cy="80" r="14" class="outline-detail"/>
      <text x="110" y="85" class="callout-text">A1 (UL)</text>

      <rect x="820" y="60" width="40" height="40" class="outline-solid"/>
      <circle cx="840" cy="80" r="14" class="outline-detail"/>
      <text x="870" y="85" class="callout-text">A2 (UR)</text>

      <rect x="140" y="580" width="40" height="40" class="outline-solid"/>
      <circle cx="160" cy="600" r="14" class="outline-detail"/>
      <text x="110" y="605" class="callout-text">A3 (LL)</text>

      <rect x="820" y="580" width="40" height="40" class="outline-solid"/>
      <circle cx="840" cy="600" r="14" class="outline-detail"/>
      <text x="870" y="605" class="callout-text">A4 (LR)</text>

      <!-- Central End-Effector Platform (110 x 85 mm Scaled: 88 x 68 px) -->
      <rect x="456" y="306" width="88" height="68" rx="6" class="outline-solid"/>
      <circle cx="500" cy="340" r="14" class="outline-detail"/>
      <circle cx="500" cy="340" r="3" class="outline-solid"/>
      <text x="500" y="325" class="callout-text" text-anchor="middle">B0 (CENTER)</text>

      <!-- 4 Cables C1..C4 with Tension Vectors -->
      <line x1="160" y1="80" x2="466" y2="316" class="outline-solid"/>
      <line x1="840" y1="80" x2="534" y2="316" class="outline-solid"/>
      <line x1="160" y1="600" x2="466" y2="364" class="outline-solid"/>
      <line x1="840" y1="600" x2="534" y2="364" class="outline-solid"/>

      <!-- Cable Callout Labels -->
      <text x="290" y="170" class="callout-text">CABLE C1 (T1 = 18.2 N)</text>
      <text x="710" y="170" class="callout-text">CABLE C2 (T2 = 18.2 N)</text>
      <text x="290" y="510" class="callout-text">CABLE C3 (T3 = 14.5 N)</text>
      <text x="710" y="510" class="callout-text">CABLE C4 (T4 = 14.5 N)</text>

      <!-- Overall Board Dimensions -->
      <!-- Width Dimension: 800 mm -->
      <line x1="180" y1="90" x2="180" y2="40" class="dim-extension"/>
      <line x1="820" y1="90" x2="820" y2="40" class="dim-extension"/>
      <line x1="180" y1="45" x2="820" y2="45" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
      <text x="500" y="40" class="dim-text">800.00 mm (W_WALL)</text>

      <!-- Height Dimension: 600 mm -->
      <line x1="830" y1="100" x2="890" y2="100" class="dim-extension"/>
      <line x1="830" y1="580" x2="890" y2="580" class="dim-extension"/>
      <line x1="880" y1="100" x2="880" y2="580" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
      <text x="895" y="345" class="dim-text-vert" transform="rotate(90, 895, 345)">600.00 mm (H_WALL)</text>

      <!-- Kinematic Centerlines -->
      <line x1="500" y1="90" x2="500" y2="590" class="outline-center"/>
      <line x1="170" y1="340" x2="830" y2="340" class="outline-center"/>
    `;
  }

  drawSvgSheet02() {
    // Sheet 02: NEMA 17 Winch Station
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 02 &bull; NEMA 17 MOTOR WINCH ASSEMBLY & CORNER MOUNT</text>

      <!-- VIEW A: FRONT ELEVATION -->
      <g transform="translate(100, 120)">
        <text x="80" y="-15" class="callout-text" text-anchor="middle">FRONT ELEVATION &bull; SCALE 1:1</text>
        <!-- Motor 42.3 x 42.3 mm Stator (Scale 3.5x: 148 x 148 px) -->
        <rect x="0" y="0" width="148" height="148" class="outline-solid"/>
        <!-- Flutes -->
        <line x1="25" y1="0" x2="25" y2="148" class="outline-detail"/>
        <line x1="50" y1="0" x2="50" y2="148" class="outline-detail"/>
        <line x1="98" y1="0" x2="98" y2="148" class="outline-detail"/>
        <line x1="123" y1="0" x2="123" y2="148" class="outline-detail"/>
        <!-- Pilot Boss Collar Dia 22mm (77 px) -->
        <circle cx="74" cy="74" r="38.5" class="outline-detail"/>
        <!-- 4x M3 Corner Screw Holes at PCD 31mm (108 px) -->
        <circle cx="74" cy="74" r="54" class="outline-center"/>
        <circle cx="36" cy="36" r="5" class="outline-solid"/>
        <circle cx="112" cy="36" r="5" class="outline-solid"/>
        <circle cx="36" cy="112" r="5" class="outline-solid"/>
        <circle cx="112" cy="112" r="5" class="outline-solid"/>
        <!-- 5mm D-Shaft (17.5 px) -->
        <circle cx="74" cy="74" r="8.75" class="outline-solid"/>

        <!-- Dimensions -->
        <line x1="0" y1="-5" x2="0" y2="-25" class="dim-extension"/>
        <line x1="148" y1="-5" x2="148" y2="-25" class="dim-extension"/>
        <line x1="0" y1="-20" x2="148" y2="-20" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="74" y="-25" class="dim-text">42.30 &plusmn; 0.10 mm</text>

        <!-- PCD Dimension Leader -->
        <path d="M 112 36 L 150 15 L 180 15" class="callout-leader"/>
        <text x="185" y="18" class="callout-text">4x M3 &times; 0.5 PCD 31.0 mm</text>

        <!-- Centerline -->
        <line x1="-15" y1="74" x2="163" y2="74" class="outline-center"/>
        <line x1="74" y1="-15" x2="74" y2="163" class="outline-center"/>
      </g>

      <!-- VIEW B: SIDE SECTION / CABLE DRUM & BEARINGS -->
      <g transform="translate(390, 120)">
        <text x="110" y="-15" class="callout-text" text-anchor="middle">SIDE SECTION &bull; TRANSMISSION STACK</text>
        <!-- Motor Stator Depth: 40mm (140 px) -->
        <rect x="0" y="0" width="140" height="148" class="outline-solid"/>
        <!-- Front Flange: 4mm (14 px) -->
        <rect x="140" y="0" width="14" height="148" class="outline-detail"/>
        <!-- Shaft Coupler (19mm OD, 25mm length: 66 x 87 px) -->
        <rect x="154" y="41" width="87" height="66" class="outline-solid"/>
        <!-- Helical Drum (Dia 28mm root, 44mm flange, 22mm width) -->
        <rect x="241" y="22" width="77" height="104" class="outline-solid"/>
        <rect x="241" y="50" width="77" height="48" class="outline-detail"/>
        <!-- Dyneema Cable Wound Coils -->
        <line x1="248" y1="50" x2="311" y2="50" class="outline-hidden"/>
        <line x1="248" y1="98" x2="311" y2="98" class="outline-hidden"/>
        <!-- Bearing F688ZZ Rings -->
        <rect x="235" y="46" width="14" height="56" class="outline-detail"/>
        <rect x="318" y="46" width="14" height="56" class="outline-detail"/>

        <!-- Length Dimensions -->
        <line x1="0" y1="160" x2="0" y2="185" class="dim-extension"/>
        <line x1="140" y1="160" x2="140" y2="185" class="dim-extension"/>
        <line x1="0" y1="180" x2="140" y2="180" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="70" y="195" class="dim-text">40.00 mm (BODY)</text>

        <line x1="140" y1="160" x2="140" y2="215" class="dim-extension"/>
        <line x1="332" y1="160" x2="332" y2="215" class="dim-extension"/>
        <line x1="140" y1="210" x2="332" y2="210" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="236" y="225" class="dim-text">55.00 mm (SPOOL STACK)</text>
      </g>

      <!-- ELECTRICAL 4-LEAD HARNESS WIRING CALLOUT -->
      <g transform="translate(100, 380)">
        <rect x="0" y="0" width="560" height="150" class="outline-detail"/>
        <text x="20" y="25" class="callout-text" font-weight="bold">STEPPER MOTOR ELECTRICAL PINOUT (JST-XH 4-PIN CONNECTOR):</text>
        <text x="30" y="55" class="callout-text">PIN 1 &bull; RED WIRE: PHASE B+ (TMC2209 B1 TERMINAL)</text>
        <text x="30" y="80" class="callout-text">PIN 2 &bull; BLUE/YELLOW WIRE: PHASE B- (TMC2209 B2 TERMINAL)</text>
        <text x="30" y="105" class="callout-text">PIN 3 &bull; GREEN WIRE: PHASE A- (TMC2209 A2 TERMINAL)</text>
        <text x="30" y="130" class="callout-text">PIN 4 &bull; BLACK WIRE: PHASE A+ (TMC2209 A1 TERMINAL)</text>

        <!-- Wiring Diagram Graphic -->
        <circle cx="480" cy="50" r="8" fill="#ef4444"/>
        <circle cx="480" cy="75" r="8" fill="#3b82f6"/>
        <circle cx="480" cy="100" r="8" fill="#10b981"/>
        <circle cx="480" cy="125" r="8" fill="#000000"/>
      </g>
    `;
  }

  drawSvgSheet03() {
    // Sheet 03: Helical Grooved Winch Drum Spool
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 03 &bull; HELICAL GROOVED WINCH SPOOL DRUM (DWG-WALL-CAD-002)</text>

      <!-- SECTION A-A CROSS-SECTION (Scale 5x) -->
      <g transform="translate(180, 160)">
        <text x="180" y="-30" class="callout-text" text-anchor="middle">SECTION A-A &bull; CABLE GROOVE GEOMETRY</text>

        <!-- Main Spool Profile (w_total = 27mm: 270px, d_flange = 44mm: 220px, d_root = 28mm: 140px) -->
        <rect x="0" y="0" width="270" height="220" class="outline-solid"/>
        <!-- Flange Thickness 2.5mm (25px) -->
        <line x1="25" y1="0" x2="25" y2="40" class="outline-solid"/>
        <line x1="25" y1="180" x2="25" y2="220" class="outline-solid"/>
        <line x1="245" y1="0" x2="245" y2="40" class="outline-solid"/>
        <line x1="245" y1="180" x2="245" y2="220" class="outline-solid"/>

        <!-- Root Barrel (220px width x 140px height) -->
        <rect x="25" y="40" width="220" height="140" class="outline-detail"/>

        <!-- Helical Grooves (pitch = 1.25mm: 12.5px, rg = 0.65mm) -->
        <g class="outline-detail">
          <path d="M 35 40 A 6.5 6.5 0 0 1 48 40 A 6.5 6.5 0 0 1 61 40 A 6.5 6.5 0 0 1 74 40 A 6.5 6.5 0 0 1 87 40 A 6.5 6.5 0 0 1 100 40 A 6.5 6.5 0 0 1 113 40 A 6.5 6.5 0 0 1 126 40 A 6.5 6.5 0 0 1 139 40 A 6.5 6.5 0 0 1 152 40 A 6.5 6.5 0 0 1 165 40 A 6.5 6.5 0 0 1 178 40 A 6.5 6.5 0 0 1 191 40 A 6.5 6.5 0 0 1 204 40 A 6.5 6.5 0 0 1 217 40 A 6.5 6.5 0 0 1 230 40"/>
        </g>

        <!-- 8mm Shaft Bore Through Center (40px height) -->
        <rect x="0" y="90" width="270" height="40" class="outline-hidden"/>

        <!-- F688ZZ Bearing Counterbores (16mm OD: 80px, 4mm depth: 40px) -->
        <rect x="0" y="70" width="40" height="80" class="outline-solid"/>
        <rect x="230" y="70" width="40" height="80" class="outline-solid"/>

        <!-- Dimensions -->
        <!-- Flange Outer Diameter -->
        <line x1="-10" y1="0" x2="-35" y2="0" class="dim-extension"/>
        <line x1="-10" y1="220" x2="-35" y2="220" class="dim-extension"/>
        <line x1="-30" y1="0" x2="-30" y2="220" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="-40" y="115" class="dim-text-vert" transform="rotate(-90, -40, 115)">&Oslash; 44.00 &plusmn; 0.05 mm (D_FLANGE)</text>

        <!-- Root Diameter -->
        <line x1="280" y1="40" x2="310" y2="40" class="dim-extension"/>
        <line x1="280" y1="180" x2="310" y2="180" class="dim-extension"/>
        <line x1="305" y1="40" x2="305" y2="180" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="325" y="115" class="dim-text-vert" transform="rotate(90, 325, 115)">&Oslash; 28.00 &plusmn; 0.02 mm (D_ROOT)</text>

        <!-- Spool Width -->
        <line x1="25" y1="230" x2="25" y2="260" class="dim-extension"/>
        <line x1="245" y1="230" x2="245" y2="260" class="dim-extension"/>
        <line x1="25" y1="255" x2="245" y2="255" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="135" y="275" class="dim-text">22.00 mm (SPOOL WIDTH)</text>

        <!-- Helical Pitch Callout -->
        <path d="M 61 40 L 90 -10 L 140 -10" class="callout-leader"/>
        <text x="145" y="-7" class="callout-text">HELICAL GROOVE: PITCH = 1.25 mm &bull; r_g = 0.65 mm</text>
      </g>
    `;
  }

  drawSvgSheet04() {
    // Sheet 04: Platform Chassis Baseplate
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 04 &bull; SUSPENDED 2-DOF END-EFFECTOR CHASSIS (DWG-WALL-CAD-003)</text>

      <!-- TOP PLAN VIEW (Scale 4x: 110 x 85 mm -> 440 x 340 px) -->
      <g transform="translate(180, 140)">
        <text x="220" y="-20" class="callout-text" text-anchor="middle">TOP PLAN VIEW &bull; SCALE 1:1 FULL</text>
        <!-- Main Plate (440 x 340 mm, r = 24 px) -->
        <rect x="0" y="0" width="440" height="340" rx="24" class="outline-solid"/>

        <!-- 4 Corner Cable Attachment Eyelet Bores (B1..B4) -->
        <!-- Centers: 47mm x 34.5mm from center -> 94mm span (376px), 69mm span (276px) -->
        <!-- Left: 32px, Right: 408px, Top: 32px, Bottom: 308px -->
        <circle cx="32" cy="32" r="8" class="outline-solid"/>
        <circle cx="408" cy="32" r="8" class="outline-solid"/>
        <circle cx="32" cy="308" r="8" class="outline-solid"/>
        <circle cx="408" cy="308" r="8" class="outline-solid"/>
        <text x="32" y="55" class="callout-text" text-anchor="middle">B1</text>
        <text x="408" y="55" class="callout-text" text-anchor="middle">B2</text>
        <text x="32" y="295" class="callout-text" text-anchor="middle">B3</text>
        <text x="408" y="295" class="callout-text" text-anchor="middle">B4</text>

        <!-- 3 POM Ball Transfer Sockets (Dia 12mm: 48px) -->
        <circle cx="52" cy="170" r="24" class="outline-detail"/>
        <circle cx="388" cy="58" r="24" class="outline-detail"/>
        <circle cx="388" cy="282" r="24" class="outline-detail"/>
        <text x="52" y="175" class="callout-text" text-anchor="middle">POM-1</text>
        <text x="388" y="63" class="callout-text" text-anchor="middle">POM-2</text>
        <text x="388" y="287" class="callout-text" text-anchor="middle">POM-3</text>

        <!-- Dual 4mm Linear Guide Rod Bores (Span 36mm: 144px) -->
        <circle cx="148" cy="170" r="8" class="outline-solid"/>
        <circle cx="292" cy="170" r="8" class="outline-solid"/>

        <!-- Central Aperture (Dia 22mm: 88px) -->
        <circle cx="220" cy="170" r="44" class="outline-solid"/>

        <!-- Hexagonal Weight-Reduction Pockets -->
        <polygon points="116,90 136,78 156,90 156,114 136,126 116,114" class="outline-detail"/>
        <polygon points="116,226 136,214 156,226 156,250 136,262 116,250" class="outline-detail"/>
        <polygon points="284,90 304,78 324,90 324,114 304,126 284,114" class="outline-detail"/>
        <polygon points="284,226 304,214 324,226 324,250 304,262 284,250" class="outline-detail"/>

        <!-- Plate Dimensions -->
        <line x1="0" y1="-5" x2="0" y2="-25" class="dim-extension"/>
        <line x1="440" y1="-5" x2="440" y2="-25" class="dim-extension"/>
        <line x1="0" y1="-20" x2="440" y2="-20" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="220" y="-25" class="dim-text">110.00 &plusmn; 0.10 mm (WIDTH)</text>

        <line x1="450" y1="0" x2="475" y2="0" class="dim-extension"/>
        <line x1="450" y1="340" x2="475" y2="340" class="dim-extension"/>
        <line x1="470" y1="0" x2="470" y2="340" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="485" y="175" class="dim-text-vert" transform="rotate(90, 485, 175)">85.00 &plusmn; 0.10 mm (HEIGHT)</text>

        <!-- Eyelet Span Dimensions -->
        <line x1="32" y1="350" x2="32" y2="380" class="dim-extension"/>
        <line x1="408" y1="350" x2="408" y2="380" class="dim-extension"/>
        <line x1="32" y1="375" x2="408" y2="375" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="220" y="395" class="dim-text">94.00 &plusmn; 0.05 mm (EYELET SPAN X)</text>
      </g>
    `;
  }

  drawSvgSheet05() {
    // Sheet 05: Compliance Spring
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 05 &bull; 1.2N HELICAL COMPLIANCE SPRING MECHANISM (DWG-WALL-CAD-004)</text>

      <g transform="translate(180, 160)">
        <text x="180" y="-30" class="callout-text" text-anchor="middle">DETAIL ELEVATION &bull; SCALE 5:1</text>

        <!-- Spring Coils (L0 = 34mm: 340px, Dm = 8.5mm: 85px, d = 1.6mm: 16px) -->
        <path d="M 0 0 L 85 22 L 0 45 L 85 68 L 0 91 L 85 114 L 0 137 L 85 160 L 0 183 L 85 206 L 0 229 L 85 252 L 0 275 L 85 298 L 0 320 L 85 340" class="outline-solid" stroke-width="12"/>

        <!-- Centerline -->
        <line x1="42.5" y1="-20" x2="42.5" y2="360" class="outline-center"/>

        <!-- Dimensions -->
        <!-- Free Length L0 -->
        <line x1="-30" y1="0" x2="-70" y2="0" class="dim-extension"/>
        <line x1="-30" y1="340" x2="-70" y2="340" class="dim-extension"/>
        <line x1="-65" y1="0" x2="-65" y2="340" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="-80" y="175" class="dim-text-vert" transform="rotate(-90, -80, 175)">34.00 mm (FREE LENGTH L_0)</text>

        <!-- Preloaded Operating Length L_installed -->
        <line x1="115" y1="0" x2="160" y2="0" class="dim-extension"/>
        <line x1="115" y1="255" x2="160" y2="255" class="dim-extension"/>
        <line x1="155" y1="0" x2="155" y2="255" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="175" y="130" class="dim-text-vert" transform="rotate(90, 175, 130)">25.50 mm (INSTALLED &bull; &delta; = 8.5 mm &bull; F = 1.20 N)</text>

        <!-- Mean Diameter -->
        <line x1="0" y1="350" x2="0" y2="380" class="dim-extension"/>
        <line x1="85" y1="350" x2="85" y2="380" class="dim-extension"/>
        <line x1="0" y1="375" x2="85" y2="375" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="42.5" y="395" class="dim-text">D_m = 8.50 mm</text>
      </g>

      <!-- SPRING MECHANICS SPECIFICATION TABLE -->
      <g transform="translate(480, 160)">
        <rect x="0" y="0" width="380" height="320" class="outline-detail"/>
        <text x="15" y="25" class="callout-text" font-weight="bold">SPRING MECHANICS & COMPLIANCE EQUATIONS:</text>
        <text x="15" y="55" class="callout-text">&bull; MATERIAL: ASTM A228 High-Tensile Music Wire</text>
        <text x="15" y="80" class="callout-text">&bull; WIRE DIAMETER (d): 1.60 &plusmn; 0.02 mm</text>
        <text x="15" y="105" class="callout-text">&bull; ACTIVE COILS (n_a): 7.5 active turns</text>
        <text x="15" y="130" class="callout-text">&bull; TOTAL COILS (n_t): 9.5 turns (squared & ground flat)</text>
        <text x="15" y="155" class="callout-text">&bull; SHEAR MODULUS (G): 79,300 MPa (79.3 GPa)</text>
        <text x="15" y="190" class="callout-text" font-weight="bold">&bull; SPRING RATE (k):</text>
        <text x="35" y="215" class="callout-text" font-style="italic">k = (G &bull; d^4) / (8 &bull; D_m^3 &bull; n_a)</text>
        <text x="35" y="235" class="callout-text" font-weight="bold">k = 0.1411 N/mm = 141.1 N/m</text>
        <text x="15" y="270" class="callout-text" font-weight="bold">&bull; NORMAL FORCE AT 8.5mm DEFLECTION:</text>
        <text x="35" y="295" class="callout-text">F_normal = k &bull; &delta; = 0.1411 &times; 8.5 = 1.20 N (PRELOAD)</text>
      </g>
    `;
  }

  drawSvgSheet06() {
    // Sheet 06: Module A Piezo
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 06 &bull; MODULE A: 48-NOZZLE DROP-ON-DEMAND PIEZO INKJET PRINTHEAD</text>

      <g transform="translate(180, 140)">
        <!-- Printhead Body (26 x 30 x 36 mm -> 208 x 240 px) -->
        <rect x="0" y="0" width="208" height="240" class="outline-solid"/>
        <!-- Orifice Plate (18 x 22 mm -> 144 x 176 px) -->
        <rect x="32" y="200" width="144" height="40" class="outline-detail"/>

        <!-- 48 Micro-Nozzles (Dual Staggered Rows) -->
        <g class="outline-solid">
          <circle cx="80" cy="220" r="3"/><circle cx="128" cy="220" r="3"/>
          <circle cx="80" cy="225" r="3"/><circle cx="128" cy="225" r="3"/>
          <circle cx="80" cy="230" r="3"/><circle cx="128" cy="230" r="3"/>
        </g>
        <text x="104" y="215" class="callout-text" text-anchor="middle">48 MICRO-ORIFICES (&Oslash; 21.5 &mu;m)</text>

        <!-- 26-Pin FPC Flex Ribbon -->
        <rect x="44" y="-60" width="120" height="60" class="outline-solid" fill="rgba(217,119,6,0.2)"/>
        <text x="104" y="-30" class="callout-text" text-anchor="middle">26-PIN GOLD FPC BUS</text>

        <!-- Dual PTFE Ink Inlets -->
        <rect x="20" y="-30" width="16" height="30" class="outline-detail"/>
        <rect x="172" y="-30" width="16" height="30" class="outline-detail"/>
        <text x="28" y="-35" class="callout-text" text-anchor="middle">INK</text>
        <text x="180" y="-35" class="callout-text" text-anchor="middle">PURGE</text>
      </g>

      <g transform="translate(480, 140)">
        <rect x="0" y="0" width="380" height="320" class="outline-detail"/>
        <text x="15" y="25" class="callout-text" font-weight="bold">MICRO-PIEZO OPERATING PARAMETERS:</text>
        <text x="15" y="55" class="callout-text">&bull; DROPLET VOLUME: 14.0 &plusmn; 1.5 pL (14 &times; 10^-12 L)</text>
        <text x="15" y="80" class="callout-text">&bull; DROPLET VELOCITY: 7.2 &plusmn; 0.8 m/s</text>
        <text x="15" y="105" class="callout-text">&bull; NATIVE NOZZLE PITCH: 0.254 mm (100 DPI)</text>
        <text x="15" y="130" class="callout-text">&bull; FIRING FREQUENCY: 100 Hz &dots; 15.0 kHz</text>
        <text x="15" y="155" class="callout-text">&bull; STANDOFF DISTANCE: 2.00 &plusmn; 0.05 mm to wall</text>
        <text x="15" y="180" class="callout-text">&bull; DRIVE PULSE: 24V Trapezoidal Waveform (2.5 &mu;s slew)</text>
        <text x="15" y="215" class="callout-text" font-weight="bold">&bull; COMPATIBLE FLUIDS:</text>
        <text x="35" y="240" class="callout-text">Water-Based Pigment Inks (Viscosity: 2.5 - 4.5 cP)</text>
        <text x="35" y="260" class="callout-text">Solvent-Resistant PTFE Fluidic Path</text>
      </g>
    `;
  }

  drawSvgSheet07() {
    // Sheet 07: Module B Paint Marker
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 07 &bull; MODULE B: SPRING-COMPLIANT PAINT MARKER ACTUATOR</text>

      <g transform="translate(180, 140)">
        <!-- Marker Sleeve (Dia 22mm: 88px, Length 50mm: 200px) -->
        <rect x="0" y="0" width="88" height="200" class="outline-solid"/>
        <!-- Knurled Ring -->
        <rect x="-10" y="30" width="108" height="24" class="outline-detail"/>
        <!-- 6mm Chisel Felt Nib -->
        <polygon points="28,200 60,200 52,240 36,240" class="outline-solid"/>
        <text x="44" y="255" class="callout-text" text-anchor="middle">6.0mm CHISEL NIB</text>

        <!-- Limit Micro-switch Omron D2F -->
        <rect x="98" y="60" width="40" height="70" class="outline-detail"/>
        <line x1="98" y1="80" x2="88" y2="90" class="outline-solid"/>
        <text x="118" y="100" class="callout-text" text-anchor="middle">D2F SWITCH</text>
      </g>

      <g transform="translate(380, 140)">
        <rect x="0" y="0" width="480" height="320" class="outline-detail"/>
        <text x="15" y="25" class="callout-text" font-weight="bold">PAINT MARKER ACTUATOR SPECIFICATIONS:</text>
        <text x="15" y="55" class="callout-text">&bull; MARKER COMPATIBILITY: Standard 15 - 16.5mm Industrial Valve Marker</text>
        <text x="15" y="80" class="callout-text">&bull; NIB TYPE: 6.0mm High-Density Acrylic Felt Chisel Tip</text>
        <text x="15" y="105" class="callout-text">&bull; VALVE ACTUATION: Continuous 1.2N compliance pressure</text>
        <text x="15" y="130" class="callout-text">&bull; CONTACT SENSOR: Omron D2F-01 Ultra-Subminiature Switch</text>
        <text x="15" y="155" class="callout-text">&bull; TRIP POINT: Contact force &gt; 0.35 N signals surface engagement</text>
      </g>
    `;
  }

  drawSvgSheet08() {
    // Sheet 08: Electrical & Umbilical Harness
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 08 &bull; ELECTRICAL WIRING SCHEMATIC & UMBILICAL HARNESS</text>

      <g transform="translate(80, 120)">
        <!-- Master Control Box -->
        <rect x="0" y="0" width="220" height="420" class="outline-solid"/>
        <text x="110" y="30" class="callout-text" text-anchor="middle" font-weight="bold">MASTER CDPR CONTROLLER</text>
        <text x="110" y="50" class="callout-text" text-anchor="middle">STM32H7 / TMC2209 DRIVERS</text>

        <!-- Driver Blocks -->
        <rect x="20" y="80" width="180" height="40" class="outline-detail"/>
        <text x="30" y="105" class="callout-text">STEPPER M1..M4 (4x TMC2209)</text>

        <rect x="20" y="140" width="180" height="40" class="outline-detail"/>
        <text x="30" y="165" class="callout-text">TIMER INPUTS (E1..E4 ENCODERS)</text>

        <rect x="20" y="200" width="180" height="40" class="outline-detail"/>
        <text x="30" y="225" class="callout-text">I2C1 BUS (VL53L1X ToF SENSOR)</text>

        <rect x="20" y="260" width="180" height="40" class="outline-detail"/>
        <text x="30" y="285" class="callout-text">PIEZO PULSE GEN (24V DRIVER)</text>

        <!-- UMBILICAL DRAG HARNESS (Arching to End-Effector) -->
        <path d="M 220 220 C 350 100, 480 100, 600 220" class="outline-solid" stroke-width="8"/>
        <text x="410" y="130" class="callout-text" text-anchor="middle" font-weight="bold">MULTI-LINE UMBILICAL BUNDLE</text>

        <!-- Central End-Effector -->
        <rect x="600" y="140" width="200" height="200" class="outline-solid"/>
        <text x="700" y="170" class="callout-text" text-anchor="middle" font-weight="bold">SUSPENDED END-EFFECTOR</text>
        <text x="620" y="205" class="callout-text">&bull; ToF Sensor (I2C 3.3V)</text>
        <text x="620" y="230" class="callout-text">&bull; 48-Nozzle Printhead (FPC)</text>
        <text x="620" y="255" class="callout-text">&bull; Contact Switch (GPIO)</text>
        <text x="620" y="280" class="callout-text">&bull; Dual PTFE Ink Lines</text>
      </g>
    `;
  }

  build3DHyperActuator() {
    // 3D Assembly of HYPER-ACTUATOR Mk-1 (Sheet 09)
    const grp = new THREE.Group();

    // 1. CDPR Carriage Structural Interface Adapter Baseplate (Dark Anodized 6061-T6)
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x22262d, roughness: 0.45, metalness: 0.65 });
    const baseGeo = new THREE.BoxGeometry(98, 78, 6);
    const base = new THREE.Mesh(baseGeo, baseMat);
    grp.add(base);

    // 2. MGN7C Miniature Linear Rail (Stainless Steel)
    const railMat = new THREE.MeshStandardMaterial({ color: 0xd8dde4, roughness: 0.25, metalness: 0.90 });
    const rail = new THREE.Mesh(new THREE.BoxGeometry(7, 60, 4.8), railMat);
    rail.position.set(0, 0, 5.4);
    grp.add(rail);

    // 3. Voice Coil Actuator (VCA) Stator Housing & Neodymium Magnet
    const vcaStatorMat = new THREE.MeshStandardMaterial({ color: 0xb58900, roughness: 0.35, metalness: 0.75 });
    const vcaStator = new THREE.Mesh(new THREE.CylinderGeometry(12, 12, 14, 24), vcaStatorMat);
    vcaStator.position.set(0, 24, 10);
    grp.add(vcaStator);

    // 4. Moving Active Z-Carriage (Actuated in and out by VCA)
    const zCarriageMat = new THREE.MeshStandardMaterial({ color: 0x303642, roughness: 0.50, metalness: 0.50 });
    const zCarriage = new THREE.Mesh(new THREE.BoxGeometry(64, 56, 12), zCarriageMat);
    zCarriage.position.set(0, 0, 16.5);
    grp.add(zCarriage);

    // VCA Moving Coil (Copper Wire Winding)
    const coilMat = new THREE.MeshStandardMaterial({ color: 0xc86420, roughness: 0.30, metalness: 0.80 });
    const coil = new THREE.Mesh(new THREE.CylinderGeometry(10, 10, 8, 24), coilMat);
    coil.position.set(0, 18, 12);
    grp.add(coil);

    // ST VL53L4CD Micro-LiDAR Sensor
    const lidarMat = new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.20, metalness: 0.30 });
    const lidar = new THREE.Mesh(new THREE.BoxGeometry(12, 8, 2.5), lidarMat);
    lidar.position.set(22, 0, 23);
    grp.add(lidar);

    // 5. 128-Nozzle MEMS Micro-Piezo Printhead Manifold Dock
    const headMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.40, metalness: 0.60 });
    const head = new THREE.Mesh(new THREE.BoxGeometry(34, 48, 30), headMat);
    head.position.set(0, 0, -10);
    grp.add(head);

    // Silicon Orifice Plate (Gold / Mirrored Silicon Face)
    const siliconMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.10, metalness: 0.95 });
    const orificePlate = new THREE.Mesh(new THREE.BoxGeometry(12, 28, 2), siliconMat);
    orificePlate.position.set(0, 0, -26);
    grp.add(orificePlate);

    // Dual Fluidic Inlets
    const luerMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.3, metalness: 0.7 });
    [-7, 7].forEach(x => {
      const luer = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 8, 16), luerMat);
      luer.position.set(x, 0, 7);
      grp.add(luer);
    });

    // 6. Dual In-Situ 395nm UV-LED Pinning Wings (Left & Right)
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.35, metalness: 0.70 });
    [-27, 27].forEach(x => {
      const wing = new THREE.Mesh(new THREE.BoxGeometry(16, 44, 26), wingMat);
      wing.position.set(x, 0, -6);
      grp.add(wing);

      // Quartz Cylindrical Focus Lens
      const quartzMat = new THREE.MeshPhysicalMaterial({
        color: 0xffffff,
        transmission: 0.92,
        opacity: 0.95,
        transparent: true,
        roughness: 0.05,
        ior: 1.46
      });
      const lens = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 36, 20), quartzMat);
      lens.rotation.x = Math.PI / 2;
      lens.position.set(x, 0, -19);
      grp.add(lens);

      // UV-A Pinning Light Cone (Violet Glow at 395nm)
      const uvConeMat = new THREE.MeshBasicMaterial({
        color: 0x8b5cf6,
        transparent: true,
        opacity: 0.35
      });
      const uvCone = new THREE.Mesh(new THREE.ConeGeometry(8, 14, 16), uvConeMat);
      uvCone.rotation.x = Math.PI;
      uvCone.position.set(x, 0, -26);
      grp.add(uvCone);
    });

    // 7. Onboard Constant Meniscus Fluidic Tank & Damper
    const tankMat = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      transmission: 0.75,
      opacity: 0.85,
      transparent: true,
      roughness: 0.2
    });
    const tank = new THREE.Mesh(new THREE.CylinderGeometry(13, 13, 40, 24), tankMat);
    tank.position.set(34, 0, 14);
    grp.add(tank);

    // 8. Motorized Auto-Sealing Capping Servo & Arm
    const servoMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.6 });
    const servo = new THREE.Mesh(new THREE.BoxGeometry(12, 22, 22), servoMat);
    servo.position.set(-32, -10, 12);
    grp.add(servo);

    const armMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 });
    const arm = new THREE.Mesh(new THREE.BoxGeometry(32, 10, 4), armMat);
    arm.position.set(-16, -10, 25);
    grp.add(arm);

    // 9. Wall Plane with Non-Contact Standoff Gap (1.50 mm)
    const wallPlaneMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.12, wireframe: true });
    const wallPlane = new THREE.Mesh(new THREE.PlaneGeometry(120, 100, 10, 10), wallPlaneMat);
    wallPlane.position.set(0, 0, -28.5); // Exact 1.5mm offset from orifice plate (-27.0)
    grp.add(wallPlane);

    this.cadModelGroup.add(grp);
    this.camera.position.set(110, 90, 140);
  }

  drawSvgSheet09() {
    // Sheet 09: HYPER-ACTUATOR Mk-1 Engineering Blueprint Drawing
    this.svgContentGroup.innerHTML = `
      <text x="50" y="60" class="view-label">SHEET 09 &bull; HYPER-ACTUATOR MK-1: NON-CONTACT DUAL-STAGE ACTIVE UV-PIEZO ENGINE</text>
      <text x="50" y="78" class="spec-note-title">DWG-WALL-HACT-000 &bull; ISO 2768-mK &bull; ACTIVE 1.50mm STANDOFF WITH 395nm IN-SITU PHOTOPOLYMERIZATION</text>

      <!-- View A: Front Elevation (Looking toward Wall) -->
      <g transform="translate(100, 140)">
        <text x="0" y="-15" class="view-label">VIEW A: FRONT ELEVATION (ACTIVE FACE)</text>
        
        <!-- Adapter Plate Outer Border -->
        <rect x="0" y="0" width="340" height="280" rx="12" class="outline-solid"/>
        <line x1="170" y1="-10" x2="170" y2="290" class="center-line"/>
        <line x1="-10" y1="140" x2="350" y2="140" class="center-line"/>

        <!-- MGN7C Central Linear Guideway -->
        <rect x="155" y="20" width="30" height="240" class="outline-detail"/>
        <circle cx="170" cy="50" r="4" class="outline-detail"/>
        <circle cx="170" cy="110" r="4" class="outline-detail"/>
        <circle cx="170" cy="170" r="4" class="outline-detail"/>
        <circle cx="170" cy="230" r="4" class="outline-detail"/>

        <!-- Active Z-Carriage Box -->
        <rect x="90" y="50" width="160" height="180" rx="8" class="outline-solid" fill="none" stroke-width="2"/>
        <circle cx="170" cy="80" r="32" class="outline-detail"/> <!-- Voice Coil Stator -->
        <circle cx="170" cy="80" r="22" class="outline-detail"/> <!-- Voice Coil Bobbin -->

        <!-- Central 128-Nozzle MEMS Printhead Manifold -->
        <rect x="125" y="120" width="90" height="100" class="outline-solid" stroke="#f59e0b" stroke-width="2"/>
        <!-- Dual Staggered Nozzle Rows -->
        <line x1="165" y1="135" x2="165" y2="205" stroke="#f59e0b" stroke-dasharray="2,2"/>
        <line x1="175" y1="135" x2="175" y2="205" stroke="#f59e0b" stroke-dasharray="2,2"/>
        <text x="170" y="175" class="callout-text" text-anchor="middle" fill="#f59e0b" font-weight="bold">128 NOZZLES</text>

        <!-- Left UV-LED Pinning Wing -->
        <rect x="35" y="60" width="45" height="160" rx="4" class="outline-solid" stroke="#8b5cf6"/>
        <line x1="57" y1="70" x2="57" y2="210" stroke="#8b5cf6" stroke-width="3"/> <!-- Cylindrical Lens -->
        <text x="57" y="145" class="callout-text" text-anchor="middle" fill="#8b5cf6">UV WING L</text>

        <!-- Right UV-LED Pinning Wing -->
        <rect x="260" y="60" width="45" height="160" rx="4" class="outline-solid" stroke="#8b5cf6"/>
        <line x1="282" y1="70" x2="282" y2="210" stroke="#8b5cf6" stroke-width="3"/> <!-- Cylindrical Lens -->
        <text x="282" y="145" class="callout-text" text-anchor="middle" fill="#8b5cf6">UV WING R</text>

        <!-- Non-Contact VL53L4CD Micro-LiDAR Sensor -->
        <rect x="210" y="65" width="30" height="20" rx="2" class="outline-detail" stroke="#3b82f6"/>
        <circle cx="220" cy="75" r="3" fill="#3b82f6"/>
        <circle cx="230" cy="75" r="3" fill="#3b82f6"/>
        <text x="225" y="98" class="callout-text" text-anchor="middle" fill="#3b82f6" font-size="9">LiDAR ToF</text>

        <!-- Dimensions -->
        <line x1="0" y1="300" x2="340" y2="300" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="170" y="318" class="dim-text" text-anchor="middle">98.0 mm (CARRIAGE WIDTH)</text>

        <line x1="360" y1="0" x2="360" y2="280" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="380" y="145" class="dim-text" text-anchor="middle" transform="rotate(90, 380, 145)">78.0 mm (HEIGHT)</text>
      </g>

      <!-- View B: Side Elevation & Fluidic Schematic -->
      <g transform="translate(560, 140)">
        <text x="0" y="-15" class="view-label">VIEW B: SIDE ELEVATION & ACTIVE FLUIDICS</text>

        <!-- Baseplate -->
        <rect x="0" y="0" width="24" height="280" class="outline-solid"/>
        <!-- MGN7C Rail -->
        <rect x="24" y="20" width="16" height="240" class="outline-detail"/>
        <!-- Moving Z Carriage -->
        <rect x="40" y="50" width="38" height="180" class="outline-solid"/>
        <!-- Voice Coil -->
        <rect x="18" y="60" width="35" height="40" class="outline-detail" stroke="#c86420"/>
        <text x="35" y="85" class="callout-text" text-anchor="middle" fill="#c86420" font-size="9">VCA</text>

        <!-- Printhead Body -->
        <rect x="78" y="110" width="70" height="90" class="outline-solid" stroke="#f59e0b"/>
        <!-- Orifice Plate Face -->
        <rect x="148" y="125" width="6" height="60" fill="#f59e0b"/>

        <!-- Zero-Contact Standoff Gap to Wall -->
        <line x1="160" y1="0" x2="160" y2="280" stroke="#00ff88" stroke-width="2" stroke-dasharray="4,3"/>
        <text x="175" y="30" class="callout-text" fill="#00ff88" font-weight="bold">WALL SURFACE</text>

        <line x1="154" y1="155" x2="160" y2="155" class="dim-line" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>
        <text x="195" y="159" class="dim-text" fill="#00ff88">1.50 ±0.02 mm GAP</text>
        <text x="195" y="174" class="callout-text" fill="#00ff88">(ZERO FRICTION / NO TILT)</text>

        <!-- Technical Callouts & Features Summary -->
        <g transform="translate(0, 310)">
          <rect x="-10" y="0" width="460" height="120" class="title-block-bg"/>
          <text x="10" y="22" class="callout-text" font-weight="bold" fill="#f59e0b">NOVEL ACTUATOR MECHATRONIC ADVANTAGES:</text>
          <text x="10" y="44" class="callout-text">&bull; 1. ZERO WALL CONTACT: Non-contact active voice-coil standoff prevents platform tilt & smudging.</text>
          <text x="10" y="64" class="callout-text">&bull; 2. IN-SITU 395nm UV PINNING: Freezes 6-24 pL droplets in <50ms (Zero vertical drip on drywall/glass).</text>
          <text x="10" y="84" class="callout-text">&bull; 3. ACTIVE MENISCUS REGULATOR: Continuous -1.45 kPa back-pressure prevents nozzle weeping under motion.</text>
          <text x="10" y="104" class="callout-text">&bull; 4. CLOSED-LOOP DUAL-STAGE: 100 Hz micro-LiDAR cancels cable elasticity & wall undulations.</text>
        </g>
      </g>
    `;
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.blueprintApp = new BlueprintApp();
});

