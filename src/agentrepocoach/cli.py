"""AgentRepoCoach CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import VERSION
from .adapters import NoAdapterError
from .compute import compute_cah
from .config import ConfigError, load_config
from .output import (
    format_comparison,
    format_comparison_markdown,
    format_summary,
    format_verbose,
    write_json,
    write_markdown_comment,
    write_prometheus,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``agentrepocoach`` CLI."""
    parser = argparse.ArgumentParser(
        prog="agentrepocoach",
        description="Compute the Codebase Agent Health (CAH) composite score for a repository.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path to the repository to score (default: current directory).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Explicit config file path (default: <repo>/.agentrepocoach.toml).",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Override language detection (csharp|python|auto).",
    )
    parser.add_argument("--json", type=Path, help="Write full JSON result to this path.")
    parser.add_argument("--prometheus", type=Path, help="Write Prometheus metrics to this path.")
    parser.add_argument("--comment", type=Path, help="Write a PR-comment markdown file to this path.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default=None,
        help="Output format when using --output. 'json' writes the full report, "
             "'markdown' writes a PR-comment summary, 'both' writes both (markdown "
             "path derived from --output by swapping the extension to .md).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for --format. Ignored if --format is not set.",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="Path to a baseline JSON report. Prints a delta comparison instead of "
             "the normal summary.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print per-sub-component breakdown.")
    parser.add_argument("--quiet", action="store_true", help="Print only the total score.")
    parser.add_argument("--version", action="version", version=f"agentrepocoach {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, parse arguments, compute the CAH score, and write outputs."""
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = args.repo.resolve()
    if not repo_root.is_dir():
        print(f"error: repo path is not a directory: {repo_root}", file=sys.stderr)
        return 2

    try:
        config = load_config(repo_root, config_path=args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.language:
        # Replace the config's language field. Dataclass is frozen -> rebuild.
        from dataclasses import replace as _replace
        config = _replace(config, language=args.language)

    try:
        result = compute_cah(repo_root, config=config)
    except NoAdapterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.compare:
        baseline_path = args.compare.resolve()
        if not baseline_path.is_file():
            print(f"error: baseline report not found: {baseline_path}", file=sys.stderr)
            return 2
        import json as _json
        baseline = _json.loads(baseline_path.read_text())
        if args.quiet:
            delta = result["total"] - baseline["total"]
            print(f"{delta:+.2f}")
        else:
            print(format_comparison(result, baseline))
    elif args.quiet:
        print(f"{result['total']:.2f}")
    elif args.verbose:
        print(format_verbose(result))
    else:
        print(format_summary(result))

    if args.json:
        write_json(result, args.json)
        if not args.quiet:
            print(f"\nJSON report written to {args.json}")

    if args.prometheus:
        write_prometheus(result, args.prometheus)
        if not args.quiet:
            print(f"Prometheus metrics written to {args.prometheus}")

    if args.comment:
        write_markdown_comment(result, args.comment)
        if not args.quiet:
            print(f"PR comment written to {args.comment}")

    if args.format and args.output:
        _write_formatted(result, args.format, args.output, quiet=args.quiet)
    elif args.format and not args.output:
        print("error: --format requires --output", file=sys.stderr)
        return 2

    return 0


def _write_formatted(
    result: dict,
    fmt: str,
    output: Path,
    *,
    quiet: bool,
) -> None:
    """Dispatch --format/--output combinations to the underlying writers."""
    if fmt == "json":
        write_json(result, output)
        if not quiet:
            print(f"\nJSON report written to {output}")
        return
    if fmt == "markdown":
        write_markdown_comment(result, output)
        if not quiet:
            print(f"\nMarkdown report written to {output}")
        return
    # fmt == "both"
    json_path = output
    markdown_path = output.with_suffix(".md")
    write_json(result, json_path)
    write_markdown_comment(result, markdown_path)
    if not quiet:
        print(f"\nJSON report written to {json_path}")
        print(f"Markdown report written to {markdown_path}")


if __name__ == "__main__":
    sys.exit(main())
