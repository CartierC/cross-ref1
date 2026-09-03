# Real-World Validation Test 001

**Task domain:** Operational/execution plan (mobile game wealth-challenge strategy) --
matches the "operational plan" candidate type from the handoff (Section 27, Step 1).

**Provider note:** No LLM API keys are configured in this execution environment, so
Stage 1 and Stage 2 were not run through `crossref.runner` against a live provider
API. Instead:

- **Stage 1** ran in a genuinely isolated context: a fresh subagent (Claude Code's
  `Agent` tool) with zero conversation history and zero exposure to Primary Output A,
  given only the objective, source material, and locked decisions extracted from the
  user's message. This is arguably a *stronger* information barrier than an in-process
  API call would have provided, since it is a structurally separate process, not just a
  separate prompt within the same session.
- **Stage 2** (audit + synthesis) was authored directly by the orchestrating Claude
  session, which is architecturally correct -- Stage 2 is the point where Primary Output
  A is allowed to enter context.
- The resulting artifacts were then run through the actual production code
  (`crossref.schemas`, `crossref.storage`, `crossref.validation`) via
  `/tmp/.../scratchpad/build_test001.py` -- exercising real schema validation and
  the real guardrail checks, not a reimplementation. Result: `PASSED`, zero
  validation issues.

## Scores

| | Objective Alignment | Completeness | Accuracy | Reasoning | Precision | Structure | Relevance | Efficiency | Risk Coverage | Opportunity Capture | Executability | Constraint Compliance | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Primary (A) | 5 | 4 | 3 | 4 | 4 | 5 | 5 | 4 | 3 | 3 | 5 | 5 | **50** (Strong) |
| Independent (B) | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 5 | **56** (Exceptional) |
| Canonical (C) | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | **58** (Exceptional) |

## Pass criteria check (Section 28)

- **Independence Integrity** -- PASS. B was generated in a subagent with no
  conversation history and a prompt that never referenced A's existence.
- **Independent Utility** -- PASS. B is a complete, usable standalone plan.
- **Useful Divergence** -- PASS. B independently surfaced the Large Factory gap,
  the offline-income test, ad-boost usage, and the 10th-slot decision tree -- none
  present in A.
- **Defect Detection** -- PASS. Real gaps identified in both directions (A missing
  offline-income/ad-boost/Large-Factory-audit; B missing taxes/crypto guidance).
- **Positive Recognition** -- PASS. Findings and strengths lists credit both A and B
  where each was stronger, not just criticize.
- **Low Artificial Criticism** -- PASS on inspection. No fabricated defects; every
  finding traces to a specific, checkable gap or a genuine cross-source contradiction.
- **Scope Discipline** -- PASS. Canonical output stays inside the original objective;
  no unrelated scope introduced.
- **Synthesis Quality** -- pending human judgment (see below). Canonical C scores
  higher than either input under the rubric and is not a concatenation of A and B.
- **Efficiency** -- pending human judgment.

## What still needs a human (Section 27, Step 10 / Section 29)

This run cannot self-certify "worth it." The following need the user's actual
judgment, since the rubric score is a structuring aid, not proof:

1. Was Independent Output B genuinely useful, or just plausible-sounding?
2. Did the audit catch real defects in A, or invent ones?
3. Did Canonical C actually feel better than A alone?
4. Did C become unnecessarily longer for the value added?
5. Was the extra generation worth the cost?

See `canonical.md` for the deliverable, `result.json` for the full structured audit,
`independent.json` for locked Output B, and `input.json` for the exact task package used.
