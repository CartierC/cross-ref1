"""Guardrail checks run after Stage 2 completes (Section 15, G1-G10).

These are heuristics, not proofs. They exist to catch the cheap, common
failure modes described in the handoff (Section 30): anchoring, schema
violations, scope drift, and A/B concatenation — before a run is marked
PASSED.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import CrossReferenceResult, IndependentArtifact, RunInput

_MIN_INDEPENDENT_CHARS = 40
_SIMILARITY_FLOOR = 0.98  # near-identical text to primary output is a red flag


@dataclass
class ValidationIssue:
    code: str
    severity: str  # "FAIL" or "WARN"
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(i.severity == "FAIL" for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "passed": not self.has_failures,
            "issues": [
                {"code": i.code, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
        }


def _char_overlap_ratio(a: str, b: str) -> float:
    """Cheap similarity proxy: longest common substring length / shorter length.
    Not a real diff algorithm — good enough to flag near-verbatim copies."""
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if shorter in longer:
        return 1.0
    # crude n-gram overlap fallback
    n = 20
    grams_short = {shorter[i : i + n] for i in range(max(0, len(shorter) - n + 1))}
    if not grams_short:
        return 0.0
    grams_long = {longer[i : i + n] for i in range(max(0, len(longer) - n + 1))}
    return len(grams_short & grams_long) / len(grams_short)


def validate_run(
    run_input: RunInput,
    independent: IndependentArtifact,
    result: CrossReferenceResult,
) -> ValidationReport:
    report = ValidationReport()

    # G1 / anchoring symptom: independent output should not be a near-copy
    # of primary output. This cannot detect an actual context leak (that is
    # prevented structurally in independent_pass.py), but it catches the
    # symptom a leak would produce.
    overlap = _char_overlap_ratio(independent.independent_output, run_input.primary_output.content)
    if overlap >= _SIMILARITY_FLOOR:
        report.issues.append(
            ValidationIssue(
                code="ANCHORING_SUSPECTED",
                severity="FAIL",
                message=(
                    f"Independent output is {overlap:.0%} overlapping with primary output; "
                    "suspected anchoring or accidental context leak."
                ),
            )
        )

    if len(independent.independent_output.strip()) < _MIN_INDEPENDENT_CHARS:
        report.issues.append(
            ValidationIssue(
                code="INDEPENDENT_TOO_SHORT",
                severity="FAIL",
                message="Independent output is implausibly short to be a complete standalone answer.",
            )
        )

    if independent.status.value != "LOCKED":
        report.issues.append(
            ValidationIssue(
                code="INDEPENDENT_NOT_LOCKED",
                severity="FAIL",
                message="Independent artifact was not locked before Stage 2 ran.",
            )
        )

    # Canonical should not just be A or B concatenated verbatim.
    concat_overlap_a = _char_overlap_ratio(result.canonical_output, run_input.primary_output.content)
    concat_overlap_b = _char_overlap_ratio(result.canonical_output, independent.independent_output)
    if concat_overlap_a >= _SIMILARITY_FLOOR and concat_overlap_b >= _SIMILARITY_FLOOR:
        report.issues.append(
            ValidationIssue(
                code="CANONICAL_LOOKS_LIKE_CONCATENATION",
                severity="WARN",
                message="Canonical output appears to fully contain both A and B verbatim.",
            )
        )

    if not result.synthesis_decisions:
        report.issues.append(
            ValidationIssue(
                code="NO_SYNTHESIS_DECISIONS",
                severity="WARN",
                message="No synthesis decisions were recorded; traceability (Section 13) is reduced.",
            )
        )

    # Scope lock (G5): canonical output should reference the stated objective.
    objective_terms = [w.lower() for w in run_input.original_task.objective.split() if len(w) > 4]
    if objective_terms:
        hits = sum(1 for w in objective_terms if w in result.canonical_output.lower())
        if hits == 0:
            report.issues.append(
                ValidationIssue(
                    code="POSSIBLE_SCOPE_DRIFT",
                    severity="WARN",
                    message="Canonical output shares no significant terms with the stated objective.",
                )
            )

    return report
