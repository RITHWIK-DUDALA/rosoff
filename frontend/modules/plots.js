/**
 * Real-time diagnostic chart renderer for 4 telemetry streams:
 * 1. Tracking Error (mm)
 * 2. Cable Tensions (N)
 * 3. Motor RPMs
 * 4. Actuator Torques (Nm)
 */
class PlotManager {
  constructor() {
    this.historyLength = 120; // 120 data points buffer
    this.timeHistory = [];

    this.trackingErrorHistory = [];
    this.tensionsHistory = [[], [], [], []];
    this.rpmsHistory = [[], [], [], []];
    this.torquesHistory = [[], [], [], []];

    this.cvsPos = document.getElementById('plot-pos-canvas');
    this.cvsTen = document.getElementById('plot-tension-canvas');
    this.cvsRpm = document.getElementById('plot-rpm-canvas');
    this.cvsTorque = document.getElementById('plot-torque-canvas');

    this.ctxPos = this.cvsPos.getContext('2d');
    this.ctxTen = this.cvsTen.getContext('2d');
    this.ctxRpm = this.cvsRpm.getContext('2d');
    this.ctxTorque = this.cvsTorque.getContext('2d');
  }

  pushData(telemetry) {
    if (!telemetry) return;

    this.timeHistory.push(telemetry.sim_time_s);
    this.trackingErrorHistory.push(telemetry.tracking_error_mm);

    for (let i = 0; i < 4; i++) {
      this.tensionsHistory[i].push(telemetry.cable_tensions_N[i] || 0);
      this.rpmsHistory[i].push(telemetry.motor_speeds_rpm[i] || 0);
      this.torquesHistory[i].push(telemetry.motor_torques_Nm[i] || 0);
    }

    if (this.timeHistory.length > this.historyLength) {
      this.timeHistory.shift();
      this.trackingErrorHistory.shift();
      for (let i = 0; i < 4; i++) {
        this.tensionsHistory[i].shift();
        this.rpmsHistory[i].shift();
        this.torquesHistory[i].shift();
      }
    }

    this.render();
  }

  render() {
    this.drawSinglePlot(this.cvsPos, this.ctxPos, [
      { data: this.trackingErrorHistory, color: '#f85149', label: 'Error' }
    ], 0, 5, 'mm');

    this.drawMultiPlot(this.cvsTen, this.ctxTen, this.tensionsHistory, 0, 45, 'N');
    this.drawMultiPlot(this.cvsRpm, this.ctxRpm, this.rpmsHistory, -300, 300, 'RPM');
    this.drawMultiPlot(this.cvsTorque, this.ctxTorque, this.torquesHistory, 0, 0.45, 'Nm');
  }

  drawSinglePlot(canvas, ctx, seriesList, defaultMin, defaultMax, unit) {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    ctx.clearRect(0, 0, w, h);

    if (this.timeHistory.length < 2) return;

    let yMin = defaultMin;
    let yMax = defaultMax;
    seriesList.forEach(s => {
      s.data.forEach(v => {
        if (v < yMin) yMin = v;
        if (v > yMax) yMax = v;
      });
    });

    const range = (yMax - yMin) || 1;

    // Draw baseline / grid
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(35, h - 15);
    ctx.lineTo(w, h - 15);
    ctx.stroke();

    // Axis labels
    ctx.fillStyle = '#8b949e';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.fillText(`${yMax.toFixed(1)} ${unit}`, 2, 12);
    ctx.fillText(`${yMin.toFixed(1)}`, 2, h - 16);

    seriesList.forEach(s => {
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      const n = s.data.length;
      for (let i = 0; i < n; i++) {
        const x = 35 + (i / (this.historyLength - 1)) * (w - 40);
        const yNorm = (s.data[i] - yMin) / range;
        const y = (h - 18) - yNorm * (h - 32);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });
  }

  drawMultiPlot(canvas, ctx, fourSeries, defaultMin, defaultMax, unit) {
    const colors = ['#ffd700', '#58a6ff', '#3fb950', '#d29922'];
    const seriesList = fourSeries.map((data, i) => ({
      data: data,
      color: colors[i],
      label: `C${i+1}`
    }));
    this.drawSinglePlot(canvas, ctx, seriesList, defaultMin, defaultMax, unit);
  }
}

window.PlotManager = PlotManager;
