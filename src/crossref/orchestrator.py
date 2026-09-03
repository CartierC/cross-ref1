"""Ties Stage 1, Stage 2, validation, and run-artifact persistence together.

One call to `run()` = one full Cross Reference run: independent pass ->
lock -> audit/synthesis pass -> validate -> persist -> manifest state.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .audit_pass import run_audit_pass
from .independent_pass import build_stage1_context, run_independent_pass
from .providers.base import Provider, ProviderError
from .schemas import (
    ManifestProviderInfo,
    ManifestState,
    RunInput,
    RunManifest,
)
from .storage import DEFAULT_RUNS_ROOT, next_run_id, run_dir, write_json, write_text
from .validation import validate_run


class RunFailure(RuntimeError):
    def __init__(self, message: str, state: ManifestState):
        super().__init__(message)
        self.state = state


def run(
    run_input: RunInput,
    stage1_provider: Provider,
    stage2_provider: Provider,
    runs_root: Path = DEFAULT_RUNS_ROOT,
) -> tuple[str, RunManifest]:
    run_id = run_input.run_id or next_run_id(runs_root)
    out_dir = run_dir(run_id, runs_root)

    manifest = RunManifest(
        run_id=run_id,
        state=ManifestState.RUNNING,
        providers=ManifestProviderInfo(
            stage1_provider=stage1_provider.name,
            stage1_model=stage1_provider.model,
            stage2_provider=stage2_provider.name,
            stage2_model=stage2_provider.model,
        ),
    )
    write_json(out_dir / "manifest.json", manifest.model_dump(mode="json"))
    write_json(out_dir / "input.json", run_input.model_dump(mode="json"))

    try:
        # --- Stage 1: independent generation, primary_output never enters ---
        stage1_ctx = build_stage1_context(run_input)
        independent = run_independent_pass(stage1_ctx, stage1_provider)
        write_json(out_dir / "independent.json", independent.model_dump(mode="json"))

        # --- Stage 2: audit + synthesis, primary_output revealed now ---
        result = run_audit_pass(run_input, independent, stage2_provider)
        write_json(out_dir / "result.json", result.model_dump(mode="json"))
        write_text(out_dir / "canonical.md", result.canonical_output)

    except ProviderError as exc:
        manifest.state = ManifestState.FAILED_RUNTIME
        manifest.error = str(exc)
        _finalize(out_dir, manifest)
        return run_id, manifest
    except (ValidationError, ValueError) as exc:
        manifest.state = ManifestState.FAILED_VALIDATION
        manifest.error = f"Stage 2 response did not match the required schema: {exc}"
        _finalize(out_dir, manifest)
        return run_id, manifest

    report = validate_run(run_input, independent, result)
    write_json(out_dir / "validation.json", report.to_dict())
    manifest.validation_summary = report.to_dict()

    manifest.state = ManifestState.PASSED if not report.has_failures else ManifestState.FAILED_VALIDATION
    _finalize(out_dir, manifest)
    return run_id, manifest


def _finalize(out_dir: Path, manifest: RunManifest) -> None:
    from .schemas import utcnow_iso

    manifest.updated_at = utcnow_iso()
    write_json(out_dir / "manifest.json", manifest.model_dump(mode="json"))
