# Cross Reference Agent — Architecture (v1.1)

## Purpose

Automates a manual workflow: take a task and a first output (Platform 1),
generate an independent second opinion (Platform 2) with zero visibility
into the first, then compare both against the original objective and
source material to produce one canonical result that is deliberately
reconstructed, not concatenated.

## The three passes, two calls

1. **Independent Creator** (Stage 1 call) — produces Independent Output B
   from the original task, source context, and locked decisions only.
2. **Comparative Auditor** + **Canonical Synthesizer** (Stage 2 call,
   single response) — receives everything from Stage 1 plus the locked
   Independent Output B and Primary Output A, and returns a structured
   audit (scorecards, findings, synthesis decisions) plus Canonical
   Output C in one JSON payload.

There are exactly two LLM calls per run. Pass 2 and Pass 3 are conceptually
distinct responsibilities but are produced by the same Stage 2 call — this
matches the "two separate LLM calls" constraint in the project spec while
keeping audit and synthesis reasoning grounded in the same context.

## The information barrier

The barrier is structural, not just an instruction:

- `crossref.schemas.Stage1Context` has no field that can hold
  `primary_output`. It is a different Pydantic model from `RunInput`.
- `crossref.independent_pass.build_stage1_context()` is the only sanctioned
  way to derive Stage 1 input, and it only ever reads
  `original_task`, `source_context`, and `locked_decisions` off the
  `RunInput`.
- `run_independent_pass()` accepts a `Stage1Context`, not a `RunInput` —
  there is no code path by which `primary_output` can reach the Stage 1
  prompt or the Stage 1 provider call.
- A runtime assertion in `run_independent_pass()` additionally checks the
  rendered prompt for a `PRIMARY OUTPUT` marker as a defense-in-depth
  guard against a careless template edit.
- `validation.py` checks the *symptom* a leak would produce (near-total
  text overlap between Independent Output B and Primary Output A) as a
  post-hoc guardrail, since a structural bypass could still exist in code
  not covered here.

## Data flow

```
RunInput (input.json)
   │
   ├─ build_stage1_context() ──> Stage1Context ──> Stage 1 LLM call
   │                                                     │
   │                                                     ▼
   │                                     IndependentArtifact (independent.json, LOCKED)
   │
   └────────────────────────────────────────────────────┤
                                                          ▼
                                    Stage 2 LLM call (RunInput + locked B)
                                                          │
                                                          ▼
                              CrossReferenceResult (result.json, canonical.md)
                                                          │
                                                          ▼
                                          validate_run() (validation.json)
                                                          │
                                                          ▼
                                            RunManifest (manifest.json)
```

## Modules

| Module | Responsibility |
| --- | --- |
| `schemas.py` | Pydantic contracts: `RunInput`, `Stage1Context`, `IndependentArtifact`, `CrossReferenceResult`, `RunManifest`. |
| `providers/` | `Provider` ABC + `AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`, `MockProvider`, with shared retry/backoff. |
| `prompts/` | `system.md` (guardrails, authority hierarchy), `independent.md` (Stage 1 template), `audit.md` (Stage 2 template, strict JSON contract). |
| `independent_pass.py` | Stage 1: builds `Stage1Context`, renders prompt, calls provider, returns a `LOCKED` `IndependentArtifact`. |
| `audit_pass.py` | Stage 2: renders the full comparison prompt, calls provider, parses/validates the JSON response into `CrossReferenceResult`. |
| `validation.py` | Post-hoc guardrail checks (anchoring symptom, scope drift, concatenation, missing traceability). |
| `orchestrator.py` | Runs Stage 1 → Stage 2 → validation, persists artifacts, drives the `RunManifest` state machine. |
| `storage.py` | `RUN_ID` generation (`CR-YYYYMMDD-XXX`), run-directory layout, JSON/text IO. |
| `runner.py` | CLI (`python -m crossref.runner run --input ...`). |

## Run manifest states

- `RUNNING` — written immediately, before Stage 1 starts.
- `PASSED` — both stages succeeded, schema-valid, no `FAIL`-severity
  validation issue.
- `FAILED_VALIDATION` — Stage 2 response failed schema validation, or a
  post-hoc guardrail check failed (e.g. anchoring suspected).
- `FAILED_RUNTIME` — a provider call exhausted its retry budget.

## Rubric and severity

See `schemas.py:RUBRIC_DIMENSIONS` for the 12 scoring dimensions (0-5
each, 60 max) and `Severity`/`FindingAction`/`SynthesisDecisionType` for
the finding and synthesis vocabularies. These mirror Sections 10-13 of the
project handoff exactly — do not rename or reorder them without updating
`prompts/audit.md` in lockstep, since the JSON contract the LLM is asked
to produce depends on the exact key names.

## What this version deliberately does not do

Per the handoff's Section 23/31: no autonomous web retrieval, no
recursive multi-agent loops, no approval UI, no dashboard, no
self-modifying prompts. One independent pass, one audit/synthesis pass,
one canonical result, per run — enforced by `orchestrator.run()` making
exactly one call to each of `run_independent_pass` and `run_audit_pass`.
