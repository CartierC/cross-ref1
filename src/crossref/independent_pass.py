"""Stage 1 — Independent Creator.

The information barrier lives here structurally, not just as a prompt
instruction: `run_independent_pass` accepts a `Stage1Context`, a type that
has no field capable of carrying `primary_output`. There is no code path in
this module that can read `RunInput.primary_output` — it is never passed
in, so it cannot leak by accident.
"""

from __future__ import annotations

from importlib import resources

from .providers.base import Provider
from .schemas import IndependentArtifact, RunInput, Stage1Context


def _load_prompt(name: str) -> str:
    return resources.files("crossref.prompts").joinpath(name).read_text(encoding="utf-8")


def _load_system_prompt() -> str:
    return _load_prompt("system.md")


def build_stage1_context(run_input: RunInput) -> Stage1Context:
    """The only sanctioned way to derive Stage 1 input from a RunInput.

    Constructing a Stage1Context explicitly drops primary_output — it has
    no such field to assign into.
    """
    return Stage1Context(
        original_task=run_input.original_task,
        source_context=run_input.source_context,
        locked_decisions=run_input.locked_decisions,
    )


def render_independent_prompt(ctx: Stage1Context) -> str:
    template = _load_prompt("independent.md")
    task = ctx.original_task
    src = ctx.source_context
    return template.format(
        objective=task.objective,
        expected_result=task.expected_result or "(not specified)",
        constraints="\n".join(f"- {c}" for c in task.constraints) or "(none)",
        requested_format=task.requested_format or "(not specified)",
        source_material="\n".join(f"- {m}" for m in src.source_material) or "(none provided)",
        facts="\n".join(f"- {f}" for f in src.facts) or "(none provided)",
        references="\n".join(f"- {r}" for r in src.references) or "(none provided)",
        attachments="\n".join(f"- {a}" for a in src.attachments) or "(none)",
        locked_decisions="\n".join(f"- {d}" for d in ctx.locked_decisions) or "(none)",
    )


def run_independent_pass(ctx: Stage1Context, provider: Provider) -> IndependentArtifact:
    system = _load_system_prompt()
    user = render_independent_prompt(ctx)

    # Hard assertion: the rendered prompt must never contain a
    # primary_output marker. This cannot fire in practice since Stage1Context
    # has no such field, but it documents and guards the invariant in case
    # the template is ever edited carelessly.
    assert "PRIMARY OUTPUT" not in user, "Information barrier violated: primary output leaked into Stage 1 prompt"

    text = provider.complete(system=system, user=user)
    return IndependentArtifact(
        independent_output=text,
        provider=provider.name,
        model=provider.model,
    )
