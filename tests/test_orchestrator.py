import json
from pathlib import Path

from crossref.orchestrator import run
from crossref.providers.mock_provider import MockProvider
from crossref.schemas import ManifestState, RunInput

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


def _valid_stage2_payload() -> dict:
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
        "canonical_output": (
            "Automation consulting 30-day launch plan: define target customer, "
            "offer a $3k/mo retainer, run outbound to warm contacts, deliver a "
            "pilot automation, then convert to retainer while tracking KPIs and risks."
        ),
        "scorecard_canonical": _dim_scores(5),
        "residual_uncertainties": ["Close rate unverified."],
    }


def test_full_run_passes_with_valid_providers(tmp_path):
    run_input = _load_run_input()
    stage1 = MockProvider(
        responder=lambda system, user: (
            "Independent 30-day plan: target seed-stage founders, $3k/mo retainer, "
            "outbound to warm network, pilot delivery in week 2, KPIs tracked weekly, "
            "risk: slow outbound response handled by widening warm-contact list."
        )
    )
    stage2 = MockProvider(responder=lambda system, user: json.dumps(_valid_stage2_payload()))

    run_id, manifest = run(run_input, stage1, stage2, runs_root=tmp_path)

    assert manifest.state == ManifestState.PASSED
    out_dir = Path(manifest.output_directory)
    assert out_dir.parent == tmp_path
    assert (out_dir / "input.json").exists()
    assert (out_dir / "independent.json").exists()
    assert (out_dir / "result.json").exists()
    assert (out_dir / "validation.json").exists()
    assert (out_dir / "canonical.md").exists()
    assert (out_dir / "manifest.json").exists()

    # primary_output content must never appear in the persisted independent artifact
    independent_json = json.loads((out_dir / "independent.json").read_text())
    assert run_input.primary_output.content not in independent_json["independent_output"]


def test_full_run_fails_validation_on_malformed_stage2_json(tmp_path):
    run_input = _load_run_input()
    stage1 = MockProvider(responder=lambda system, user: "A complete independent plan with pricing and KPIs.")
    stage2 = MockProvider(responder=lambda system, user: "not json at all")

    run_id, manifest = run(run_input, stage1, stage2, runs_root=tmp_path)

    assert manifest.state == ManifestState.FAILED_VALIDATION
    assert manifest.error is not None


def test_full_run_marks_runtime_failure_on_exhausted_retries(tmp_path):
    from crossref.providers.base import RetryPolicy

    def blow_up(system, user):
        raise RuntimeError("simulated provider outage")

    run_input = _load_run_input()
    stage1 = MockProvider(responder=blow_up, retry_policy=RetryPolicy(max_retries=0, base_delay_seconds=0))
    stage2 = MockProvider(responder=lambda system, user: json.dumps(_valid_stage2_payload()))

    run_id, manifest = run(run_input, stage1, stage2, runs_root=tmp_path)

    assert manifest.state == ManifestState.FAILED_RUNTIME
    assert "simulated provider outage" in manifest.error
