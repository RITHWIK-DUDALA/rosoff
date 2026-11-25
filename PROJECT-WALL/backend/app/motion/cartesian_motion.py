"""
PROJECT W.A.L.L. — Planar Motion Shims
Forwards legacy references to SynchronizedTrajectoryPlanner in compliance with Part 0 Rules (CDPR Architecture).
"""
from .trajectory_planner import SynchronizedTrajectoryPlanner, MotionWaypoint

__all__ = ["SynchronizedTrajectoryPlanner", "MotionWaypoint"]

