/**
 * Full Dimensioned Engineering Blueprint View (CAD / Drafting Standard).
 * Renders high-precision orthographic engineering drawings:
 * - Frame envelope (500.0 x 400.0 x 120.0 mm) with extension and dimension lines
 * - Anchor coordinates A1-A4 with datum markers
 * - Platform footprint (100.0 x 80.0 x 6.0 mm) with attachment spacing
 * - Feasible safe workspace (360.0 x 280.0 mm) with clearance callouts
 * - Dual anti-rotation guide rods (dia 10.0 mm, 120.0 mm center-to-center)
 * - NEMA 17 motor footprints (42x42 mm) and drum spool diameters (dia 20.0 mm)
 * - ISO 7200 / ANSI Engineering Title Block & Bill of Materials (BOM)
 * - Side Elevation / Cross-Section View (XZ plane)
 * - Live dynamic kinematic telemetry overlay & PNG export capability
 */
class BlueprintView {
  constructor(canvasElement, config) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');
    this.config = config;

    this.fw = (config.frame.width_m || 0.300) * 1000.0;     // 300 mm
    this.fh = (config.frame.height_m || 0.200) * 1000.0;    // 200 mm
    this.fd = (config.frame.depth_m || 0.080) * 1000.0;     // 80 mm
    this.pw = (config.platform.width_m || 0.060) * 1000.0;  // 60 mm
    this.ph = (config.platform.height_m || 0.040) * 1000.0; // 40 mm
    this.pt = (config.platform.thickness_m || 0.005) * 1000.0; // 5 mm
    this.drumR = (config.actuators.drum_radius_m || 0.010) * 1000.0; // 10 mm
    this.ws = config.workspace || { x_min_m: -0.11, x_max_m: 0.11, y_min_m: -0.07, y_max_m: 0.07 };

    this.anchors = [
      [-this.fw / 2,  this.fh / 2], // C1 (-150, 100)
      [ this.fw / 2,  this.fh / 2], // C2 ( 150, 100)
      [ this.fw / 2, -this.fh / 2], // C3 ( 150,-100)
      [-this.fw / 2, -this.fh / 2]  // C4 (-150,-100)
    ];

    this.attachments = [
      [-this.pw / 2,  this.ph / 2], // b1 (-30, 20)
      [ this.pw / 2,  this.ph / 2], // b2 ( 30, 20)
      [ this.pw / 2, -this.ph / 2], // b3 ( 30,-20)
      [-this.pw / 2, -this.ph / 2]  // b4 (-30,-20)
    ];

    this.latestTelemetry = null;
    this.showSectionView = true;
    this.showLiveTelemetry = true;
  }

  update(telemetry) {
    this.latestTelemetry = telemetry;
    this.render();
  }

  exportImage() {
    const link = document.createElement('a');
    link.download = `CDPR-Blueprint-DWG-001-${new Date().toISOString().slice(0, 10)}.png`;
    link.href = this.canvas.toDataURL('image/png');
    link.click();
  }

  render() {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (w === 0 || h === 0) return;

    // HiDPI support
    const dpr = window.devicePixelRatio || 1;
    if (this.canvas.width !== Math.floor(w * dpr) || this.canvas.height !== Math.floor(h * dpr)) {
      this.canvas.width = Math.floor(w * dpr);
      this.canvas.height = Math.floor(h * dpr);
    }

    const ctx = this.ctx;
    ctx.save();
    ctx.scale(dpr, dpr);

    // 1. Classic CAD Blueprint Background (Deep Cyan/Navy)
    ctx.fillStyle = '#061325';
    ctx.fillRect(0, 0, w, h);

    // 2. Precision Blueprint Grid (10 mm minor, 50 mm major)
    this.renderBlueprintGrid(ctx, w, h);

    // 3. Drawing Sheet Border & Margins (ISO Standard)
    const margin = 16;
    ctx.strokeStyle = '#2b7fff';
    ctx.lineWidth = 2.0;
    ctx.strokeRect(margin, margin, w - margin * 2, h - margin * 2);
    ctx.lineWidth = 1.0;
    ctx.strokeRect(margin + 4, margin + 4, w - (margin + 4) * 2, h - (margin + 4) * 2);

    // 4. Determine Layout Scale & Viewport Centers
    // Split space: Main Plan View (Top Orthographic XY) on left/center,
    // Side Inset (XZ Section) at bottom-left, Title Block & BOM at right/bottom.
    const isWide = w > 900;
    const rightPanelWidth = isWide ? Math.min(340, w * 0.32) : 260;
    const titleBlockHeight = 110;

    const mainAreaW = w - rightPanelWidth - margin * 2 - 20;
    const mainAreaH = h - margin * 2 - (this.showSectionView ? 120 : 20);

    // Scale calculation to comfortably fit 500x400 mm with dimension margins (120mm extra)
    const viewEnvelopeW = this.fw + 140; // 640 mm
    const viewEnvelopeH = this.fh + 140; // 540 mm
    const scale = Math.min(mainAreaW / viewEnvelopeW, mainAreaH / viewEnvelopeH);

    const originX = margin + 20 + mainAreaW / 2;
    const originY = margin + 20 + mainAreaH / 2;

    const toPxX = (x_mm) => originX + x_mm * scale;
    const toPxY = (y_mm) => originY - y_mm * scale;

    // 5. Draw Main Orthographic Projection (XY Plane)
    this.drawMainOrthographic(ctx, toPxX, toPxY, scale, originX, originY);

    // 6. Draw Section / Side Elevation View (XZ Plane) if space permits
    if (this.showSectionView && h > 600) {
      this.drawSectionElevation(ctx, margin + 24, h - margin - 110, mainAreaW - 20, 90);
    }

    // 7. Draw Bill of Materials (BOM) Table
    this.drawBOMTable(ctx, w - margin - rightPanelWidth, margin + 14, rightPanelWidth - 10);

    // 8. Draw ISO 7200 / ANSI Engineering Title Block
    this.drawTitleBlock(ctx, w - margin - rightPanelWidth, h - margin - titleBlockHeight - 6, rightPanelWidth - 10, titleBlockHeight);

    ctx.restore();
  }

  renderBlueprintGrid(ctx, w, h) {
    const gridStep = 20;
    ctx.save();
    // Minor grid
    ctx.strokeStyle = '#0d2238';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (let x = 0; x < w; x += gridStep) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = 0; y < h; y += gridStep) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    // Major grid (every 5 divisions)
    ctx.strokeStyle = '#143557';
    ctx.lineWidth = 1.0;
    ctx.beginPath();
    for (let x = 0; x < w; x += gridStep * 5) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = 0; y < h; y += gridStep * 5) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  drawMainOrthographic(ctx, toX, toY, scale, cx, cy) {
    ctx.save();

    // Section Title
    ctx.fillStyle = '#6cb6ff';
    ctx.font = 'bold 12px "JetBrains Mono", monospace';
    ctx.fillText('VIEW A-A: TOP ORTHOGRAPHIC PROJECTION (XY PLANE)', toX(-this.fw/2) - 10, toY(this.fh/2 + 50));
    ctx.fillStyle = '#8b949e';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillText('ALL DIMENSIONS IN MILLIMETERS [mm] — SCALE 1:2 CAD RATIO', toX(-this.fw/2) - 10, toY(this.fh/2 + 36));

    // A. Datum Center Crosshair and Origin Marker (0,0)
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([8, 4, 2, 4]); // Centerline style
    // Vertical centerline
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(this.fh / 2 + 35));
    ctx.lineTo(toX(0), toY(-this.fh / 2 - 35));
    ctx.stroke();
    // Horizontal centerline
    ctx.beginPath();
    ctx.moveTo(toX(-this.fw / 2 - 35), toY(0));
    ctx.lineTo(toX(this.fw / 2 + 35), toY(0));
    ctx.stroke();
    ctx.setLineDash([]); // Reset dash

    // Datum symbol at (0,0)
    ctx.strokeStyle = '#38bdf8';
    ctx.fillStyle = '#061325';
    ctx.beginPath();
    ctx.arc(toX(0), toY(0), 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#38bdf8';
    ctx.beginPath();
    ctx.arc(toX(0), toY(0), 9, 0, Math.PI / 2);
    ctx.lineTo(toX(0), toY(0));
    ctx.fill();
    ctx.beginPath();
    ctx.arc(toX(0), toY(0), 9, Math.PI, Math.PI * 1.5);
    ctx.lineTo(toX(0), toY(0));
    ctx.fill();
    ctx.fillStyle = '#58a6ff';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.fillText('DATUM (0,0)', toX(12), toY(12));

    // B. Dual Anti-Rotation Precision Guide Rods (Parallel to X axis at Y = +/- 60 mm)
    const rodY1 = 60;
    const rodY2 = -60;
    const rodDiameter = 10;
    ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 1.2;
    // Top Rod
    ctx.fillRect(toX(-this.fw/2), toY(rodY1 + rodDiameter/2), this.fw * scale, rodDiameter * scale);
    ctx.strokeRect(toX(-this.fw/2), toY(rodY1 + rodDiameter/2), this.fw * scale, rodDiameter * scale);
    // Bottom Rod
    ctx.fillRect(toX(-this.fw/2), toY(rodY2 + rodDiameter/2), this.fw * scale, rodDiameter * scale);
    ctx.strokeRect(toX(-this.fw/2), toY(rodY2 + rodDiameter/2), this.fw * scale, rodDiameter * scale);

    // Guide rod centerlines
    ctx.setLineDash([5, 3]);
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(toX(-this.fw/2 - 10), toY(rodY1));
    ctx.lineTo(toX(this.fw/2 + 10), toY(rodY1));
    ctx.moveTo(toX(-this.fw/2 - 10), toY(rodY2));
    ctx.lineTo(toX(this.fw/2 + 10), toY(rodY2));
    ctx.stroke();
    ctx.setLineDash([]);

    // Rod spacing dimension (120 mm)
    this.drawLinearDimension(ctx, toX(-this.fw/2 + 30), toY(rodY1), toX(-this.fw/2 + 30), toY(rodY2), '120.0 (ROD CTC)', -25, false);

    // C. Structural Aluminum Frame Boundary (500.0 x 400.0 mm)
    ctx.strokeStyle = '#79c0ff';
    ctx.lineWidth = 2.5;
    ctx.strokeRect(toX(-this.fw / 2), toY(this.fh / 2), this.fw * scale, this.fh * scale);

    // Diagonal stiffeners / corner gusset plates
    ctx.strokeStyle = '#1d4ed8';
    ctx.lineWidth = 1.0;
    const gusset = 25;
    [[-1, 1], [1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => {
      ctx.beginPath();
      ctx.moveTo(toX(sx * (this.fw/2 - gusset)), toY(sy * this.fh/2));
      ctx.lineTo(toX(sx * this.fw/2), toY(sy * (this.fh/2 - gusset)));
      ctx.stroke();
    });

    // Frame Major Dimensions
    // 500.0 mm Width (Top dimension)
    this.drawLinearDimension(ctx, toX(-this.fw / 2), toY(this.fh / 2), toX(this.fw / 2), toY(this.fh / 2), `${this.fw.toFixed(1)} mm FRAME WIDTH`, 32, true);
    // 400.0 mm Height (Right dimension)
    this.drawLinearDimension(ctx, toX(this.fw / 2), toY(this.fh / 2), toX(this.fw / 2), toY(-this.fh / 2), `${this.fh.toFixed(1)} mm FRAME HEIGHT`, 38, false);

    // D. Safe Feasible Workspace Boundary (360.0 x 280.0 mm)
    const wsXMin = this.ws.x_min_m * 1000.0;
    const wsXMax = this.ws.x_max_m * 1000.0;
    const wsYMin = this.ws.y_min_m * 1000.0;
    const wsYMax = this.ws.y_max_m * 1000.0;
    const wsW = wsXMax - wsXMin;
    const wsH = wsYMax - wsYMin;

    ctx.save();
    ctx.setLineDash([6, 3]);
    ctx.strokeStyle = '#39c5bb';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(toX(wsXMin), toY(wsYMax), wsW * scale, wsH * scale);
    ctx.fillStyle = 'rgba(57, 197, 187, 0.04)';
    ctx.fillRect(toX(wsXMin), toY(wsYMax), wsW * scale, wsH * scale);
    ctx.restore();

    // Clearance callout (20 mm clearance from frame border)
    ctx.strokeStyle = '#39c5bb';
    ctx.lineWidth = 0.8;
    this.drawLinearDimension(ctx, toX(-this.fw/2), toY(wsYMax), toX(wsXMin), toY(wsYMax), '20.0 CLEARANCE', 18, true);
    // Workspace internal dimensions
    this.drawLinearDimension(ctx, toX(wsXMin), toY(wsYMin), toX(wsXMax), toY(wsYMin), `${wsW.toFixed(1)} mm (WORKSPACE X)`, -24, true);

    // E. 4x Actuator Stepper Motors (28BYJ-48 5VDC, P/N: 15031801, dia 28 mm, 35 mm pitch) & Winch Drums (dia 20.0 mm)
    const canRadMm = 14;
    const canOffsetMm = 8;
    this.anchors.forEach(([ax, ay], i) => {
      const isLeft = ax < 0;
      const isTop = ay > 0;
      const dirX = isLeft ? -1 : 1;
      const dirY = isTop ? 1 : -1;
      const canX = ax + dirX * (canOffsetMm * 0.7071);
      const canY = ay + dirY * (canOffsetMm * 0.7071);

      // Stamped mounting ears (35 mm pitch, 42 mm across)
      ctx.save();
      ctx.translate(toX(canX), toY(canY));
      ctx.rotate(Math.atan2(dirY, dirX) + Math.PI / 4);
      ctx.fillStyle = 'rgba(100, 116, 139, 0.4)';
      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 1;
      ctx.fillRect(-21 * scale, -4 * scale, 42 * scale, 8 * scale);
      ctx.strokeRect(-21 * scale, -4 * scale, 42 * scale, 8 * scale);
      // M3 screw holes (35 mm pitch)
      ctx.fillStyle = '#38bdf8';
      [-17.5, 17.5].forEach(hx => {
        ctx.beginPath();
        ctx.arc(hx * scale, 0, 1.8, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();

      // Cylindrical tin-can body (dia 28.0 mm)
      ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(toX(canX), toY(canY), canRadMm * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Blue terminal housing representation
      const blueX = canX + dirX * 11;
      const blueY = canY + dirY * 11;
      ctx.fillStyle = '#1d5bc7';
      ctx.strokeStyle = '#60a5fa';
      ctx.fillRect(toX(blueX - 5), toY(blueY + 5), 10 * scale, 10 * scale);
      ctx.strokeRect(toX(blueX - 5), toY(blueY + 5), 10 * scale, 10 * scale);

      // Spool Winch Drum (radius = 10 mm, diameter = 20 mm)
      ctx.fillStyle = '#facc15';
      ctx.strokeStyle = '#ca8a04';
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.arc(toX(ax), toY(ay), this.drumR * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Drum Center Shaft
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(toX(ax), toY(ay), 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Anchor Coordinate Callout Flag
      ctx.fillStyle = '#93c5fd';
      ctx.font = 'bold 9px "JetBrains Mono", monospace';
      const anchorName = `A${i+1} [C${i+1}]`;
      const coordStr = `(${ax > 0 ? '+' : ''}${ax.toFixed(0)}, ${ay > 0 ? '+' : ''}${ay.toFixed(0)})`;
      const flagX = toX(ax + (isLeft ? -10 : 10));
      const flagY = toY(ay + (isTop ? 22 : -20));
      ctx.textAlign = isLeft ? 'right' : 'left';
      ctx.fillText(anchorName, flagX, flagY);
      ctx.fillStyle = '#64748b';
      ctx.fillText(coordStr, flagX, flagY + 11);
    });

    // F. End-Effector Platform Footprint (100.0 x 80.0 x 6.0 mm)
    const curX = (this.latestTelemetry && this.showLiveTelemetry) ? this.latestTelemetry.platform_pos[0] : 0.0;
    const curY = (this.latestTelemetry && this.showLiveTelemetry) ? this.latestTelemetry.platform_pos[1] : 0.0;

    // Cables Routing (Yellow Dyneema Lines)
    this.anchors.forEach(([ax, ay], i) => {
      const [bx, by] = this.attachments[i];
      const px = curX + bx;
      const py = curY + by;

      ctx.strokeStyle = '#facc15';
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(toX(ax), toY(ay));
      ctx.lineTo(toX(px), toY(py));
      ctx.stroke();

      // Cable dynamic length callout
      const cableLenMm = Math.hypot(ax - px, ay - py);
      const midX = (ax + px) / 2;
      const midY = (ay + py) / 2;
      ctx.fillStyle = '#fef08a';
      ctx.font = '8px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`L${i+1}=${cableLenMm.toFixed(1)}mm`, toX(midX), toY(midY) - 5);

      // Eyelet fastener at platform
      ctx.fillStyle = '#facc15';
      ctx.beginPath();
      ctx.arc(toX(px), toY(py), 3.0, 0, Math.PI * 2);
      ctx.fill();
    });

    // Platform Body (100 x 80 mm)
    ctx.fillStyle = 'rgba(37, 99, 235, 0.75)';
    ctx.strokeStyle = '#60a5fa';
    ctx.lineWidth = 2.0;
    const platX0 = curX - this.pw / 2;
    const platY0 = curY + this.ph / 2;
    ctx.fillRect(toX(platX0), toY(platY0), this.pw * scale, this.ph * scale);
    ctx.strokeRect(toX(platX0), toY(platY0), this.pw * scale, this.ph * scale);

    // Platform LM10UU Linear Bearing Blocks on guide rods
    const bW = 28 * scale;
    const bH = 14 * scale;
    ctx.fillStyle = '#475569';
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    // Top bearing block
    ctx.fillRect(toX(curX) - bW/2, toY(rodY1) - bH/2, bW, bH);
    ctx.strokeRect(toX(curX) - bW/2, toY(rodY1) - bH/2, bW, bH);
    // Bottom bearing block
    ctx.fillRect(toX(curX) - bW/2, toY(rodY2) - bH/2, bW, bH);
    ctx.strokeRect(toX(curX) - bW/2, toY(rodY2) - bH/2, bW, bH);

    // Platform Center Crosshair & Coordinates
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(toX(curX) - 8, toY(curY));
    ctx.lineTo(toX(curX) + 8, toY(curY));
    ctx.moveTo(toX(curX), toY(curY) - 8);
    ctx.lineTo(toX(curX), toY(curY) + 8);
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`P [${curX.toFixed(1)}, ${curY.toFixed(1)}]`, toX(curX), toY(curY) + 14);

    // Platform Dimensions (100.0 x 80.0 mm)
    this.drawLinearDimension(ctx, toX(platX0), toY(platY0), toX(platX0 + this.pw), toY(platY0), `${this.pw.toFixed(1)} PLATFORM W`, 16, true);
    this.drawLinearDimension(ctx, toX(platX0 + this.pw), toY(platY0), toX(platX0 + this.pw), toY(platY0 - this.ph), `${this.ph.toFixed(1)} H`, 16, false);

    // Draw Breadcrumb Drawing Trail (Pen Plotter effect)
    if (this.pathPlanner && this.pathPlanner.breadcrumbTrail.length > 1) {
      const trail = this.pathPlanner.breadcrumbTrail;
      ctx.save();
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.0;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(toX(trail[0][0]), toY(trail[0][1]));
      for (let i = 1; i < trail.length; i++) {
        ctx.lineTo(toX(trail[i][0]), toY(trail[i][1]));
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw Planned Waypoints Polyline
    if (this.pathPlanner && this.pathPlanner.waypoints.length > 0) {
      const wps = this.pathPlanner.waypoints;
      ctx.save();
      if (wps.length > 1) {
        ctx.strokeStyle = '#facc15';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(toX(wps[0][0]), toY(wps[0][1]));
        for (let i = 1; i < wps.length; i++) {
          ctx.lineTo(toX(wps[i][0]), toY(wps[i][1]));
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      wps.forEach(([wx, wy], idx) => {
        const px = toX(wx);
        const py = toY(wy);
        ctx.fillStyle = idx === 0 ? '#4ade80' : (idx === wps.length - 1 ? '#f87171' : '#facc15');
        ctx.beginPath();
        ctx.arc(px, py, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#0f172a';
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    }

    ctx.restore();
  }

  drawSectionElevation(ctx, x, y, w, h) {
    ctx.save();
    // Inset Background Card
    ctx.fillStyle = 'rgba(10, 25, 47, 0.85)';
    ctx.strokeStyle = '#1e40af';
    ctx.lineWidth = 1.0;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);

    // Section Header
    ctx.fillStyle = '#93c5fd';
    ctx.font = 'bold 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText('SECTION B-B: FRONT ELEVATION / DEPTH STACK-UP (XZ PLANE)', x + 10, y + 16);

    const floorY = y + h - 22;
    const secScale = Math.min((w - 220) / this.fw, (h - 40) / this.fd);

    const toSecX = (x_mm) => x + 90 + (x_mm + this.fw / 2) * secScale;
    const toSecZ = (z_mm) => floorY - z_mm * secScale;

    // Frame Base & Uprights (Depth = 120.0 mm)
    ctx.strokeStyle = '#60a5fa';
    ctx.lineWidth = 2.0;
    // Lower plate / bed
    ctx.strokeRect(toSecX(-this.fw/2), toSecZ(10), this.fw * secScale, 10 * secScale);
    // Vertical corner extrusions
    ctx.strokeRect(toSecX(-this.fw/2), toSecZ(this.fd), 20 * secScale, this.fd * secScale);
    ctx.strokeRect(toSecX(this.fw/2 - 20), toSecZ(this.fd), 20 * secScale, this.fd * secScale);

    // Guide Rods elevation (at Z = 60 mm)
    ctx.fillStyle = '#38bdf8';
    ctx.fillRect(toSecX(-this.fw/2), toSecZ(65), this.fw * secScale, 10 * secScale);

    // Platform plate (6.0 mm thickness)
    ctx.fillStyle = '#2563eb';
    ctx.strokeStyle = '#93c5fd';
    ctx.lineWidth = 1;
    ctx.fillRect(toSecX(-this.pw/2), toSecZ(68), this.pw * secScale, 6 * secScale);
    ctx.strokeRect(toSecX(-this.pw/2), toSecZ(68), this.pw * secScale, 6 * secScale);

    // Depth Dimension: 120.0 mm
    this.drawLinearDimension(ctx, toSecX(this.fw/2 + 10), toSecZ(this.fd), toSecX(this.fw/2 + 10), toSecZ(0), '120.0 mm DEPTH', 16, false);
    // Platform Plate Thickness: 6.0 mm
    ctx.fillStyle = '#bfdbfe';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('THK: 6.0 mm', toSecX(this.pw/2 + 5), toSecZ(65));

    ctx.restore();
  }

  drawBOMTable(ctx, x, y, w) {
    ctx.save();
    const rows = [
      { id: '1', item: 'Extruded Al Frame 2020', qty: '4', spec: '500x400x120 mm envelope' },
      { id: '2', item: 'End-Effector Carriage', qty: '1', spec: '100x80x6 mm (0.50 kg)' },
      { id: '3', item: '28BYJ-48 Stepper Motors', qty: '4', spec: '5VDC, P/N: 15031801, 64:1' },
      { id: '4', item: 'Winch Spool Drums', qty: '4', spec: 'dia 20.0 mm (r=10.0 mm)' },
      { id: '5', item: 'Dyneema UHMWPE Cable', qty: '4', spec: 'dia 1.0 mm, 300 N max' },
      { id: '6', item: 'Dual Linear Guide Rods', qty: '2', spec: 'dia 10.0 mm, CTC 120 mm' },
      { id: '7', item: 'Linear Ball Bearings', qty: '4', spec: 'LM10UU anti-rotation' },
      { id: '8', item: 'Optical / Micro Limit Sw.', qty: '4', spec: 'Safety travel limits' }
    ];

    const rowH = 17;
    const tableH = 26 + rows.length * rowH;

    // Background & Border
    ctx.fillStyle = 'rgba(6, 19, 37, 0.95)';
    ctx.fillRect(x, y, w, tableH);
    ctx.strokeStyle = '#1d4ed8';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(x, y, w, tableH);

    // Header Bar
    ctx.fillStyle = '#1e3a5f';
    ctx.fillRect(x, y, w, 22);
    ctx.fillStyle = '#60a5fa';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText('BILL OF MATERIALS (BOM) / SCHEDULE', x + 8, y + 14);

    // Columns: No (20px), Component (110px), Qty (30px), Specification (remaining)
    let curY = y + 22;
    rows.forEach((r, idx) => {
      if (idx % 2 === 1) {
        ctx.fillStyle = 'rgba(15, 23, 42, 0.5)';
        ctx.fillRect(x, curY, w, rowH);
      }
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(x, curY + rowH);
      ctx.lineTo(x + w, curY + rowH);
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '8.5px "JetBrains Mono", monospace';
      ctx.fillText(r.id, x + 6, curY + 12);
      ctx.fillStyle = '#e2e8f0';
      ctx.fillText(r.item, x + 24, curY + 12);
      ctx.fillStyle = '#38bdf8';
      ctx.fillText(r.qty, x + 155, curY + 12);
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(r.spec, x + 180, curY + 12);

      curY += rowH;
    });

    ctx.restore();
  }

  drawTitleBlock(ctx, x, y, w, h) {
    ctx.save();
    // Classic Blueprint Title Block (ISO 7200 format)
    ctx.fillStyle = 'rgba(6, 19, 37, 0.98)';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);

    // Internal Grid lines
    ctx.strokeStyle = '#1e40af';
    ctx.lineWidth = 1.0;
    // Horizontal dividers
    ctx.beginPath();
    ctx.moveTo(x, y + 28);
    ctx.lineTo(x + w, y + 28);
    ctx.moveTo(x, y + 56);
    ctx.lineTo(x + w, y + 56);
    ctx.moveTo(x, y + 84);
    ctx.lineTo(x + w, y + 84);
    ctx.stroke();

    // Vertical divider
    ctx.beginPath();
    ctx.moveTo(x + w * 0.55, y + 28);
    ctx.lineTo(x + w * 0.55, y + h);
    ctx.stroke();

    // Top Header
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 11px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText('PLANAR CDPR 2-DOF TESTBED', x + 10, y + 18);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText('SHEET 1 OF 1', x + w - 10, y + 18);

    // Drawing Title & Number
    ctx.textAlign = 'left';
    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('DRAWING NO:', x + 10, y + 40);
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
    ctx.fillText('CDPR-DWG-001-REV-B', x + 10, y + 51);

    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('TOLERANCE:', x + w * 0.55 + 8, y + 40);
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.fillText('±0.5 mm / ±0.2°', x + w * 0.55 + 8, y + 51);

    // Material & Units
    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('MATERIAL / FINISH:', x + 10, y + 68);
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
    ctx.fillText('6061-T6 AL / POM / HARDENED SUS', x + 10, y + 79);

    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('CAD RATIO:', x + w * 0.55 + 8, y + 68);
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.fillText('1:2 (MILLIMETERS)', x + w * 0.55 + 8, y + 79);

    // Third Angle Projection Symbol & Status
    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('PROJECTION:', x + 10, y + 96);

    // Draw Third Angle Projection cone and circle
    this.drawProjectionSymbol(ctx, x + 85, y + 97);

    ctx.fillStyle = '#64748b';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('STATUS:', x + w * 0.55 + 8, y + 96);
    ctx.fillStyle = '#4ade80';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.fillText('VERIFIED FOR PROTOTYPE', x + w * 0.55 + 8, y + 106);

    ctx.restore();
  }

  drawProjectionSymbol(ctx, px, py) {
    ctx.save();
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 0.8;
    // Frustum cone
    ctx.beginPath();
    ctx.moveTo(px - 14, py - 6);
    ctx.lineTo(px, py - 3);
    ctx.lineTo(px, py + 3);
    ctx.lineTo(px - 14, py + 6);
    ctx.closePath();
    ctx.stroke();
    // Target circles
    ctx.beginPath();
    ctx.arc(px + 10, py, 3, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(px + 10, py, 6, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  drawLinearDimension(ctx, x1, y1, x2, y2, text, offset, isHorizontal = true) {
    ctx.save();
    ctx.strokeStyle = '#60a5fa';
    ctx.fillStyle = '#bfdbfe';
    ctx.lineWidth = 1.0;
    ctx.font = 'bold 8.5px "JetBrains Mono", monospace';

    const extLen = Math.abs(offset) + 6;
    const sign = offset >= 0 ? 1 : -1;

    if (isHorizontal) {
      const dimY = y1 - offset;
      // Extension lines
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x1, y1 - sign * extLen);
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2, y2 - sign * extLen);
      ctx.stroke();

      // Dimension line
      ctx.beginPath();
      ctx.moveTo(x1, dimY);
      ctx.lineTo(x2, dimY);
      ctx.stroke();

      // Dimension tick marks / arrowheads
      this.drawArrowhead(ctx, x1, dimY, 1, 0);
      this.drawArrowhead(ctx, x2, dimY, -1, 0);

      // Text label
      ctx.textAlign = 'center';
      ctx.fillText(text, (x1 + x2) / 2, dimY - 4);
    } else {
      const dimX = x1 + offset;
      // Extension lines
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x1 + sign * extLen, y1);
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 + sign * extLen, y2);
      ctx.stroke();

      // Dimension line
      ctx.beginPath();
      ctx.moveTo(dimX, y1);
      ctx.lineTo(dimX, y2);
      ctx.stroke();

      // Arrowheads
      this.drawArrowhead(ctx, dimX, y1, 0, 1);
      this.drawArrowhead(ctx, dimX, y2, 0, -1);

      // Text label rotated
      ctx.save();
      ctx.translate(dimX + 11, (y1 + y2) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.fillText(text, 0, 0);
      ctx.restore();
    }

    ctx.restore();
  }

  drawArrowhead(ctx, x, y, dx, dy) {
    const len = 6;
    const wid = 3;
    ctx.save();
    ctx.fillStyle = '#60a5fa';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + dx * len - dy * wid, y + dy * len + dx * wid);
    ctx.lineTo(x + dx * len + dy * wid, y + dy * len - dx * wid);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
}

window.BlueprintView = BlueprintView;
