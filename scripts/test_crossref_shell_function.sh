#!/usr/bin/env bash
# Smoke test for crossref_shell_function.sh's control flow: PASSED,
# FAILED_VALIDATION, and relative-path execution. Stubs `python` and `open`
# so it needs no network access, API keys, or a real cross-ref1 install --
# it only exercises the shell function's own logic (parsing run_id/state,
# gating the auto-open on exit status, and path resolution).
#
# Run: bash scripts/test_crossref_shell_function.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUNCTION_FILE="$SCRIPT_DIR/crossref_shell_function.sh"

failures=0
pass() { echo "ok   - $1"; }
fail() { echo "FAIL - $1"; failures=$((failures + 1)); }

# --- Build a throwaway fake repo with a stub `python` and stub `open` ------

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

REPO="$WORK/repo"
BIN="$WORK/bin"
mkdir -p "$REPO" "$BIN" "$REPO/runs_input"
( cd "$REPO" && git init -q && git config user.email t@t.com && git config user.name t )

# Stub `python`: ignores its args, reads scenario config from env vars set
# by the test, prints the runner's real stdout shape, and writes
# canonical.md when the scenario says the run got that far.
cat > "$BIN/python" <<'EOF'
#!/usr/bin/env bash
# Mimics the real runner's behavior enough to catch path-resolution bugs:
# it actually looks for the --input file (relative to *its own* cwd, same
# as `Path(args.input).read_text()` would) and fails like argparse's
# target script would if it's missing, rather than trusting the caller.
input_path=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--input" ]]; then
    input_path="$arg"
  fi
  prev="$arg"
done

if [[ ! -f "$input_path" ]]; then
  echo "FileNotFoundError: [Errno 2] No such file or directory: '$input_path' (cwd=$(pwd))" >&2
  exit 2
fi

mkdir -p "$STUB_REPO/runs/$STUB_RUN_ID"
if [[ "$STUB_WRITE_CANONICAL" == "1" ]]; then
  echo "stub canonical output" > "$STUB_REPO/runs/$STUB_RUN_ID/canonical.md"
fi
echo "run_id=$STUB_RUN_ID state=$STUB_STATE"
exit "$STUB_EXIT"
EOF
chmod +x "$BIN/python"

# Stub `open`: records what it was called with instead of launching a GUI.
cat > "$BIN/open" <<EOF
#!/usr/bin/env bash
echo "\$1" >> "$WORK/open_calls.log"
EOF
chmod +x "$BIN/open"

export PATH="$BIN:$PATH"

# shellcheck source=/dev/null
source "$FUNCTION_FILE"

# --- Scenario 1: PASSED -> canonical.md must be opened, exit 0 ------------

echo '{}' > "$REPO/runs_input/passed.json"
rm -f "$WORK/open_calls.log"
STUB_REPO="$REPO" STUB_RUN_ID="CR-TEST-001" STUB_STATE="PASSED" STUB_EXIT=0 STUB_WRITE_CANONICAL=1 \
  crossref "$REPO/runs_input/passed.json" >/tmp/crossref_test_out 2>&1
status=$?

if [[ "$status" -eq 0 ]]; then pass "PASSED scenario exits 0"; else fail "PASSED scenario exited $status"; fi
if [[ -f "$WORK/open_calls.log" ]] && grep -q "$REPO/runs/CR-TEST-001/canonical.md" "$WORK/open_calls.log"; then
  pass "PASSED scenario opens the correct canonical.md"
else
  fail "PASSED scenario did not open canonical.md"
fi

# --- Scenario 2: FAILED_VALIDATION -> must NOT open, non-zero exit --------

echo '{}' > "$REPO/runs_input/failed.json"
rm -f "$WORK/open_calls.log"
STUB_REPO="$REPO" STUB_RUN_ID="CR-TEST-002" STUB_STATE="FAILED_VALIDATION" STUB_EXIT=1 STUB_WRITE_CANONICAL=1 \
  crossref "$REPO/runs_input/failed.json" >/tmp/crossref_test_out 2>&1
status=$?

if [[ "$status" -ne 0 ]]; then pass "FAILED_VALIDATION scenario exits non-zero"; else fail "FAILED_VALIDATION scenario exited 0"; fi
if [[ -f "$WORK/open_calls.log" ]]; then
  fail "FAILED_VALIDATION scenario opened canonical.md even though the run failed"
else
  pass "FAILED_VALIDATION scenario does not open canonical.md (even though the file exists on disk)"
fi
if grep -q "state=FAILED_VALIDATION" /tmp/crossref_test_out; then
  pass "FAILED_VALIDATION scenario reports the failing state to the user"
else
  fail "FAILED_VALIDATION scenario did not report the failing state"
fi

# --- Scenario 3: relative input path from a different cwd -----------------

mkdir -p "$REPO/subdir"
echo '{}' > "$REPO/runs_input/relative.json"
rm -f "$WORK/open_calls.log"
(
  cd "$REPO/subdir" || exit 1
  STUB_REPO="$REPO" STUB_RUN_ID="CR-TEST-003" STUB_STATE="PASSED" STUB_EXIT=0 STUB_WRITE_CANONICAL=1 \
    crossref "../runs_input/relative.json" >/tmp/crossref_test_out 2>&1
)
status=$?

if [[ "$status" -eq 0 ]]; then
  pass "relative-path scenario resolves and exits 0"
else
  fail "relative-path scenario failed (exit $status): $(cat /tmp/crossref_test_out)"
fi
if [[ -f "$WORK/open_calls.log" ]] && grep -q "$REPO/runs/CR-TEST-003/canonical.md" "$WORK/open_calls.log"; then
  pass "relative-path scenario opens the correct canonical.md"
else
  fail "relative-path scenario did not open the expected canonical.md"
fi

# --- Summary ----------------------------------------------------------------

echo
if [[ "$failures" -eq 0 ]]; then
  echo "All crossref shell function smoke tests passed."
  exit 0
else
  echo "$failures crossref shell function smoke test(s) failed."
  exit 1
fi
