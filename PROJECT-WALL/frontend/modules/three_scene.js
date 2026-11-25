/**
 * High-Fidelity Mechanical CAD Digital Twin Engine for PROJECT W.A.L.L.
 * Universal Planar Cable-Driven Autonomous Surface Printing System (CDPR)
 * 
 * REAL-WORLD MECHANICAL & KINEMATIC MODELING:
 * - Real NEMA 17 Stepper Motors: 8-sided chamfered stator, silicon steel lamination stack,
 *   heatsink flutes, die-cast endbells, M3 socket head cap screws with hex sockets,
 *   ground D-shaft with flat keyway, helical beam coupler with spiral slits, and 4-lead JST-XH wiring harness.
 * - Real Winch Spool Stations: Helical-grooved CNC drum, dual F688ZZ flanged shielded ball bearings,
 *   dual bearing pillow blocks, optical encoder disc with radial slits, U-clevis fairlead idler pulley,
 *   and heavy corner mounting L-bracket with dual silicone suction cups & brass vacuum barbs.
 * - Real 4 Dyneema Cables: Braided UHMWPE 3D cylindrical lines with swage ferrules, stainless teardrop thimbles,
 *   and clevis pins; real-time kinematic rotation and tension color states.
 * - Real Suspended 2-DOF Chassis: 6061-T6 pocketed skeleton baseplate with lightening pockets,
 *   4 Heim joint spherical rod ends that swivel toward anchor vectors, 3 POM ball-transfer standoff units,
 *   dual ground 4mm linear guide rods with sintered bronze bushings, and VL53L1X ToF optical distance sensor.
 * - Real Working 1.2N Helical Compliance Spring: Formed with squared & ground flat ends,
 *   7.5 active coils of ASTM A228 spring steel, physically compressing/deflecting under cable tension.
 * - Real Interchangeable Actuators:
 *     * Module A: 48-nozzle micro-piezo silicon printhead, gold-traced 26-pin FPC ribbon, dual PTFE Luer-lock lines.
 *     * Module B: Split-collet aluminum marker clamp with M16 knurled ring, 6mm chisel nib, Omron D2F micro-switch.
 * - Real Working Kinematics: Motors and drums physically rotate in real-time as the platform moves!
 */

// Helper: Parametric Helical Spring Curve with Ground Flat Ends
class PrecisionSpringCurve extends THREE.Curve {
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
    // Linear pitch with squared end transition
    const z = this.height * (t - 0.5);
    return new THREE.Vector3(x, y, z);
  }
}

// Helper: Umbilical Drag Harness Curve
class UmbilicalArchCurve extends THREE.Curve {
  constructor(length = 200.0, height = 85.0) {
    super();
    this.length = length;
    this.height = height;
  }
  getPoint(t) {
    const x = (t - 0.5) * this.length;
    const y = 4.0 * this.height * t * (1.0 - t);
    const z = Math.sin(t * Math.PI) * 20.0;
    return new THREE.Vector3(x, y, z);
  }
}

export class ThreeScene {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.width = this.container.clientWidth || 900;
    this.height = this.container.clientHeight || 650;

    // 1. Scene & Environment (Industrial Obsidian Slate — Zero Blue)
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0c10);

    // 2. Camera: Isometric Perspective
    this.camera = new THREE.PerspectiveCamera(36, this.width / this.height, 1, 8000);
    this.camera.position.set(400, 180, 1280);

    // 3. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    // 4. Orbit Controls
    if (window.THREE && window.THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.target.set(400, 300, 20);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
      this.controls.maxPolarAngle = Math.PI / 2 + 0.12;
    }

    // 5. High-Clarity Progressive Canvas Texture for Wall Surface (2400x1800 HD)
    this.wallCanvas = document.createElement('canvas');
    this.wallCanvas.width = 2400;
    this.wallCanvas.height = 1800;
    this.wallCtx = this.wallCanvas.getContext('2d');
    this.wallCtx.imageSmoothingEnabled = true;
    this.wallCtx.imageSmoothingQuality = 'high';
    this.wallCtx.fillStyle = '#f8fafc';
    this.wallCtx.fillRect(0, 0, 2400, 1800);

    this.canvasTexture = new THREE.CanvasTexture(this.wallCanvas);
    this.canvasTexture.minFilter = THREE.LinearMipmapLinearFilter;
    this.canvasTexture.magFilter = THREE.LinearFilter;
    this.canvasTexture.generateMipmaps = true;
    if (this.renderer && this.renderer.capabilities) {
      this.canvasTexture.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    }

    // Active Print Module ('inkjet' or 'paint')
    this.activeModule = 'inkjet';

    // Kinematic Tracking State
    this.lastX = 400.0;
    this.lastY = 300.0;
    this.motorAngles = { M1: 0, M2: 0, M3: 0, M4: 0 };

    // 6. Build High-Fidelity Mechanical Assemblies
    this.initSharedMaterials();
    this.buildLighting();
    this.buildWallAndBoard();
    this.buildRealWinchMechanisms();
    this.buildRealEndEffectorWithSpring();
    this.build3DCables();

    // 7. Initial Cable Positioning (Guarantees visible wires on load)
    this.updatePlatform(400.0, 300.0, [12.0, 12.0, 12.0, 12.0]);

    // 8. Event Listeners & Animation Loop
    window.addEventListener('resize', () => this.onResize());
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  initSharedMaterials() {
    // Industrial Precision Metal Materials (Zero Blue, strictly engineering alloys)
    this.matAlum6061 = new THREE.MeshStandardMaterial({
      color: 0x94a3b8, // Brushed 6061-T6 Aluminum
      metalness: 0.88,
      roughness: 0.24
    });

    this.matAlumDark = new THREE.MeshStandardMaterial({
      color: 0x242830, // Black Anodized 6061-T6
      metalness: 0.82,
      roughness: 0.32
    });

    this.matStatorSteel = new THREE.MeshStandardMaterial({
      color: 0x16181d, // Silicon Steel Stator Stack
      metalness: 0.75,
      roughness: 0.45
    });

    this.matStainless304 = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9, // Polished 304 Stainless Steel (Shafts & Screws)
      metalness: 0.95,
      roughness: 0.12
    });

    this.matBrass = new THREE.MeshStandardMaterial({
      color: 0xd97706, // C360 Brass (Couplers, Bushings, Pulleys)
      metalness: 0.92,
      roughness: 0.22
    });

    this.matSpringSteel = new THREE.MeshStandardMaterial({
      color: 0xf59e0b, // Golden High-Tensile Spring Steel (ASTM A228)
      metalness: 0.94,
      roughness: 0.16
    });

    this.matDelrinBlack = new THREE.MeshStandardMaterial({
      color: 0x121417, // Delrin POM Polymer (Housings & Guides)
      roughness: 0.65,
      metalness: 0.1
    });

    this.matSiliconRubber = new THREE.MeshStandardMaterial({
      color: 0x1a1c20, // Vacuum Suction Cups & Grommets
      roughness: 0.9,
      metalness: 0.05
    });

    this.matGoldFpc = new THREE.MeshStandardMaterial({
      color: 0xd97706, // Gold Plated Flex PCB Traces
      metalness: 0.7,
      roughness: 0.3
    });

    this.matPtfe = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0, // Translucent PTFE Chemical Tubing
      roughness: 0.2,
      transparent: true,
      opacity: 0.75
    });

    this.matDyneema = new THREE.MeshStandardMaterial({
      color: 0xf8fafc, // Braided UHMWPE Dyneema Line (High Visibility)
      roughness: 0.4,
      metalness: 0.5
    });

    this.matHexSocket = new THREE.MeshBasicMaterial({ color: 0x0a0a0c }); // Dark Socket Interior
  }

  // CAD Helper: DIN 912 / ISO 4762 Socket Head Cap Screw
  createSocketHeadCapScrew(headDia = 5.5, headH = 3.0, hexSize = 2.5, shankLen = 6.0) {
    const group = new THREE.Group();
    // Cylindrical Head
    const head = new THREE.Mesh(new THREE.CylinderGeometry(headDia / 2, headDia / 2, headH, 20), this.matStainless304);
    head.rotation.x = Math.PI / 2;
    group.add(head);

    // Recessed Hex Socket (6-sided prism cutout representation)
    const hex = new THREE.Mesh(new THREE.CylinderGeometry(hexSize / 2, hexSize / 2, 0.4, 6), this.matHexSocket);
    hex.rotation.x = Math.PI / 2;
    hex.position.z = headH / 2 + 0.05;
    group.add(hex);

    // Threaded Shank
    if (shankLen > 0) {
      const shank = new THREE.Mesh(new THREE.CylinderGeometry(headDia * 0.55 / 2, headDia * 0.55 / 2, shankLen, 16), this.matStainless304);
      shank.rotation.x = Math.PI / 2;
      shank.position.z = -shankLen / 2;
      group.add(shank);
    }
    return group;
  }

  // CAD Helper: F688ZZ Flanged Shielded Ball Bearing
  createFlangedBearing(id = 8.0, od = 16.0, flangeOd = 18.0, width = 5.0, flangeT = 1.0) {
    const group = new THREE.Group();
    // Outer Race
    const outer = new THREE.Mesh(new THREE.CylinderGeometry(od / 2, od / 2, width, 32), this.matStainless304);
    outer.rotation.x = Math.PI / 2;
    group.add(outer);

    // Retaining Flange
    const flange = new THREE.Mesh(new THREE.CylinderGeometry(flangeOd / 2, flangeOd / 2, flangeT, 32), this.matStainless304);
    flange.rotation.x = Math.PI / 2;
    flange.position.z = -width / 2 + flangeT / 2;
    group.add(flange);

    // Inner Race with Bore
    const inner = new THREE.Mesh(new THREE.CylinderGeometry(id / 2 + 1.2, id / 2 + 1.2, width + 0.2, 24), this.matStainless304);
    inner.rotation.x = Math.PI / 2;
    group.add(inner);

    // Annular Shield Ring
    const shield = new THREE.Mesh(new THREE.RingGeometry(id / 2 + 1.4, od / 2 - 1.0, 24), this.matAlumDark);
    shield.position.z = width / 2 + 0.05;
    group.add(shield);

    return group;
  }

  // CAD Helper: Heim Joint / Spherical Rod End (PHS4)
  createSphericalRodEnd(ballDia = 8.0, boreDia = 4.0, shankLen = 14.0) {
    const group = new THREE.Group();
    // Housing Eye
    const eye = new THREE.Mesh(new THREE.CylinderGeometry(ballDia / 2 + 2.5, ballDia / 2 + 2.5, 5.0, 24), this.matAlumDark);
    eye.rotation.x = Math.PI / 2;
    group.add(eye);

    // Chrome Steel Spherical Ball
    const ball = new THREE.Mesh(new THREE.SphereGeometry(ballDia / 2, 24, 24), this.matStainless304);
    group.add(ball);

    // Through-Bore Sleeve
    const bore = new THREE.Mesh(new THREE.CylinderGeometry(boreDia / 2, boreDia / 2, 6.2, 16), this.matStainless304);
    bore.rotation.x = Math.PI / 2;
    group.add(bore);

    // Threaded Shank
    const shank = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, shankLen, 16), this.matStainless304);
    shank.position.y = -shankLen / 2 - ballDia / 2 + 1.0;
    group.add(shank);

    return group;
  }

  buildLighting() {
    // Ambient Neutral Studio Illumination (Soft, uniform, true-to-life color rendering)
    const ambient = new THREE.AmbientLight(0xffffff, 1.05);
    this.scene.add(ambient);

    // Key Light (Angled studio light, avoids direct normal specular reflection)
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.75);
    keyLight.position.set(400, 850, 700);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    this.scene.add(keyLight);

    // Neutral Fill Light (Soft side fill)
    const fillLight = new THREE.DirectionalLight(0xfff8ee, 0.35);
    fillLight.position.set(-250, 200, 550);
    this.scene.add(fillLight);

    // Gentle Studio Ceiling Fill (No direct spotlight into center of wall)
    const ceilingFill = new THREE.DirectionalLight(0xffffff, 0.30);
    ceilingFill.position.set(400, 400, 900);
    this.scene.add(ceilingFill);
  }

  buildWallAndBoard() {
    // Architectural Mounting Wall (Slate Charcoal)
    const wallGeo = new THREE.PlaneGeometry(2400, 1800);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x14171c, roughness: 0.92, metalness: 0.08 });
    const wallMesh = new THREE.Mesh(wallGeo, wallMat);
    wallMesh.position.set(400, 300, -12);
    wallMesh.receiveShadow = true;
    this.scene.add(wallMesh);

    // Studio Concrete Floor
    const floorGeo = new THREE.PlaneGeometry(2400, 850);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x0f1115, roughness: 0.85, metalness: 0.15 });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(400, -300, 413);
    this.scene.add(floorMesh);

    // 800 x 600 mm Precision Printable Surface Board
    const boardGeo = new THREE.BoxGeometry(800, 600, 14);
    const borderMat = new THREE.MeshStandardMaterial({ color: 0x1f232a, metalness: 0.6, roughness: 0.4 });
    const frontMat = new THREE.MeshStandardMaterial({
      map: this.canvasTexture,
      roughness: 0.90, // Non-glare matte architectural substrate
      metalness: 0.0,
      toneMapped: true
    });

    const materials = [borderMat, borderMat, borderMat, borderMat, frontMat, borderMat];
    this.surfaceBoard = new THREE.Mesh(boardGeo, materials);
    this.surfaceBoard.position.set(400, 300, 0);
    this.surfaceBoard.receiveShadow = true;
    this.scene.add(this.surfaceBoard);

    // Extruded Aluminum Board Outer Frame (Brushed 6061-T6)
    const frameEdges = [
      { size: [812, 6, 16], pos: [400, 603, 0] },
      { size: [812, 6, 16], pos: [400, -3, 0] },
      { size: [6, 612, 16], pos: [-3, 300, 0] },
      { size: [6, 612, 16], pos: [803, 300, 0] }
    ];
    frameEdges.forEach(f => {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(f.size[0], f.size[1], f.size[2]), this.matAlum6061);
      bar.position.set(f.pos[0], f.pos[1], f.pos[2]);
      this.scene.add(bar);
    });

    // Printable Margin Boundary (100mm Margin Line in Safety Amber — Zero Blue)
    const marginGeo = new THREE.EdgesGeometry(new THREE.PlaneGeometry(600, 400));
    const marginMat = new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 2 });
    const marginLines = new THREE.LineSegments(marginGeo, marginMat);
    marginLines.position.set(400, 300, 7.5);
    this.scene.add(marginLines);
  }

  buildRealWinchMechanisms() {
    this.anchors = {
      A1: { x: 0,   y: 600, z: 28, leadOut: [1, -1],  angle: -Math.PI / 4 },
      A2: { x: 800, y: 600, z: 28, leadOut: [-1, -1], angle: Math.PI / 4 },
      A3: { x: 0,   y: 0,   z: 28, leadOut: [1, 1],   angle: -3 * Math.PI / 4 },
      A4: { x: 800, y: 0,   z: 28, leadOut: [-1, 1],  angle: 3 * Math.PI / 4 }
    };

    this.winchGroups = {};
    this.winchDrums = {};
    this.fairleadPulleys = {};

    Object.entries(this.anchors).forEach(([aid, cfg]) => {
      const group = new THREE.Group();

      // 1. CNC Corner Mounting L-Bracket (75 x 75 x 6 mm 6061-T6)
      const basePlate = new THREE.Mesh(new THREE.BoxGeometry(75, 75, 6), this.matAlumDark);
      basePlate.position.set(0, 0, -10);
      group.add(basePlate);

      // Stiffener Gusset Webs on L-Bracket
      const gussetGeo = new THREE.BufferGeometry();
      const vertices = new Float32Array([
        -35, -35, -7,   -35, 35, -7,   -35, -35, 15,
         35, -35, -7,    35, 35, -7,    35, -35, 15
      ]);
      gussetGeo.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
      gussetGeo.computeVertexNormals();
      const gusset = new THREE.Mesh(gussetGeo, this.matAlumDark);
      group.add(gusset);

      // 4x Counterbored Corner Mounting Screws (M5 DIN 912)
      [[-28, -28], [28, -28], [-28, 28], [28, 28]].forEach(([hx, hy]) => {
        const screw = this.createSocketHeadCapScrew(8.5, 4.0, 4.0, 10.0);
        screw.position.set(hx, hy, -7);
        group.add(screw);
      });

      // Dual Industrial Vacuum Suction Cups with Brass Barb Fittings
      [[-22, 0], [22, 0]].forEach(([cx, cy]) => {
        const cup = new THREE.Mesh(new THREE.CylinderGeometry(20, 24, 10, 24), this.matSiliconRubber);
        cup.rotation.x = Math.PI / 2;
        cup.position.set(cx, cy, -18);
        group.add(cup);

        const barb = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 8, 16), this.matBrass);
        barb.rotation.x = Math.PI / 2;
        barb.position.set(cx, cy, -25);
        group.add(barb);
      });

      // 2. REAL NEMA 17 STEPPER MOTOR ASSEMBLY (42.3 x 42.3 x 40 mm)
      const motorAssembly = new THREE.Group();

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
      const stator = new THREE.Mesh(statorGeo, this.matStatorSteel);
      motorAssembly.add(stator);

      // Longitudinal Heat-Sink Cooling Flutes on all 4 faces
      [-12, -4, 4, 12].forEach(fx => {
        const fluteTop = new THREE.Mesh(new THREE.BoxGeometry(1.4, 43, 32), this.matAlumDark);
        fluteTop.position.set(fx, 0, 0);
        motorAssembly.add(fluteTop);
        const fluteSide = new THREE.Mesh(new THREE.BoxGeometry(43, 1.4, 32), this.matAlumDark);
        fluteSide.position.set(0, fx, 0);
        motorAssembly.add(fluteSide);
      });

      // Die-Cast Aluminum Front Faceplate (42.3 x 42.3 x 4 mm)
      const frontPlate = new THREE.Mesh(new THREE.BoxGeometry(42.3, 42.3, 4), this.matAlum6061);
      frontPlate.position.set(0, 0, 19);
      motorAssembly.add(frontPlate);

      // 22mm Diameter Precision Pilot Boss Collar
      const pilotBoss = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 2.5, 32), this.matAlum6061);
      pilotBoss.rotation.x = Math.PI / 2;
      pilotBoss.position.set(0, 0, 21.5);
      motorAssembly.add(pilotBoss);

      // Die-Cast Aluminum Rear Endcap (42.3 x 42.3 x 4 mm)
      const rearPlate = new THREE.Mesh(new THREE.BoxGeometry(42.3, 42.3, 4), this.matAlum6061);
      rearPlate.position.set(0, 0, -19);
      motorAssembly.add(rearPlate);

      // 4 Corner M3 Hex Socket Assembly Tie Screws (DIN 912)
      [[-15.5, -15.5], [15.5, -15.5], [-15.5, 15.5], [15.5, 15.5]].forEach(([sx, sy]) => {
        const screw = this.createSocketHeadCapScrew(5.2, 2.8, 2.5, 4.0);
        screw.position.set(sx, sy, 21.0);
        motorAssembly.add(screw);
      });

      // 4-WIRE COLOR-CODED STEPPER HARNESS (Red, Green, Yellow, Black)
      const harnessGroup = new THREE.Group();
      const wireCols = [0xef4444, 0x10b981, 0xf59e0b, 0x050505];
      [-4.5, -1.5, 1.5, 4.5].forEach((wx, wi) => {
        const wire = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 26, 8), new THREE.MeshBasicMaterial({ color: wireCols[wi] }));
        wire.rotation.x = Math.PI / 2;
        wire.position.set(wx, -22, -28);
        harnessGroup.add(wire);
      });
      // 4-Pin Polarized JST-XH Female Housing Connector
      const jstBox = new THREE.Mesh(new THREE.BoxGeometry(13, 6, 8), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.35 }));
      jstBox.position.set(0, -22, -41);
      harnessGroup.add(jstBox);
      motorAssembly.add(harnessGroup);

      motorAssembly.position.set(0, 0, 10);
      group.add(motorAssembly);

      // 3. WORKING ROTATING SHAFT & WINCH DRUM SPOOL
      const rotatingSpoolGroup = new THREE.Group();

      // 5mm D-Cut Stainless Steel Motor Output Shaft
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 26, 20), this.matStainless304);
      shaft.rotation.x = Math.PI / 2;
      shaft.position.set(0, 0, 33);
      rotatingSpoolGroup.add(shaft);

      // Helical Beam Flexible Shaft Coupler (19mm OD x 25mm Length)
      const coupler = new THREE.Mesh(new THREE.CylinderGeometry(9.5, 9.5, 20, 24), this.matAlum6061);
      coupler.rotation.x = Math.PI / 2;
      coupler.position.set(0, 0, 44);
      rotatingSpoolGroup.add(coupler);
      // Coupler Split Clamp Screws
      const cs1 = this.createSocketHeadCapScrew(4.0, 2.0, 2.0, 4.0);
      cs1.position.set(7.5, 0, 40);
      rotatingSpoolGroup.add(cs1);
      const cs2 = this.createSocketHeadCapScrew(4.0, 2.0, 2.0, 4.0);
      cs2.position.set(7.5, 0, 48);
      rotatingSpoolGroup.add(cs2);

      // CNC Machined Helical-Grooved Aluminum Winch Drum (28mm root, 44mm flange, 22mm spool)
      const drumBarrel = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, 22, 32), this.matAlum6061);
      drumBarrel.rotation.x = Math.PI / 2;
      drumBarrel.position.set(0, 0, 70);
      rotatingSpoolGroup.add(drumBarrel);

      // Spiral Cable Coil Layer inside Drum
      const coil = new THREE.Mesh(new THREE.CylinderGeometry(17.2, 17.2, 20, 32), this.matDyneema);
      coil.rotation.x = Math.PI / 2;
      coil.position.set(0, 0, 70);
      rotatingSpoolGroup.add(coil);

      // Lower Retaining Flange (44mm OD, 2.5mm thick with 6 lightening holes)
      const flangeGeo = new THREE.CylinderGeometry(22, 22, 2.5, 32);
      const flangeL = new THREE.Mesh(flangeGeo, this.matAlum6061);
      flangeL.rotation.x = Math.PI / 2;
      flangeL.position.set(0, 0, 58);
      rotatingSpoolGroup.add(flangeL);

      const flangeU = new THREE.Mesh(flangeGeo, this.matAlum6061);
      flangeU.rotation.x = Math.PI / 2;
      flangeU.position.set(0, 0, 82);
      rotatingSpoolGroup.add(flangeU);

      // 6 Circumferential Weight-Reduction Holes
      for (let i = 0; i < 6; i++) {
        const ang = (i * Math.PI) / 3;
        const hole = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 3, 16), this.matAlumDark);
        hole.rotation.x = Math.PI / 2;
        hole.position.set(Math.cos(ang) * 15, Math.sin(ang) * 15, 58);
        rotatingSpoolGroup.add(hole);
      }

      // Optical Quadrature Encoder Disc (with slotted grating slits)
      const encDisc = new THREE.Mesh(new THREE.CylinderGeometry(16, 16, 1.2, 32), this.matDelrinBlack);
      encDisc.rotation.x = Math.PI / 2;
      encDisc.position.set(0, 0, 86);
      rotatingSpoolGroup.add(encDisc);

      group.add(rotatingSpoolGroup);
      this.winchDrums[aid] = rotatingSpoolGroup;

      // 4. STATIONARY BEARING BLOCKS & FAIRLEAD GUIDE PULLEY
      // Dual F688ZZ Flanged Ball Bearings
      const bearingL = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
      bearingL.position.set(0, 0, 54);
      group.add(bearingL);

      const bearingU = this.createFlangedBearing(8.0, 16.0, 18.0, 5.0);
      bearingU.position.set(0, 0, 89);
      group.add(bearingU);

      // Bearing Support Pillow Block Uprights (CNC 6061-T6)
      const upright = new THREE.Mesh(new THREE.BoxGeometry(12, 50, 42), this.matAlumDark);
      upright.position.set(cfg.leadOut[0] * -24, 0, 70);
      group.add(upright);

      // U-Clevis Fairlead Tangency Guide Pulley Assembly
      const fairleadGroup = new THREE.Group();
      const pulleyBracket = new THREE.Mesh(new THREE.BoxGeometry(10, 12, 18), this.matAlumDark);
      fairleadGroup.add(pulleyBracket);

      // Brass V-Grooved Guide Pulley
      const pulley = new THREE.Mesh(new THREE.CylinderGeometry(6.5, 6.5, 8.0, 24), this.matBrass);
      pulley.rotation.x = Math.PI / 2;
      fairleadGroup.add(pulley);

      fairleadGroup.position.set(cfg.leadOut[0] * 18, cfg.leadOut[1] * 18, 70);
      group.add(fairleadGroup);
      this.fairleadPulleys[aid] = fairleadGroup;

      group.position.set(cfg.x, cfg.y, cfg.z);
      this.scene.add(group);
      this.winchGroups[aid] = group;
    });
  }

  buildRealEndEffectorWithSpring() {
    this.platformGroup = new THREE.Group();
    this.dropletGroup = new THREE.Group();
    this.scene.add(this.dropletGroup);

    // 1. CNC 6061-T6 ALUMINUM SKELETAL CHASSIS BASEPLATE (110 x 85 x 8 mm)
    // Filleted profile with structural web pockets
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(110, 85, 8), this.matAlum6061);
    chassis.castShadow = true;
    chassis.position.set(0, 0, 10);
    this.platformGroup.add(chassis);

    // Hexagonal Weight-Reduction Pocket Insets (Lightening Webbing)
    [[-30, 22], [30, 22], [-30, -22], [30, -22], [0, 26], [0, -26]].forEach(([px, py]) => {
      const pocket = new THREE.Mesh(new THREE.CylinderGeometry(9, 9, 8.5, 6), this.matAlumDark);
      pocket.rotation.x = Math.PI / 2;
      pocket.position.set(px, py, 10);
      this.platformGroup.add(pocket);
    });

    // 2. 4 CORNER SWIVELING SPHERICAL ROD ENDS (HEIM JOINTS B1..B4)
    this.eyeletRodEnds = {};
    const rodEndCoords = {
      B1: { x: -47.0, y:  34.5, z: 14.0 }, // Upper-Left
      B2: { x:  47.0, y:  34.5, z: 14.0 }, // Upper-Right
      B3: { x: -47.0, y: -34.5, z: 14.0 }, // Lower-Left
      B4: { x:  47.0, y: -34.5, z: 14.0 }  // Lower-Right
    };

    Object.entries(rodEndCoords).forEach(([bid, pt]) => {
      const rodEnd = this.createSphericalRodEnd(8.0, 4.0, 12.0);
      rodEnd.position.set(pt.x, pt.y, pt.z);
      this.platformGroup.add(rodEnd);
      this.eyeletRodEnds[bid] = rodEnd;
    });

    // 3. 3-POINT KINEMATIC POM BALL TRANSFER STANDOFF UNITS (2.0mm Planar Gap)
    [
      { x: -42, y: 0, z: 4 },
      { x:  42, y: 28, z: 4 },
      { x:  42, y: -28, z: 4 }
    ].forEach(bp => {
      const casing = new THREE.Mesh(new THREE.CylinderGeometry(6, 6, 8, 20), this.matDelrinBlack);
      casing.rotation.x = Math.PI / 2;
      casing.position.set(bp.x, bp.y, bp.z);
      this.platformGroup.add(casing);

      // Polished Stainless Rolling Ball (protruding -2.0mm to wall surface)
      const ball = new THREE.Mesh(new THREE.SphereGeometry(4.5, 20, 20), this.matStainless304);
      ball.position.set(bp.x, bp.y, bp.z - 6.5);
      this.platformGroup.add(ball);
    });

    // 4. OPTICAL ToF DISTANCE SENSOR (VL53L1X Ranging Module)
    const tofHousing = new THREE.Mesh(new THREE.BoxGeometry(14, 10, 6), this.matDelrinBlack);
    tofHousing.position.set(22, 0, 4);
    this.platformGroup.add(tofHousing);

    [-3, 3].forEach(tx => {
      const lens = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 1.5, 16), new THREE.MeshStandardMaterial({ color: 0xef4444, metalness: 0.9 }));
      lens.rotation.x = Math.PI / 2;
      lens.position.set(22 + tx, 0, 0.5);
      this.platformGroup.add(lens);
    });

    // 5. DUAL GROUND 4mm GUIDE SHAFTS & SINTERED BRONZE BUSHINGS
    [-18, 18].forEach(gx => {
      const rod = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 48, 20), this.matStainless304);
      rod.rotation.x = Math.PI / 2;
      rod.position.set(gx, 0, 28);
      this.platformGroup.add(rod);

      const bushing = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 4.5, 14, 20), this.matBrass);
      bushing.rotation.x = Math.PI / 2;
      bushing.position.set(gx, 0, 24);
      this.platformGroup.add(bushing);
    });

    // 6. REAL 1.2N HELICAL COMPLIANCE SPRING (ASTM A228 Spring Steel)
    // Coiled with squared & ground flat ends; physically compresses under tension
    const springCurve = new PrecisionSpringCurve(8.5, 34.0, 7.5);
    const springGeo = new THREE.TubeGeometry(springCurve, 100, 1.6, 14, false);
    this.complianceSpring = new THREE.Mesh(springGeo, this.matSpringSteel);
    this.complianceSpring.position.set(0, 0, 24);
    this.platformGroup.add(this.complianceSpring);

    // Spring Ground Flat End Caps
    [-17, 17].forEach(zy => {
      const endRing = new THREE.Mesh(new THREE.TorusGeometry(8.5, 1.6, 16, 32), this.matBrass);
      endRing.position.set(0, 0, 24 + zy);
      this.platformGroup.add(endRing);
    });

    // Knurled Brass Preload Adjusting Collar Ring
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 4.5, 24), this.matBrass);
    collar.rotation.x = Math.PI / 2;
    collar.position.set(0, 0, 42);
    this.platformGroup.add(collar);

    // 7. QUICK-RELEASE DOVETAIL SLIDE RECEIVER
    const dovetail = new THREE.Mesh(new THREE.BoxGeometry(36, 42, 6), this.matAlumDark);
    dovetail.position.set(0, 0, 20);
    this.platformGroup.add(dovetail);

    const thumbScrew = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 4.5, 10, 20), this.matBrass);
    thumbScrew.position.set(20, 0, 20);
    this.platformGroup.add(thumbScrew);

    // 8. INTERCHANGEABLE ACTUATORS (Module A & Module B)
    this.moduleAGroup = new THREE.Group(); // Piezo Inkjet
    this.moduleBGroup = new THREE.Group(); // Paint Marker

    // --- MODULE A: Micro-Piezo Drop-on-Demand Printhead ---
    const piezoBody = new THREE.Mesh(new THREE.BoxGeometry(26, 30, 36), this.matAlumDark);
    piezoBody.position.set(0, 0, 22);
    this.moduleAGroup.add(piezoBody);

    // Silicon Orifice Plate (48 Micro-Nozzles)
    const nozzlePlate = new THREE.Mesh(new THREE.BoxGeometry(18, 22, 2), this.matStainless304);
    nozzlePlate.position.set(0, 0, 2);
    this.moduleAGroup.add(nozzlePlate);

    // 48 Micro-Nozzles (Dual Staggered Rows)
    for (let r = 0; r < 12; r++) {
      [-2, 2].forEach(col => {
        const microHole = new THREE.Mesh(new THREE.CircleGeometry(0.35, 8), this.matHexSocket);
        microHole.position.set(col, (r - 5.5) * 1.5, 0.9);
        this.moduleAGroup.add(microHole);
      });
    }

    // Gold FPC Flex Ribbon Cable
    const fpcRibbon = new THREE.Mesh(new THREE.BoxGeometry(16, 1, 46), this.matGoldFpc);
    fpcRibbon.position.set(0, 16, 32);
    this.moduleAGroup.add(fpcRibbon);

    // Dual PTFE Tubing Lines with Luer-Locks
    [-6, 6].forEach(tx => {
      const luer = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 6, 16), this.matAlum6061);
      luer.rotation.x = Math.PI / 2;
      luer.position.set(tx, -14, 38);
      this.moduleAGroup.add(luer);

      const tubeCurve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(tx, -14, 41),
        new THREE.Vector3(tx * 1.8, -32, 65),
        new THREE.Vector3(tx * 2.2, -50, 85)
      );
      const tube = new THREE.Mesh(new THREE.TubeGeometry(tubeCurve, 24, 1.3, 10, false), this.matPtfe);
      this.moduleAGroup.add(tube);
    });

    // Ink Spray Cone
    const sprayGeo = new THREE.ConeGeometry(5.5, 12, 18, 1, true);
    const sprayMat = new THREE.MeshBasicMaterial({ color: 0x111111, transparent: true, opacity: 0.0 });
    this.inkSprayCone = new THREE.Mesh(sprayGeo, sprayMat);
    this.inkSprayCone.rotation.x = Math.PI;
    this.inkSprayCone.position.set(0, 0, -5);
    this.moduleAGroup.add(this.inkSprayCone);

    this.platformGroup.add(this.moduleAGroup);

    // --- MODULE B: Paint Marker Actuator ---
    const collarMesh = new THREE.Mesh(new THREE.CylinderGeometry(10.5, 10.5, 30, 24), this.matAlum6061);
    collarMesh.rotation.x = Math.PI / 2;
    collarMesh.position.set(0, 0, 24);
    this.moduleBGroup.add(collarMesh);

    const markerBody = new THREE.Mesh(new THREE.CylinderGeometry(8.5, 8.5, 46, 24), this.matDelrinBlack);
    markerBody.rotation.x = Math.PI / 2;
    markerBody.position.set(0, 0, 28);
    this.moduleBGroup.add(markerBody);

    const feltNib = new THREE.Mesh(new THREE.BoxGeometry(6, 4, 12), this.matAlumDark);
    feltNib.position.set(0, 0, 0);
    this.moduleBGroup.add(feltNib);

    const microSwitch = new THREE.Mesh(new THREE.BoxGeometry(6, 10, 5), this.matDelrinBlack);
    microSwitch.position.set(13, 0, 16);
    this.moduleBGroup.add(microSwitch);

    this.moduleBGroup.visible = false;
    this.platformGroup.add(this.moduleBGroup);

    // 9. UMBILICAL CABLE & FLUID DRAG HARNESS
    const umbilicalCurve = new UmbilicalArchCurve(160, 75);
    const umbilicalGeo = new THREE.TubeGeometry(umbilicalCurve, 40, 3.8, 14, false);
    const umbilicalBundle = new THREE.Mesh(umbilicalGeo, this.matDelrinBlack);
    umbilicalBundle.position.set(0, 42, 34);
    this.platformGroup.add(umbilicalBundle);

    const clampBracket = new THREE.Mesh(new THREE.BoxGeometry(20, 12, 10), this.matAlum6061);
    clampBracket.position.set(0, 42, 34);
    this.platformGroup.add(clampBracket);

    this.platformGroup.position.set(400, 300, 20);
    this.scene.add(this.platformGroup);
  }

  build3DCables() {
    this.cables = {};
    const cableCylGeo = new THREE.CylinderGeometry(1.4, 1.4, 1.0, 16);
    cableCylGeo.translate(0, 0.5, 0);

    ['C1', 'C2', 'C3', 'C4'].forEach(cid => {
      const mat = new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        roughness: 0.35,
        metalness: 0.65
      });
      const mesh = new THREE.Mesh(cableCylGeo, mat);
      this.scene.add(mesh);
      this.cables[cid] = mesh;
    });
  }

  setModule(moduleType) {
    this.activeModule = moduleType;
    if (moduleType === 'paint') {
      this.moduleAGroup.visible = false;
      this.moduleBGroup.visible = true;
    } else {
      this.moduleAGroup.visible = true;
      this.moduleBGroup.visible = false;
    }
  }

  updatePlatform(x, y, tensions = [12, 12, 12, 12]) {
    if (!this.platformGroup) return;

    // Kinematic Velocity Estimation for Realistic Motor Spinning
    const dx = x - this.lastX;
    const dy = y - this.lastY;
    const dist = Math.hypot(dx, dy);
    this.lastX = x;
    this.lastY = y;

    this.platformGroup.position.x = x;
    this.platformGroup.position.y = y;

    // Anchor Guide Exit Points (World Coordinates)
    const anchorExitPoints = {
      C1: new THREE.Vector3(18,  582, 70), // A1: Upper-Left
      C2: new THREE.Vector3(782, 582, 70), // A2: Upper-Right
      C3: new THREE.Vector3(18,  18,  70), // A3: Lower-Left
      C4: new THREE.Vector3(782, 18,  70)  // A4: Lower-Right
    };

    // Platform Spherical Rod End Centers (World Coordinates)
    const rodEndWorldPoints = {
      C1: new THREE.Vector3(x - 47.0, y + 34.5, 34),
      C2: new THREE.Vector3(x + 47.0, y + 34.5, 34),
      C3: new THREE.Vector3(x - 47.0, y - 34.5, 34),
      C4: new THREE.Vector3(x + 47.0, y - 34.5, 34)
    };

    const cableKeys = ['C1', 'C2', 'C3', 'C4'];
    const upVector = new THREE.Vector3(0, 1, 0);

    cableKeys.forEach((cid, i) => {
      const mesh = this.cables[cid];
      if (!mesh) return;

      const pStart = anchorExitPoints[cid];
      const pEnd = rodEndWorldPoints[cid];

      const diff = new THREE.Vector3().subVectors(pEnd, pStart);
      const len = diff.length();

      // Transform 3D cylindrical cable mesh
      mesh.position.copy(pStart);
      mesh.scale.set(1, Math.max(1.0, len), 1);
      mesh.quaternion.setFromUnitVectors(upVector, diff.clone().normalize());

      // 1. REAL KINEMATIC SWIVELING: Align Heim joint rod ends directly with cable vector
      const bid = `B${i + 1}`;
      if (this.eyeletRodEnds && this.eyeletRodEnds[bid]) {
        const rodEnd = this.eyeletRodEnds[bid];
        const localTarget = new THREE.Vector3().subVectors(pStart, this.platformGroup.position);
        rodEnd.rotation.z = Math.atan2(localTarget.y, localTarget.x) - Math.PI / 2;
      }

      // 2. REAL KINEMATIC ROTATION: Spin Winch Drums in proportion to cable movement
      const mid = `M${i + 1}`;
      const aid = `A${i + 1}`;
      if (this.winchDrums && this.winchDrums[aid] && dist > 0.05) {
        // Delta theta = delta L / r_eff (r_eff = 14mm)
        const sign = (i === 0 || i === 2) ? 1 : -1;
        this.motorAngles[mid] += sign * (dist / 14.0);
        this.winchDrums[aid].rotation.z = this.motorAngles[mid];
      }

      // 3. Tension Feedback Coloring (No Blue)
      const t = tensions[i] !== undefined ? tensions[i] : 12.0;
      if (t < 2.5) {
        mesh.material.color.setHex(0xf59e0b); // Slack Amber
      } else if (t > 45.0) {
        mesh.material.color.setHex(0xef4444); // Overload Red
      } else {
        mesh.material.color.setHex(0xf8fafc); // Nominal Braided White
      }
    });

    // 4. REAL DYNAMIC SPRING DEFLECTION (Hooke's Law: delta_x = F / k)
    if (this.complianceSpring) {
      const avgTension = tensions.reduce((a, b) => a + b, 0) / 4.0;
      // Normal force equilibrium deflection
      const compressionScale = Math.max(0.72, Math.min(1.15, 1.0 - (avgTension - 12.0) * 0.006));
      this.complianceSpring.scale.set(1, 1, compressionScale);
    }
  }

  updateCanvasTexture(base64Image) {
    if (!base64Image) return;
    const img = new Image();
    img.onload = () => {
      const targetW = Math.max(2400, img.naturalWidth || img.width || 2400);
      const targetH = Math.max(1800, img.naturalHeight || img.height || 1800);
      if (this.wallCanvas.width !== targetW || this.wallCanvas.height !== targetH) {
        this.wallCanvas.width = targetW;
        this.wallCanvas.height = targetH;
      }
      this.wallCtx.imageSmoothingEnabled = true;
      this.wallCtx.imageSmoothingQuality = 'high';
      this.wallCtx.drawImage(img, 0, 0, this.wallCanvas.width, this.wallCanvas.height);
      this.canvasTexture.needsUpdate = true;
    };
    img.src = base64Image.startsWith('data:') ? base64Image : ('data:image/jpeg;base64,' + base64Image);
  }

  setSprayActive(active) {
    this.isSpraying = active;
    if (this.inkSprayCone) {
      this.inkSprayCone.material.opacity = active ? 0.85 : 0.0;
    }
    // Spawn micro-droplet burst
    if (active && this.dropletGroup && this.platformGroup) {
      for (let i = 0; i < 4; i++) {
        const dropMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 });
        const drop = new THREE.Mesh(new THREE.SphereGeometry(0.65, 8, 8), dropMat);
        const px = this.platformGroup.position.x + (Math.random() - 0.5) * 4;
        const py = this.platformGroup.position.y + (Math.random() - 0.5) * 4;
        const pz = this.platformGroup.position.z - 4;
        drop.position.set(px, py, pz);
        this.dropletGroup.add(drop);
        if (!this.activeDroplets) this.activeDroplets = [];
        this.activeDroplets.push({ mesh: drop, vz: -45, life: 0 });
      }
    }
  }

  onResize() {
    if (!this.container) return;
    this.width = this.container.clientWidth || 900;
    this.height = this.container.clientHeight || 650;
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(this.width, this.height);
  }

  animate() {
    requestAnimationFrame(this.animate);
    if (this.controls) this.controls.update();

    // Animate flying micro-droplets toward wall
    if (this.activeDroplets && this.activeDroplets.length > 0) {
      for (let i = this.activeDroplets.length - 1; i >= 0; i--) {
        const d = this.activeDroplets[i];
        d.life += 0.016;
        d.mesh.position.z += d.vz * 0.016;
        if (d.mesh.position.z <= 0.0 || d.life > 0.25) {
          this.dropletGroup.remove(d.mesh);
          d.mesh.geometry.dispose();
          d.mesh.material.dispose();
          this.activeDroplets.splice(i, 1);
        }
      }
    }

    this.renderer.render(this.scene, this.camera);
  }
}
