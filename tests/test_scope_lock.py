import json
from pathlib import Path

from crossref.schemas import (
    CrossReferenceResult,
    IndependentArtifact,
    RunInput,
)
from crossref.validation import validate_run

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


def _base_result(canonical_output: str) -> CrossReferenceResult:
    return CrossReferenceResult.model_validate(
        {
            "executive_verdict": "verdict",
            "scorecard_primary": _dim_scores(3),
            "scorecard_independent": _dim_scores(3),
            "strengths": {"primary": [], "independent": []},
            "findings": [],
            "synthesis_decisions": [
                {
                    "topic": "topic",
                    "primary": "Present",
                    "independent": "Present",
                    "decision": "MERGE",
                    "reason": "reason",
                }
            ],
            "canonical_output": canonical_output,
            "scorecard_canonical": _dim_scores(4),
            "residual_uncertainties": [],
        }
    )


def test_on_topic_canonical_output_passes_scope_check():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="A genuinely different consulting launch plan with pricing and KPIs, distinct from the primary output entirely.",
        provider="mock",
        model="mock-model",
    )
    result = _base_result(
        "Automation consulting launch plan: target customer, pricing at $3k/mo, "
        "outbound acquisition, delivery pilots, KPIs and risks tracked weekly."
    )
    report = validate_run(run_input, independent, result)
    codes = [i.code for i in report.issues]
    assert "POSSIBLE_SCOPE_DRIFT" not in codes
    assert not report.has_failures


def test_off_topic_canonical_output_flags_scope_drift():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="A genuinely different consulting launch plan with pricing and KPIs, distinct from the primary output entirely.",
        provider="mock",
        model="mock-model",
    )
    result = _base_result("A recipe for banana bread with step by step baking instructions.")
    report = validate_run(run_input, independent, result)
    codes = [i.code for i in report.issues]
    assert "POSSIBLE_SCOPE_DRIFT" in codes


def test_anchoring_suspected_when_independent_matches_primary():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output=run_input.primary_output.content,  # identical -> suspected leak
        provider="mock",
        model="mock-model",
    )
    result = _base_result("Automation consulting launch plan covering pricing and KPIs.")
    report = validate_run(run_input, independent, result)
    assert report.has_failures
    codes = [i.code for i in report.issues]
    assert "ANCHORING_SUSPECTED" in codes


def test_independent_too_short_fails():
    run_input = _load_run_input()
    independent = IndependentArtifact(independent_output="Too short.", provider="mock", model="mock-model")
    result = _base_result("Automation consulting launch plan covering pricing and KPIs.")
    report = validate_run(run_input, independent, result)
    assert report.has_failures
    codes = [i.code for i in report.issues]
    assert "INDEPENDENT_TOO_SHORT" in codes
