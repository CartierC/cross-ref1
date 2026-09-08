# Daily Use

Three steps, every time: **COPY → FILL → RUN**.

## 1. Copy

```bash
cp templates/input_template.json runs_input/2026-09-08-faa107-study-guide.json
```

## 2. Fill

Open the copy and fill in `original_task`, `source_context`,
`locked_decisions`, and `primary_output` (see `tests/fixtures/sample_run.json`
for a fully worked example). Leave `topic` as `null` unless you want to
override the name the system derives from the filename.

```bash
open runs_input/2026-09-08-faa107-study-guide.json
```

## 3. Run

```bash
crossref run --input runs_input/2026-09-08-faa107-study-guide.json --provider anthropic
```

(`python -m crossref.runner run --input ...` works identically if the
`crossref` console script isn't on your PATH.)

## What happens automatically

Every execution gets its own history folder under `runs/`, named
`<timestamp>_<topic>__<run_id>` (e.g.
`runs/2026-09-08_1135_faa107-study-guide__CR-20260908-001/`), containing a
snapshot of the exact input plus every artifact that run produced
(`independent.json`, `result.json`, `validation.json`, `canonical.md`,
`manifest.json`). Nothing you run today can overwrite a run from
yesterday, or from five minutes ago.

- **On PASSED**: `latest/canonical.md` is updated to this run's canonical
  result, and the run's own `canonical.md` opens automatically. The
  terminal prints the run folder and canonical path so you always know
  exactly which run you're looking at.
- **On FAILED** (schema, guardrail, or provider failure): nothing opens,
  `latest/canonical.md` is left untouched, and the command exits non-zero.
  The run's folder still exists (for auditing what went wrong), but it is
  never treated as your newest result.

`latest/canonical.md` therefore always means "the newest result that
actually passed" — never a stale or failed run wearing that name.

## Reference

- `runs/` — every run's full history, one folder per execution.
- `latest/canonical.md` — pointer/copy of the newest PASSED run's canonical
  output.
- `runs_input/` — your filled-in input files, staged before a run.
- `templates/input_template.json` — the blank shape to copy in step 1.

See `ARCHITECTURE.md` for how the agent itself works (the two-pass,
information-barrier design) and `DEPLOYMENT.md` for install/setup.
