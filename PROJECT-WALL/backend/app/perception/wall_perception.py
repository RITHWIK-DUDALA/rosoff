"""
PROJECT W.A.L.L. — Surface Perception Shims
Forwards legacy references to SurfaceScanner in compliance with Part 0 Rules (CDPR Architecture).
"""
from .surface_scanner import SurfaceScanner, SurfaceScanReport

__all__ = ["SurfaceScanner", "SurfaceScanReport"]

