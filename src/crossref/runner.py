"""CLI entrypoint: python -m crossref.runner run --input path/to/input.json"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from .orchestrator import run
from .providers import get_provider
from .schemas import ManifestState, RunInput
from .storage import DEFAULT_LATEST_ROOT


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crossref", description="Cross Reference Agent runner")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Execute a full Cross Reference run")
    run_cmd.add_argument("--input", required=True, help="Path to a RunInput JSON file")
    run_cmd.add_argument("--provider", default="anthropic", help="Provider for both stages (default: anthropic)")
    run_cmd.add_argument("--model", default=None, help="Model for both stages")
    run_cmd.add_argument("--stage1-provider", default=None, help="Override provider for Stage 1")
    run_cmd.add_argument("--stage1-model", default=None, help="Override model for Stage 1")
    run_cmd.add_argument("--stage2-provider", default=None, help="Override provider for Stage 2")
    run_cmd.add_argument("--stage2-model", default=None, help="Override model for Stage 2")
    run_cmd.add_argument("--runs-root", default=None, help="Directory to write runs/ into")
    run_cmd.add_argument("--latest-root", default=None, help="Directory to write latest/canonical.md into")
    run_cmd.add_argument(
        "--no-open",
        action="store_true",
        help="Do not attempt to open canonical.md after a PASSED run",
    )

    return parser


def _open_file(path: Path) -> None:
    """Best-effort, cross-platform "open in the default app". Never raises —
    an unavailable opener (e.g. a headless/CI environment) must not fail
    an otherwise-successful run."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("win"):
            import os

            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


def _print_outcome(manifest, latest_root: Path) -> None:
    out_dir = manifest.output_directory
    if manifest.state == ManifestState.PASSED:
        print("PASSED")
        print()
        print("Run:")
        print(f"  {out_dir}/")
        print()
        print("Canonical:")
        print(f"  {manifest.canonical_path}")
        print()
        print("Latest successful canonical updated:")
        print(f"  {latest_root / 'canonical.md'}")
    else:
        print("FAILED")
        print()
        print("Run:")
        print(f"  {out_dir}/")
        if manifest.error:
            print()
            print(f"error: {manifest.error}", file=sys.stderr)
        print()
        print(f"{latest_root / 'canonical.md'} was NOT changed.")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        input_path = Path(args.input)
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        run_input = RunInput.model_validate(raw)

        stage1_provider = get_provider(
            args.stage1_provider or args.provider, model=args.stage1_model or args.model
        )
        stage2_provider = get_provider(
            args.stage2_provider or args.provider, model=args.stage2_model or args.model
        )

        kwargs = {"source_input_path": input_path}
        if args.runs_root:
            kwargs["runs_root"] = Path(args.runs_root)
        latest_root = Path(args.latest_root) if args.latest_root else DEFAULT_LATEST_ROOT
        kwargs["latest_root"] = latest_root

        run_id, manifest = run(run_input, stage1_provider, stage2_provider, **kwargs)

        _print_outcome(manifest, latest_root)

        if manifest.state == ManifestState.PASSED and not args.no_open and manifest.canonical_path:
            _open_file(Path(manifest.canonical_path))

        return 0 if manifest.state == ManifestState.PASSED else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
