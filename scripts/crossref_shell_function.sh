# crossref — run the Cross Reference Agent on an input file and open the
# resulting canonical.md automatically.
#
# Install: paste this whole block into the end of ~/.zshrc (or ~/.bashrc),
# then `source ~/.zshrc`.
#
# Usage:
#   cp templates/input_template.json runs_input/today.json
#   # fill in: original_task, source_context, locked_decisions, primary_output
#   crossref runs_input/today.json

crossref() {
  local input_file="$1"
  if [[ -z "$input_file" ]]; then
    echo "Usage: crossref <path/to/input.json>" >&2
    return 1
  fi
  if [[ ! -f "$input_file" ]]; then
    echo "crossref: input file not found: $input_file" >&2
    return 1
  fi

  local input_dir repo_root
  input_dir="$(cd "$(dirname "$input_file")" && pwd)"
  repo_root="$(git -C "$input_dir" rev-parse --show-toplevel 2>/dev/null)"
  if [[ -z "$repo_root" ]]; then
    echo "crossref: could not locate the cross-ref1 repo root from $input_file" >&2
    return 1
  fi

  (
    cd "$repo_root" || exit 1
    if [[ -f ".venv/bin/activate" ]]; then
      source ".venv/bin/activate"
    fi

    local run_output
    run_output="$(python -m crossref.runner run --input "$input_file" --provider anthropic --model claude-sonnet-5)"
    local status=$?
    echo "$run_output"

    local run_id
    run_id="$(printf '%s\n' "$run_output" | sed -n 's/^run_id=\([^ ]*\) .*/\1/p')"

    if [[ -z "$run_id" ]]; then
      echo "crossref: run failed before a run_id was assigned; see output above." >&2
      exit "$status"
    fi

    local canonical="$repo_root/runs/$run_id/canonical.md"
    if [[ ! -f "$canonical" ]]; then
      echo "crossref: run_id=$run_id but canonical.md not found at $canonical" >&2
      exit "$status"
    fi

    if command -v open >/dev/null 2>&1; then
      open "$canonical"
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$canonical"
    else
      echo "crossref: could not auto-open $canonical (no 'open' or 'xdg-open' found); path printed above." >&2
    fi

    exit "$status"
  )
}
