/**
 * UI Controls binding: Move, Home, Jogging, Predefined trajectories,
 * E-Stop, Pause/Resume, Reset, and Keyboard Arrow navigation.
 */
class ControlsManager {
  constructor(apiBaseUrl, onStatusMessage) {
    this.apiBase = apiBaseUrl;
    this.onStatus = onStatusMessage;

    this.bindDOM();
    this.bindKeyboard();
  }

  bindDOM() {
    // Speed range slider readout
    const speedInput = document.getElementById('input-speed');
    const speedVal = document.getElementById('speed-val');
    speedInput.addEventListener('input', () => {
      speedVal.textContent = speedInput.value;
    });

    // Move form
    const formMove = document.getElementById('form-move');
    formMove.addEventListener('submit', (e) => {
      e.preventDefault();
      const x = parseFloat(document.getElementById('input-x').value);
      const y = parseFloat(document.getElementById('input-y').value);
      const speed = parseFloat(speedInput.value);
      this.sendMove(x, y, speed);
    });

    // Home button
    document.getElementById('btn-home').addEventListener('click', () => {
      this.sendMove(0.0, 0.0, parseFloat(speedInput.value));
    });

    // Jog buttons
    const getStep = () => parseFloat(document.getElementById('jog-step-size').value);
    document.getElementById('jog-up').addEventListener('click', () => this.sendJog(0, getStep()));
    document.getElementById('jog-down').addEventListener('click', () => this.sendJog(0, -getStep()));
    document.getElementById('jog-left').addEventListener('click', () => this.sendJog(-getStep(), 0));
    document.getElementById('jog-right').addEventListener('click', () => this.sendJog(getStep(), 0));

    // Trajectory presets
    document.getElementById('btn-traj-circle').addEventListener('click', () => {
      this.sendTrajectory('circle', { radius_mm: 50.0, speed_mm_s: 50.0, center_mm: [0, 0], cycles: 1 });
    });
    document.getElementById('btn-traj-rect').addEventListener('click', () => {
      this.sendTrajectory('rectangle', { width_mm: 120.0, height_mm: 80.0, speed_mm_s: 50.0, center_mm: [0, 0] });
    });
    document.getElementById('btn-traj-figure8').addEventListener('click', () => {
      const wps = [
        [0, 0], [60, 40], [0, 0], [-60, -40], [0, 0],
        [-60, 40], [0, 0], [60, -40], [0, 0]
      ];
      this.sendTrajectory('waypoints', { waypoints_mm: wps, speed_mm_s: 60.0 });
    });

    // Motion supervisor action buttons
    document.getElementById('btn-pause').addEventListener('click', () => this.postAction('/command/pause', 'Paused'));
    document.getElementById('btn-resume').addEventListener('click', () => this.postAction('/command/resume', 'Resumed'));
    document.getElementById('btn-stop').addEventListener('click', () => this.postAction('/command/stop', 'Stopped'));
    document.getElementById('btn-reset').addEventListener('click', () => this.postAction('/command/reset', 'Reset to Origin'));
    const headerReset = document.getElementById('btn-header-reset');
    if (headerReset) {
      headerReset.addEventListener('click', () => this.postAction('/command/reset', 'System Reset to Origin (0,0)'));
    }
    document.getElementById('btn-estop').addEventListener('click', () => {
      if (this.currentMode === 'ESTOP') {
        this.postAction('/command/reset', 'E-STOP Cleared & System Reset');
      } else {
        this.postAction('/command/estop', 'E-STOP ACTIVATED', true);
      }
    });
  }

  setMode(mode) {
    this.currentMode = mode;
    const estopBtn = document.getElementById('btn-estop');
    if (estopBtn) {
      if (mode === 'ESTOP') {
        estopBtn.textContent = 'RESET E-STOP';
        estopBtn.title = 'Click to release E-STOP and reset robot to home';
        estopBtn.classList.add('in-estop');
      } else {
        estopBtn.textContent = 'E-STOP';
        estopBtn.title = 'Emergency Stop';
        estopBtn.classList.remove('in-estop');
      }
    }
  }

  bindKeyboard() {
    window.addEventListener('keydown', (e) => {
      // Ignore if user is typing in form inputs
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

      const step = parseFloat(document.getElementById('jog-step-size').value);
      if (e.key === 'ArrowUp') { e.preventDefault(); this.sendJog(0, step); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); this.sendJog(0, -step); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); this.sendJog(-step, 0); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); this.sendJog(step, 0); }
      else if (e.key === ' ' || e.key === 'Escape') { e.preventDefault(); this.postAction('/command/stop', 'Stopped via Keyboard'); }
    });
  }

  async sendMove(x_mm, y_mm, speed_mm_s) {
    try {
      const res = await fetch(`${this.apiBase}/command/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x_mm, y_mm, speed_mm_s })
      });
      const data = await res.json();
      if (!res.ok) {
        this.onStatus(data.detail?.message || 'Move rejected', true);
      } else {
        this.onStatus(`Target accepted: [${x_mm}, ${y_mm}] mm`, false);
      }
    } catch (e) {
      this.onStatus(`Command error: ${e.message}`, true);
    }
  }

  async sendJog(dx_mm, dy_mm) {
    try {
      const res = await fetch(`${this.apiBase}/command/jog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta_x_mm: dx_mm, delta_y_mm: dy_mm })
      });
      const data = await res.json();
      if (!res.ok) {
        this.onStatus(data.detail?.message || 'Jog rejected', true);
      } else {
        this.onStatus(`Jogged dX=${dx_mm}, dY=${dy_mm}`, false);
      }
    } catch (e) {
      this.onStatus(`Jog error: ${e.message}`, true);
    }
  }

  async sendTrajectory(type, params) {
    try {
      const res = await fetch(`${this.apiBase}/command/trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, params })
      });
      const data = await res.json();
      if (!res.ok) {
        this.onStatus(data.detail?.message || 'Trajectory rejected', true);
      } else {
        this.onStatus(data.message || 'Trajectory started', false);
      }
    } catch (e) {
      this.onStatus(`Trajectory error: ${e.message}`, true);
    }
  }

  async postAction(endpoint, successMsg, isCritical = false) {
    try {
      const res = await fetch(`${this.apiBase}${endpoint}`, { method: 'POST' });
      const data = await res.json();
      this.onStatus(data.message || successMsg, isCritical);
    } catch (e) {
      this.onStatus(`Action failed: ${e.message}`, true);
    }
  }
}

window.ControlsManager = ControlsManager;
