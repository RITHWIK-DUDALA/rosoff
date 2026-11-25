/**
 * Real-time strip charts for PROJECT W.A.L.L.
 * Plots cable tensions, motor RPMs, kinematic conditioning, and thermal loads.
 */

export class AnalyticsCharts {
  constructor() {
    this.historyLength = 100;
    this.data = {
      tensions: { C1: [], C2: [], C3: [], C4: [] },
      motors: { M1: [], M2: [], M3: [], M4: [] },
      dexterity: [],
      error: [],
      temps: { M1: [], M2: [], M3: [], M4: [] }
    };

    this.cvTensions = document.getElementById('chart-tensions');
    this.cvMotors = document.getElementById('chart-motors');
    this.cvDexterity = document.getElementById('chart-dexterity');
    this.cvTemps = document.getElementById('chart-temps');
  }

  update(telemetry) {
    if (!telemetry) return;

    // Cable Tensions
    if (telemetry.cables && telemetry.cables.cables) {
      const c = telemetry.cables.cables;
      ['C1', 'C2', 'C3', 'C4'].forEach(cid => {
        const arr = this.data.tensions[cid];
        arr.push(c[cid].tension_n);
        if (arr.length > this.historyLength) arr.shift();
      });
    }

    // Motor RPMs & Temps
    if (telemetry.motors) {
      ['M1', 'M2', 'M3', 'M4'].forEach(mid => {
        const m = telemetry.motors[mid];
        if (m) {
          const arrRpm = this.data.motors[mid];
          arrRpm.push(m.rpm);
          if (arrRpm.length > this.historyLength) arrRpm.shift();

          const arrTemp = this.data.temps[mid];
          arrTemp.push(m.temperature_c);
          if (arrTemp.length > this.historyLength) arrTemp.shift();
        }
      });
    }

    // Dexterity & Tracking Error
    if (telemetry.end_effector) {
      this.data.dexterity.push(telemetry.end_effector.dexterity_index || 0);
      if (this.data.dexterity.length > this.historyLength) this.data.dexterity.shift();

      this.data.error.push(telemetry.end_effector.tracking_error_mm || 0);
      if (this.data.error.length > this.historyLength) this.data.error.shift();
    }

    this.render();
  }

  render() {
    this.renderMultiLine(this.cvTensions, [
      { data: this.data.tensions.C1, color: '#38bdf8', label: 'C1' },
      { data: this.data.tensions.C2, color: '#34d399', label: 'C2' },
      { data: this.data.tensions.C3, color: '#fbbf24', label: 'C3' },
      { data: this.data.tensions.C4, color: '#f43f5e', label: 'C4' }
    ], 0, 55, 'N');

    this.renderMultiLine(this.cvMotors, [
      { data: this.data.motors.M1, color: '#38bdf8', label: 'M1' },
      { data: this.data.motors.M2, color: '#34d399', label: 'M2' },
      { data: this.data.motors.M3, color: '#fbbf24', label: 'M3' },
      { data: this.data.motors.M4, color: '#f43f5e', label: 'M4' }
    ], -600, 600, 'RPM');

    this.renderMultiLine(this.cvDexterity, [
      { data: this.data.dexterity, color: '#06b6d4', label: 'KCI (0-1)' },
      { data: this.data.error, color: '#ef4444', label: 'Error (mm)' }
    ], 0, 1.2, '');

    this.renderMultiLine(this.cvTemps, [
      { data: this.data.temps.M1, color: '#38bdf8', label: 'M1' },
      { data: this.data.temps.M2, color: '#34d399', label: 'M2' },
      { data: this.data.temps.M3, color: '#fbbf24', label: 'M3' },
      { data: this.data.temps.M4, color: '#f43f5e', label: 'M4' }
    ], 20, 80, '°C');
  }

  renderMultiLine(canvas, seriesList, minVal, maxVal, unit) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth || 300;
    const h = canvas.height = canvas.clientHeight || 160;

    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let i = 0; i < 4; i++) {
      const y = (h / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    const valToY = (v) => h - ((v - minVal) / (maxVal - minVal || 1)) * h;

    seriesList.forEach(s => {
      if (s.data.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 1.5;

      const step = w / (this.historyLength - 1);
      s.data.forEach((val, idx) => {
        const x = idx * step;
        const y = Math.max(0, Math.min(h, valToY(val)));
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });

    // Min / Max labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px monospace';
    ctx.fillText(`${maxVal} ${unit}`, 5, 12);
    ctx.fillText(`${minVal} ${unit}`, 5, h - 4);
  }
}

