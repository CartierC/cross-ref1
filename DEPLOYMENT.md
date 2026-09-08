# Deployment / Local Setup

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,anthropic,openai,gemini]"
```

Or minimally, without provider SDKs (tests use `MockProvider`, no network):

```bash
pip install -e ".[dev]"
```

## Configure

```bash
cp .env.example .env
# fill in whichever of ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY you need
```

`runner.py` loads `.env` automatically via `python-dotenv`.

## Run the test suite

```bash
pytest -q
```

All tests run against `MockProvider` — no API keys or network access
required. Expect the independence, audit-schema, scope-lock/guardrail, and
end-to-end orchestrator suites to pass (17 tests as of this writing).

## Execute a real run

For the day-to-day COPY → FILL → RUN workflow, see `docs/DAILY_USE.md`.
The mechanics:

1. Write a `RunInput` JSON file (see `templates/input_template.json` for the
   blank shape, or `tests/fixtures/sample_run.json` for a filled example:
   `original_task`, `source_context`, `locked_decisions`, `primary_output`,
   plus an optional `topic` used to name the run directory).
2. Run:

```bash
python -m crossref.runner run \
  --input path/to/run_input.json \
  --provider anthropic \
  --model claude-sonnet-5
```

Use `--stage1-provider`/`--stage1-model` and
`--stage2-provider`/`--stage2-model` to mix providers across stages (e.g.
Claude for Stage 1, GPT for Stage 2) instead of `--provider`/`--model` for
both. Pass `--no-open` to skip auto-opening the canonical result on a
PASSED run (useful in CI/headless environments).

3. Inspect `runs/<timestamp>_<topic>__<run_id>/` (a fresh, uniquely named
   directory every run — see `docs/DAILY_USE.md` for the naming scheme):
   - `input.json` — a snapshot of the exact `RunInput` that was run.
   - `independent.json` — Independent Output B, locked.
   - `result.json` — full Stage 2 structured output (scorecards, findings,
     synthesis decisions, canonical output, residual uncertainties).
   - `canonical.md` — Canonical Output C alone, for quick reading.
   - `validation.json` — guardrail check results.
   - `manifest.json` — run state (`RUNNING` / `PASSED` /
     `FAILED_VALIDATION` / `FAILED_RUNTIME`), provider/model metadata, and
     traceability fields (`topic`, `source_input`, `output_directory`,
     `canonical_path`).

On a `PASSED` run, `latest/canonical.md` is refreshed to that run's
canonical output and the run's own `canonical.md` is opened automatically.
A failed run leaves `latest/canonical.md` untouched and opens nothing.
Exit code is `0` on `PASSED`, `1` otherwise.

## Adding a provider

Implement `Provider._complete_once(self, system: str, user: str) -> str`
in `providers/<name>_provider.py` (see `anthropic_provider.py` for the
pattern: lazy SDK import, API key from env, single non-retried call —
retry/backoff is handled by the base class). Register it in
`providers/__init__.py`'s `_REGISTRY`.
