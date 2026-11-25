"""
REST API Endpoints for Planar Cable Robot PROJECT W.A.L.L.
Implements typed HTTP routes for surface setup, motion commands, image upload,
progressive print execution, diagnostics, emergency stop, and scenario execution.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, Tuple, List
import io
import math
import numpy as np
from PIL import Image

from ..simulation.cdpr_orchestrator import CDPROrchestrator
from ..models.surface_model import SurfaceMaterialCatalog
from ..processing.image_loader import UniversalImageLoader


def create_cdpr_api_router(orchestrator: CDPROrchestrator) -> APIRouter:
    router = APIRouter(prefix="/api")

    class SurfaceConfigRequest(BaseModel):
        width_mm: float = 800.0
        height_mm: float = 600.0
        material_id: str = "smooth_panel"
        mounting_type: str = "suction"

    class MoveRequest(BaseModel):
        x_mm: float
        y_mm: float

    class SwapActuatorRequest(BaseModel):
        module_type: str = "inkjet"

    @router.get("/health")
    async def health():
        return {
            "status": "HEALTHY",
            "system": "PROJECT W.A.L.L. 4-Cable Planar Surface Printing Digital Twin",
            "version": "1.0.0",
            "state": orchestrator.supervisor.state.value
        }

    @router.get("/telemetry")
    async def get_telemetry():
        return orchestrator.get_telemetry()

    @router.get("/surface")
    async def get_surface():
        return orchestrator.surface.to_dict()

    @router.post("/surface/configure")
    async def configure_surface(req: SurfaceConfigRequest):
        orchestrator.surface.set_dimensions(req.width_mm, req.height_mm)
        orchestrator.surface.material = SurfaceMaterialCatalog.get(req.material_id)
        orchestrator.surface.mounting_type = req.mounting_type
        orchestrator.kinematics.anchors = orchestrator.surface.anchors
        verification = orchestrator.surface.verify_mounting()
        return {
            "success": True,
            "surface": orchestrator.surface.to_dict(),
            "mounting_verification": verification.__dict__
        }

    @router.post("/motion/move")
    async def move_to_target(req: MoveRequest):
        ok, msg = orchestrator.move_to(req.x_mm, req.y_mm)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

    @router.post("/actuator/swap")
    async def swap_actuator(req: SwapActuatorRequest):
        from ..printing.actuator import PrintingModuleType
        mod_type = PrintingModuleType.PIEZO_INKJET if "inkjet" in req.module_type.lower() else PrintingModuleType.PAINT_MARKER
        orchestrator.actuator.swap_module(mod_type)
        return {
            "success": True,
            "module_type": orchestrator.actuator.module_type.value,
            "actuator": orchestrator.actuator.to_dict()
        }

    @router.post("/image/upload")
    async def upload_artwork(
        file: UploadFile = File(...),
        target_width_mm: Optional[float] = Form(300.0),
        target_height_mm: Optional[float] = Form(250.0)
    ):
        file_bytes = await file.read()
        try:
            img, orig_size, thumb_b64 = UniversalImageLoader.load_image(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")

        target_w = float(target_width_mm) if target_width_mm is not None else 300.0
        target_h = float(target_height_mm) if target_height_mm is not None else 250.0
        res = orchestrator.load_artwork_image(img, file.filename or "artwork.png", target_w_mm=target_w, target_h_mm=target_h)
        res["thumbnail_base64"] = thumb_b64
        return {"success": True, "job": res}

    @router.post("/print/start")
    async def start_print():
        ok, msg = orchestrator.start_printing()
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

    @router.post("/print/pause")
    async def pause_print():
        orchestrator.pause_printing()
        return {"success": True, "status": "PAUSED"}

    @router.post("/print/resume")
    async def resume_print():
        orchestrator.resume_printing()
        return {"success": True, "status": "PRINTING"}

    @router.post("/control/estop")
    async def emergency_stop():
        orchestrator.emergency_stop()
        return {"success": True, "status": "EMERGENCY_STOP"}

    @router.post("/control/reset")
    async def reset():
        orchestrator.reset()
        return {"success": True, "status": "RESET_OK"}

    @router.get("/scenarios")
    async def list_scenarios():
        return orchestrator.scenario_mgr.list_scenarios()

    @router.post("/scenarios/run/{scenario_id}")
    async def run_scenario(scenario_id: str):
        return orchestrator.scenario_mgr.execute_scenario(scenario_id)

    # ---------------------------------------------------------
    # IMAGE PROCESSOR & CAM CLASSIFICATION ENDPOINTS
    # ---------------------------------------------------------
    def _create_preset_image(preset_id: str) -> Tuple[Image.Image, str]:
        """Generates realistic test artwork image for testing processor capabilities"""
        w, h = 600, 500
        if preset_id == "preset_graphic_logo":
            # Bold high-contrast industrial emblem (Tests Module B Marker)
            img = Image.new("RGB", (w, h), (248, 246, 240))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Outer dark border
            draw.rectangle([40, 40, w - 40, h - 40], outline=(15, 23, 42), width=12)
            # Safety amber triangle
            draw.polygon([(w//2, 80), (w - 90, h - 90), (90, h - 90)], fill=(245, 158, 11), outline=(15, 23, 42))
            # Black exclamation mark
            draw.rectangle([w//2 - 14, 180, w//2 + 14, 310], fill=(15, 23, 42))
            draw.ellipse([w//2 - 14, 335, w//2 + 14, 365], fill=(15, 23, 42))
            return img, "industrial_hazard_logo.png"

        elif preset_id == "preset_gradient_art":
            # Multi-tonal photographic gradient (Tests Module A Piezo)
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            for y in range(h):
                for x in range(w):
                    # Multi-harmonic smooth color field
                    r = int(127.0 + 110.0 * math.sin(x * 0.015) * math.cos(y * 0.01))
                    g = int(100.0 + 90.0 * math.cos((x + y) * 0.012))
                    b = int(40.0 + 35.0 * math.sin(y * 0.02))
                    arr[y, x] = [np.clip(r, 10, 245), np.clip(g, 10, 200), np.clip(b, 10, 180)]
            return Image.fromarray(arr), "continuous_gradient_field.png"

        elif preset_id == "preset_line_schematic":
            # Technical vector schematic
            img = Image.new("RGB", (w, h), (245, 245, 245))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Draw technical crosshair and concentric rings
            cx, cy = w // 2, h // 2
            draw.rectangle([50, 50, w - 50, h - 50], outline=(30, 41, 59), width=4)
            for rad in [60, 120, 180]:
                draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(245, 158, 11), width=4)
            draw.line([(cx, 50), (cx, h - 50)], fill=(30, 41, 59), width=3)
            draw.line([(50, cy), (w - 50, cy)], fill=(30, 41, 59), width=3)
            return img, "optical_alignment_target.png"

        else:
            # Default fallback 3-color industrial badge
            img = Image.new("RGB", (w, h), (245, 245, 245))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([60, 60, w - 60, h - 60], fill=(22, 24, 29), outline=(245, 158, 11), width=8)
            draw.ellipse([150, 150, w - 150, h - 150], fill=(245, 158, 11), outline=(248, 250, 252), width=4)
            return img, "project_wall_badge.png"

    @router.get("/processor/presets")
    async def list_presets():
        return [
            {
                "id": "preset_graphic_logo",
                "title": "Industrial Hazard Emblem",
                "classification_hint": "Module B (Paint Marker, 6mm chisel nib, 1.2N compliance spring)",
                "description": "High-contrast bold vector outlines with solid amber infill. Demonstrates compliance spring force control."
            },
            {
                "id": "preset_gradient_art",
                "title": "Multi-Tonal Continuous Gradient",
                "classification_hint": "Module A (Piezo Inkjet, 48 nozzles, 14 pL micro-droplets)",
                "description": "Smooth harmonic continuous tone field. Demonstrates 14 pL drop-on-demand progressive accumulation without surface contact."
            },
            {
                "id": "preset_line_schematic",
                "title": "Optical Alignment Grid",
                "classification_hint": "Module B (Paint Marker, Fine Vector Pass)",
                "description": "Concentric rings and calibration crosshairs for kinematic precision verification."
            }
        ]

    @router.post("/processor/analyze")
    async def process_and_analyze_artwork(
        file: Optional[UploadFile] = File(None),
        preset_id: Optional[str] = Form(None),
        target_width_mm: float = Form(300.0),
        target_height_mm: float = Form(250.0),
        row_pitch_mm: float = Form(3.0),
        actuator_override: Optional[str] = Form(None)
    ):
        img = None
        filename = "artwork.png"

        if file and file.filename:
            file_bytes = await file.read()
            try:
                img, orig_size, thumb_b64 = UniversalImageLoader.load_image(file_bytes)
                filename = file.filename
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid uploaded image: {str(e)}")
        elif preset_id:
            img, filename = _create_preset_image(preset_id)
        else:
            # Default calibration image
            img, filename = _create_preset_image("preset_graphic_logo")

        report = orchestrator.process_artwork_file(
            img=img,
            filename=filename,
            target_w_mm=target_width_mm,
            target_h_mm=target_height_mm,
            pitch_mm=row_pitch_mm,
            actuator_override=actuator_override
        )
        return {"success": True, "report": report}

    @router.post("/processor/execute")
    async def execute_processed_job():
        ok, msg = orchestrator.execute_processed_job()
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

    @router.get("/processor/current_report")
    async def get_current_report():
        if orchestrator.last_processed_report:
            from dataclasses import asdict
            return {"success": True, "report": asdict(orchestrator.last_processed_report)}
        # If no report yet, create default
        img, filename = _create_preset_image("preset_graphic_logo")
        report = orchestrator.process_artwork_file(img, filename)
        return {"success": True, "report": report}

    @router.get("/processor/logs")
    async def get_execution_logs(since_id: int = 0, limit: int = 150):
        return {
            "since_id": since_id,
            "total_available": orchestrator.event_log_counter,
            "logs": orchestrator.get_logs(since_id=since_id, limit=limit)
        }

    @router.get("/algorithms")
    async def list_algorithms():
        from ..diagnostics.algorithm_registry import GLOBAL_ALGORITHM_REGISTRY
        return {
            "total_algorithms": len(GLOBAL_ALGORITHM_REGISTRY.get_all()),
            "specification_version": "COMPLETE ALGORITHMIC ENGINEERING SPECIFICATION 2.0",
            "algorithms": GLOBAL_ALGORITHM_REGISTRY.get_all()
        }

    return router

