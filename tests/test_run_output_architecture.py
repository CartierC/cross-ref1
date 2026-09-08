"""Per-run output directories, latest/canonical.md, and topic sanitization.

Covers the reliability invariants from the run-output architecture upgrade:
a run never overwrites another run's history, a failed run never touches
latest/canonical.md, and every canonical result is traceable to its run and
source input.
"""

import json
from pathlib import Path

from crossref.orchestrator import run
from crossref.providers.mock_provider import MockProvider
from crossref.schemas import ManifestState, RunInput
from crossref.storage import sanitize_topic

FIXTURE = Path(__file__).parent / "fixtures" / "sample_run.json"


def _load_run_input() -> RunInput:
    return RunInput.model_validate(json.loads(FIXTURE.read_text()))


def _dim_scores(value: int) -> dict:
    dims = [
        "objective_alignment", "completeness", "accuracy", "reasoning", "precision",
        "structure", "relevance", "efficiency", "risk_coverage", "opportunity_capture",
        "executability", "constraint_compliance",
    ]
    return {d: value for d in dims}


def _valid_stage2_payload(canonical_text: str) -> dict:
    return {
        "executive_verdict": "C outperforms both A and B on completeness.",
        "scorecard_primary": _dim_scores(2),
        "scorecard_independent": _dim_scores(4),
        "strengths": {"primary": ["cadence"], "independent": ["pricing defined"]},
        "findings": [
            {
                "finding": "No pricing structure",
                "category": "Completeness",
                "severity": "S2",
                "action": "ADD",
                "source": "primary",
            }
        ],
        "synthesis_decisions": [
            {
                "topic": "Pricing",
                "primary": "Absent",
                "independent": "Present",
                "decision": "KEEP_B",
                "reason": "Only B has a price point.",
            }
        ],
        "canonical_output": canonical_text,
        "scorecard_canonical": _dim_scores(5),
        "residual_uncertainties": ["Close rate unverified."],
    }


def _passing_providers(canonical_text: str = "Canonical result text."):
    stage1 = MockProvider(
        responder=lambda system, user: (
            "Independent 30-day plan: target seed-stage founders, $3k/mo retainer, "
            "outbound to warm network, pilot delivery in week 2, KPIs tracked weekly, "
            "risk: slow outbound response handled by widening warm-contact list."
        )
    )
    stage2 = MockProvider(responder=lambda system, user: json.dumps(_valid_stage2_payload(canonical_text)))
    return stage1, stage2


def _failing_providers():
    stage1 = MockProvider(responder=lambda system, user: "A complete independent plan with pricing and KPIs.")
    stage2 = MockProvider(responder=lambda system, user: "not json at all")
    return stage1, stage2


# --- Test 1: successful run -------------------------------------------------


def test_successful_run_produces_unique_directory_and_updates_latest(tmp_path):
    runs_root = tmp_path / "runs"
    latest_root = tmp_path / "latest"
    run_input = _load_run_input()
    stage1, stage2 = _passing_providers("The canonical answer.")

    run_id, manifest = run(
        run_input, stage1, stage2,
        runs_root=runs_root, latest_root=latest_root,
        source_input_path=Path("runs_input/test-topic.json"),
    )

    assert manifest.state == ManifestState.PASSED
    out_dir = Path(manifest.output_directory)

    # Unique, human-readable run directory under runs/.
    assert out_dir.parent == runs_root
    assert out_dir.name.endswith(f"__{run_id}")
    assert "test-topic" in out_dir.name

    # Input snapshot and expected run artifacts exist.
    assert (out_dir / "input.json").exists()
    assert (out_dir / "independent.json").exists()
    assert (out_dir / "result.json").exists()
    assert (out_dir / "validation.json").exists()
    assert (out_dir / "canonical.md").exists()
    assert (out_dir / "manifest.json").exists()

    # PASS status is recorded in the manifest on disk too.
    on_disk_manifest = json.loads((out_dir / "manifest.json").read_text())
    assert on_disk_manifest["state"] == "PASSED"
    assert on_disk_manifest["topic"] == "test-topic"
    assert on_disk_manifest["canonical_path"] == str(out_dir / "canonical.md")

    # latest/canonical.md updates to this run's canonical output.
    latest_canonical = latest_root / "canonical.md"
    assert latest_canonical.exists()
    assert latest_canonical.read_text() == "The canonical answer."

    # The run's own canonical.md is the one that would be opened/selected.
    assert (out_dir / "canonical.md").read_text() == "The canonical answer."


# --- Test 2: failed run ------------------------------------------------------


def test_failed_run_does_not_touch_latest_canonical(tmp_path):
    runs_root = tmp_path / "runs"
    latest_root = tmp_path / "latest"
    run_input = _load_run_input()

    # First, a genuine PASSED run establishes a known-good latest/canonical.md.
    stage1, stage2 = _passing_providers("Previous good canonical.")
    run(run_input, stage1, stage2, runs_root=runs_root, latest_root=latest_root)
    latest_canonical = latest_root / "canonical.md"
    assert latest_canonical.read_text() == "Previous good canonical."

    # Then a failing run must not disturb it.
    fail1, fail2 = _failing_providers()
    run_id, manifest = run(run_input, fail1, fail2, runs_root=runs_root, latest_root=latest_root)

    assert manifest.state == ManifestState.FAILED_VALIDATION
    assert manifest.error is not None

    # The failed run's own directory may still exist for auditability...
    out_dir = Path(manifest.output_directory)
    assert out_dir.exists()
    assert (out_dir / "manifest.json").exists()
    # ...but it never produced a canonical.md (Stage 2 JSON was malformed).
    assert not (out_dir / "canonical.md").exists()
    assert manifest.canonical_path is None

    # Previous successful canonical remains byte-for-byte intact.
    assert latest_canonical.read_text() == "Previous good canonical."


# --- Test 3: two consecutive successful runs --------------------------------


def test_two_consecutive_successful_runs_do_not_clobber_each_other(tmp_path):
    runs_root = tmp_path / "runs"
    latest_root = tmp_path / "latest"
    run_input = _load_run_input()

    stage1_a, stage2_a = _passing_providers("Canonical from run A.")
    run_id_a, manifest_a = run(
        run_input, stage1_a, stage2_a,
        runs_root=runs_root, latest_root=latest_root,
        source_input_path=Path("runs_input/topic-a.json"),
    )

    stage1_b, stage2_b = _passing_providers("Canonical from run B.")
    run_id_b, manifest_b = run(
        run_input, stage1_b, stage2_b,
        runs_root=runs_root, latest_root=latest_root,
        source_input_path=Path("runs_input/topic-b.json"),
    )

    assert manifest_a.state == ManifestState.PASSED
    assert manifest_b.state == ManifestState.PASSED

    dir_a = Path(manifest_a.output_directory)
    dir_b = Path(manifest_b.output_directory)
    assert dir_a != dir_b

    # Both run directories survive independently, with their own canonical.
    assert (dir_a / "canonical.md").read_text() == "Canonical from run A."
    assert (dir_b / "canonical.md").read_text() == "Canonical from run B."

    # latest/canonical.md corresponds only to the second (later) run.
    assert (latest_root / "canonical.md").read_text() == "Canonical from run B."


# --- Test 4: filename sanitization ------------------------------------------


def test_topic_sanitization_produces_filesystem_safe_directory(tmp_path):
    runs_root = tmp_path / "runs"
    latest_root = tmp_path / "latest"
    run_input = _load_run_input()
    stage1, stage2 = _passing_providers()

    unsafe_path = Path("runs_input/Q3 Report: Final?! (v2).json")
    run_id, manifest = run(
        run_input, stage1, stage2,
        runs_root=runs_root, latest_root=latest_root,
        source_input_path=unsafe_path,
    )

    out_dir = Path(manifest.output_directory)
    assert out_dir.exists()
    # Only lowercase letters, digits, and single hyphens.
    import re

    topic_part = manifest.topic
    assert topic_part == sanitize_topic(unsafe_path.stem)
    assert re.fullmatch(r"[a-z0-9-]+", topic_part)
    assert "--" not in topic_part
    assert not topic_part.startswith("-") and not topic_part.endswith("-")


def test_sanitize_topic_handles_spaces_unsafe_chars_and_long_input():
    assert sanitize_topic("FAA 107 Study Guide!!") == "faa-107-study-guide"
    assert sanitize_topic("  Q3 Report: Final?! (v2)  ") == "q3-report-final-v2"
    assert sanitize_topic("2026-09-08_faa107-study-guide") == "faa107-study-guide"
    assert sanitize_topic("") == "run"
    assert sanitize_topic("---") == "run"
    long_topic = sanitize_topic("x" * 200)
    assert len(long_topic) <= 50
