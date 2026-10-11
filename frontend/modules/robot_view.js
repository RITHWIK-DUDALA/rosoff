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

    // 2. Corner Servo Motors & Cable Winch Assemblies
    this.drumMeshes = [];
    this.motorAssemblies = [];
    const drumR = this.config.actuators.drum_radius_m || 0.010;

    // Materials for servo motor components
    const motorBodyMat = new THREE.MeshStandardMaterial({
      color: 0x1a1d24, // Matt dark grey / black anodized aluminum
      metalness: 0.7,
      roughness: 0.35
    });
    const motorFlangeMat = new THREE.MeshStandardMaterial({
      color: 0x8b949e, // Brushed aluminum faceplate
      metalness: 0.85,
      roughness: 0.25
    });
    const shaftMat = new THREE.MeshStandardMaterial({
      color: 0xd0d7de, // Steel shaft
      metalness: 0.95,
      roughness: 0.1
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

    const cornerCoords = [
      [-fw / 2,  fh / 2, "MOTOR 1 (C1)"], // Top-Left
      [ fw / 2,  fh / 2, "MOTOR 2 (C2)"], // Top-Right
      [ fw / 2, -fh / 2, "MOTOR 3 (C3)"], // Bottom-Right
      [-fw / 2, -fh / 2, "MOTOR 4 (C4)"]  // Bottom-Left
    ];

    cornerCoords.forEach(([x, y, labelText], idx) => {
      const anchorPos = new THREE.Vector3(x, y, 0);
      this.anchors.push(anchorPos);

      const motorGroup = new THREE.Group();
      motorGroup.position.set(x, y, 0);

      // (a) Motor Mounting Bracket attached to frame
      const bracketMat = new THREE.MeshStandardMaterial({ color: 0x30363d, metalness: 0.8 });
      const bracket = new THREE.Mesh(new THREE.BoxGeometry(0.052, 0.052, 0.008), bracketMat);
      bracket.position.set(0, 0, -0.018);
      motorGroup.add(bracket);

      // (b) NEMA / Servo Motor Main Body (42x42x50 mm)
      // Motor body extends downward into -Z
      const motorBody = new THREE.Mesh(new THREE.BoxGeometry(0.044, 0.044, 0.052), motorBodyMat);
      motorBody.position.set(0, 0, -0.048);
      motorGroup.add(motorBody);

      // (c) Motor Front Aluminum Faceplate
      const motorFace = new THREE.Mesh(new THREE.BoxGeometry(0.046, 0.046, 0.006), motorFlangeMat);
      motorFace.position.set(0, 0, -0.020);
      motorGroup.add(motorFace);

      // (d) Rear Encoder / Connector Cap (cylinder at bottom of motor)
      const encoderCap = new THREE.Mesh(
        new THREE.CylinderGeometry(0.016, 0.016, 0.014, 20),
        new THREE.MeshStandardMaterial({ color: 0x0d1117, roughness: 0.6 })
      );
      encoderCap.rotation.x = Math.PI / 2;
      encoderCap.position.set(0, 0, -0.078);
      motorGroup.add(encoderCap);

      // (e) Rotating Output Shaft & Spool Drum Sub-Assembly
      const drumGroup = new THREE.Group();
      drumGroup.position.set(0, 0, 0);

      // Drive shaft through center (axis along Z)
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, 0.028, 16), shaftMat);
      shaft.rotation.x = Math.PI / 2;
      drumGroup.add(shaft);

      // Main spool cylinder (drum radius r = 10mm, height 18mm)
      const drumCore = new THREE.Mesh(new THREE.CylinderGeometry(drumR, drumR, 0.016, 24), drumMat);
      drumCore.rotation.x = Math.PI / 2;
      drumGroup.add(drumCore);

      // Drum bottom retention flange (wider rim)
      const btmFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR * 1.5, drumR * 1.5, 0.003, 24),
        drumFlangeMat
      );
      btmFlange.rotation.x = Math.PI / 2;
      btmFlange.position.set(0, 0, -0.008);
      drumGroup.add(btmFlange);

      // Drum top retention flange (wider rim)
      const topFlange = new THREE.Mesh(
        new THREE.CylinderGeometry(drumR * 1.5, drumR * 1.5, 0.003, 24),
        drumFlangeMat
      );
      topFlange.rotation.x = Math.PI / 2;
      topFlange.position.set(0, 0, 0.008);
      drumGroup.add(topFlange);

      // Visual alignment spoke on drum face so rotation is clearly visible
      const spoke = new THREE.Mesh(
        new THREE.BoxGeometry(drumR * 2.6, 0.002, 0.001),
        new THREE.MeshBasicMaterial({ color: 0xffffff })
      );
      spoke.position.set(0, 0, 0.010);
      drumGroup.add(spoke);

      motorGroup.add(drumGroup);
      this.drumMeshes.push(drumGroup);

      // (f) Motor Identification Text Badge (3D Billboard sprite)
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'rgba(13, 17, 23, 0.85)';
      ctx.roundRect ? ctx.roundRect(4, 4, 248, 56, 10) : ctx.rect(4, 4, 248, 56);
      ctx.fill();
      ctx.strokeStyle = '#39c5bb';
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.fillStyle = '#58a6ff';
      ctx.font = 'bold 26px "JetBrains Mono", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, 128, 32);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.09, 0.0225, 1);
      // Offset label outward from frame corner
      const offsetX = x > 0 ? 0.035 : -0.035;
      const offsetY = y > 0 ? 0.035 : -0.035;
      sprite.position.set(offsetX, offsetY, 0.025);
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
}

window.RobotView = RobotView;
