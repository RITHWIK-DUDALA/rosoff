/**
 * PlotManager - Real-Time Kinematic & Actuator Analytics Engine
 * Manages 6 high-resolution telemetry graphs and live KPI metric readouts:
 * 1. Position & Tracking Error Dynamics (mm)
 * 2. Cable Tensions T1..T4 (N) with 300N Limit
 * 3. Motor Rotational Speeds RPM1..RPM4 with ±300 RPM Limits
 * 4. Actuator Spool Torques τ1..τ4 (Nm) with 0.4 Nm Rated Limit
 * 5. Jacobian Conditioning κ(J) & FK Residual Norm (mm)
 * 6. Cable Velocities dl/dt (mm/s)
 */
class PlotManager {
  constructor() {
    this.historyLength = 120; // Default window: 120 samples (~4 sec at 30Hz)
    this.isPaused = false;

    // Time & Data Histories
    this.timeHistory = [];
    this.posActual = { x: [], y: [] };
    this.trackingErrorHistory = [];
    this.tensionsHistory = [[], [], [], []];
    this.rpmsHistory = [[], [], [], []];
    this.torquesHistory = [[], [], [], []];
    this.conditionHistory = [];
    this.fkResidualHistory = [];
    this.cableRatesHistory = [[], [], [], []];

    // Peak KPI metrics
    this.peakError = 0.0;
    this.peakTension = 0.0;
    this.peakRpm = 0.0;
    this.peakTorque = 0.0;

    // DOM Elements - Canvases
    this.cvsPos = document.getElementById('plot-pos-canvas');
    this.cvsTen = document.getElementById('plot-tension-canvas');
    this.cvsRpm = document.getElementById('plot-rpm-canvas');
    this.cvsTorque = document.getElementById('plot-torque-canvas');
    this.cvsCond = document.getElementById('plot-cond-canvas');
    this.cvsRates = document.getElementById('plot-rates-canvas');

    // DOM Elements - KPIs
    this.kpiMaxError = document.getElementById('kpi-max-error');
    this.kpiCurrError = document.getElementById('kpi-curr-error');
    this.kpiMaxTension = document.getElementById('kpi-max-tension');
    this.kpiMaxRpm = document.getElementById('kpi-max-rpm');
    this.kpiMaxTorque = document.getElementById('kpi-max-torque');
    this.kpiCondNo = document.getElementById('kpi-cond-no');
    this.kpiCondEval = document.getElementById('kpi-cond-eval');
    this.kpiFeasBadge = document.getElementById('kpi-feas-badge');
    this.kpiFeasSub = document.getElementById('kpi-feas-sub');

    // Controls
    this.btnPause = document.getElementById('btn-chart-pause');
  }

  setWindow(windowSize) {
    this.historyLength = Math.max(30, parseInt(windowSize) || 120);
    this.trimBuffers();
    this.render();
  }

  togglePause() {
    this.isPaused = !this.isPaused;
    if (this.btnPause) {
      this.btnPause.textContent = this.isPaused ? '▶️ Resume' : '⏸️ Pause';
      this.btnPause.style.background = this.isPaused ? '#fef3c7' : '';
      this.btnPause.style.borderColor = this.isPaused ? '#f59e0b' : '';
      this.btnPause.style.color = this.isPaused ? '#b45309' : '';
    }
    return this.isPaused;
  }

  clear() {
    this.timeHistory = [];
    this.posActual = { x: [], y: [] };
    this.trackingErrorHistory = [];
    this.tensionsHistory = [[], [], [], []];
    this.rpmsHistory = [[], [], [], []];
    this.torquesHistory = [[], [], [], []];
    this.conditionHistory = [];
    this.fkResidualHistory = [];
    this.cableRatesHistory = [[], [], [], []];

    this.peakError = 0.0;
    this.peakTension = 0.0;
    this.peakRpm = 0.0;
    this.peakTorque = 0.0;

    this.updateKPIs(null);
    this.render();
  }

  trimBuffers() {
    while (this.timeHistory.length > this.historyLength) {
      this.timeHistory.shift();
      this.posActual.x.shift();
      this.posActual.y.shift();
      this.trackingErrorHistory.shift();
      for (let i = 0; i < 4; i++) {
        this.tensionsHistory[i].shift();
        this.rpmsHistory[i].shift();
        this.torquesHistory[i].shift();
        this.cableRatesHistory[i].shift();
      }
      this.conditionHistory.shift();
      this.fkResidualHistory.shift();
    }
  }

  pushData(telemetry) {
    if (!telemetry || this.isPaused) return;

    const t = telemetry.sim_time_s || 0;
    const err = telemetry.tracking_error_mm != null ? telemetry.tracking_error_mm : 0;
    const px = (telemetry.platform_pos && telemetry.platform_pos[0] != null) ? telemetry.platform_pos[0] : 0;
    const py = (telemetry.platform_pos && telemetry.platform_pos[1] != null) ? telemetry.platform_pos[1] : 0;

    this.timeHistory.push(t);
    this.posActual.x.push(px);
    this.posActual.y.push(py);
    this.trackingErrorHistory.push(err);

    // Cable Tensions & Motor States
    for (let i = 0; i < 4; i++) {
      const ten = telemetry.cable_tensions_N ? (telemetry.cable_tensions_N[i] || 0) : 0;
      const rpm = telemetry.motor_speeds_rpm ? (telemetry.motor_speeds_rpm[i] || 0) : 0;
      const tau = telemetry.motor_torques_Nm ? (telemetry.motor_torques_Nm[i] || 0) : 0;
      const rate = telemetry.cable_rates_mm_s ? (telemetry.cable_rates_mm_s[i] || 0) : 0;

      this.tensionsHistory[i].push(ten);
      this.rpmsHistory[i].push(rpm);
      this.torquesHistory[i].push(tau);
      this.cableRatesHistory[i].push(rate);

      if (ten > this.peakTension) this.peakTension = ten;
      if (Math.abs(rpm) > this.peakRpm) this.peakRpm = Math.abs(rpm);
      if (Math.abs(tau) > this.peakTorque) this.peakTorque = Math.abs(tau);
    }

    if (err > this.peakError) this.peakError = err;

    // Condition number & FK Residual
    const cond = telemetry.condition_number != null ? telemetry.condition_number : 1.0;
    this.conditionHistory.push(cond);

    let resNorm = 0.0;
    if (telemetry.constraint_residuals_mm && telemetry.constraint_residuals_mm.length > 0) {
      let sumSq = 0;
      for (const r of telemetry.constraint_residuals_mm) sumSq += r * r;
      resNorm = Math.sqrt(sumSq);
    }
    this.fkResidualHistory.push(resNorm);

    this.trimBuffers();
    this.updateKPIs(telemetry);
    this.render();
  }

  updateKPIs(telem) {
    if (!telem) {
      if (this.kpiMaxError) this.kpiMaxError.textContent = '0.00 mm';
      if (this.kpiCurrError) this.kpiCurrError.textContent = 'Curr: 0.00 mm';
      if (this.kpiMaxTension) this.kpiMaxTension.textContent = '0.0 N';
      if (this.kpiMaxRpm) this.kpiMaxRpm.textContent = '0.0 RPM';
      if (this.kpiMaxTorque) this.kpiMaxTorque.textContent = '0.00 Nm';
      if (this.kpiCondNo) this.kpiCondNo.textContent = '1.00';
      if (this.kpiCondEval) this.kpiCondEval.textContent = 'Well-Conditioned';
      if (this.kpiFeasBadge) {
        this.kpiFeasBadge.textContent = 'FEASIBLE';
        this.kpiFeasBadge.className = 'kpi-value text-green';
      }
      return;
    }

    const currErr = telem.tracking_error_mm != null ? telem.tracking_error_mm : 0;
    if (this.kpiMaxError) this.kpiMaxError.textContent = `${this.peakError.toFixed(2)} mm`;
    if (this.kpiCurrError) this.kpiCurrError.textContent = `Curr: ${currErr.toFixed(2)} mm`;

    if (this.kpiMaxTension) {
      this.kpiMaxTension.textContent = `${this.peakTension.toFixed(1)} N`;
      this.kpiMaxTension.className = `kpi-value ${this.peakTension > 290 ? 'text-accent' : 'text-gold'}`;
    }

    if (this.kpiMaxRpm) {
      this.kpiMaxRpm.textContent = `${this.peakRpm.toFixed(1)} RPM`;
      this.kpiMaxRpm.className = `kpi-value ${this.peakRpm > 290 ? 'text-accent' : 'text-blue'}`;
    }

    if (this.kpiMaxTorque) {
      this.kpiMaxTorque.textContent = `${this.peakTorque.toFixed(2)} Nm`;
      this.kpiMaxTorque.className = `kpi-value ${this.peakTorque > 0.38 ? 'text-accent' : 'text-green'}`;
    }

    const cond = telem.condition_number != null ? telem.condition_number : 1.0;
    if (this.kpiCondNo) this.kpiCondNo.textContent = cond.toFixed(2);
    if (this.kpiCondEval) {
      if (cond < 5.0) {
        this.kpiCondEval.textContent = 'Well-Conditioned';
        this.kpiCondEval.style.color = '#10b981';
      } else if (cond < 20.0) {
        this.kpiCondEval.textContent = 'Moderate Condition';
        this.kpiCondEval.style.color = '#f59e0b';
      } else {
        this.kpiCondEval.textContent = 'Near Singular Boundary';
        this.kpiCondEval.style.color = '#ef4444';
      }
    }

    if (this.kpiFeasBadge) {
      const isFeas = telem.tension_feasible !== false;
      this.kpiFeasBadge.textContent = isFeas ? 'FEASIBLE' : 'INFEASIBLE';
      this.kpiFeasBadge.className = `kpi-value ${isFeas ? 'text-green' : 'text-accent'}`;
      if (this.kpiFeasSub) {
        this.kpiFeasSub.textContent = isFeas ? 'T_min ≥ 2.0 N' : 'Slack / Force Limit';
        this.kpiFeasSub.style.color = isFeas ? 'var(--text-muted)' : '#dc2626';
      }
    }
  }

  exportCSV() {
    if (this.timeHistory.length === 0) {
      alert('No telemetry data points available to export.');
      return;
    }

    const headers = [
      'timestamp_s',
      'x_pos_mm',
      'y_pos_mm',
      'tracking_error_mm',
      'tension_c1_N',
      'tension_c2_N',
      'tension_c3_N',
      'tension_c4_N',
      'speed_m1_rpm',
      'speed_m2_rpm',
      'speed_m3_rpm',
      'speed_m4_rpm',
      'torque_spool1_Nm',
      'torque_spool2_Nm',
      'torque_spool3_Nm',
      'torque_spool4_Nm',
      'jacobian_cond_no',
      'fk_residual_norm_mm',
      'rate_c1_mm_s',
      'rate_c2_mm_s',
      'rate_c3_mm_s',
      'rate_c4_mm_s'
    ];

    const rows = [];
    rows.push(headers.join(','));

    for (let i = 0; i < this.timeHistory.length; i++) {
      const row = [
        this.timeHistory[i].toFixed(3),
        (this.posActual.x[i] || 0).toFixed(2),
        (this.posActual.y[i] || 0).toFixed(2),
        (this.trackingErrorHistory[i] || 0).toFixed(3),
        (this.tensionsHistory[0][i] || 0).toFixed(2),
        (this.tensionsHistory[1][i] || 0).toFixed(2),
        (this.tensionsHistory[2][i] || 0).toFixed(2),
        (this.tensionsHistory[3][i] || 0).toFixed(2),
        (this.rpmsHistory[0][i] || 0).toFixed(1),
        (this.rpmsHistory[1][i] || 0).toFixed(1),
        (this.rpmsHistory[2][i] || 0).toFixed(1),
        (this.rpmsHistory[3][i] || 0).toFixed(1),
        (this.torquesHistory[0][i] || 0).toFixed(3),
        (this.torquesHistory[1][i] || 0).toFixed(3),
        (this.torquesHistory[2][i] || 0).toFixed(3),
        (this.torquesHistory[3][i] || 0).toFixed(3),
        (this.conditionHistory[i] || 1.0).toFixed(2),
        (this.fkResidualHistory[i] || 0).toFixed(4),
        (this.cableRatesHistory[0][i] || 0).toFixed(2),
        (this.cableRatesHistory[1][i] || 0).toFixed(2),
        (this.cableRatesHistory[2][i] || 0).toFixed(2),
        (this.cableRatesHistory[3][i] || 0).toFixed(2)
      ];
      rows.push(row.join(','));
    }

    const csvContent = rows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `cdpr_telemetry_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  render() {
    // Only render if viewport is visible or has layout dimensions
    if (this.cvsPos && this.cvsPos.clientWidth > 0) {
      // 1. Position & Error Dynamics
      this.drawPlot(this.cvsPos, [
        { data: this.trackingErrorHistory, color: '#ef4444', label: 'Error' },
        { data: this.posActual.x, color: '#06b6d4', label: 'X Pos' },
        { data: this.posActual.y, color: '#10b981', label: 'Y Pos' }
      ], -150, 150, 'mm');

      // 2. Cable Tensions T1..T4 with 300N Limit
      this.drawPlot(this.cvsTen, [
        { data: this.tensionsHistory[0], color: '#f59e0b', label: 'C1' },
        { data: this.tensionsHistory[1], color: '#3b82f6', label: 'C2' },
        { data: this.tensionsHistory[2], color: '#10b981', label: 'C3' },
        { data: this.tensionsHistory[3], color: '#8b5cf6', label: 'C4' }
      ], 0, 50, 'N', [
        { value: 300, color: '#ef4444', label: '300N Limit' },
        { value: 2, color: '#94a3b8', label: '2N Min' }
      ]);

      // 3. Motor Speeds with ±300 RPM Limits
      this.drawPlot(this.cvsRpm, [
        { data: this.rpmsHistory[0], color: '#f59e0b', label: 'M1' },
        { data: this.rpmsHistory[1], color: '#3b82f6', label: 'M2' },
        { data: this.rpmsHistory[2], color: '#10b981', label: 'M3' },
        { data: this.rpmsHistory[3], color: '#8b5cf6', label: 'M4' }
      ], -300, 300, 'RPM', [
        { value: 300, color: '#ef4444', label: '+300 RPM' },
        { value: -300, color: '#ef4444', label: '-300 RPM' }
      ]);

      // 4. Actuator Torques with 0.4 Nm Limit
      this.drawPlot(this.cvsTorque, [
        { data: this.torquesHistory[0], color: '#f59e0b', label: 'τ1' },
        { data: this.torquesHistory[1], color: '#3b82f6', label: 'τ2' },
        { data: this.torquesHistory[2], color: '#10b981', label: 'τ3' },
        { data: this.torquesHistory[3], color: '#8b5cf6', label: 'τ4' }
      ], 0, 0.45, 'Nm', [
        { value: 0.40, color: '#ef4444', label: '0.40 Nm' }
      ]);

      // 5. Condition Number & FK Residual
      this.drawPlot(this.cvsCond, [
        { data: this.conditionHistory, color: '#06b6d4', label: 'κ(J)' },
        { data: this.fkResidualHistory, color: '#ef4444', label: 'FK Res' }
      ], 0, 10, 'Ratio/mm', [
        { value: 1.0, color: '#64748b', label: 'Isotropic' }
      ]);

      // 6. Cable Rates dl/dt
      this.drawPlot(this.cvsRates, [
        { data: this.cableRatesHistory[0], color: '#f59e0b', label: 'dl1/dt' },
        { data: this.cableRatesHistory[1], color: '#3b82f6', label: 'dl2/dt' },
        { data: this.cableRatesHistory[2], color: '#10b981', label: 'dl3/dt' },
        { data: this.cableRatesHistory[3], color: '#8b5cf6', label: 'dl4/dt' }
      ], -100, 100, 'mm/s');
    }
  }

  drawPlot(canvas, seriesList, defaultMin, defaultMax, unit, thresholdLines = []) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    if (w <= 0 || h <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }

    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // Dynamic auto-scaling with fallback defaults
    let yMin = defaultMin;
    let yMax = defaultMax;

    seriesList.forEach(s => {
      s.data.forEach(v => {
        if (v < yMin) yMin = v;
        if (v > yMax) yMax = v;
      });
    });

    // Check threshold lines for scale expansion if needed
    thresholdLines.forEach(th => {
      if (th.value > yMax && th.value <= defaultMax * 1.5) yMax = th.value;
      if (th.value < yMin && th.value >= defaultMin * 1.5) yMin = th.value;
    });

    const range = (yMax - yMin) || 1;
    const padLeft = 45;
    const padRight = 15;
    const padTop = 16;
    const padBottom = 22;
    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    // Background chart grid
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = 1;
    const gridRows = 4;
    for (let r = 0; r <= gridRows; r++) {
      const gy = padTop + (r / gridRows) * plotH;
      ctx.beginPath();
      ctx.moveTo(padLeft, gy);
      ctx.lineTo(w - padRight, gy);
      ctx.stroke();
    }

    // Zero-line if spanned
    if (yMin < 0 && yMax > 0) {
      const zeroNorm = (0 - yMin) / range;
      const zeroY = padTop + (1 - zeroNorm) * plotH;
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      ctx.moveTo(padLeft, zeroY);
      ctx.lineTo(w - padRight, zeroY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw reference threshold lines (e.g. 300N, 300 RPM, 0.4 Nm)
    thresholdLines.forEach(th => {
      if (th.value >= yMin && th.value <= yMax) {
        const thNorm = (th.value - yMin) / range;
        const thY = padTop + (1 - thNorm) * plotH;
        ctx.strokeStyle = th.color || '#ef4444';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(padLeft, thY);
        ctx.lineTo(w - padRight, thY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Label
        ctx.fillStyle = th.color || '#ef4444';
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.textAlign = 'right';
        ctx.fillText(th.label || '', w - padRight - 4, thY - 3);
      }
    });

    // Plot Border
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.strokeRect(padLeft, padTop, plotW, plotH);

    // Axis Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`${yMax >= 100 ? yMax.toFixed(0) : yMax.toFixed(1)}`, padLeft - 6, padTop + 10);
    ctx.fillText(`${((yMax + yMin) / 2) >= 100 ? ((yMax + yMin) / 2).toFixed(0) : ((yMax + yMin) / 2).toFixed(1)}`, padLeft - 6, padTop + plotH / 2 + 3);
    ctx.fillText(`${yMin >= 100 ? yMin.toFixed(0) : yMin.toFixed(1)}`, padLeft - 6, padTop + plotH - 2);

    // Bottom time labels
    ctx.textAlign = 'left';
    ctx.fillText('-' + ((this.historyLength / 30).toFixed(0)) + 's', padLeft, h - 8);
    ctx.textAlign = 'right';
    ctx.fillText('Now', w - padRight, h - 8);

    // Render Data Series
    const totalPts = this.timeHistory.length;
    if (totalPts >= 2) {
      seriesList.forEach(s => {
        if (!s.data || s.data.length < 2) return;
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 1.6;
        ctx.beginPath();

        const n = s.data.length;
        for (let i = 0; i < n; i++) {
          const x = padLeft + (i / (this.historyLength - 1)) * plotW;
          const yNorm = (s.data[i] - yMin) / range;
          const clampedNorm = Math.max(0, Math.min(1, yNorm));
          const y = padTop + (1 - clampedNorm) * plotH;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Current value readout at end of series line
        const lastVal = s.data[n - 1];
        if (lastVal != null) {
          const lastNorm = Math.max(0, Math.min(1, (lastVal - yMin) / range));
          const lastY = padTop + (1 - lastNorm) * plotH;
          ctx.fillStyle = s.color;
          ctx.beginPath();
          ctx.arc(padLeft + ((n - 1) / (this.historyLength - 1)) * plotW, lastY, 2.5, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    ctx.restore();
  }
}

window.PlotManager = PlotManager;
