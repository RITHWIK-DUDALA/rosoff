# Troubleshooting & Diagnostic Guide

## 1. Quick Diagnostics Check

Always start troubleshooting by running the automated diagnostic script:
```bash
# On Linux / macOS
./scripts/diagnostics.sh

# On Windows PowerShell
.\scripts\diagnostics.ps1
```
This tests:
1. Python environment and installed libraries.
2. Canonical configuration YAML and JSON Schema validity.
3. Automated unit test suite status.
4. Port availability (FastAPI default port 8000).

---

## 2. Common Symptoms & Solutions

### 2.1 Backend Fails to Start
- **Symptom:** `ModuleNotFoundError: No module named 'fastapi'` or similar.
  - **Cause:** Virtual environment not active or dependencies missing.
  - **Fix:** 
    ```bash
    pip install -r backend/requirements.txt
    ```
- **Symptom:** `jsonschema.exceptions.ValidationError` on startup.
  - **Cause:** `config/robot_config.yaml` has syntax errors, missing mandatory keys, or unformatted scientific notation (e.g. `1.0e11` without plus sign).
  - **Fix:** Check formatting against `config/configuration.schema.json`. Ensure scientific notation is written as `1.0e+11`.
- **Symptom:** `OSError: [Errno 98] Address already in use: ('0.0.0.0', 8000)`.
  - **Cause:** Previous backend instance or another web server is holding port 8000.
  - **Fix:**
    - On Linux: `fuser -k 8000/tcp`
    - On Windows: `netstat -ano | findstr :8000` then `taskkill /F /PID <PID>`

---

### 2.2 Browser Interface & WebSocket Issues
- **Symptom:** Browser shows `Connection: Disconnected` (red badge).
  - **Cause:** Backend server is not running, or WebSocket URL is blocked by firewall/proxy.
  - **Fix:** Verify backend console shows `Application startup complete`. Ensure browser URL is `http://localhost:8000` (or local IP) and port 8000 is open.
- **Symptom:** Three.js viewport is blank black screen.
  - **Cause:** WebGL disabled or JavaScript error in browser console.
  - **Fix:** Open browser DevTools (F12) -> Console. Check for missing script imports or WebGL context failures. Verify Three.js CDN/local script loaded successfully.
- **Symptom:** Platform doesn't move when clicking "Move to Target".
  - **Cause:** Emergency stop latched, mode set to `HARDWARE` while unverified, or target out of bounds.
  - **Fix:** Check the "Active Faults" badge in the UI. If E-Stop is active, click "Reset Faults". If target is invalid (red input highlight), select a coordinate within $X \in [-180, +180]$, $Y \in [-140, +140]\text{ mm}$.

---

### 2.3 Forward Kinematics & Tracking Residuals
- **Symptom:** Telemetry shows `Tracking Error: INVALID` or high residual warnings ($> 5.0\text{ mm}$).
  - **Cause:** Cable lengths given to the forward kinematics solver are physically inconsistent (e.g., severe sensor noise, incorrect spool calibration, or mechanical binding).
  - **Fix:**
    1. Verify individual cable lengths using caliper / tape measure.
    2. Check initial guess: solver uses current estimated pose or center $(0, 0)$.
    3. Verify spool radius calibration ($r_{\text{eff}} = 10.0\text{ mm}$).

---

### 2.4 ROS 2 & micro-ROS Issues
- **Symptom:** `ros2 launch cdpr_bringup simulation.launch.py` errors with `Package 'cdpr_bringup' not found`.
  - **Cause:** Workspace not sourced in current shell.
  - **Fix:**
    ```bash
    source /opt/ros/humble/setup.bash
    source ros2_ws/install/setup.bash
    ```
- **Symptom:** micro-ROS Agent shows `[agent] [error] serial: cannot open /dev/ttyUSB0: Permission denied`.
  - **Cause:** Linux user lacks read/write permissions for USB serial device.
  - **Fix:**
    ```bash
    sudo usermod -a -G dialout $USER
    # Log out and log back in, or run with sudo for quick test
    ```
- **Symptom:** ESP32 continuously resets with watchdog panic.
  - **Cause:** FreeRTOS micro-ROS task starving IDLE task, or serial buffer overflow.
  - **Fix:** Ensure micro-ROS task has a small `vTaskDelay(pdMS_TO_TICKS(10))` in its loop and execution core is pinned to Core 1.
