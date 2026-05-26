"""AgentRepoCoach scoring components.

Each component returns a dict with ``{"score": float, "total": 100,
"breakdown": {...}}``. The orchestrator in :mod:`agentrepocoach.compute` combines
them with weights from config to produce the final composite score.

File-to-component mapping:

- ``documentation.py``       -> ``navigability`` (AGENTS.md, codebase map, CLI manifest, root hygiene)
- ``error_quality.py``       -> ``error_quality``
- ``decision_queryability.py`` -> ``decision_queryability``
- ``test_quality.py``        -> ``test_quality``
- ``module_hygiene.py``      -> ``module_hygiene``
- ``bootstrap_signals.py``   -> ``bootstrap_signals`` (CI workflow + README quality)
"""
from .bootstrap_signals import compute_bootstrap_signals
from .decision_queryability import compute_decision_queryability
from .documentation import compute_navigability
from .error_quality import compute_error_quality
from .module_hygiene import compute_module_hygiene
from .test_quality import compute_test_quality

__all__ = [
    "compute_bootstrap_signals",
    "compute_decision_queryability",
    "compute_error_quality",
    "compute_module_hygiene",
    "compute_navigability",
    "compute_test_quality",
]
