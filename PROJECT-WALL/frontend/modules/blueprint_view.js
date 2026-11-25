/**
 * 2D Dimensioned Blueprint View for PROJECT W.A.L.L.
 * Renders orthographic planar view with exact dimensions, tension vectors,
 * margin boundaries, and progressive deposition bitmap.
 */

export class BlueprintView {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');

    // Surface bounds
    this.surfaceW = 800.0;
    this.surfaceH = 600.0;

    // Latest state
    this.x = 400.0;
    this.y = 300.0;
    this.estX = 400.0;
    this.estY = 300.0;
    this.tensions = [12, 12, 12, 12];
    this.dropletImg = null;

    this.onResize();
    window.addEventListener('resize', () => this.onResize());
  }

  onResize() {
    this.canvas.width = this.canvas.clientWidth || 800;
    this.canvas.height = this.canvas.clientHeight || 600;
    this.render();
  }

  update(telemetry) {
    if (!telemetry || !telemetry.end_effector) return;

    this.x = telemetry.end_effector.x_mm;
    this.y = telemetry.end_effector.y_mm;
    this.estX = telemetry.end_effector.estimated_x_mm;
    this.estY = telemetry.end_effector.estimated_y_mm;

    if (telemetry.cables && telemetry.cables.cables) {
      this.tensions = [
        telemetry.cables.cables.C1.tension_n,
        telemetry.cables.cables.C2.tension_n,
        telemetry.cables.cables.C3.tension_n,
        telemetry.cables.cables.C4.tension_n
      ];
    }

    if (telemetry.canvas_base64) {
      const img = new Image();
      img.onload = () => {
        this.dropletImg = img;
        this.render();
      };
      img.src = 'data:image/png;base64,' + telemetry.canvas_base64;
    } else {
      this.render();
    }
  }

  render() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, w, h);

    // Coordinate transformation: fit 800x600 mm in canvas with padding
    const padding = 50;
    const scale = Math.min((w - padding * 2) / this.surfaceW, (h - padding * 2) / this.surfaceH);
    const offsetX = (w - this.surfaceW * scale) / 2;
    const offsetY = (h - this.surfaceH * scale) / 2;

    const toScreenX = (xMm) => offsetX + xMm * scale;
    // Y inverted for 2D cartesian (Y=0 at bottom)
    const toScreenY = (yMm) => offsetY + (this.surfaceH - yMm) * scale;

    // 1. Grid
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 1;
    for (let x = 0; x <= this.surfaceW; x += 100) {
      ctx.beginPath();
      ctx.moveTo(toScreenX(x), toScreenY(0));
      ctx.lineTo(toScreenX(x), toScreenY(this.surfaceH));
      ctx.stroke();
    }
    for (let y = 0; y <= this.surfaceH; y += 100) {
      ctx.beginPath();
      ctx.moveTo(toScreenX(0), toScreenY(y));
      ctx.lineTo(toScreenX(this.surfaceW), toScreenY(y));
      ctx.stroke();
    }

    // 2. Surface Frame (800x600)
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.strokeRect(toScreenX(0), toScreenY(this.surfaceH), this.surfaceW * scale, this.surfaceH * scale);

    // 3. Printable Margins (100mm margin)
    ctx.strokeStyle = '#06b6d4';
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(toScreenX(100), toScreenY(500), (this.surfaceW - 200) * scale, (this.surfaceH - 200) * scale);
    ctx.setLineDash([]);

    // 4. Progressive Bitmap Deposition Overlay
    if (this.dropletImg) {
      ctx.drawImage(
        this.dropletImg,
        toScreenX(100),
        toScreenY(500),
        (this.surfaceW - 200) * scale,
        (this.surfaceH - 200) * scale
      );
    }

    // 5. Anchors (A1: UL, A2: UR, A3: LL, A4: LR)
    const anchors = [
      { id: 'A1', x: 0, y: this.surfaceH },
      { id: 'A2', x: this.surfaceW, y: this.surfaceH },
      { id: 'A3', x: 0, y: 0 },
      { id: 'A4', x: this.surfaceW, y: 0 }
    ];

    ctx.fillStyle = '#0284c7';
    anchors.forEach(a => {
      ctx.fillRect(toScreenX(a.x) - 10, toScreenY(a.y) - 10, 20, 20);
      ctx.fillStyle = '#fff';
      ctx.font = '10px monospace';
      ctx.fillText(a.id, toScreenX(a.x) + 12, toScreenY(a.y) + 4);
      ctx.fillStyle = '#0284c7';
    });

    // 6. Four Cables
    const hw = 50.0;
    const hh = 40.0;
    const eyelets = [
      { x: this.x - hw, y: this.y + hh },
      { x: this.x + hw, y: this.y + hh },
      { x: this.x - hw, y: this.y - hh },
      { x: this.x + hw, y: this.y - hh }
    ];

    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.strokeStyle = this.tensions[i] < 2.5 ? '#f59e0b' : (this.tensions[i] > 45 ? '#ef4444' : '#10b981');
      ctx.lineWidth = 2;
      ctx.moveTo(toScreenX(anchors[i].x), toScreenY(anchors[i].y));
      ctx.lineTo(toScreenX(eyelets[i].x), toScreenY(eyelets[i].y));
      ctx.stroke();

      // Tension text label
      const midX = (toScreenX(anchors[i].x) + toScreenX(eyelets[i].x)) / 2;
      const midY = (toScreenY(anchors[i].y) + toScreenY(eyelets[i].y)) / 2;
      ctx.fillStyle = '#f3f4f6';
      ctx.font = '11px monospace';
      ctx.fillText(`${this.tensions[i].toFixed(1)} N`, midX, midY);
    }

    // 7. Central Platform Box (100x80mm)
    const platSx = toScreenX(this.x - hw);
    const platSy = toScreenY(this.y + hh);
    const platSw = 100 * scale;
    const platSh = 80 * scale;

    ctx.fillStyle = 'rgba(6, 182, 212, 0.4)';
    ctx.fillRect(platSx, platSy, platSw, platSh);
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    ctx.strokeRect(platSx, platSy, platSw, platSh);

    // Crosshair at center
    ctx.strokeStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(toScreenX(this.x), toScreenY(this.y), 4, 0, Math.PI * 2);
    ctx.stroke();

    // FK Estimated coordinate marker
    ctx.strokeStyle = '#f59e0b';
    ctx.beginPath();
    ctx.arc(toScreenX(this.estX), toScreenY(this.estY), 6, 0, Math.PI * 2);
    ctx.stroke();
  }
}

