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

    // 1. Structural Frame (Aluminum extrusion representation)
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0x484f58,
      metalness: 0.8,
      roughness: 0.3
    });

    const beamThick = 0.025; // 25 mm extrusion
    // Horizontal top & bottom beams
    const topBeam = new THREE.Mesh(new THREE.BoxGeometry(fw + beamThick, beamThick, beamThick), frameMat);
    topBeam.position.set(0, fh / 2 + beamThick / 2, 0);
    const btmBeam = new THREE.Mesh(new THREE.BoxGeometry(fw + beamThick, beamThick, beamThick), frameMat);
    btmBeam.position.set(0, -fh / 2 - beamThick / 2, 0);

    // Vertical left & right beams
    const leftBeam = new THREE.Mesh(new THREE.BoxGeometry(beamThick, fh + beamThick, beamThick), frameMat);
    leftBeam.position.set(-fw / 2 - beamThick / 2, 0, 0);
    const rightBeam = new THREE.Mesh(new THREE.BoxGeometry(beamThick, fh + beamThick, beamThick), frameMat);
    rightBeam.position.set(fw / 2 + beamThick / 2, 0, 0);

    this.frameGroup.add(topBeam, btmBeam, leftBeam, rightBeam);

    // 2. Corner 28BYJ-48 Stepper Motors (5VDC 15031801) & Cable Spool Assemblies
    this.drumMeshes = [];
    this.motorAssemblies = [];
    const drumR = this.config.actuators.drum_radius_m || 0.010;

    // Shared label texture for the rear stamped tin-can plate
    const motorLabelTexture = this.create28BYJ48LabelTexture();

    // High-fidelity materials for authentic 28BYJ-48 stepper motor components
    const tinCanMat = new THREE.MeshStandardMaterial({
      color: 0xcfd6dc, // Tin-can brushed sheet metal
      metalness: 0.90,
      roughness: 0.25
    });
    const stampedFlangeMat = new THREE.MeshStandardMaterial({
      color: 0xb0b8c0, // Stamped sheet steel mounting ears
      metalness: 0.85,
      roughness: 0.30
    });
    const brassShaftMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37, // Real machined brass output D-shaft
      metalness: 0.90,
      roughness: 0.28
    });
    const blueBoxMat = new THREE.MeshStandardMaterial({
      color: 0x1d5bc7, // Signature royal blue ABS injection-molded terminal casing
      roughness: 0.36,
      metalness: 0.08
    });
    const screwMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8, // Zinc-plated steel M3 mounting screws
      metalness: 0.95,
      roughness: 0.15
    });
    const connectorMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9, // Off-white nylon JST-XH 5-pin socket
      roughness: 0.45,
      metalness: 0.05
    });
    const drumMat = new THREE.MeshStandardMaterial({
      color: 0x39c5bb, // Cyan anodized cable spool drum
      metalness: 0.8,
      roughness: 0.2
    });
    const drumFlangeMat = new THREE.MeshStandardMaterial({
      color: 0x238636, // Green rim retention flange
      metalness: 0.85,
      roughness: 0.25
    });

    const wireMaterials = [
      new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.4 }), // Blue (Coil 1)
      new THREE.MeshStandardMaterial({ color: 0xec4899, roughness: 0.4 }), // Pink (Coil 2)
      new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.4 }), // Yellow (Coil 3)
      new THREE.MeshStandardMaterial({ color: 0xf97316, roughness: 0.4 }), // Orange (Coil 4)
      new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.4 })  // Red (Common 5V)
    ];

    const cornerCoords = [
      [-fw / 2,  fh / 2, "C1", -1,  1], // Top-Left
      [ fw / 2,  fh / 2, "C2",  1,  1], // Top-Right
      [ fw / 2, -fh / 2, "C3",  1, -1], // Bottom-Right
      [-fw / 2, -fh / 2, "C4", -1, -1]  // Bottom-Left
    ];

    cornerCoords.forEach(([x, y, cornerId, dirX, dirY], idx) => {
      const anchorPos = new THREE.Vector3(x, y, 0);
      this.anchors.push(anchorPos);

      const motorGroup = new THREE.Group();
      motorGroup.position.set(x, y, 0);

      // (a) Sturdy corner aluminum mounting bracket attached to frame
      const bracketMat = new THREE.MeshStandardMaterial({ color: 0x30363d, metalness: 0.8, roughness: 0.3 });
      const bracket = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.048, 0.006), bracketMat);
      bracket.position.set(dirX * 0.008, dirY * 0.008, -0.012);
      motorGroup.add(bracket);

      // (b) 28BYJ-48 Eccentric Offset:
      // The output shaft sits at (0, 0, 0) for true analytical cable anchor tangency.
      // The cylindrical motor can (dia 28 mm) is offset outward by 8 mm (0.008 m) along the corner diagonal.
      const canOffsetDist = 0.008; // Exact 8 mm 28BYJ-48 gearbox center-to-shaft distance
      const canOffsetX = dirX * (canOffsetDist * 0.7071);
      const canOffsetY = dirY * (canOffsetDist * 0.7071);
      const canPosZ = -0.022; // Can lies behind the mounting plane

      // (c) Main 28BYJ-48 Cylindrical Tin-Can Body (Diameter: 28 mm, Depth: 19 mm)
      const canRadius = 0.014;  // 14 mm radius = 28 mm diameter
      const canLength = 0.019;  // 19 mm body depth
      const canGeom = new THREE.CylinderGeometry(canRadius, canRadius, canLength, 36);
      const motorCan = new THREE.Mesh(canGeom, tinCanMat);
      motorCan.rotation.x = Math.PI / 2; // Axis along Z
      motorCan.position.set(canOffsetX, canOffsetY, canPosZ);
      motorGroup.add(motorCan);

      // (d) Stamped Tin-Can Rear Face with Printed Specification Text: "28BYJ-48 5V DC 15031801"
      const rearLabelMat = new THREE.MeshBasicMaterial({
        map: motorLabelTexture,
        transparent: true
      });
      const rearLabelDisk = new THREE.Mesh(
        new THREE.CircleGeometry(canRadius * 0.98, 36),
        rearLabelMat
      );
      rearLabelDisk.position.set(canOffsetX, canOffsetY, canPosZ - canLength / 2 - 0.0002);
      rearLabelDisk.rotation.y = Math.PI; // Face outwards toward rear of robot
      motorGroup.add(rearLabelDisk);

      // (e) Stamped Sheet Metal Mounting Ears (Flanges) with 35 mm Hole Pitch
      // Total width: 42 mm across, height: 7.5 mm, thickness: 0.8 mm
      const flangeGroup = new THREE.Group();
      flangeGroup.position.set(canOffsetX, canOffsetY, canPosZ + canLength / 2);
      // Angle the ears to line up diagonally with the bracket
      flangeGroup.rotation.z = Math.atan2(dirY, dirX) + Math.PI / 4;

      const flangePlate = new THREE.Mesh(
        new THREE.BoxGeometry(0.042, 0.0075, 0.0008),
        stampedFlangeMat
      );
      flangeGroup.add(flangePlate);

      // 2x Mounting Screws & Washers (Pitch: 35 mm -> +/- 17.5 mm from can center)
      [-0.0175, 0.0175].forEach(holeX => {
        const screwHead = new THREE.Mesh(
          new THREE.CylinderGeometry(0.0025, 0.0025, 0.002, 16),
          screwMat
        );
        screwHead.rotation.x = Math.PI / 2;
        screwHead.position.set(holeX, 0, 0.001);
        flangeGroup.add(screwHead);
      });
      motorGroup.add(flangeGroup);

      // (f) Front Gearbox Output Neck / Boss (Diameter: 9 mm, Height: 1.5 mm)
      // Located at (0, 0), concentric with the output shaft
      const bossCollar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.0045, 0.0045, 0.002, 24),
        tinCanMat
      );
      bossCollar.rotation.x = Math.PI / 2;
      bossCollar.position.set(0, 0, -0.011);
      motorGroup.add(bossCollar);

      // (g) Characteristic Blue Plastic Wire Terminal Enclosure (14.6 x 16 x 16 mm)
      // Molded on the side of the 28 mm can
      const blueBoxAngle = Math.atan2(dirY, dirX) + Math.PI * 0.75;
      const blueBoxDist = canRadius + 0.004;
      const blueBoxX = canOffsetX + Math.cos(blueBoxAngle) * blueBoxDist;
      const blueBoxY = canOffsetY + Math.sin(blueBoxAngle) * blueBoxDist;

      const blueBox = new THREE.Mesh(
        new THREE.BoxGeometry(0.0146, 0.015, 0.016),
        blueBoxMat
      );
      blueBox.position.set(blueBoxX, blueBoxY, canPosZ);
      blueBox.rotation.z = blueBoxAngle;
      motorGroup.add(blueBox);

      // Molded clip detail on blue box
      const clipDetail = new THREE.Mesh(
        new THREE.BoxGeometry(0.004, 0.0165, 0.004),
        blueBoxMat
      );
      clipDetail.position.set(blueBoxX, blueBoxY, canPosZ);
      clipDetail.rotation.z = blueBoxAngle;
      motorGroup.add(clipDetail);

      // (h) 5-Wire Colored Ribbon Harness (Blue, Pink, Yellow, Orange, Red)
      // Emerging from the blue terminal housing toward an off-white JST-XH connector
      const wireGroup = new THREE.Group();
      const wirePitch = 0.0018;
      const wireLen = 0.024;

      for (let w = 0; w < 5; w++) {
        const wOffset = (w - 2) * wirePitch;
        const curve = new THREE.CatmullRomCurve3([
          new THREE.Vector3(blueBoxX + wOffset * 0.5, blueBoxY, canPosZ),
          new THREE.Vector3(blueBoxX + dirX * 0.008 + wOffset * 0.5, blueBoxY + dirY * 0.008, canPosZ - 0.006),
          new THREE.Vector3(blueBoxX + dirX * 0.016 + wOffset, blueBoxY + dirY * 0.016, canPosZ - 0.014)
        ]);
        const wireTube = new THREE.Mesh(
          new THREE.TubeGeometry(curve, 10, 0.0006, 8, false),
          wireMaterials[w]
        );
        wireGroup.add(wireTube);
      }
      motorGroup.add(wireGroup);

      // 5-Pin JST-XH White Female Connector Plug
      const jstPlug = new THREE.Mesh(
        new THREE.BoxGeometry(0.012, 0.005, 0.006),
        connectorMat
      );
      jstPlug.position.set(blueBoxX + dirX * 0.016, blueBoxY + dirY * 0.016, canPosZ - 0.016);
      motorGroup.add(jstPlug);

      // (i) Rotating Output Sub-Assembly: Brass D-Shaft & Cable Spool Drum
      const drumGroup = new THREE.Group();
      drumGroup.position.set(0, 0, 0);

      // Precision Machined Brass D-Shaft (Diameter: 5 mm, Length: 10 mm)
      const brassShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.0025, 0.0025, 0.020, 20),
        brassShaftMat
      );
      brassShaft.rotation.x = Math.PI / 2;
      brassShaft.position.set(0, 0, -0.002);
      drumGroup.add(brassShaft);

      // Brass D-Flat Machined Face (creates classic 3 mm D-shaft profile)
      const flatCutMat = new THREE.MeshStandardMaterial({
        color: 0xbf9b30,
        metalness: 0.85,
        roughness: 0.35
      });
      const dFlat = new THREE.Mesh(
        new THREE.BoxGeometry(0.0032, 0.001, 0.012),
        flatCutMat
      );
      dFlat.position.set(0, 0.0021, 0.004);
      drumGroup.add(dFlat);

      // Spool Core Cylinder (Radius r = 10 mm, width = 14 mm)
      const drumCore = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR, drumR, 0.014, 28),
        drumMat
      );
      drumCore.rotation.x = Math.PI / 2;
      drumGroup.add(drumCore);

      // Drum bottom retention flange (wider green rim)
      const btmFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR * 1.45, drumR * 1.45, 0.0025, 28),
        drumFlangeMat
      );
      btmFlange.rotation.x = Math.PI / 2;
      btmFlange.position.set(0, 0, -0.007);
      drumGroup.add(btmFlange);

      // Drum top retention flange (wider green rim)
      const topFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR * 1.45, drumR * 1.45, 0.0025, 28),
        drumFlangeMat
      );
      topFlange.rotation.x = Math.PI / 2;
      topFlange.position.set(0, 0, 0.007);
      drumGroup.add(topFlange);

      // Visual alignment spoke on drum face so stepper rotation is clearly visible
      const spoke = new THREE.Mesh(
        new THREE.BoxGeometry(drumR * 2.5, 0.002, 0.001),
        new THREE.MeshBasicMaterial({ color: 0xffffff })
      );
      spoke.position.set(0, 0, 0.0085);
      drumGroup.add(spoke);

      motorGroup.add(drumGroup);
      this.drumMeshes.push(drumGroup);

      // (j) Exact 28BYJ-48 Stepper Motor Identification Badge (3D Billboard sprite)
      const badgeCanvas = document.createElement('canvas');
      badgeCanvas.width = 320;
      badgeCanvas.height = 96;
      const bCtx = badgeCanvas.getContext('2d');

      // Dark translucent badge background
      bCtx.fillStyle = 'rgba(13, 17, 23, 0.88)';
      bCtx.roundRect ? bCtx.roundRect(4, 4, 312, 88, 10) : bCtx.rect(4, 4, 312, 88);
      bCtx.fill();
      bCtx.strokeStyle = '#38bdf8';
      bCtx.lineWidth = 3;
      bCtx.stroke();

      // Top Title: Motor Corner & Model
      bCtx.fillStyle = '#38bdf8';
      bCtx.font = 'bold 24px "Space Grotesk", sans-serif';
      bCtx.textAlign = 'center';
      bCtx.fillText(`${cornerId} • 28BYJ-48 (5V DC)`, 160, 36);

      // Subtitle: Part Number & Stepper Details
      bCtx.fillStyle = '#94a3b8';
      bCtx.font = '500 18px "JetBrains Mono", monospace';
      bCtx.fillText(`P/N: 15031801 | 64:1 GEAR`, 160, 68);

      const badgeTexture = new THREE.CanvasTexture(badgeCanvas);
      const spriteMat = new THREE.SpriteMaterial({ map: badgeTexture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.11, 0.033, 1);
      // Offset badge outward from frame corner
      const offsetX = dirX * 0.040;
      const offsetY = dirY * 0.040;
      sprite.position.set(offsetX, offsetY, 0.030);
      motorGroup.add(sprite);

      this.frameGroup.add(motorGroup);
      this.motorAssemblies.push(motorGroup);
    });

    // 3. Moving Platform Assembly (Clean cable-suspended platform)
    this.platformGroup = new THREE.Group();
    const platMat = new THREE.MeshStandardMaterial({
      color: 0x1f6feb,
      metalness: 0.5,
      roughness: 0.4
    });
    const platMesh = new THREE.Mesh(new THREE.BoxGeometry(pw, ph, pt), platMat);
    this.platformGroup.add(platMesh);

    // Local platform attachment points
    this.attachments = [
      new THREE.Vector3(-pw / 2,  ph / 2, 0), // C1
      new THREE.Vector3( pw / 2,  ph / 2, 0), // C2
      new THREE.Vector3( pw / 2, -ph / 2, 0), // C3
      new THREE.Vector3(-pw / 2, -ph / 2, 0)  // C4
    ];

    // Attachment eyelet markers on platform
    const eyeletMat = new THREE.MeshBasicMaterial({ color: 0xffd700 });
    this.attachments.forEach(att => {
      const eyelet = new THREE.Mesh(new THREE.SphereGeometry(0.004, 12, 12), eyeletMat);
      eyelet.position.copy(att);
      this.platformGroup.add(eyelet);
    });

    this.scene.add(this.platformGroup);

    // 5. Four Rigid Cables (Lines between Anchors and Platform Attachments)
    const cableMat = new THREE.LineBasicMaterial({ color: 0xffd700, linewidth: 2 });
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
    const targetMat = new THREE.MeshBasicMaterial({ color: 0xf85149, wireframe: true });
    this.targetMesh = new THREE.Mesh(new THREE.SphereGeometry(0.006, 16, 16), targetMat);
    this.scene.add(this.targetMesh);
  }

  initTrajectoryTrail() {
    const trailMat = new THREE.LineBasicMaterial({ color: 0x39c5bb, transparent: true, opacity: 0.6 });
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
}

window.RobotView = RobotView;
