"""Stage 2 — Cross-Reference Auditor + Canonical Synthesizer.

Runs only after Stage 1's IndependentArtifact is LOCKED. This is the first
and only point in the pipeline where Primary Output A enters an LLM
context, alongside the full task package and the locked Independent Output
B.
"""

from __future__ import annotations

import json
import re
from importlib import resources

from .providers.base import Provider
from .schemas import CrossReferenceResult, IndependentArtifact, RunInput

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _load_prompt(name: str) -> str:
    return resources.files("crossref.prompts").joinpath(name).read_text(encoding="utf-8")


def render_audit_prompt(run_input: RunInput, independent: IndependentArtifact) -> str:
    template = _load_prompt("audit.md")
    task = run_input.original_task
    src = run_input.source_context
    primary = run_input.primary_output
    return template.format(
        objective=task.objective,
        expected_result=task.expected_result or "(not specified)",
        constraints="\n".join(f"- {c}" for c in task.constraints) or "(none)",
        requested_format=task.requested_format or "(not specified)",
        source_material="\n".join(f"- {m}" for m in src.source_material) or "(none provided)",
        facts="\n".join(f"- {f}" for f in src.facts) or "(none provided)",
        references="\n".join(f"- {r}" for r in src.references) or "(none provided)",
        attachments="\n".join(f"- {a}" for a in src.attachments) or "(none)",
        locked_decisions="\n".join(f"- {d}" for d in run_input.locked_decisions) or "(none)",
        primary_platform=primary.platform,
        primary_model=primary.model or "(unspecified)",
        primary_output=primary.content,
        independent_output=independent.independent_output,
    )


def _extract_json(raw: str) -> dict:
    cleaned = _JSON_FENCE_RE.sub("", raw.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in Stage 2 response")
    return json.loads(cleaned[start : end + 1])


def run_audit_pass(
    run_input: RunInput, independent: IndependentArtifact, provider: Provider
) -> CrossReferenceResult:
    system = _load_prompt("system.md")
    user = render_audit_prompt(run_input, independent)
    raw = provider.complete(system=system, user=user)
    payload = _extract_json(raw)
    return CrossReferenceResult.model_validate(payload)
