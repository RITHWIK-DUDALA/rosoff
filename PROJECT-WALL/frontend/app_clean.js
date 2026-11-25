/**
 * PROJECT W.A.L.L. — Unified 3D Digital Twin Cockpit App
 * Fully synchronized 3D mechanism, motors, Dyneema wires, compliance spring,
 * progressive surface canvas, and artwork toolpath generator.
 */

import { ThreeScene } from './modules/three_scene.js?v=7.0';

class ProjectWallCockpit {
  constructor() {
    const host = window.location.hostname || 'localhost';
    this.apiBase = `http://${host}:8000/api`;
    this.wsUrl = `ws://${host}:8000/ws`;
    this.pollingInterval = null;
    this.isFetching = false;

    // 1. Initialize Hero 3D Mechanism
    this.threeScene = new ThreeScene('three-viewport');

    // 2. 2D Progressive Surface Canvas
    this.studioCanvas = document.getElementById('studio-progressive-canvas');
    this.studioCtx = this.studioCanvas ? this.studioCanvas.getContext('2d') : null;

    this.dropletImg = null;
    this.latestTelemetry = null;

    // 3. Setup event listeners
    this.initViewToggle();
    this.initArtworkDropzone();
    this.initControls();
    this.initJogging();
    this.initTelemetry();

    this.resizeCanvas();
    window.addEventListener('resize', () => {
      this.resizeCanvas();
      this.threeScene.onResize();
    });
  }

  initViewToggle() {
    const btn3D = document.getElementById('btn-view-3d');
    const btn2D = document.getElementById('btn-view-canvas');
    const view3D = document.getElementById('three-viewport');
    const view2D = document.getElementById('canvas-2d-container');

    if (btn3D && btn2D && view3D && view2D) {
      btn3D.addEventListener('click', () => {
        btn3D.classList.add('active');
        btn2D.classList.remove('active');
        view3D.style.display = 'block';
        view2D.style.display = 'none';
        this.threeScene.onResize();
      });

      btn2D.addEventListener('click', () => {
        btn2D.classList.add('active');
        btn3D.classList.remove('active');
        view3D.style.display = 'none';
        view2D.style.display = 'block';
        this.resizeCanvas();
      });
    }
  }

  initArtworkDropzone() {
    const dropzone = document.getElementById('artwork-dropzone');
    const fileInput = document.getElementById('artwork-file-input');
    const browseBtn = document.getElementById('btn-browse-file');

    if (browseBtn && fileInput) {
      browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
      });
    }

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());

      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) this.handleFile(e.target.files[0]);
      });

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
          this.handleFile(e.dataTransfer.files[0]);
        }
      });
    }

    // Module radio toggle
    const radios = document.querySelectorAll('.module-radio');
    radios.forEach(r => {
      r.addEventListener('click', () => {
        radios.forEach(x => x.classList.remove('active'));
        r.classList.add('active');
        const inp = r.querySelector('input');
        if (inp) {
          inp.checked = true;
          this.threeScene.setModule(inp.value);
          fetch(`${this.apiBase}/actuator/swap`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ module_type: inp.value })
          }).catch(() => {});
        }
      });
    });
  }

  async handleFile(file) {
    // 1. Show immediate local preview & auto-detect aspect ratio
    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById('artwork-preview-box').style.display = 'flex';
      document.getElementById('artwork-thumbnail').src = e.target.result;
      document.getElementById('artwork-meta-name').textContent = file.name;
      document.getElementById('artwork-meta-details').textContent = `${(file.size / 1024).toFixed(1)} KB \u2022 Processing...`;

      const img = new Image();
      img.onload = () => {
        if (img.naturalWidth && img.naturalHeight) {
          const ratio = img.naturalWidth / img.naturalHeight;
          const wInp = document.getElementById('input-print-w');
          const hInp = document.getElementById('input-print-h');
          if (wInp && hInp) {
            let w = parseFloat(wInp.value) || 300;
            let h = Math.round(w / ratio);
            if (h > 380) {
              h = 380;
              w = Math.round(h * ratio);
            }
            if (w > 540) {
              w = 540;
              h = Math.round(w / ratio);
            }
            wInp.value = w;
            hInp.value = h;
          }
        }
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // 2. Upload to FastAPI backend with user dimensions
    const wInp = document.getElementById('input-print-w');
    const hInp = document.getElementById('input-print-h');
    const formData = new FormData();
    formData.append('file', file);
    if (wInp) formData.append('target_width_mm', parseFloat(wInp.value) || 300);
    if (hInp) formData.append('target_height_mm', parseFloat(hInp.value) || 250);

    try {
      const res = await fetch(`${this.apiBase}/image/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        document.getElementById('artwork-meta-details').textContent = `${data.job.canvas_size[0]} \u00D7 ${data.job.canvas_size[1]} px \u2022 Ready to print`;
        document.getElementById('artwork-wps-badge').textContent = `${data.job.raster_waypoints} waypoints generated`;
      } else {
        alert(data.detail || 'Upload failed');
      }
    } catch (err) {
      alert('Network error connecting to backend: ' + err.message);
    }
  }

  initControls() {
    // Start / Pause / Resume
    document.getElementById('btn-start-print-main').addEventListener('click', async () => {
      const res = await fetch(`${this.apiBase}/print/start`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) alert(data.detail || 'Failed to start print');
    });

    document.getElementById('btn-pause-print-main').addEventListener('click', async () => {
      await fetch(`${this.apiBase}/print/pause`, { method: 'POST' });
    });

    document.getElementById('btn-resume-print-main').addEventListener('click', async () => {
      await fetch(`${this.apiBase}/print/resume`, { method: 'POST' });
    });

    // Reset & E-STOP
    document.getElementById('btn-reset-sys').addEventListener('click', async () => {
      await fetch(`${this.apiBase}/control/reset`, { method: 'POST' });
    });

    document.getElementById('btn-estop-main').addEventListener('click', async () => {
      await fetch(`${this.apiBase}/control/estop`, { method: 'POST' });
    });

    // Scenarios Runner
    document.getElementById('btn-trigger-scenario').addEventListener('click', async () => {
      const scId = document.getElementById('select-scenario-exec').value;
      const res = await fetch(`${this.apiBase}/scenarios/run/${scId}`, { method: 'POST' });
      const data = await res.json();
      const msgBox = document.getElementById('scenario-result-msg');
      if (data.evaluation) {
        msgBox.textContent = `${scId}: ${data.evaluation.summary}`;
      } else {
        msgBox.textContent = `Executed ${scId}`;
      }
    });
  }

  initJogging() {
    const jog = async (dx, dy) => {
      const curX = this.latestTelemetry?.end_effector?.x_mm || 400.0;
      const curY = this.latestTelemetry?.end_effector?.y_mm || 300.0;
      await fetch(`${this.apiBase}/motion/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x_mm: curX + dx, y_mm: curY + dy })
      });
    };

    document.getElementById('jog-x-minus').addEventListener('click', () => jog(-10, 0));
    document.getElementById('jog-x-plus').addEventListener('click', () => jog(10, 0));
    document.getElementById('jog-y-minus').addEventListener('click', () => jog(0, -10));
    document.getElementById('jog-y-plus').addEventListener('click', () => jog(0, 10));
    document.getElementById('jog-center-btn').addEventListener('click', async () => {
      await fetch(`${this.apiBase}/motion/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x_mm: 400.0, y_mm: 300.0 })
      });
    });
  }

  initTelemetry() {
    const ws = new WebSocket(this.wsUrl);
    const dot = document.getElementById('live-indicator');
    const statusText = document.getElementById('ws-status-text');

    ws.onopen = () => {
      dot.className = 'live-dot connected';
      statusText.textContent = 'ONLINE (30 Hz)';
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
        this.pollingInterval = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.updateTelemetry(data);
      } catch (e) {
        console.error(e);
      }
    };

    ws.onerror = () => {
      dot.className = 'live-dot';
      statusText.textContent = 'REST FALLBACK';
      this.startRestPolling();
    };

    ws.onclose = () => {
      dot.className = 'live-dot';
      statusText.textContent = 'RECONNECTING';
      this.startRestPolling();
      setTimeout(() => this.initTelemetry(), 4000);
    };
  }

  startRestPolling() {
    if (this.pollingInterval) return;
    this.pollingInterval = setInterval(async () => {
      if (this.isFetching) return;
      this.isFetching = true;
      try {
        const res = await fetch(`${this.apiBase}/telemetry`);
        if (res.ok) {
          const data = await res.json();
          this.updateTelemetry(data);
        }
      } catch (e) {
        // Backend momentarily unavailable or reconnecting
      } finally {
        this.isFetching = false;
      }
    }, 250);
  }

  updateTelemetry(data) {
    this.latestTelemetry = data;

    // Header State & Clock
    if (data.supervisor) {
      document.getElementById('supervisor-badge').textContent = data.supervisor.state;
    }
    if (data.sim_time_s !== undefined) {
      document.getElementById('sim-clock').textContent = `T+ ${data.sim_time_s.toFixed(2)}s`;
    }

    // Top HUD
    if (data.end_effector) {
      const ee = data.end_effector;
      document.getElementById('hud-pos').textContent = `X: ${ee.x_mm.toFixed(1)} \u2022 Y: ${ee.y_mm.toFixed(1)}`;
      document.getElementById('hud-kci').textContent = ee.dexterity_index.toFixed(2);
      document.getElementById('hud-err').textContent = `${ee.tracking_error_mm.toFixed(2)} mm`;
    }

    if (data.deposition) {
      document.getElementById('hud-droplets').textContent = data.deposition.total_droplets;
      document.getElementById('hud-coverage').textContent = `${(data.deposition.coverage_ratio * 100).toFixed(1)}%`;
      document.getElementById('audit-cov').textContent = `${(data.deposition.coverage_ratio * 100).toFixed(1)}%`;
    }

    // Quality Audit
    if (data.quality_report) {
      const q = data.quality_report;
      document.getElementById('audit-delta-e').textContent = q.mean_delta_e.toFixed(2);
      document.getElementById('audit-mae').textContent = q.mean_absolute_error.toFixed(2);
      document.getElementById('audit-edge').textContent = `${(q.edge_fidelity_ratio * 100).toFixed(1)}%`;
    }

    // 4 Cables & Tensions
    const cablesObj = (data.cables && data.cables.cables) ? data.cables.cables : data.cables;
    if (cablesObj && cablesObj.C1) {
      ['C1', 'C2', 'C3', 'C4'].forEach((cid, idx) => {
        const cData = cablesObj[cid];
        if (!cData) return;
        const t = cData.tension_n !== undefined ? cData.tension_n : 12.0;
        const txtElem = document.getElementById(`t${idx+1}-val-text`);
        const barElem = document.getElementById(`t${idx+1}-bar`);

        if (txtElem) txtElem.textContent = `${t.toFixed(1)} N`;
        if (barElem) {
          const pct = Math.min(100, Math.max(0, (t / 50.0) * 100));
          barElem.style.width = `${pct}%`;
          if (cData.is_slack) {
            barElem.style.background = 'var(--accent-amber)';
          } else if (cData.is_overloaded) {
            barElem.style.background = 'var(--accent-red)';
          } else {
            barElem.style.background = 'var(--accent-green)';
          }
        }
      });

      // Update 3D Viewport with 4 thick solid cables and compliance spring
      if (data.end_effector) {
        this.threeScene.updatePlatform(
          data.end_effector.x_mm,
          data.end_effector.y_mm,
          [cablesObj.C1.tension_n, cablesObj.C2.tension_n, cablesObj.C3.tension_n, cablesObj.C4.tension_n]
        );
      }
    }

    // Dynamic Firing Spray State in 3D
    if (data.supervisor) {
      this.threeScene.setSprayActive(data.supervisor.state === 'PRINTING');
    }

    // 4 Motors
    if (data.motors) {
      ['M1', 'M2', 'M3', 'M4'].forEach((mid, idx) => {
        const m = data.motors[mid];
        const num = idx + 1;
        if (m) {
          const rpm = document.getElementById(`m${num}-rpm-val`);
          const tor = document.getElementById(`m${num}-torque-val`);
          const lay = document.getElementById(`m${num}-layer-val`);
          const tmp = document.getElementById(`m${num}-temp-val`);
          const curRpm = m.speed_rpm !== undefined ? m.speed_rpm : (m.rpm || 0);
          if (rpm) rpm.textContent = `${curRpm.toFixed(0)} RPM`;
          if (tor) tor.textContent = `${m.torque_nm.toFixed(2)} Nm`;
          if (lay) lay.textContent = m.effective_drum_radius_mm ? `r=${m.effective_drum_radius_mm.toFixed(1)}` : 'Layer 1';
          if (tmp) tmp.textContent = `${m.temperature_c.toFixed(1)}°C`;
        }
      });
    }

    // Progressive Droplet Buffer Texture
    if (data.canvas_base64) {
      this.threeScene.updateCanvasTexture(data.canvas_base64);
      if (this.studioCtx) {
        const img = new Image();
        img.onload = () => {
          this.dropletImg = img;
          this.renderStudioCanvas();
        };
        img.src = data.canvas_base64.startsWith('data:') ? data.canvas_base64 : ('data:image/jpeg;base64,' + data.canvas_base64);
      }
    } else if (this.studioCtx) {
      this.renderStudioCanvas();
    }
  }

  resizeCanvas() {
    if (!this.studioCanvas) return;
    const parent = this.studioCanvas.parentElement;
    if (!parent) return;
    this.studioCanvas.width = parent.clientWidth || 800;
    this.studioCanvas.height = parent.clientHeight || 550;
    this.renderStudioCanvas();
  }

  renderStudioCanvas() {
    if (!this.studioCtx) return;
    const ctx = this.studioCtx;
    const w = this.studioCanvas.width;
    const h = this.studioCanvas.height;
    ctx.clearRect(0, 0, w, h);

    const surfaceW = 800.0;
    const surfaceH = 600.0;
    const padding = 20;

    const scale = Math.min((w - padding * 2) / surfaceW, (h - padding * 2) / surfaceH);
    const offsetX = (w - surfaceW * scale) / 2;
    const offsetY = (h - surfaceH * scale) / 2;

    const toX = (x) => offsetX + x * scale;
    const toY = (y) => offsetY + (surfaceH - y) * scale;

    // Board Base
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(toX(0), toY(surfaceH), surfaceW * scale, surfaceH * scale);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.strokeRect(toX(0), toY(surfaceH), surfaceW * scale, surfaceH * scale);

    // Printable Boundary (100mm Margin)
    ctx.strokeStyle = '#f59e0b';
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(toX(100), toY(500), (surfaceW - 200) * scale, (surfaceH - 200) * scale);
    ctx.setLineDash([]);

    // Progressive Droplet Image (Full Surface Dimensions)
    if (this.dropletImg) {
      ctx.drawImage(
        this.dropletImg,
        toX(0),
        toY(surfaceH),
        surfaceW * scale,
        surfaceH * scale
      );
    }

    // Anchors
    const anchors = [
      { id: 'A1', x: 0, y: surfaceH },
      { id: 'A2', x: surfaceW, y: surfaceH },
      { id: 'A3', x: 0, y: 0 },
      { id: 'A4', x: surfaceW, y: 0 }
    ];
    anchors.forEach(a => {
      ctx.fillStyle = '#475569';
      ctx.fillRect(toX(a.x) - 8, toY(a.y) - 8, 16, 16);
      ctx.fillStyle = '#f59e0b';
      ctx.font = 'bold 10px monospace';
      ctx.fillText(a.id, toX(a.x) + 10, toY(a.y) + 4);
    });

    // Current Platform
    const curX = this.latestTelemetry?.end_effector?.x_mm || 400.0;
    const curY = this.latestTelemetry?.end_effector?.y_mm || 300.0;

    const pw = 100 * scale;
    const ph = 80 * scale;
    ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1.5;
    ctx.fillRect(toX(curX) - pw/2, toY(curY) - ph/2, pw, ph);
    ctx.strokeRect(toX(curX) - pw/2, toY(curY) - ph/2, pw, ph);

    // Cables
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1.5;
    const eyelets = [
      { x: curX - 50, y: curY + 40 },
      { x: curX + 50, y: curY + 40 },
      { x: curX - 50, y: curY - 40 },
      { x: curX + 50, y: curY - 40 }
    ];
    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.moveTo(toX(anchors[i].x), toY(anchors[i].y));
      ctx.lineTo(toX(eyelets[i].x), toY(eyelets[i].y));
      ctx.stroke();
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  new ProjectWallCockpit();
});
