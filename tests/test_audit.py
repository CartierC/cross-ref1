import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from crossref.audit_pass import render_audit_prompt, run_audit_pass
from crossref.providers.mock_provider import MockProvider
from crossref.schemas import IndependentArtifact, RunInput

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
        "executive_verdict": "B independently surfaced pricing and KPIs that A omitted; C merges A's tone with B's structure.",
        "scorecard_primary": _dim_scores(2),
        "scorecard_independent": _dim_scores(4),
        "strengths": {"primary": ["Clear weekly cadence"], "independent": ["Defines target customer and pricing"]},
        "findings": [
            {
                "finding": "No pricing structure defined",
                "category": "Completeness",
                "severity": "S2",
                "action": "ADD",
                "source": "primary",
            },
            {
                "finding": "Branding prioritized over revenue in week 1-2",
                "category": "Relevance",
                "severity": "S3",
                "action": "FIX",
                "source": "primary",
            },
        ],
        "synthesis_decisions": [
            {
                "topic": "Pricing structure",
                "primary": "Absent",
                "independent": "Present",
                "decision": "KEEP_B",
                "reason": "Only B defines a concrete price point.",
            }
        ],
        "canonical_output": "Week 1: define target customer and $3k/mo retainer offer. Week 2: outbound to 50 warm contacts. Week 3: deliver pilot automation. Week 4: convert to retainer, track KPIs (calls booked, pilots closed, MRR).",
        "scorecard_canonical": _dim_scores(4),
        "residual_uncertainties": ["Actual close rate for outbound is unverified."],
    }


def test_render_audit_prompt_includes_both_outputs():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="Independent plan text.", provider="mock", model="mock-model"
    )
    prompt = render_audit_prompt(run_input, independent)
    assert run_input.primary_output.content in prompt
    assert independent.independent_output in prompt


def test_run_audit_pass_parses_valid_json():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="Independent plan text.", provider="mock", model="mock-model"
    )
    payload = _valid_stage2_payload()
    provider = MockProvider(responder=lambda system, user: json.dumps(payload))

    result = run_audit_pass(run_input, independent, provider)

    assert result.scorecard_primary.total == 24
    assert result.scorecard_independent.total == 48
    assert result.scorecard_canonical.total == 48
    assert len(result.findings) == 2
    assert result.findings[1].severity.value == "S3"
    assert "3k" in result.canonical_output


def test_run_audit_pass_handles_markdown_fenced_json():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="Independent plan text.", provider="mock", model="mock-model"
    )
    payload = _valid_stage2_payload()
    fenced = f"```json\n{json.dumps(payload)}\n```"
    provider = MockProvider(responder=lambda system, user: fenced)

    result = run_audit_pass(run_input, independent, provider)
    assert result.canonical_output == payload["canonical_output"]


def test_run_audit_pass_rejects_malformed_schema():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="Independent plan text.", provider="mock", model="mock-model"
    )
    bad_payload = _valid_stage2_payload()
    del bad_payload["canonical_output"]
    provider = MockProvider(responder=lambda system, user: json.dumps(bad_payload))

    with pytest.raises(ValidationError):
        run_audit_pass(run_input, independent, provider)


def test_dimension_score_out_of_range_rejected():
    run_input = _load_run_input()
    independent = IndependentArtifact(
        independent_output="Independent plan text.", provider="mock", model="mock-model"
    )
    payload = _valid_stage2_payload()
    payload["scorecard_primary"]["accuracy"] = 9  # out of 0-5 range
    provider = MockProvider(responder=lambda system, user: json.dumps(payload))

    with pytest.raises(ValidationError):
        run_audit_pass(run_input, independent, provider)
