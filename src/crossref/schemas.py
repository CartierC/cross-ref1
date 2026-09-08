"""Pydantic data contracts for the Cross Reference Agent.

These types are the single source of truth for run inputs, the locked
independent artifact, the audit/synthesis result, and the run manifest.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "objective_alignment",
    "completeness",
    "accuracy",
    "reasoning",
    "precision",
    "structure",
    "relevance",
    "efficiency",
    "risk_coverage",
    "opportunity_capture",
    "executability",
    "constraint_compliance",
)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Input architecture (Section 8)
# ---------------------------------------------------------------------------


class OriginalTask(BaseModel):
    objective: str
    expected_result: str = ""
    constraints: list[str] = Field(default_factory=list)
    requested_format: Optional[str] = None


class SourceContext(BaseModel):
    source_material: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)


class PrimaryOutput(BaseModel):
    platform: str
    model: Optional[str] = None
    content: str


class RunInput(BaseModel):
    """The full task package. `primary_output` MUST NOT be read by Stage 1.

    Enforcement lives in independent_pass.build_stage1_prompt(), which only
    ever receives a Stage1Context (see below) — a type that structurally
    cannot carry primary_output. This model exists to parse/validate the
    input file; nothing in Stage 1 is allowed to construct a Stage1Context
    from a RunInput field that includes primary_output.
    """

    run_id: Optional[str] = None
    topic: Optional[str] = None
    original_task: OriginalTask
    source_context: SourceContext = Field(default_factory=SourceContext)
    locked_decisions: list[str] = Field(default_factory=list)
    primary_output: PrimaryOutput


# ---------------------------------------------------------------------------
# Stage 1 — Independent Creator (Section 9)
# ---------------------------------------------------------------------------


class Stage1Context(BaseModel):
    """Exactly what Stage 1 is allowed to see. No primary_output field exists
    on this type, by construction — that is the information barrier."""

    original_task: OriginalTask
    source_context: SourceContext
    locked_decisions: list[str] = Field(default_factory=list)


class IndependentOutputStatus(str, Enum):
    LOCKED = "LOCKED"


class IndependentArtifact(BaseModel):
    independent_output: str
    generated_at: str = Field(default_factory=utcnow_iso)
    status: IndependentOutputStatus = IndependentOutputStatus.LOCKED
    provider: str
    model: Optional[str] = None


# ---------------------------------------------------------------------------
# Stage 2 — Cross-Reference Auditor + Canonical Synthesizer (Sections 10-14)
# ---------------------------------------------------------------------------


class DimensionScores(BaseModel):
    objective_alignment: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    accuracy: int = Field(ge=0, le=5)
    reasoning: int = Field(ge=0, le=5)
    precision: int = Field(ge=0, le=5)
    structure: int = Field(ge=0, le=5)
    relevance: int = Field(ge=0, le=5)
    efficiency: int = Field(ge=0, le=5)
    risk_coverage: int = Field(ge=0, le=5)
    opportunity_capture: int = Field(ge=0, le=5)
    executability: int = Field(ge=0, le=5)
    constraint_compliance: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return sum(getattr(self, dim) for dim in RUBRIC_DIMENSIONS)

    @property
    def interpretation(self) -> str:
        t = self.total
        if t >= 55:
            return "Exceptional"
        if t >= 49:
            return "Strong"
        if t >= 42:
            return "Pass with improvements"
        if t >= 32:
            return "Material revision required"
        return "Reconstruction required"


class Severity(str, Enum):
    S0 = "S0"  # Observation
    S1 = "S1"  # Enhancement
    S2 = "S2"  # Material
    S3 = "S3"  # Critical


class FindingAction(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    FIX = "FIX"
    FLAG = "FLAG"
    KEEP = "KEEP"


class FindingSource(str, Enum):
    PRIMARY = "primary"
    INDEPENDENT = "independent"
    BOTH = "both"
    NEITHER = "neither"


class Finding(BaseModel):
    finding: str
    category: str
    severity: Severity
    action: FindingAction
    source: FindingSource = FindingSource.NEITHER


class SynthesisDecisionType(str, Enum):
    KEEP_A = "KEEP_A"
    KEEP_B = "KEEP_B"
    MERGE = "MERGE"
    REWRITE = "REWRITE"
    DELETE = "DELETE"
    NEW = "NEW"
    UNRESOLVED = "UNRESOLVED"


class SynthesisDecision(BaseModel):
    topic: str
    primary: str = "Present"
    independent: str = "Present"
    decision: SynthesisDecisionType
    reason: str


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"


class Strengths(BaseModel):
    primary: list[str] = Field(default_factory=list)
    independent: list[str] = Field(default_factory=list)


class CrossReferenceResult(BaseModel):
    """Full structured output of the Stage 2 call."""

    executive_verdict: str
    scorecard_primary: DimensionScores
    scorecard_independent: DimensionScores
    strengths: Strengths
    findings: list[Finding] = Field(default_factory=list)
    synthesis_decisions: list[SynthesisDecision] = Field(default_factory=list)
    canonical_output: str
    scorecard_canonical: DimensionScores
    residual_uncertainties: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _canonical_not_empty(self) -> "CrossReferenceResult":
        if not self.canonical_output.strip():
            raise ValueError("canonical_output must not be empty")
        return self


# ---------------------------------------------------------------------------
# Run manifest (Section 19)
# ---------------------------------------------------------------------------


class ManifestState(str, Enum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_RUNTIME = "FAILED_RUNTIME"


class ManifestProviderInfo(BaseModel):
    stage1_provider: str
    stage1_model: Optional[str] = None
    stage2_provider: str
    stage2_model: Optional[str] = None


class RunManifest(BaseModel):
    run_id: str
    topic: Optional[str] = None
    source_input: Optional[str] = None
    output_directory: Optional[str] = None
    canonical_path: Optional[str] = None
    state: ManifestState = ManifestState.RUNNING
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    providers: ManifestProviderInfo
    error: Optional[str] = None
    validation_summary: Optional[dict] = None
