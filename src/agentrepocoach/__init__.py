"""AgentRepoCoach — Codebase Agent Health (CAH) composite score.

Public entry points:

    from agentrepocoach import compute_cah, VERSION
    result = compute_cah(Path("/path/to/repo"))
"""
from __future__ import annotations

from .compute import compute_cah

VERSION = "0.3.0"

__all__ = ["compute_cah", "VERSION"]
