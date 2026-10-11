/**
 * 2D Dimensioned Engineering Canvas View.
 * Renders orthographic projection in exact millimeters:
 * - Frame rectangle (500 x 400 mm)
 * - Safe workspace polygon boundary
 * - Platform footprint (100 x 80 mm)
 * - 4 cable line segments with tension indicators
 * - Coordinate axes and dimension annotations
 * - Interactive click-to-target dispatch
 */
class EngineeringView {
  constructor(canvasElement, config, onTargetSelectedCallback) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');
    this.config = config;
    this.onTargetSelected = onTargetSelectedCallback;

    this.fw_mm = (config.frame.width_m || 0.500) * 1000.0;
    this.fh_mm = (config.frame.height_m || 0.400) * 1000.0;
    this.pw_mm = (config.platform.width_m || 0.100) * 1000.0;
    this.ph_mm = (config.platform.height_m || 0.080) * 1000.0;
    this.ws = config.workspace || { x_min_m: -0.18, x_max_m: 0.18, y_min_m: -0.14, y_max_m: 0.14 };

    this.anchors_mm = [
      [-this.fw_mm / 2,  this.fh_mm / 2], // C1: (-250, 200)
      [ this.fw_mm / 2,  this.fh_mm / 2], // C2: ( 250, 200)
      [ this.fw_mm / 2, -this.fh_mm / 2], // C3: ( 250,-200)
      [-this.fw_mm / 2, -this.fh_mm / 2]  // C4: (-250,-200)
    ];

    this.attachments_mm = [
      [-this.pw_mm / 2,  this.ph_mm / 2], // C1: (-50, 40)
      [ this.pw_mm / 2,  this.ph_mm / 2], // C2: ( 50, 40)
      [ this.pw_mm / 2, -this.ph_mm / 2], // C3: ( 50,-40)
      [-this.pw_mm / 2, -this.ph_mm / 2]  // C4: (-50,-40)
    ];

    this.latestTelemetry = null;
    this.scale = 1.0;
    this.originX = 0;
    this.originY = 0;

    this.setupEvents();
  }

  setupEvents() {
    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clickPxX = e.clientX - rect.left;
      const clickPxY = e.clientY - rect.top;

      // Convert pixel to robot mm coordinates
      const robotX = (clickPxX - this.originX) / this.scale;
      const robotY = (this.originY - clickPxY) / this.scale;

      if (this.pathPlanner && this.pathPlanner.mode === 'waypoints') {
        this.pathPlanner.addWaypoint(robotX, robotY);
        this.render();
      } else if (this.onTargetSelected) {
        this.onTargetSelected(Math.round(robotX), Math.round(robotY));
      }
    });
  }

  update(telemetry) {
    this.latestTelemetry = telemetry;
    this.render();
  }

  render() {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (w === 0 || h === 0) return;

    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }

    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);

    // Coordinate system: center of frame is at canvas center
    this.originX = w / 2;
    this.originY = h / 2;

    // Determine scale to fit 550x450 mm envelope with margins
    const margin = 40;
    const scaleX = (w - margin * 2) / (this.fw_mm + 40);
    const scaleY = (h - margin * 2) / (this.fh_mm + 40);
    this.scale = Math.min(scaleX, scaleY);

    const toPxX = (x_mm) => this.originX + x_mm * this.scale;
    const toPxY = (y_mm) => this.originY - y_mm * this.scale; // Invert Y for screen

    // 1. Grid lines (50 mm spacing)
    ctx.strokeStyle = '#1b2129';
    ctx.lineWidth = 1;
    for (let x = -250; x <= 250; x += 50) {
      ctx.beginPath();
      ctx.moveTo(toPxX(x), toPxY(-200));
      ctx.lineTo(toPxX(x), toPxY(200));
      ctx.stroke();
    }
    for (let y = -200; y <= 200; y += 50) {
      ctx.beginPath();
      ctx.moveTo(toPxX(-250), toPxY(y));
      ctx.lineTo(toPxX(250), toPxY(y));
      ctx.stroke();
    }

    // 2. Structural Frame boundary (500 x 400 mm)
    ctx.strokeStyle = '#484f58';
    ctx.lineWidth = 3;
    ctx.strokeRect(toPxX(-this.fw_mm / 2), toPxY(this.fh_mm / 2), this.fw_mm * this.scale, this.fh_mm * this.scale);

    // Dimension labels
    ctx.fillStyle = '#8b949e';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillText(`${this.fw_mm.toFixed(0)} mm`, toPxX(-20), toPxY(this.fh_mm / 2 + 15));
    ctx.fillText(`${this.fh_mm.toFixed(0)} mm`, toPxX(this.fw_mm / 2 + 10), toPxY(0));

    // 3. Feasible Workspace Polygon Boundary (dashed cyan)
    const wsXMin = this.ws.x_min_m * 1000.0;
    const wsXMax = this.ws.x_max_m * 1000.0;
    const wsYMin = this.ws.y_min_m * 1000.0;
    const wsYMax = this.ws.y_max_m * 1000.0;

    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#39c5bb';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(toPxX(wsXMin), toPxY(wsYMax), (wsXMax - wsXMin) * this.scale, (wsYMax - wsYMin) * this.scale);
    ctx.fillStyle = 'rgba(57, 197, 187, 0.05)';
    ctx.fillRect(toPxX(wsXMin), toPxY(wsYMax), (wsXMax - wsXMin) * this.scale, (wsYMax - wsYMin) * this.scale);
    ctx.restore();

    // 4. Corner Actuator Motors & Cable Spools (M1 - M4)
    const motorSizeMm = 42; // NEMA 17 size footprint (42 mm)
    this.anchors_mm.forEach(([ax, ay], i) => {
      const isLeft = ax < 0;
      const isTop = ay > 0;
      const mX = isLeft ? ax - motorSizeMm : ax;
      const mY = isTop ? ay : ay - motorSizeMm;

      // Motor housing body
      ctx.fillStyle = '#161b22';
      ctx.strokeStyle = '#39c5bb';
      ctx.lineWidth = 1.5;
      ctx.fillRect(toPxX(mX), toPxY(mY + motorSizeMm), motorSizeMm * this.scale, motorSizeMm * this.scale);
      ctx.strokeRect(toPxX(mX), toPxY(mY + motorSizeMm), motorSizeMm * this.scale, motorSizeMm * this.scale);

      // Spool drum circle at anchor point
      const drumRadPx = 10 * this.scale;
      ctx.fillStyle = '#238636';
      ctx.beginPath();
      ctx.arc(toPxX(ax), toPxY(ay), drumRadPx, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffd700';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Shaft center point
      ctx.fillStyle = '#f0f6fc';
      ctx.beginPath();
      ctx.arc(toPxX(ax), toPxY(ay), 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Motor label callout badge
      ctx.fillStyle = '#58a6ff';
      ctx.font = 'bold 10px "JetBrains Mono", monospace';
      const labelText = `M${i+1} (C${i+1})`;
      const textX = toPxX(isLeft ? ax - motorSizeMm / 2 : ax + motorSizeMm / 2);
      const textY = toPxY(isTop ? ay + motorSizeMm + 14 : ay - motorSizeMm - 6);
      ctx.textAlign = 'center';
      ctx.fillText(labelText, textX, textY);
    });

    // 5. Cables and Platform
    const qx = this.latestTelemetry ? this.latestTelemetry.platform_pos[0] : 0.0;
    const qy = this.latestTelemetry ? this.latestTelemetry.platform_pos[1] : 0.0;

    // Draw 4 Cables
    this.anchors_mm.forEach(([ax, ay], i) => {
      const [bx, by] = this.attachments_mm[i];
      const px = qx + bx;
      const py = qy + by;

      ctx.strokeStyle = '#ffd700';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(toPxX(ax), toPxY(ay));
      ctx.lineTo(toPxX(px), toPxY(py));
      ctx.stroke();

      // Attachment eyelet
      ctx.fillStyle = '#ffd700';
      ctx.beginPath();
      ctx.arc(toPxX(px), toPxY(py), 3.5, 0, Math.PI * 2);
      ctx.fill();
    });

    // Platform Body (100 x 80 mm centered at [qx, qy])
    ctx.fillStyle = 'rgba(31, 111, 235, 0.85)';
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 2;
    const platLeft = toPxX(qx - this.pw_mm / 2);
    const platTop = toPxY(qy + this.ph_mm / 2);
    ctx.fillRect(platLeft, platTop, this.pw_mm * this.scale, this.ph_mm * this.scale);
    ctx.strokeRect(platLeft, platTop, this.pw_mm * this.scale, this.ph_mm * this.scale);

    // Platform Center Crosshair
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(toPxX(qx) - 5, toPxY(qy));
    ctx.lineTo(toPxX(qx) + 5, toPxY(qy));
    ctx.moveTo(toPxX(qx), toPxY(qy) - 5);
    ctx.lineTo(toPxX(qx), toPxY(qy) + 5);
    ctx.stroke();

    // Draw Breadcrumb Drawing Trail (Pen Plotter effect)
    if (this.pathPlanner && this.pathPlanner.breadcrumbTrail.length > 1) {
      const trail = this.pathPlanner.breadcrumbTrail;
      ctx.save();
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.moveTo(toPxX(trail[0][0]), toPxY(trail[0][1]));
      for (let i = 1; i < trail.length; i++) {
        ctx.lineTo(toPxX(trail[i][0]), toPxY(trail[i][1]));
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw Active Planned Waypoints Polyline & Handles
    if (this.pathPlanner && this.pathPlanner.waypoints.length > 0) {
      const wps = this.pathPlanner.waypoints;
      ctx.save();

      // Dashed connection line
      if (wps.length > 1) {
        ctx.strokeStyle = '#e3b341';
        ctx.lineWidth = 1.8;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(toPxX(wps[0][0]), toPxY(wps[0][1]));
        for (let i = 1; i < wps.length; i++) {
          ctx.lineTo(toPxX(wps[i][0]), toPxY(wps[i][1]));
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Waypoint nodes
      wps.forEach(([wx, wy], idx) => {
        const px = toPxX(wx);
        const py = toPxY(wy);

        // Outer halo
        ctx.fillStyle = idx === 0 ? '#3fb950' : (idx === wps.length - 1 ? '#f85149' : '#e3b341');
        ctx.beginPath();
        ctx.arc(px, py, 6, 0, Math.PI * 2);
        ctx.fill();

        // Inner dot
        ctx.fillStyle = '#0d1117';
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Node index badge
        ctx.fillStyle = '#f0f6fc';
        ctx.font = 'bold 9px "JetBrains Mono", monospace';
        ctx.fillText(`W${idx + 1}`, px + 8, py - 6);
      });

      ctx.restore();
    }

    // Target Marker
    if (this.latestTelemetry) {
      const tx = this.latestTelemetry.target_pos[0];
      const ty = this.latestTelemetry.target_pos[1];
      ctx.strokeStyle = '#f85149';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(toPxX(tx), toPxY(ty), 6, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

window.EngineeringView = EngineeringView;
