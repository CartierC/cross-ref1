"""CLI entrypoint: python -m crossref.runner run --input path/to/input.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .orchestrator import run
from .providers import get_provider
from .schemas import ManifestState, RunInput


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

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
        run_input = RunInput.model_validate(raw)

        stage1_provider = get_provider(
            args.stage1_provider or args.provider, model=args.stage1_model or args.model
        )
        stage2_provider = get_provider(
            args.stage2_provider or args.provider, model=args.stage2_model or args.model
        )

        kwargs = {}
        if args.runs_root:
            kwargs["runs_root"] = Path(args.runs_root)

        run_id, manifest = run(run_input, stage1_provider, stage2_provider, **kwargs)

        print(f"run_id={run_id} state={manifest.state.value}")
        if manifest.error:
            print(f"error: {manifest.error}", file=sys.stderr)
        return 0 if manifest.state == ManifestState.PASSED else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
