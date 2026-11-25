"""
Comprehensive HTML and JSON Job Verification Report Generator for PROJECT W.A.L.L.
Compiles post-print quality inspection, color accuracy, mechanical telemetry statistics,
and photographic visual provenance into a self-contained deliverable document (Section 13).
"""

from typing import Dict, Any, Optional
import time
from ..quality.quality_inspector import CompletedJobReport


class ReportGenerator:
    @staticmethod
    def generate_html_report(report: CompletedJobReport) -> str:
        q = report.quality
        img_tag = f'<img src="{report.deposited_image_b64}" alt="Print Result" style="max-width:100%; border:1px solid #374151; border-radius:6px;"/>' if report.deposited_image_b64 else '<p style="color:#9ca3af;">No visual capture available</p>'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Job Verification Report — {report.job_id}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }}
    .container {{ max-width: 900px; margin: 0 auto; background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 32px; }}
    h1 {{ color: #06b6d4; font-size: 22px; margin-top: 0; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px; background: #10b981; color: #000; }}
    .badge.fail {{ background: #ef4444; color: #fff; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }}
    .card {{ background: #1f2937; border-left: 3px solid #06b6d4; padding: 16px; border-radius: 4px; }}
    .val {{ font-size: 24px; font-weight: 700; color: #fff; font-family: monospace; }}
    .lbl {{ font-size: 11px; text-transform: uppercase; color: #9ca3af; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #374151; font-size: 13px; }}
    th {{ color: #06b6d4; }}
    .footer {{ font-size: 11px; color: #6b7280; margin-top: 32px; border-top: 1px solid #374151; padding-top: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <div>
        <h1>PROJECT W.A.L.L. — Autonomous Print Job Report</h1>
        <p style="color:#9ca3af; margin:0; font-size:13px;">Job ID: <b>{report.job_id}</b> &bull; Mode: <b>{report.printing_mode.upper()}</b></p>
      </div>
      <div>
        <span class="badge {'fail' if not q.inspection_passed else ''}">{'PASSED' if q.inspection_passed else 'NEEDS ATTENTION'}</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="val">{q.coverage_percentage:.1f}%</div>
        <div class="lbl">Coverage Ratio</div>
      </div>
      <div class="card">
        <div class="val">{q.delta_e_color_error:.2f}</div>
        <div class="lbl">Mean CIE &Delta;E</div>
      </div>
      <div class="card">
        <div class="val">{q.mean_absolute_error:.2f}</div>
        <div class="lbl">RGB MAE Error</div>
      </div>
      <div class="card">
        <div class="val">{q.edge_fidelity_score:.1f}%</div>
        <div class="lbl">Edge Fidelity</div>
      </div>
    </div>

    <h3>Job Provenance & Mechanical Execution</h3>
    <table>
      <tr><th>Parameter</th><th>Value</th><th>Parameter</th><th>Value</th></tr>
      <tr><td>Surface Dimensions</td><td>{report.surface_width_mm:.0f} &times; {report.surface_height_mm:.0f} mm</td><td>Printed Artwork Area</td><td>{report.print_width_mm:.0f} &times; {report.print_height_mm:.0f} mm</td></tr>
      <tr><td>Source Image File</td><td>{report.image_filename}</td><td>Total Path Length</td><td>{report.total_path_length_m:.2f} m</td></tr>
      <tr><td>Elapsed Print Duration</td><td>{report.elapsed_time_s:.1f} s</td><td>Completion Status</td><td>{report.completion_status}</td></tr>
    </table>

    <h3>Visual Deposition Output</h3>
    {img_tag}

    <div class="footer">
      Generated automatically by PROJECT W.A.L.L. CDPR Simulation Engine &bull; Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
    </div>
  </div>
</body>
</html>
"""
        return html

