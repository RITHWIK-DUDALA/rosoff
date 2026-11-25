/**
 * PROJECT W.A.L.L. — Processor & CAM Studio Application Logic
 * Coordinates artwork computer vision analysis, actuator classification,
 * paint recipe calculation, 4-cable motion planning, autonomous print execution,
 * real-time flight recording logs, and 3D digital twin synchronization.
 */

import { ThreeScene } from './three_scene.js?v=7.0';

export class ProcessorApp {
  constructor() {
    const host = window.location.hostname || 'localhost';
    this.apiBase = `http://${host}:8000/api`;
    this.wsUrl = `ws://${host}:8000/ws`;

    this.activePreset = 'preset_graphic_logo';
    this.selectedFile = null;
    this.currentReport = null;
    this.isPrinting = false;
    this.lastLogId = 0;
    this.allLogs = [];

    // 1. Initialize Synchronized 3D Digital Twin Viewport
    this.threeScene = new ThreeScene('proc-three-viewport');

    // 2. Progressive 2D Canvas Viewport
    this.canvas2D = document.getElementById('proc-progressive-canvas');
    this.ctx2D = this.canvas2D ? this.canvas2D.getContext('2d') : null;

    // 3. Setup UI Listeners & Telemetry
    this.initNavbarActions();
    this.initIngestionDropzone();
    this.initPresetButtons();
    this.initCamControls();
    this.initLogTerminal();
    this.initTelemetryConnection();

    // 4. Run Initial Analysis on Default Preset
    setTimeout(() => {
      this.analyzeCurrentSelection();
    }, 300);
  }

  initNavbarActions() {
    // Reset & Emergency Stop
    document.getElementById('btn-proc-reset')?.addEventListener('click', async () => {
      try {
        await fetch(`${this.apiBase}/control/reset`, { method: 'POST' });
        this.addLocalLog('ACTION', 'SUPERVISOR', 'Operator issued SYSTEM RESET.');
      } catch (e) {
        console.error(e);
      }
    });

    document.getElementById('btn-proc-estop')?.addEventListener('click', async () => {
      try {
        await fetch(`${this.apiBase}/control/estop`, { method: 'POST' });
        this.addLocalLog('FAULT', 'SUPERVISOR', 'EMERGENCY STOP ENGAGED BY OPERATOR.');
      } catch (e) {
        console.error(e);
      }
    });

    // Viewport 3D vs 2D Tabs
    const btn3D = document.getElementById('btn-tab-3d');
    const btnCanvas = document.getElementById('btn-tab-canvas');
    const view3D = document.getElementById('proc-three-viewport');
    const view2D = document.getElementById('proc-canvas-2d-wrap');

    if (btn3D && btnCanvas && view3D && view2D) {
      btn3D.addEventListener('click', () => {
        btn3D.classList.add('active');
        btnCanvas.classList.remove('active');
        view3D.style.display = 'block';
        view2D.style.display = 'none';
        this.threeScene.onResize();
      });

      btnCanvas.addEventListener('click', () => {
        btnCanvas.classList.add('active');
        btn3D.classList.remove('active');
        view3D.style.display = 'none';
        view2D.style.display = 'flex';
      });
    }
  }

  initIngestionDropzone() {
    const dropzone = document.getElementById('proc-dropzone');
    const fileInput = document.getElementById('proc-file-input');

    if (!dropzone || !fileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        this.handleFileUpload(files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });
  }

  handleFileUpload(file) {
    this.selectedFile = file;
    this.activePreset = null;

    // Deselect preset buttons
    document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));

    const dropPrimary = document.querySelector('.drop-primary');
    if (dropPrimary) {
      dropPrimary.textContent = `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`;
    }

    this.addLocalLog('ACTION', 'PROCESSOR', `Selected custom file for processing: ${file.name}`);
    this.analyzeCurrentSelection();
  }

  initPresetButtons() {
    const buttons = document.querySelectorAll('.btn-preset');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activePreset = btn.getAttribute('data-preset');
        this.selectedFile = null;

        const dropPrimary = document.querySelector('.drop-primary');
        if (dropPrimary) dropPrimary.textContent = 'Drop Artwork Image Here';

        this.addLocalLog('ACTION', 'PROCESSOR', `Selected engineering preset: ${this.activePreset}`);
        this.analyzeCurrentSelection();
      });
    });
  }

  initCamControls() {
    // Process & Classify Button
    const btnProcess = document.getElementById('btn-process-artwork');
    if (btnProcess) {
      btnProcess.addEventListener('click', () => this.analyzeCurrentSelection());
    }

    // Execute Print Job Button
    const btnExecute = document.getElementById('btn-execute-print-job');
    if (btnExecute) {
      btnExecute.addEventListener('click', () => this.executePrintJob());
    }

    // Pause / Resume
    document.getElementById('btn-pause-job')?.addEventListener('click', async () => {
      try {
        await fetch(`${this.apiBase}/print/pause`, { method: 'POST' });
        this.addLocalLog('ACTION', 'SUPERVISOR', 'Operator paused surface deposition.');
      } catch (e) {
        console.error(e);
      }
    });

    document.getElementById('btn-resume-job')?.addEventListener('click', async () => {
      try {
        await fetch(`${this.apiBase}/print/resume`, { method: 'POST' });
        this.addLocalLog('ACTION', 'SUPERVISOR', 'Operator resumed surface deposition.');
      } catch (e) {
        console.error(e);
      }
    });
  }

  async analyzeCurrentSelection() {
    const widthMm = parseFloat(document.getElementById('inp-print-w')?.value || 300);
    const heightMm = parseFloat(document.getElementById('inp-print-h')?.value || 250);
    const pitchMm = parseFloat(document.getElementById('inp-row-pitch')?.value || 3.0);
    const actuatorMode = document.getElementById('inp-actuator-override')?.value || 'auto';

    const formData = new FormData();
    formData.append('target_width_mm', widthMm);
    formData.append('target_height_mm', heightMm);
    formData.append('row_pitch_mm', pitchMm);
    if (actuatorMode !== 'auto') {
      formData.append('actuator_override', actuatorMode);
    }

    if (this.selectedFile) {
      formData.append('file', this.selectedFile);
    } else if (this.activePreset) {
      formData.append('preset_id', this.activePreset);
    }

    this.addLocalLog('INFO', 'PROCESSOR', `Analyzing artwork (${widthMm}x${heightMm} mm, pitch: ${pitchMm} mm)...`);

    try {
      const res = await fetch(`${this.apiBase}/processor/analyze`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success && data.report) {
        this.currentReport = data.report;
        this.renderAnalysisReport(data.report);
      }
    } catch (e) {
      this.addLocalLog('FAULT', 'PROCESSOR', `Artwork analysis failed: ${e.message}`);
    }
  }

  renderAnalysisReport(report) {
    const recipe = report.paint_recipe;
    const motion = report.motion_plan;

    // 1. Actuator Classification Hero
    const badgeModule = document.getElementById('badge-rec-module');
    const heroTitle = document.getElementById('class-module-title');
    const heroDesc = document.getElementById('class-module-desc');
    const specDelivery = document.getElementById('spec-delivery');
    const specSpring = document.getElementById('spec-spring');
    const specStandoff = document.getElementById('spec-standoff');

    if (recipe.recommended_actuator === 'paint') {
      if (badgeModule) {
        badgeModule.textContent = 'MODULE B (PAINT MARKER)';
        badgeModule.className = 'badge-amber';
      }
      if (heroTitle) heroTitle.textContent = 'Module B: Spring-Compliant Paint Marker';
      if (specDelivery) specDelivery.textContent = '6mm Chisel Felt Nib';
      if (specSpring) specSpring.textContent = '1.2N Compliance Spring';
      if (specStandoff) specStandoff.textContent = 'Surface Contact (0.0mm)';
      this.threeScene.setModule('paint');
    } else {
      if (badgeModule) {
        badgeModule.textContent = 'MODULE A (PIEZO INKJET)';
        badgeModule.className = 'badge-green';
      }
      if (heroTitle) heroTitle.textContent = 'Module A: 48-Nozzle Drop-on-Demand Piezo Inkjet';
      if (specDelivery) specDelivery.textContent = '48-Nozzle Silicon Matrix';
      if (specSpring) specSpring.textContent = '14 pL Micro-Droplets';
      if (specStandoff) specStandoff.textContent = 'Non-Contact (2.0mm)';
      this.threeScene.setModule('inkjet');
    }

    if (heroDesc) heroDesc.textContent = recipe.rationale;

    // 2. Paint & Ink Recipe
    const badgeVol = document.getElementById('badge-total-vol');
    if (badgeVol) badgeVol.textContent = `Total: ${recipe.total_volume_ml} mL`;

    const rChem = document.getElementById('r-chemistry');
    const rVisc = document.getElementById('r-viscosity');
    const rDry = document.getElementById('r-drying');
    const rSub = document.getElementById('r-substrate');

    if (rChem) rChem.textContent = recipe.ink_chemistry;
    if (rVisc) rVisc.textContent = `${recipe.viscosity_cp} cP`;
    if (rDry) rDry.textContent = `${recipe.drying_time_per_pass_s} seconds`;
    if (rSub) {
      rSub.textContent = `${recipe.substrate_compatibility.status} (${recipe.substrate_compatibility.material_name})`;
    }

    // Swatches
    const swatchesContainer = document.getElementById('palette-swatches-container');
    if (swatchesContainer && recipe.color_breakdown) {
      swatchesContainer.innerHTML = '';
      recipe.color_breakdown.forEach(c => {
        const div = document.createElement('div');
        div.className = 'swatch-card';
        div.innerHTML = `
          <div class="swatch-box" style="background-color: ${c.hex_code};"></div>
          <div class="swatch-meta">
            <div class="swatch-name">${c.name}</div>
            <div class="swatch-details">${c.hex_code} &bull; ${c.coverage_percent}% (${c.estimated_volume_ml} mL)</div>
          </div>
        `;
        swatchesContainer.appendChild(div);
      });
    }

    // 3. 4-Cable Motion Plan
    document.getElementById('m-passes').textContent = Math.round(report.target_size_mm[1] / motion.row_pitch_mm);
    document.getElementById('m-waypoints').textContent = motion.total_waypoints;
    document.getElementById('m-distance').textContent = `${motion.total_distance_m} m`;
    document.getElementById('m-duration').textContent = `${motion.estimated_time_s} s`;
    document.getElementById('m-t-min').textContent = `${motion.tension_range_n[0]} N`;
    document.getElementById('m-t-max').textContent = `${motion.tension_range_n[1]} N`;

    const badgeKin = document.getElementById('badge-kin-status');
    if (badgeKin) {
      if (motion.kinematic_feasible) {
        badgeKin.textContent = 'KINEMATICALLY FEASIBLE';
        badgeKin.className = 'badge-green';
      } else {
        badgeKin.textContent = 'TENSION WARNING';
        badgeKin.className = 'badge-amber';
      }
    }

    this.addLocalLog('ACTION', 'PROCESSOR', `CAM Plan verified: ${motion.total_waypoints} waypoints, ${motion.total_distance_m}m path.`);
  }

  async executePrintJob() {
    if (!this.currentReport) {
      this.addLocalLog('WARN', 'PROCESSOR', 'Cannot execute: no analyzed artwork report available.');
      return;
    }

    this.addLocalLog('ACTION', 'PROCESSOR', `Executing Print Job ${this.currentReport.job_id}...`);

    try {
      const res = await fetch(`${this.apiBase}/processor/execute`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        this.isPrinting = true;
        this.addLocalLog('ACTION', 'SUPERVISOR', `Print Job successfully dispatched to 4-cable CDPR!`);
      } else {
        throw new Error(data.detail || data.message || 'Execution rejected');
      }
    } catch (e) {
      this.addLocalLog('FAULT', 'SUPERVISOR', `Failed to launch print job: ${e.message}`);
    }
  }

  initTelemetryConnection() {
    const dot = document.getElementById('live-indicator');
    const statusText = document.getElementById('ws-status-text');

    const connectWs = () => {
      const ws = new WebSocket(this.wsUrl);

      ws.onopen = () => {
        if (dot) dot.className = 'live-dot active';
        if (statusText) statusText.textContent = 'LIVE 30Hz';
        this.addLocalLog('INFO', 'SUPERVISOR', 'WebSocket telemetry stream connected at 30 Hz.');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleTelemetry(data);
        } catch (e) {
          console.error(e);
        }
      };

      ws.onerror = () => {
        if (dot) dot.className = 'live-dot';
        if (statusText) statusText.textContent = 'FALLBACK';
      };

      ws.onclose = () => {
        if (dot) dot.className = 'live-dot';
        if (statusText) statusText.textContent = 'RECONNECTING';
        setTimeout(connectWs, 3000);
      };
    };

    connectWs();
  }

  handleTelemetry(data) {
    // 1. Navbar State & Clock
    if (data.supervisor) {
      const badge = document.getElementById('supervisor-badge');
      if (badge) {
        badge.textContent = data.supervisor.state;
        if (data.supervisor.state === 'PRINTING') {
          badge.className = 'state-badge';
          badge.style.borderColor = 'var(--accent-amber)';
          badge.style.color = 'var(--accent-amber)';
        } else if (data.supervisor.state === 'EMERGENCY_STOP' || data.supervisor.state === 'FAULT') {
          badge.className = 'state-badge';
          badge.style.borderColor = 'var(--status-red)';
          badge.style.color = 'var(--status-red)';
        } else {
          badge.className = 'state-badge';
          badge.style.borderColor = 'var(--status-green)';
          badge.style.color = 'var(--status-green)';
        }
      }
    }

    if (data.sim_time_s !== undefined) {
      const clock = document.getElementById('sim-clock');
      if (clock) clock.textContent = `T+ ${data.sim_time_s.toFixed(2)}s`;
    }

    // 2. End Effector Position Label
    if (data.end_effector) {
      const lblPos = document.getElementById('lbl-twin-pos');
      if (lblPos) {
        lblPos.textContent = `EE: (${data.end_effector.x_mm.toFixed(1)}, ${data.end_effector.y_mm.toFixed(1)}) mm`;
      }

      // Update 3D Digital Twin Mechanism
      const tensions = data.cables?.cables ? [
        data.cables.cables.C1?.tension_n || 12,
        data.cables.cables.C2?.tension_n || 12,
        data.cables.cables.C3?.tension_n || 12,
        data.cables.cables.C4?.tension_n || 12
      ] : [12, 12, 12, 12];

      this.threeScene.updatePlatform(data.end_effector.x_mm, data.end_effector.y_mm, tensions);
    }

    // 3. Progressive 2D Surface Deposition Canvas
    if (data.canvas_base64 && this.ctx2D) {
      const img = new Image();
      img.onload = () => {
        this.ctx2D.drawImage(img, 0, 0, this.canvas2D.width, this.canvas2D.height);
      };
      img.src = data.canvas_base64;
    }

    // 4. Ingest Telemetry Execution Logs
    if (data.recent_logs && Array.isArray(data.recent_logs)) {
      data.recent_logs.forEach(log => {
        if (log.id > this.lastLogId) {
          this.lastLogId = log.id;
          this.appendLogEntry(log);
        }
      });
    }
  }

  initLogTerminal() {
    // Clear logs
    document.getElementById('btn-clear-logs')?.addEventListener('click', () => {
      const term = document.getElementById('log-terminal-output');
      if (term) term.innerHTML = '';
      this.allLogs = [];
    });

    // Export logs (.log text file)
    document.getElementById('btn-export-log')?.addEventListener('click', () => {
      if (this.allLogs.length === 0) return;
      const text = this.allLogs.map(l => `[${l.time_s}s] [${l.level}] [${l.subsystem}] ${l.message}`).join('\n');
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `project_wall_flight_log_${Date.now()}.log`;
      a.click();
    });

    // Subsystem filter
    document.getElementById('log-filter-subsystem')?.addEventListener('change', (e) => {
      const filter = e.target.value;
      const lines = document.querySelectorAll('.log-line');
      lines.forEach(line => {
        if (filter === 'ALL') {
          line.style.display = 'flex';
        } else {
          const tag = line.querySelector('.log-tag')?.textContent || '';
          line.style.display = tag.includes(filter) ? 'flex' : 'none';
        }
      });
    });
  }

  addLocalLog(level, subsystem, message) {
    const entry = {
      id: ++this.lastLogId,
      time_s: (performance.now() / 1000).toFixed(2),
      level,
      subsystem,
      message
    };
    this.appendLogEntry(entry);
  }

  appendLogEntry(log) {
    this.allLogs.push(log);
    const term = document.getElementById('log-terminal-output');
    if (!term) return;

    const div = document.createElement('div');
    const levelClass = log.level === 'FAULT' ? 'log-fault' : (log.level === 'WARN' ? 'log-warn' : (log.level === 'ACTION' ? 'log-action' : 'log-info'));
    div.className = `log-line ${levelClass}`;

    const tagClass = `tag-${log.subsystem.toLowerCase()}`;
    div.innerHTML = `
      <span class="log-time">[T+ ${parseFloat(log.time_s).toFixed(2)}s]</span>
      <span class="log-tag ${tagClass}">[${log.subsystem}]</span>
      <span class="log-msg">${log.message}</span>
    `;

    term.appendChild(div);

    // Auto-scroll to bottom of log container
    const container = document.getElementById('log-console-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }
}

// Boot application when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
  window.processorApp = new ProcessorApp();
});

