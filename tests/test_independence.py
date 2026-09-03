import json
from pathlib import Path

from crossref.independent_pass import (
    build_stage1_context,
    render_independent_prompt,
    run_independent_pass,
)
from crossref.providers.mock_provider import MockProvider
from crossref.schemas import RunInput, Stage1Context

FIXTURE = Path(__file__).parent / "fixtures" / "sample_run.json"


def _load_run_input() -> RunInput:
    return RunInput.model_validate(json.loads(FIXTURE.read_text()))


def test_stage1_context_has_no_primary_output_field():
    assert "primary_output" not in Stage1Context.model_fields


def test_build_stage1_context_drops_primary_output():
    run_input = _load_run_input()
    ctx = build_stage1_context(run_input)
    dumped = ctx.model_dump()
    assert "primary_output" not in dumped


def test_rendered_prompt_never_contains_primary_output_content():
    run_input = _load_run_input()
    ctx = build_stage1_context(run_input)
    prompt = render_independent_prompt(ctx)
    assert run_input.primary_output.content not in prompt
    assert "PRIMARY OUTPUT" not in prompt


def test_provider_never_receives_primary_output_text():
    run_input = _load_run_input()
    ctx = build_stage1_context(run_input)

    captured = {}

    def responder(system, user):
        captured["system"] = system
        captured["user"] = user
        return "A complete independent 30-day plan with target customer, pricing, and KPIs."

    provider = MockProvider(responder=responder)
    artifact = run_independent_pass(ctx, provider)

    assert run_input.primary_output.content not in captured["user"]
    assert run_input.primary_output.content not in captured["system"]
    assert artifact.status.value == "LOCKED"
    assert artifact.independent_output.strip() != ""


def test_independent_output_is_distinct_from_primary():
    run_input = _load_run_input()
    ctx = build_stage1_context(run_input)
    provider = MockProvider(
        responder=lambda system, user: "Target customer: seed-stage SaaS founders. Pricing: $3k/mo retainer."
    )
    artifact = run_independent_pass(ctx, provider)
    assert artifact.independent_output != run_input.primary_output.content
