"""
PROJECT W.A.L.L. — Central Orchestrator Shims
Forwards legacy references to CDPROrchestrator in compliance with Part 0 Rules (CDPR Architecture).
"""
from .cdpr_orchestrator import CDPROrchestrator

__all__ = ["CDPROrchestrator"]

