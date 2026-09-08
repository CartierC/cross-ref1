# Cross Reference Agent

Independent Creator + Comparative Auditor + Canonical Synthesizer.

Given a task, source material, locked decisions, and an existing "Primary
Output" (from any Platform 1), this agent:

1. Generates its own complete, independent answer with **zero visibility**
   into the Primary Output (Stage 1).
2. Locks that answer, then reveals the Primary Output and cross-references
   both against the original objective and source material — scoring
   each on a 12-dimension rubric, surfacing strengths, omissions, errors,
   and fluff (Stage 2).
3. Reconstructs a single Canonical Output that is deliberately better than
   either input alone — not a concatenation, not a compromise.

See `ARCHITECTURE.md` for how the information barrier between Stage 1 and
Stage 2 is enforced structurally, `DEPLOYMENT.md` for setup, and
`docs/DAILY_USE.md` for the day-to-day COPY → FILL → RUN workflow.

## Quick start

```bash
pip install -e ".[dev,anthropic]"
cp .env.example .env   # fill in ANTHROPIC_API_KEY
pytest -q
python -m crossref.runner run --input tests/fixtures/sample_run.json --provider anthropic
```

## Status

v1.1 — deployable runner with multi-provider routing (Anthropic, OpenAI,
Gemini), retry/backoff, schema-validated Stage 2 output, run manifests,
and a regression suite. Currently entering real-world validation (see
`runs/` for executed run artifacts).
