# Daily Use Setup

A local CLI convenience layer on top of `crossref.runner`. Reduces the loop
from "build JSON, remember the Python command, locate output, manually open
`canonical.md`" to "copy template, fill 4 fields, `crossref file.json`,
`canonical.md` opens."

Not a deployment architecture — a working-session interface for the current
real-world validation phase.

## Directory layout

```text
cross-ref1/
├── templates/
│   └── input_template.json      # reusable, tracked in git
│
├── runs_input/                  # your day-to-day filled-in inputs
│   ├── today.json               # gitignored (runs_input/*.json)
│   └── ...
│
└── runs/
    └── <RUN_ID>/                # written by the runner, one per run
        ├── input.json
        ├── independent.json
        ├── result.json
        ├── canonical.md
        ├── validation.json
        └── manifest.json
```

`templates/` and `runs_input/` are separate on purpose: the template is a
tracked, reusable skeleton; `runs_input/*.json` are per-day working files
that don't need to be committed (see `.gitignore`).

## One-time setup

```bash
mkdir -p templates runs_input   # runs_input is created if missing, but
                                 # do this once to be sure
```

1. `templates/input_template.json` is already in the repo — no action needed.
2. Paste the full contents of `scripts/crossref_shell_function.sh` into the
   end of `~/.zshrc` (or `~/.bashrc`).
3. `source ~/.zshrc`
4. Run one real validation test:

   ```bash
   cp templates/input_template.json runs_input/test.json
   # fill in the 4 fields in test.json
   crossref runs_input/test.json
   ```

   `canonical.md` should open automatically when the run finishes.

Confirming any ChatGPT/web GitHub connector is "Connected" in Settings is
unrelated to this — that connector lets a hosted chat UI read the repo. It
has no bearing on running `crossref.runner` locally and is not part of this
setup.

## Daily use

```bash
cp templates/input_template.json runs_input/today.json
# fill in: original_task, source_context, locked_decisions, primary_output
crossref runs_input/today.json
```

`canonical.md` opens itself once the run passes.

## What `crossref` actually guarantees

`scripts/crossref_shell_function.sh` is the only thing standing between
"convenient" and "reliable." It:

- Requires an input path; errors if missing or the file doesn't exist.
- Resolves the repo root via `git rev-parse --show-toplevel` from the input
  file's location, rather than assuming the current directory.
- Activates `.venv/bin/activate` if present, otherwise runs whatever
  `python` resolves to on `PATH`.
- Captures the runner's own `run_id=... state=...` line from *this*
  invocation's stdout — it never scans `runs/` for "the latest" directory,
  so a failed run can never cause an older, unrelated successful result to
  open instead.
- Opens `runs/<RUN_ID>/canonical.md` **only** when the runner's exit code is
  `0` (manifest state `PASSED`). If the run fails — including the case
  where Stage 2 synthesis succeeded and `canonical.md` was written, but a
  later guardrail check in `validation.json` failed — it prints the state
  and points at `manifest.json`/`validation.json` instead of opening
  anything.

## Deliberately not automated yet

The four input fields (`original_task`, `source_context`, `locked_decisions`,
`primary_output`) are filled in by hand, on purpose. Manually deciding what
the task, context, locked decisions, and primary output actually are is part
of validating the agent architecture during this phase. Auto-capturing them
is a reasonable later step, not a now step.
