/**
 * Main application bootstrap for Planar Cable Robot Simulator.
 * Connects Three.js 3D Viewport, 2D Canvas Engineering View,
 * WebSocket Telemetry streaming, Real-time Diagnostic Charts, and REST Controls.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Resolve API and WebSocket endpoints (supports Vercel frontend pointing to external backend)
  const urlParams = new URLSearchParams(window.location.search);
  const backendParam = urlParams.get('backend');
  if (backendParam) {
    localStorage.setItem('cdpr_backend_url', backendParam);
  }
  const customBackend = backendParam || localStorage.getItem('cdpr_backend_url');

  let apiBase, wsUrl;
  if (customBackend) {
    const cleanUrl = customBackend.replace(/\/+$/, '');
    const isHttps = cleanUrl.startsWith('https:');
    const wsProto = isHttps ? 'wss:' : 'ws:';
    const hostPart = cleanUrl.replace(/^https?:\/\//, '');
    apiBase = `${cleanUrl}/api`;
    wsUrl = `${wsProto}//${hostPart}/ws/telemetry`;
  } else {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    apiBase = `${protocol}//${host}/api`;
    wsUrl = `${wsProtocol}//${host}/ws/telemetry`;
  }

  // UI Element references
  const connectionDot = document.getElementById('connection-dot');
  const connectionStatus = document.getElementById('connection-status');
  const modePill = document.getElementById('controller-mode-pill');
  const simTimeDisplay = document.getElementById('sim-time-display');
  const commandMessageBox = document.getElementById('command-message-box');
  const tab3d = document.getElementById('tab-3d');
  const tab2d = document.getElementById('tab-2d');
  const tabBlueprint = document.getElementById('tab-blueprint');
  const btnExportBlueprint = document.getElementById('btn-export-blueprint');

  const threeViewport = document.getElementById('three-viewport');
  const engViewport = document.getElementById('engineering-viewport');
  const blueprintViewport = document.getElementById('blueprint-viewport');
  const canvas2d = document.getElementById('canvas-2d');
  const canvasBlueprint = document.getElementById('canvas-blueprint');

  // Load configuration from backend
  let config = null;
  try {
    const res = await fetch(`${apiBase}/config`);
    config = await res.json();
  } catch (err) {
    console.warn("Failed fetching config from backend, using default fallback:", err);
    config = {
      frame: { width_m: 0.500, height_m: 0.400, depth_m: 0.120 },
      platform: { width_m: 0.100, height_m: 0.080, thickness_m: 0.006 },
      actuators: { drum_radius_m: 0.010 },
      workspace: { x_min_m: -0.18, x_max_m: 0.18, y_min_m: -0.14, y_max_m: 0.14 }
    };
  }

  // Operating Mode Selector binding
  const selectMode = document.getElementById('select-mode');
  const provenancePill = document.getElementById('provenance-pill');
  if (selectMode) {
    selectMode.addEventListener('change', async () => {
      const chosenMode = selectMode.value;
      try {
        const res = await fetch(`${apiBase}/mode`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: chosenMode })
        });
        const data = await res.json();
        if (data.status === 'rejected_unverified') {
          showMessage(`⚠️ Hardware Motion Blocked: ${data.message}`, true);
          selectMode.value = 'SIMULATION';
          if (provenancePill) {
            provenancePill.textContent = 'BLOCKED';
            provenancePill.className = 'provenance-pill blocked';
          }
        } else {
          showMessage(data.message, false);
        }
      } catch (err) {
        showMessage(`Mode change error: ${err.message}`, true);
        selectMode.value = 'SIMULATION';
      }
    });
  }

  // 1. Initialize 3D Viewport
  const sceneMgr = new SceneManager(threeViewport);
  const robotView = new RobotView(sceneMgr.scene, config);

  // Sync coordinate input bounds with actual robot workspace configuration
  if (config && config.workspace) {
    const wsXMin = Math.round(config.workspace.x_min_m * 1000);
    const wsXMax = Math.round(config.workspace.x_max_m * 1000);
    const wsYMin = Math.round(config.workspace.y_min_m * 1000);
    const wsYMax = Math.round(config.workspace.y_max_m * 1000);

    const inputX = document.getElementById('input-x');
    const inputY = document.getElementById('input-y');
    if (inputX) {
      inputX.min = wsXMin;
      inputX.max = wsXMax;
      const hintX = inputX.parentElement.querySelector('.input-hint');
      if (hintX) hintX.textContent = `[${wsXMin}, +${wsXMax}]`;
    }
    if (inputY) {
      inputY.min = wsYMin;
      inputY.max = wsYMax;
      const hintY = inputY.parentElement.querySelector('.input-hint');
      if (hintY) hintY.textContent = `[${wsYMin}, +${wsYMax}]`;
    }
  }

  // 2. Initialize 2D Engineering View
  const engView = new EngineeringView(canvas2d, config, (targetX, targetY) => {
    // Fill form and trigger move
    document.getElementById('input-x').value = targetX;
    document.getElementById('input-y').value = targetY;
    const speed = parseFloat(document.getElementById('input-speed').value);
    controlsMgr.sendMove(targetX, targetY, speed);
  });

  // 3. Initialize CAD Blueprint View
  const blueprintView = new BlueprintView(canvasBlueprint, config);
  if (btnExportBlueprint) {
    btnExportBlueprint.addEventListener('click', () => blueprintView.exportImage());
  }

  // 4. Initialize Interactive Waypoint & Vector Drawing Manager
  const pathPlanner = new PathPlannerManager(apiBase, showMessage, (wps) => {
    // Update counter label
    const lblCount = document.getElementById('lbl-wps-count');
    if (lblCount) lblCount.textContent = wps.length;
    // Re-render views to show updated polyline
    if (activeView === '2d') engView.render();
    if (activeView === 'blueprint') blueprintView.render();
  });

  // Link pathPlanner to views
  engView.pathPlanner = pathPlanner;
  blueprintView.pathPlanner = pathPlanner;

  // Bind Drawing Player UI controls
  const btnModeClick = document.getElementById('btn-mode-click');
  const btnModeWaypoints = document.getElementById('btn-mode-waypoints');
  const pathModeBadge = document.getElementById('path-mode-badge');

  if (btnModeClick && btnModeWaypoints) {
    btnModeClick.addEventListener('click', () => {
      pathPlanner.setMode('single');
      btnModeClick.classList.add('active');
      btnModeWaypoints.classList.remove('active');
      if (pathModeBadge) pathModeBadge.textContent = 'Direct XY';
      showMessage('Direct XY Move Mode: Click anywhere on 2D view to dispatch position');
    });

    btnModeWaypoints.addEventListener('click', () => {
      pathPlanner.setMode('waypoints');
      btnModeWaypoints.classList.add('active');
      btnModeClick.classList.remove('active');
      if (pathModeBadge) pathModeBadge.textContent = 'Path Builder';
      showMessage('Path Builder Mode: Click on 2D view to place sequential waypoints');
    });
  }

  // Vector Presets
  const presetButtons = [
    { id: 'btn-preset-star', name: 'star' },
    { id: 'btn-preset-spiral', name: 'spiral' },
    { id: 'btn-preset-gear', name: 'gear' },
    { id: 'btn-preset-grid', name: 'calGrid' }
  ];
  presetButtons.forEach(({ id, name }) => {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', () => pathPlanner.loadPreset(name));
  });

  // Unified clear functions
  function handleClearTrail() {
    pathPlanner.clearTrail();
    if (robotView && robotView.clearTrail) {
      robotView.clearTrail();
    }
    if (activeView === '2d' && engView) engView.render();
    if (activeView === 'blueprint' && blueprintView) blueprintView.render();
    showMessage('Blue drawing trail cleared');
  }

  function handleClearWps() {
    pathPlanner.clearWaypoints();
    if (activeView === '2d' && engView) engView.render();
    if (activeView === 'blueprint' && blueprintView) blueprintView.render();
    showMessage('Waypoints cleared');
  }

  // Clear trail buttons (sidebar, 2D viewport, blueprint viewport)
  ['btn-clear-trail', 'btn-2d-clear-trail', 'btn-blueprint-clear-trail'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', handleClearTrail);
  });

  // Clear waypoints buttons (sidebar, 2D viewport, blueprint viewport)
  ['btn-clear-wps', 'btn-2d-clear-wps', 'btn-blueprint-clear-wps'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', handleClearWps);
  });

  // Execute Drawing Path
  const btnRunPath = document.getElementById('btn-run-path');
  const inputPathSpeed = document.getElementById('input-path-speed');
  if (btnRunPath) {
    btnRunPath.addEventListener('click', () => {
      const spd = parseFloat(inputPathSpeed ? inputPathSpeed.value : 50) || 50;
      pathPlanner.executePath(spd);
    });
  }

  // File Upload (G-Code & SVG)
  const inputVectorFile = document.getElementById('input-vector-file');
  const btnBrowseFile = document.getElementById('btn-browse-file');
  const dropzone = document.getElementById('vector-dropzone');

  if (btnBrowseFile && inputVectorFile) {
    btnBrowseFile.addEventListener('click', () => inputVectorFile.click());
  }

  function handleFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      try {
        if (file.name.toLowerCase().endsWith('.svg')) {
          pathPlanner.parseSVG(content);
        } else {
          pathPlanner.parseGCode(content);
        }
      } catch (err) {
        showMessage(`File import error: ${err.message}`, true);
      }
    };
    reader.readAsText(file);
  }

  if (inputVectorFile) {
    inputVectorFile.addEventListener('change', (e) => {
      if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });
  }

  if (dropzone) {
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });
  }

  // 5. Status message helper
  function showMessage(msg, isError = false) {
    commandMessageBox.textContent = msg;
    commandMessageBox.className = `message-box ${isError ? 'error' : 'info'}`;
  }

  // 6. Initialize Diagnostic Plots
  const plotMgr = new PlotManager();

  // 7. Initialize Controls
  const controlsMgr = new ControlsManager(apiBase, showMessage);

  // 7. Multi-view mode switcher (3D, 2D Sim, Blueprint)
  let activeView = '3d';

  function setView(view) {
    activeView = view;

    // Update active tab buttons
    tab3d.classList.toggle('active', view === '3d');
    tab2d.classList.toggle('active', view === '2d');
    tabBlueprint.classList.toggle('active', view === 'blueprint');

    // Update viewport visibility
    threeViewport.classList.toggle('hidden', view !== '3d');
    engViewport.classList.toggle('hidden', view !== '2d');
    blueprintViewport.classList.toggle('hidden', view !== 'blueprint');

    if (view === '3d') {
      sceneMgr.onResize();
    } else if (view === '2d') {
      engView.render();
    } else if (view === 'blueprint') {
      blueprintView.render();
    }
  }

  tab3d.addEventListener('click', () => setView('3d'));
  tab2d.addEventListener('click', () => setView('2d'));
  tabBlueprint.addEventListener('click', () => setView('blueprint'));

  // Toggle Workbench Table Base in 3D View
  const btnToggleTable = document.getElementById('btn-toggle-table');
  if (btnToggleTable) {
    btnToggleTable.addEventListener('click', () => {
      const isVisible = robotView.toggleTable();
      btnToggleTable.textContent = isVisible ? '🪵 Table Base: ON' : '🪵 Table Base: OFF';
      btnToggleTable.classList.toggle('active', isVisible);
      showMessage(isVisible ? 'Workbench table base added' : 'Workbench table base removed');
    });
  }

  window.addEventListener('resize', () => {
    if (activeView === 'blueprint') {
      blueprintView.render();
    } else if (activeView === '2d') {
      engView.render();
    }
  });

  // 8. Telemetry update callback
  function handleTelemetry(telem) {
    // Update header indicators
    modePill.textContent = telem.controller_mode;
    modePill.className = `mode-pill ${telem.controller_mode}`;
    simTimeDisplay.textContent = `T+ ${telem.sim_time_s.toFixed(2)} s`;
    controlsMgr.setMode(telem.controller_mode);

    // Update views
    robotView.update(telem);

    // Record carriage path breadcrumb trail for pen plotter effect
    if (pathPlanner && telem.platform_pos) {
      pathPlanner.pushTrailPoint(telem.platform_pos[0], telem.platform_pos[1]);
    }

    if (activeView === '2d') {
      engView.update(telem);
    } else {
      engView.latestTelemetry = telem;
    }

    if (activeView === 'blueprint') {
      blueprintView.update(telem);
    } else {
      blueprintView.latestTelemetry = telem;
    }

    // Update Telemetry table rows
    for (let i = 0; i < 4; i++) {
      const row = document.getElementById(`row-c${i+1}`);
      if (row) {
        row.querySelector('.cell-len').textContent = telem.cable_lengths_mm[i].toFixed(1);
        row.querySelector('.cell-rate').textContent = telem.cable_rates_mm_s[i].toFixed(1);
        row.querySelector('.cell-ten').textContent = telem.cable_tensions_N[i].toFixed(1);
        row.querySelector('.cell-rpm').textContent = telem.motor_speeds_rpm[i].toFixed(1);
        row.querySelector('.cell-tau').textContent = telem.motor_torques_Nm[i].toFixed(3);
      }
    }

    // Provenance & Mode updates
    const prov = (telem.position_provenance || 'simulated').toUpperCase();
    if (provenancePill) {
      provenancePill.textContent = prov;
      provenancePill.className = `provenance-pill ${telem.position_provenance || 'simulated'}`;
    }
    const dispProv = document.getElementById('disp-provenance');
    if (dispProv) {
      dispProv.textContent = prov;
      dispProv.className = `stat-value ${telem.position_provenance || 'simulated'}`;
    }

    // Kinematic summaries
    const dispPos = document.getElementById('disp-pos');
    if (dispPos && telem.platform_pos) {
      dispPos.textContent = `[${telem.platform_pos[0].toFixed(1)}, ${telem.platform_pos[1].toFixed(1)}] mm`;
    }

    const dispEstPos = document.getElementById('disp-est-pos');
    if (dispEstPos) {
      if (telem.estimated_pos && telem.estimated_valid) {
        dispEstPos.textContent = `[${telem.estimated_pos[0].toFixed(1)}, ${telem.estimated_pos[1].toFixed(1)}] mm`;
        dispEstPos.className = 'stat-value ok';
      } else {
        dispEstPos.textContent = 'DIVERGED / UNKNOWN';
        dispEstPos.className = 'stat-value error';
      }
    }

    const dispError = document.getElementById('disp-error');
    if (dispError) {
      if (telem.tracking_error_valid && telem.tracking_error_mm !== null && telem.tracking_error_mm !== undefined) {
        dispError.textContent = `${telem.tracking_error_mm.toFixed(2)} mm`;
        dispError.className = 'stat-value';
      } else {
        dispError.textContent = 'INVALID / STALE';
        dispError.className = 'stat-value error';
      }
    }

    const dispCond = document.getElementById('disp-cond');
    if (dispCond) {
      dispCond.textContent = telem.condition_number ? telem.condition_number.toFixed(2) : '1.00';
    }

    const feasEl = document.getElementById('disp-tension-feas');
    if (feasEl) {
      if (telem.tension_feasible) {
        feasEl.textContent = 'FEASIBLE';
        feasEl.className = 'stat-value ok';
      } else {
        feasEl.textContent = 'INFEASIBLE';
        feasEl.className = 'stat-value error';
      }
    }

    // Push data to real-time diagnostic charts
    if (plotMgr) {
      plotMgr.pushData(telem);
    }
  }

  // 8. WebSocket Telemetry Client
  const telemClient = new TelemetryClient(
    wsUrl,
    handleTelemetry,
    (status, isConnected) => {
      connectionStatus.textContent = status;
      if (isConnected) {
        connectionDot.className = 'status-dot connected';
      } else {
        connectionDot.className = 'status-dot disconnected';
      }
    }
  );

  // 9. Animation render loop (Three.js OrbitControls & rendering)
  sceneMgr.onResize();
  sceneMgr.render();

  function animate() {
    requestAnimationFrame(animate);
    if (activeView === '3d') {
      sceneMgr.render();
    }
  }
  animate();
});
