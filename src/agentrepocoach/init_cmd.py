"""Implementation of the ``agentrepocoach init`` subcommand.

Creates a ``.agentrepocoach.toml`` configuration file with sensible defaults
in the current (or specified) directory, then prints a next-steps coaching
message.  No interactive prompts — all options are CLI flags.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .config import CURRENT_SCHEMA_VERSION, DEFAULT_WEIGHTS

# Valid repo_type values.
_VALID_REPO_TYPES = ("default", "private-internal")

# TOML template — weights and schema_version are filled at runtime from the
# canonical constants in config.py so the template never drifts.
_TOML_TEMPLATE = """\
schema_version = {schema_version}

# repo_type controls bootstrap_signals weighting.
# Options: "default" | "private-internal"
{repo_type_line}

[weights]
navigability = {navigability}
error_quality = {error_quality}
decision_queryability = {decision_queryability}
test_quality = {test_quality}
module_hygiene = {module_hygiene}
bootstrap_signals = {bootstrap_signals}
"""


def _format_weight(value: float) -> str:
    """Format a weight value as a string with 2 decimal places."""
    return f"{value:.2f}"


def build_toml_content(repo_type: str) -> str:
    """Return the TOML config content for the given repo_type.

    When ``repo_type`` is ``"private-internal"`` the ``repo_type`` key is
    written as an active line.  Otherwise it is written as a comment so the
    file is immediately valid without requiring the user to delete anything.
    """
    if repo_type and repo_type != "default":
        repo_type_line = f'repo_type = "{repo_type}"'
    else:
        repo_type_line = '# repo_type = "default"'

    return _TOML_TEMPLATE.format(
        schema_version=CURRENT_SCHEMA_VERSION,
        repo_type_line=repo_type_line,
        navigability=_format_weight(DEFAULT_WEIGHTS["navigability"]),
        error_quality=_format_weight(DEFAULT_WEIGHTS["error_quality"]),
        decision_queryability=_format_weight(DEFAULT_WEIGHTS["decision_queryability"]),
        test_quality=_format_weight(DEFAULT_WEIGHTS["test_quality"]),
        module_hygiene=_format_weight(DEFAULT_WEIGHTS["module_hygiene"]),
        bootstrap_signals=_format_weight(DEFAULT_WEIGHTS["bootstrap_signals"]),
    )


def run_init(output: Path, repo_type: str) -> int:
    """Execute the init logic.

    Returns an exit code (0 = success, 1 = error).
    """
    if repo_type and repo_type not in _VALID_REPO_TYPES:
        print(
            f"error: unknown repo_type '{repo_type}'. "
            f"Valid options: {', '.join(_VALID_REPO_TYPES)}",
            file=sys.stderr,
        )
        return 1

    if output.exists():
        print(
            f"error: {output} already exists. "
            "Remove it or pass --output to specify a different path.",
            file=sys.stderr,
        )
        return 1

    content = build_toml_content(repo_type)

    try:
        output.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"error: could not write {output}: {exc}", file=sys.stderr)
        return 1

    print(f"Created {output}")
    print()
    print("Next steps:")
    print(f"  agentrepocoach score .    # see your baseline CAH score")
    print(f"  agentrepocoach score . --verbose    # per-component breakdown")
    print()
    print(
        "Edit the [weights] section to tune the scoring to your team's priorities. "
        "See docs/configuration.md for all available options."
    )
    return 0
