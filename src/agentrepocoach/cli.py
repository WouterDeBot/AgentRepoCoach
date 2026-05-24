"""AgentRepoCoach CLI entry point."""
from __future__ import annotations

import argparse
import json as _json
import sys
from pathlib import Path

from . import VERSION
from .adapters import NoAdapterError
from .compute import compute_cah, compute_cah_all
from .config import Config, ConfigError, load_config
from .output import (
    format_comparison,
    format_comparison_markdown,
    format_summary,
    format_verbose,
    render_json,
    render_markdown_comment,
    write_json,
    write_markdown_comment,
    write_prometheus,
)
from .pr_bot import compare_scores, format_pr_comment, parse_score_output


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
    lang_group = parser.add_mutually_exclusive_group()
    lang_group.add_argument(
        "--language",
        type=str,
        default=None,
        help="Override language detection (csharp|go|python|rust|typescript|auto). Mutually exclusive with --all-languages.",
    )
    lang_group.add_argument(
        "--all-languages",
        action="store_true",
        default=False,
        dest="all_languages",
        help="Score every detected language above threshold. Mutually exclusive with --language.",
    )
    parser.add_argument("--json", type=Path, help="Write full JSON result to this path.")
    parser.add_argument("--prometheus", type=Path, help="Write Prometheus metrics to this path.")
    parser.add_argument("--comment", type=Path, help="Write a PR-comment markdown file to this path.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default=None,
        help="Output format. 'json' prints the full report (to stdout or --output), "
             "'markdown' prints a PR-comment summary (to stdout or --output), "
             "'both' writes both to --output (markdown path derived by swapping "
             "the extension to .md; requires --output).",
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

    # Subcommands
    subparsers = parser.add_subparsers(dest="subcommand")

    # compare subcommand
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two JSON score files and display deltas.",
    )
    compare_parser.add_argument(
        "base_file",
        type=Path,
        help="Path to the base (target branch) JSON score file.",
    )
    compare_parser.add_argument(
        "pr_file",
        type=Path,
        help="Path to the PR (source branch) JSON score file.",
    )
    compare_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw comparison dict as JSON instead of markdown.",
    )

    return parser


def _run_compare(args: argparse.Namespace) -> int:
    """Execute the ``compare`` subcommand."""
    base_path = args.base_file.resolve()
    pr_path = args.pr_file.resolve()

    if not base_path.is_file():
        print(f"error: base file does not exist: {base_path}", file=sys.stderr)
        return 2
    if not pr_path.is_file():
        print(f"error: pr file does not exist: {pr_path}", file=sys.stderr)
        return 2

    try:
        base_scores = parse_score_output(base_path.read_text())
    except ValueError as exc:
        print(f"error: failed to parse base file: {exc}", file=sys.stderr)
        return 2

    try:
        pr_scores = parse_score_output(pr_path.read_text())
    except ValueError as exc:
        print(f"error: failed to parse pr file: {exc}", file=sys.stderr)
        return 2

    comparison = compare_scores(base_scores, pr_scores)

    if args.json_output:
        print(_json.dumps(comparison, indent=2))
    else:
        print(format_pr_comment(comparison))

    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, parse arguments, compute the CAH score, and write outputs."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Dispatch subcommands
    if args.subcommand == "compare":
        return _run_compare(args)

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

    if args.all_languages:
        return _run_all_languages(repo_root, config, args)

    try:
        result = compute_cah(repo_root, config=config)
    except NoAdapterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # When --format is used without --output, the formatted content replaces
    # the default terminal summary on stdout.
    stdout_replaced_by_format = args.format and not args.output

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
    elif stdout_replaced_by_format:
        pass  # handled below in the --format block
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
        if args.format == "both":
            print("error: --format both requires --output", file=sys.stderr)
            return 2
        _print_formatted(result, args.format)

    return 0


def _run_all_languages(
    repo_root: Path,
    config: Config,
    args: argparse.Namespace,
) -> int:
    """Handle the --all-languages code path."""
    try:
        result = compute_cah_all(repo_root, config=config)
    except (NoAdapterError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    languages: dict = result.get("languages", {})

    if not languages:
        print("No language met the detection threshold (confidence >= 0.5, file count >= 3).", file=sys.stderr)
        return 2

    # Text output: one summary block per language, separated by a header line.
    if not args.quiet:
        first = True
        for lang_name, lang_result in languages.items():
            if not first:
                print()
            print(f"=== Language: {lang_name} ===")
            print(format_summary(lang_result))
            first = False

    # JSON file output: write the nested multi-language shape.
    if args.json:
        write_json(result, args.json)
        if not args.quiet:
            print(f"\nJSON report written to {args.json}")

    # --format json to stdout.
    if args.format == "json" and not args.output:
        print(render_json(result))
    elif args.format == "json" and args.output:
        write_json(result, args.output)
        if not args.quiet:
            print(f"\nJSON report written to {args.output}")

    return 0


def _print_formatted(result: dict, fmt: str) -> None:
    """Print formatted output to stdout when --output is not provided."""
    if fmt == "json":
        print(render_json(result))
    elif fmt == "markdown":
        print(render_markdown_comment(result))


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
