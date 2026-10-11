/**
 * Waypoints Builder & G-Code / SVG Vector Drawing Parser & Player.
 * Supports:
 * 1. Interactive multi-point waypoints sequencing on the 2D workspace.
 * 2. G-Code parser for G0/G1 linear motion commands (CNC / Plotter standard).
 * 3. SVG vector path parser (converts SVG path data / polylines / polygons / rects into continuous toolpaths).
 * 4. Automatic bounding box normalization & workspace scaling into safe limits [-180..180, -140..140] mm.
 * 5. Built-in vector presets: Star, Spiral, Gear, Calibration Grid, Square Wave.
 * 6. Live path execution and real-time carriage breadcrumb drawing trail.
 */
class PathPlannerManager {
  constructor(apiBaseUrl, showMessageCallback, onPathUpdatedCallback) {
    this.apiBase = apiBaseUrl;
    this.showMessage = showMessageCallback;
    this.onPathUpdated = onPathUpdatedCallback;

    this.mode = 'single'; // 'single' (click-to-move), 'waypoints', 'gcode'
    this.waypoints = []; // Array of [x_mm, y_mm]
    this.breadcrumbTrail = []; // Historical positions drawn by platform: [[x, y], ...]
    this.maxTrailPoints = 3000;

    // Presets library (normalized coordinates that will be fit to workspace)
    this.samplePresets = {
      star: this.generateStarPreset(),
      spiral: this.generateSpiralPreset(),
      gear: this.generateGearPreset(),
      calGrid: this.generateCalibrationGridPreset(),
      diamondWave: this.generateDiamondWavePreset()
    };
  }

  setMode(mode) {
    this.mode = mode;
    if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
  }

  addWaypoint(x, y) {
    // Clamp to safe workspace bounds
    const cx = Math.max(-180, Math.min(180, Math.round(x)));
    const cy = Math.max(-140, Math.min(140, Math.round(y)));
    this.waypoints.push([cx, cy]);
    if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
  }

  removeWaypoint(index) {
    if (index >= 0 && index < this.waypoints.length) {
      this.waypoints.splice(index, 1);
      if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
    }
  }

  clearWaypoints() {
    this.waypoints = [];
    if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
  }

  clearTrail() {
    this.breadcrumbTrail = [];
  }

  pushTrailPoint(x, y) {
    if (this.breadcrumbTrail.length === 0) {
      this.breadcrumbTrail.push([x, y]);
      return;
    }
    const [lastX, lastY] = this.breadcrumbTrail[this.breadcrumbTrail.length - 1];
    if (Math.hypot(x - lastX, y - lastY) >= 1.0) {
      this.breadcrumbTrail.push([x, y]);
      if (this.breadcrumbTrail.length > this.maxTrailPoints) {
        this.breadcrumbTrail.shift();
      }
    }
  }

  // --- Presets Generators ---
  generateStarPreset() {
    const pts = [];
    const rOuter = 70;
    const rInner = 28;
    const numPoints = 5;
    for (let i = 0; i < numPoints * 2; i++) {
      const angle = (i * Math.PI) / numPoints - Math.PI / 2;
      const r = i % 2 === 0 ? rOuter : rInner;
      pts.push([Math.round(r * Math.cos(angle)), Math.round(r * Math.sin(angle))]);
    }
    pts.push([...pts[0]]); // close loop
    return pts;
  }

  generateSpiralPreset() {
    const pts = [];
    const turns = 3.5;
    const steps = 60;
    for (let i = 0; i <= steps; i++) {
      const theta = (i / steps) * (turns * 2 * Math.PI);
      const r = (i / steps) * 75;
      pts.push([Math.round(r * Math.cos(theta)), Math.round(r * Math.sin(theta))]);
    }
    return pts;
  }

  generateGearPreset() {
    const pts = [];
    const teeth = 8;
    const rRoot = 45;
    const rTip = 65;
    for (let i = 0; i < teeth; i++) {
      const a0 = (i / teeth) * 2 * Math.PI;
      const a1 = a0 + (0.35 / teeth) * 2 * Math.PI;
      const a2 = a0 + (0.50 / teeth) * 2 * Math.PI;
      const a3 = a0 + (0.85 / teeth) * 2 * Math.PI;
      pts.push([Math.round(rRoot * Math.cos(a0)), Math.round(rRoot * Math.sin(a0))]);
      pts.push([Math.round(rTip * Math.cos(a1)), Math.round(rTip * Math.sin(a1))]);
      pts.push([Math.round(rTip * Math.cos(a2)), Math.round(rTip * Math.sin(a2))]);
      pts.push([Math.round(rRoot * Math.cos(a3)), Math.round(rRoot * Math.sin(a3))]);
    }
    pts.push([...pts[0]]);
    return pts;
  }

  generateCalibrationGridPreset() {
    return [
      [-120, -90], [120, -90], [120, -45], [-120, -45],
      [-120, 0], [120, 0], [120, 45], [-120, 45],
      [-120, 90], [120, 90], [0, 90], [0, -90]
    ];
  }

  generateDiamondWavePreset() {
    const pts = [];
    const xSpan = 260;
    const ySpan = 70;
    const steps = 5;
    for (let i = 0; i <= steps; i++) {
      const x = -130 + (i / steps) * xSpan;
      const y = (i % 2 === 0 ? 1 : -1) * ySpan;
      pts.push([Math.round(x), Math.round(y)]);
    }
    pts.push([0, 0]);
    return pts;
  }

  loadPreset(presetName) {
    if (this.samplePresets[presetName]) {
      this.waypoints = JSON.parse(JSON.stringify(this.samplePresets[presetName]));
      if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
      this.showMessage(`Loaded preset: ${presetName.toUpperCase()} (${this.waypoints.length} points)`);
    }
  }

  // --- SVG Vector Parser ---
  parseSVG(svgString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgString, "image/svg+xml");
    const rawPoints = [];

    // 1. Extract from polylines & polygons
    const polylines = doc.querySelectorAll('polyline, polygon');
    polylines.forEach(poly => {
      const pointsAttr = poly.getAttribute('points') || '';
      const pairs = pointsAttr.trim().split(/\s+|,/);
      for (let i = 0; i < pairs.length - 1; i += 2) {
        const x = parseFloat(pairs[i]);
        const y = parseFloat(pairs[i + 1]);
        if (!isNaN(x) && !isNaN(y)) rawPoints.push([x, y]);
      }
    });

    // 2. Extract from lines
    const lines = doc.querySelectorAll('line');
    lines.forEach(l => {
      const x1 = parseFloat(l.getAttribute('x1'));
      const y1 = parseFloat(l.getAttribute('y1'));
      const x2 = parseFloat(l.getAttribute('x2'));
      const y2 = parseFloat(l.getAttribute('y2'));
      if (!isNaN(x1) && !isNaN(y1)) rawPoints.push([x1, y1]);
      if (!isNaN(x2) && !isNaN(y2)) rawPoints.push([x2, y2]);
    });

    // 3. Extract from paths using SVGPathElement sampling if available in DOM
    const paths = doc.querySelectorAll('path');
    paths.forEach(p => {
      try {
        const pathData = p.getAttribute('d');
        if (pathData) {
          // Approximate by creating a dummy DOM path or parsing coordinate pairs
          const dummySvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          const dummyPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
          dummyPath.setAttribute("d", pathData);
          dummySvg.appendChild(dummyPath);
          document.body.appendChild(dummySvg);

          const totalLength = dummyPath.getTotalLength();
          const sampleCount = Math.max(10, Math.min(250, Math.floor(totalLength / 8)));
          for (let i = 0; i <= sampleCount; i++) {
            const pt = dummyPath.getPointAtLength((i / sampleCount) * totalLength);
            rawPoints.push([pt.x, pt.y]);
          }
          document.body.removeChild(dummySvg);
        }
      } catch (e) {
        console.warn("Path sampling fallback:", e);
      }
    });

    if (rawPoints.length < 2) {
      throw new Error("Could not extract at least 2 coordinate points from SVG file.");
    }

    this.normalizeAndLoadPoints(rawPoints, "SVG Vector Drawing");
  }

  // --- G-Code Parser ---
  parseGCode(gcodeText) {
    const lines = gcodeText.split(/\r?\n/);
    const rawPoints = [];
    let curX = 0;
    let curY = 0;

    for (let line of lines) {
      // Strip comments
      line = line.split(';')[0].split('(')[0].trim().toUpperCase();
      if (!line) continue;

      if (line.startsWith('G0') || line.startsWith('G1') || line.startsWith('G00') || line.startsWith('G01')) {
        const xMatch = line.match(/X\s*(-?\d+(\.\d+)?)/);
        const yMatch = line.match(/Y\s*(-?\d+(\.\d+)?)/);

        if (xMatch) curX = parseFloat(xMatch[1]);
        if (yMatch) curY = parseFloat(yMatch[1]);

        if (xMatch || yMatch) {
          rawPoints.push([curX, curY]);
        }
      }
    }

    if (rawPoints.length < 2) {
      throw new Error("No G0/G1 XY coordinate movements found in G-Code file.");
    }

    this.normalizeAndLoadPoints(rawPoints, "G-Code Toolpath");
  }

  // Scales arbitrary coordinate space into robot's safe workspace [-160..160, -120..120] mm
  normalizeAndLoadPoints(rawPoints, sourceName) {
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    for (const [x, y] of rawPoints) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }

    const spanX = maxX - minX || 1;
    const spanY = maxY - minY || 1;
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    // Target max dimensions in robot workspace: 280 mm x 220 mm
    const targetSpanX = 280;
    const targetSpanY = 220;
    const scale = Math.min(targetSpanX / spanX, targetSpanY / spanY);

    const scaled = rawPoints.map(([x, y]) => {
      // Center and scale, invert SVG Y axis (downward -> upward)
      const nx = (x - centerX) * scale;
      const ny = -(y - centerY) * scale;
      return [Math.round(nx), Math.round(ny)];
    });

    // Decimate redundant points that are too close (< 2.5 mm)
    const filtered = [scaled[0]];
    for (let i = 1; i < scaled.length; i++) {
      const prev = filtered[filtered.length - 1];
      const cur = scaled[i];
      if (Math.hypot(cur[0] - prev[0], cur[1] - prev[1]) >= 2.5) {
        filtered.push(cur);
      }
    }

    this.waypoints = filtered;
    if (this.onPathUpdated) this.onPathUpdated(this.waypoints);
    this.showMessage(`Successfully imported ${sourceName} (${this.waypoints.length} waypoints)`);
  }

  // --- Dispatch Trajectory to Backend ---
  async executePath(speedMmS = 50) {
    if (this.waypoints.length < 2) {
      this.showMessage("Need at least 2 waypoints to execute path.", true);
      return false;
    }

    try {
      this.clearTrail(); // Reset trail for clean execution
      const payload = {
        type: 'waypoints',
        params: {
          waypoints_mm: this.waypoints,
          speed_mm_s: speedMmS
        }
      };

      const res = await fetch(`${this.apiBase}/command/trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        const errMsg = data.detail?.message || data.detail?.error || "Feasibility check failed";
        this.showMessage(`Trajectory error: ${errMsg}`, true);
        return false;
      }

      this.showMessage(`Executing path: ${this.waypoints.length} waypoints (${data.message})`);
      return true;
    } catch (err) {
      this.showMessage(`Network error executing path: ${err.message}`, true);
      return false;
    }
  }
}

window.PathPlannerManager = PathPlannerManager;
