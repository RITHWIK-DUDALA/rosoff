/**
 * 3D Robot view: Renders frame, winches/drums, 4 cables, moving platform,
 * anti-rotation guide rods, target marker, and trajectory trail.
 * Scaled directly from robot_config.yaml dimensions (in meters).
 */
class RobotView {
  constructor(scene, config) {
    this.scene = scene;
    this.config = config;

    this.frameGroup = new THREE.Group();
    this.scene.add(this.frameGroup);

    this.anchors = [];      // 4 Vector3 positions
    this.cables = [];       // 4 Line objects
    this.cableGeometries = [];
    this.attachments = [];  // 4 local attachment Vector3 positions

    this.trailPoints = [];
    this.maxTrailLength = 400;

    this.initRobotGeometry();
    this.initTargetMarker();
    this.initTrajectoryTrail();
  }

  initRobotGeometry() {
    const fw = this.config.frame.width_m || 0.500;
    const fh = this.config.frame.height_m || 0.400;
    const fd = this.config.frame.depth_m || 0.120;
    const pw = this.config.platform.width_m || 0.100;
    const ph = this.config.platform.height_m || 0.080;
    const pt = this.config.platform.thickness_m || 0.006;
    // 0. Workbench Table Base (Optional toggleable base)
    const deskMat = new THREE.MeshStandardMaterial({
      color: 0xb5814c, // Natural light oak/teak wood tabletop
      roughness: 0.65,
      metalness: 0.05
    });
    this.deskTable = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.38, 0.02), deskMat);
    this.deskTable.position.set(0, 0, -0.040);
    this.deskTable.visible = false; // Hidden by default, toggled via button
    this.frameGroup.add(this.deskTable);

    // 1. Structural Frame (Clear Anodized 2020 T-Slot Aluminum Extrusions)
    const alum2020Mat = new THREE.MeshStandardMaterial({
      color: 0xc8d1d9, // Clear natural silver anodized aluminum
      metalness: 0.85,
      roughness: 0.28
    });
    const slotDarkMat = new THREE.MeshStandardMaterial({
      color: 0x24292f, // Recessed T-slot dark groove
      roughness: 0.8
    });

    const beamThick = 0.020; // Exact 20 mm x 20 mm aluminum extrusion profile
    // Horizontal top & bottom 2020 rails
    [fh / 2, -fh / 2].forEach(yPos => {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(fw + beamThick, beamThick, beamThick), alum2020Mat);
      rail.position.set(0, yPos, -0.010);
      this.frameGroup.add(rail);

      // T-Slot center groove accent
      const groove = new THREE.Mesh(new THREE.BoxGeometry(fw + beamThick, 0.006, 0.002), slotDarkMat);
      groove.position.set(0, yPos, 0.0005);
      this.frameGroup.add(groove);
    });

    // Vertical left & right 2020 rails
    [-fw / 2, fw / 2].forEach(xPos => {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(beamThick, fh - beamThick, beamThick), alum2020Mat);
      rail.position.set(xPos, 0, -0.010);
      this.frameGroup.add(rail);

      const groove = new THREE.Mesh(new THREE.BoxGeometry(0.006, fh - beamThick, 0.002), slotDarkMat);
      groove.position.set(xPos, 0, 0.0005);
      this.frameGroup.add(groove);
    });

    // 2. Corner 28BYJ-48 Stepper Motors (5VDC 15031801) & Cable Spool Assemblies
    this.drumMeshes = [];
    this.motorAssemblies = [];
    const drumR = this.config.actuators.drum_radius_m || 0.010;

    // Shared label texture for the rear stamped tin-can plate
    const motorLabelTexture = this.create28BYJ48LabelTexture();

    // High-fidelity materials matching the physical hardware photo
    const cornerBracketMat = new THREE.MeshStandardMaterial({
      color: 0x181a1f, // Black 3D-printed PETG corner motor bracket
      roughness: 0.55,
      metalness: 0.1
    });
    const tinCanMat = new THREE.MeshStandardMaterial({
      color: 0xd0d7de, // Silver galvanized tin-can motor housing
      metalness: 0.88,
      roughness: 0.22
    });
    const nylonSpoolMat = new THREE.MeshStandardMaterial({
      color: 0xfacc15, // Bright yellow winch spool drum
      roughness: 0.35,
      metalness: 0.15
    });
    const brassShaftMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37, // Real machined brass output D-shaft
      metalness: 0.90,
      roughness: 0.28
    });
    const blueBoxMat = new THREE.MeshStandardMaterial({
      color: 0x1d5bc7, // Trademark royal blue wire connector box
      roughness: 0.36,
      metalness: 0.08
    });
    const silverScrewMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9, // Bright stainless steel cap-head hex screws
      metalness: 0.95,
      roughness: 0.15
    });

    const wireMaterials = [
      new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.4 }), // Blue
      new THREE.MeshStandardMaterial({ color: 0xec4899, roughness: 0.4 }), // Pink
      new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.4 }), // Yellow
      new THREE.MeshStandardMaterial({ color: 0xf97316, roughness: 0.4 }), // Orange
      new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.4 })  // Red
    ];

    // Corner positions and labels matching the exact reference photo:
    // M1 = Top-Left, M2 = Top-Right, M3 = Bottom-Right, M4 = Bottom-Left
    const cornerCoords = [
      [-fw / 2,  fh / 2, "Motor 1 (M1)", -1,  1],
      [ fw / 2,  fh / 2, "Motor 2 (M2)",  1,  1],
      [ fw / 2, -fh / 2, "Motor 3 (M3)",  1, -1],
      [-fw / 2, -fh / 2, "Motor 4 (M4)", -1, -1]
    ];

    cornerCoords.forEach(([x, y, labelTitle, dirX, dirY], idx) => {
      const anchorPos = new THREE.Vector3(x, y, 0);
      this.anchors.push(anchorPos);

      const motorGroup = new THREE.Group();
      motorGroup.position.set(x, y, 0);

      // (a) Black 3D-Printed Custom Corner Mounting Bracket (matches photo)
      const bracketBase = new THREE.Mesh(
        new THREE.BoxGeometry(0.046, 0.046, 0.012),
        cornerBracketMat
      );
      bracketBase.position.set(dirX * 0.006, dirY * 0.006, -0.016);
      motorGroup.add(bracketBase);

      // Upright motor cradle wall
      const cradleWall = new THREE.Mesh(
        new THREE.BoxGeometry(0.038, 0.038, 0.018),
        cornerBracketMat
      );
      cradleWall.position.set(dirX * 0.010, dirY * 0.010, -0.004);
      motorGroup.add(cradleWall);

      // Stainless socket head clamping bolts on the 3D-printed bracket (as in photo)
      const bolt1 = new THREE.Mesh(new THREE.CylinderGeometry(0.0025, 0.0025, 0.003, 16), silverScrewMat);
      bolt1.rotation.x = Math.PI / 2;
      bolt1.position.set(dirX * 0.018, dirY * 0.018, 0.006);
      motorGroup.add(bolt1);

      const bolt2 = new THREE.Mesh(new THREE.CylinderGeometry(0.0025, 0.0025, 0.003, 16), silverScrewMat);
      bolt2.rotation.x = Math.PI / 2;
      bolt2.position.set(dirX * 0.004, dirY * 0.020, 0.006);
      motorGroup.add(bolt2);

      // (b) 28BYJ-48 Stepper Motor Cylindrical Body (Diameter: 28 mm, Depth: 19 mm)
      // Horizontal mounting orienting spool drum toward the platform
      const canRadius = 0.014;
      const canLength = 0.019;
      const canGeom = new THREE.CylinderGeometry(canRadius, canRadius, canLength, 36);
      const motorCan = new THREE.Mesh(canGeom, tinCanMat);
      motorCan.rotation.x = Math.PI / 2; // Can along Z
      motorCan.position.set(dirX * 0.006, dirY * 0.006, -0.004);
      motorGroup.add(motorCan);

      // Rear stamped metal plate with "28BYJ-48 5V DC 15031801"
      const rearLabelDisk = new THREE.Mesh(
        new THREE.CircleGeometry(canRadius * 0.98, 36),
        new THREE.MeshBasicMaterial({ map: motorLabelTexture, transparent: true })
      );
      rearLabelDisk.position.set(dirX * 0.006, dirY * 0.006, -0.004 - canLength / 2 - 0.0002);
      rearLabelDisk.rotation.y = Math.PI;
      motorGroup.add(rearLabelDisk);

      // (c) Trademark Blue Plastic Terminal Housing
      const blueBox = new THREE.Mesh(new THREE.BoxGeometry(0.014, 0.014, 0.015), blueBoxMat);
      blueBox.position.set(dirX * 0.014, dirY * 0.014, -0.004);
      motorGroup.add(blueBox);

      // (d) 5-Wire Colored Ribbon Cable (Blue, Pink, Yellow, Orange, Red)
      const wireGroup = new THREE.Group();
      for (let w = 0; w < 5; w++) {
        const wOffset = (w - 2) * 0.0016;
        const curve = new THREE.CatmullRomCurve3([
          new THREE.Vector3(dirX * 0.016 + wOffset, dirY * 0.016, -0.004),
          new THREE.Vector3(dirX * 0.026 + wOffset, dirY * 0.024, -0.010),
          new THREE.Vector3(dirX * 0.038, dirY * 0.028 + wOffset, -0.022)
        ]);
        const wireTube = new THREE.Mesh(
          new THREE.TubeGeometry(curve, 8, 0.0006, 6, false),
          wireMaterials[w]
        );
        wireGroup.add(wireTube);
      }
      motorGroup.add(wireGroup);

      // (e) Rotating Output Sub-Assembly: White Nylon Winch Spool & Brass D-Shaft
      // Exactly matches the white spool drums in the reference photo!
      const drumGroup = new THREE.Group();
      drumGroup.position.set(0, 0, 0);

      // Machined brass output shaft
      const brassShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.0025, 0.0025, 0.018, 16),
        brassShaftMat
      );
      brassShaft.rotation.x = Math.PI / 2;
      brassShaft.position.set(0, 0, 0.002);
      drumGroup.add(brassShaft);

      // White spool drum center core (Radius r = 10 mm, width = 12 mm)
      const drumCore = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR, drumR, 0.012, 32),
        nylonSpoolMat
      );
      drumCore.rotation.x = Math.PI / 2;
      drumGroup.add(drumCore);

      // Inner white spool flange (rim dia 26 mm)
      const innerFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(0.013, 0.013, 0.002, 32),
        nylonSpoolMat
      );
      innerFlange.rotation.x = Math.PI / 2;
      innerFlange.position.set(0, 0, -0.006);
      drumGroup.add(innerFlange);

      // Outer white spool flange (rim dia 26 mm)
      const outerFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(0.013, 0.013, 0.002, 32),
        nylonSpoolMat
      );
      outerFlange.rotation.x = Math.PI / 2;
      outerFlange.position.set(0, 0, 0.006);
      drumGroup.add(outerFlange);

      // Silver retaining screw on center of spool face (as seen in photo)
      const centerRetainer = new THREE.Mesh(
        new THREE.CylinderGeometry(0.0035, 0.0035, 0.002, 16),
        silverScrewMat
      );
      centerRetainer.rotation.x = Math.PI / 2;
      centerRetainer.position.set(0, 0, 0.008);
      drumGroup.add(centerRetainer);

      motorGroup.add(drumGroup);
      this.drumMeshes.push(drumGroup);

      // (f) High-visibility Motor Identification Badge (M1-M4)
      const badgeCanvas = document.createElement('canvas');
      badgeCanvas.width = 280;
      badgeCanvas.height = 70;
      const bCtx = badgeCanvas.getContext('2d');

      const badgeBg = idx === 0 ? '#ef4444' : idx === 1 ? '#2563eb' : idx === 2 ? '#16a34a' : '#eab308';
      bCtx.fillStyle = badgeBg;
      if (bCtx.roundRect) {
        bCtx.roundRect(4, 4, 272, 62, 12);
      } else {
        bCtx.rect(4, 4, 272, 62);
      }
      bCtx.fill();
      bCtx.strokeStyle = '#ffffff';
      bCtx.lineWidth = 2;
      bCtx.stroke();

      bCtx.fillStyle = '#ffffff';
      bCtx.font = 'bold 26px "Space Grotesk", sans-serif';
      bCtx.textAlign = 'center';
      bCtx.textBaseline = 'middle';
      bCtx.fillText(labelTitle, 140, 35);

      const badgeTexture = new THREE.CanvasTexture(badgeCanvas);
      const spriteMat = new THREE.SpriteMaterial({ map: badgeTexture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.08, 0.020, 1);
      sprite.position.set(dirX * 0.038, dirY * 0.038, 0.024);
      motorGroup.add(sprite);

      this.frameGroup.add(motorGroup);
      this.motorAssemblies.push(motorGroup);
    });

    // 3. Moving Platform Assembly (Matches exact 60 x 40 mm black 3D-printed plate with 4 eyelet screws)
    this.platformGroup = new THREE.Group();

    // 3D-Printed solid black platform body (60 mm x 40 mm x 5 mm)
    const platMat = new THREE.MeshStandardMaterial({
      color: 0x111317, // Solid matte black 3D-printed PETG/PLA platform
      roughness: 0.50,
      metalness: 0.15
    });
    const platMesh = new THREE.Mesh(new THREE.BoxGeometry(pw, ph, pt), platMat);
    this.platformGroup.add(platMesh);

    // 4 Standoff Guide Feet (elevates platform above bed, as seen in photo)
    const standoffMat = new THREE.MeshStandardMaterial({
      color: 0x334155, // Dark oxide / stainless standoff spacers
      metalness: 0.85,
      roughness: 0.25
    });
    const standoffRad = 0.003;
    const standoffH = 0.016;

    // Local platform attachment points (corner eyelet bolts)
    // pw = 0.060 m (60 mm), ph = 0.040 m (40 mm)
    const attX = 0.022; // 44 mm spacing between left-right eyelets
    const attY = 0.014; // 28 mm spacing between top-bottom eyelets

    this.attachments = [
      new THREE.Vector3(-attX,  attY, 0), // C1 (M1)
      new THREE.Vector3( attX,  attY, 0), // C2 (M2)
      new THREE.Vector3( attX, -attY, 0), // C3 (M3)
      new THREE.Vector3(-attX, -attY, 0)  // C4 (M4)
    ];

    // Screw eyelet rings & bolts exactly matching the physical platform in photo
    const boltHeadMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0, // Stainless steel socket-head bolts contrasting on black plate
      metalness: 0.95,
      roughness: 0.15
    });
    const eyeletRingMat = new THREE.MeshStandardMaterial({
      color: 0xf8fafc, // Bright stainless wire eyelet loop
      metalness: 0.95,
      roughness: 0.12
    });

    this.attachments.forEach(att => {
      // (a) Standoff leg beneath the platform
      const leg = new THREE.Mesh(
        new THREE.CylinderGeometry(standoffRad, standoffRad, standoffH, 16),
        standoffMat
      );
      leg.rotation.x = Math.PI / 2;
      leg.position.set(att.x, att.y, -standoffH / 2 - pt / 2);
      this.platformGroup.add(leg);

      // (b) Hex screw head on top of the platform
      const screwHead = new THREE.Mesh(
        new THREE.CylinderGeometry(0.0035, 0.0035, 0.002, 16),
        boltHeadMat
      );
      screwHead.rotation.x = Math.PI / 2;
      screwHead.position.set(att.x, att.y, pt / 2 + 0.001);
      this.platformGroup.add(screwHead);

      // (c) Stainless cable eyelet ring
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.003, 0.0008, 12, 24),
        eyeletRingMat
      );
      ring.position.set(att.x, att.y, pt / 2 + 0.003);
      this.platformGroup.add(ring);
    });

    this.scene.add(this.platformGroup);

    // 4. Four High-Strength Braided Cables (High contrast dark slate for white background)
    const cableMat = new THREE.LineBasicMaterial({
      color: 0x1e293b, // Dark charcoal / black braided Dyneema line with sharp contrast
      linewidth: 2
    });
    for (let i = 0; i < 4; i++) {
      const geom = new THREE.BufferGeometry().setFromPoints([
        this.anchors[i],
        this.attachments[i]
      ]);
      const line = new THREE.Line(geom, cableMat);
      this.scene.add(line);
      this.cables.push(line);
      this.cableGeometries.push(geom);
    }
  }

  initTargetMarker() {
    const targetMat = new THREE.MeshBasicMaterial({ color: 0xdc2626, wireframe: true });
    this.targetMesh = new THREE.Mesh(new THREE.SphereGeometry(0.006, 16, 16), targetMat);
    this.scene.add(this.targetMesh);
  }

  initTrajectoryTrail() {
    const trailMat = new THREE.LineBasicMaterial({ color: 0x0284c7, transparent: true, opacity: 0.75 });
    this.trailGeom = new THREE.BufferGeometry();
    this.trailLine = new THREE.Line(this.trailGeom, trailMat);
    this.scene.add(this.trailLine);
  }

  update(telemetry) {
    if (!telemetry) return;

    // Convert platform position mm to meters
    const qx = telemetry.platform_pos[0] / 1000.0;
    const qy = telemetry.platform_pos[1] / 1000.0;
    this.platformGroup.position.set(qx, qy, 0);

    // Target position
    const tx = telemetry.target_pos[0] / 1000.0;
    const ty = telemetry.target_pos[1] / 1000.0;
    this.targetMesh.position.set(tx, ty, 0);

    // Update cables and rotate motor winch drums
    for (let i = 0; i < 4; i++) {
      const anchor = this.anchors[i];
      // World position of attachment P_i = q + b_i
      const attWorld = new THREE.Vector3(
        qx + this.attachments[i].x,
        qy + this.attachments[i].y,
        0
      );
      const positions = new Float32Array([
        anchor.x, anchor.y, anchor.z,
        attWorld.x, attWorld.y, attWorld.z
      ]);
      this.cableGeometries[i].setAttribute('position', new THREE.BufferAttribute(positions, 3));
      this.cableGeometries[i].attributes.position.needsUpdate = true;

      // Animate motor spool drum rotation (omega = RPM * 2*pi / 60)
      if (this.drumMeshes && this.drumMeshes[i]) {
        const rpm = telemetry.motor_speeds_rpm ? telemetry.motor_speeds_rpm[i] : 0;
        // theta_dot = (rpm * 2*pi / 60) rad/s; assuming ~30Hz update dt ≈ 0.033s
        const deltaTheta = (rpm * (2.0 * Math.PI / 60.0)) * 0.033;
        this.drumMeshes[i].rotation.z += deltaTheta;
      }
    }

    // Trajectory trail
    this.trailPoints.push(new THREE.Vector3(qx, qy, 0.001));
    if (this.trailPoints.length > this.maxTrailLength) {
      this.trailPoints.shift();
    }
    this.trailGeom.setFromPoints(this.trailPoints);
  }

  clearTrail() {
    this.trailPoints = [];
    this.trailGeom.setFromPoints([]);
  }

  create28BYJ48LabelTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    // 1. Brushed circular tin-can metal background
    const grad = ctx.createRadialGradient(256, 256, 40, 256, 256, 250);
    grad.addColorStop(0, '#f1f5f9');
    grad.addColorStop(0.45, '#e2e8f0');
    grad.addColorStop(0.8, '#cbd5e1');
    grad.addColorStop(1, '#94a3b8');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(256, 256, 250, 0, Math.PI * 2);
    ctx.fill();

    // Concentric lathe machining rings
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 2;
    for (let r = 70; r < 240; r += 26) {
      ctx.beginPath();
      ctx.arc(256, 256, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.25)';
    for (let r = 83; r < 240; r += 26) {
      ctx.beginPath();
      ctx.arc(256, 256, r, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Outer pressed tin-can lip rim
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(256, 256, 244, 0, Math.PI * 2);
    ctx.stroke();

    // 2. Exact Stamped Industrial Label Markings
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Model Name
    ctx.fillStyle = '#0f172a';
    ctx.font = '900 58px "Space Grotesk", "Arial Black", sans-serif';
    ctx.fillText('28BYJ-48', 256, 175);

    // Rated Voltage
    ctx.font = 'bold 44px "Space Grotesk", sans-serif';
    ctx.fillStyle = '#1e293b';
    ctx.fillText('5V DC', 256, 245);

    // Part Number / Batch Code
    ctx.font = '700 38px "JetBrains Mono", monospace';
    ctx.fillStyle = '#334155';
    ctx.fillText('15031801', 256, 310);

    // QC Pass Stamp
    ctx.strokeStyle = '#059669';
    ctx.lineWidth = 3;
    ctx.strokeRect(176, 365, 160, 40);
    ctx.fillStyle = '#059669';
    ctx.font = 'bold 22px "JetBrains Mono", sans-serif';
    ctx.fillText('QC PASSED', 256, 385);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
  }

  toggleTable() {
    if (this.deskTable) {
      this.deskTable.visible = !this.deskTable.visible;
      return this.deskTable.visible;
    }
    return false;
  }

  setTableVisible(visible) {
    if (this.deskTable) {
      this.deskTable.visible = !!visible;
      return this.deskTable.visible;
    }
    return false;
  }
}

window.RobotView = RobotView;
