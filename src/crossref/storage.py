"""Run artifact persistence — Section 19.

runs/<YYYY-MM-DD_HHMM>_<topic>__<RUN_ID>/
├── input.json
├── independent.json
├── result.json
├── validation.json
├── canonical.md
└── manifest.json

latest/canonical.md is a copy of the newest PASSED run's canonical.md —
see orchestrator.run(), which only refreshes it on a confirmed PASS.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_RUNS_ROOT = Path(__file__).resolve().parent.parent.parent / "runs"
DEFAULT_LATEST_ROOT = Path(__file__).resolve().parent.parent.parent / "latest"

_MAX_TOPIC_LEN = 50
_LEADING_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[_-]?")
_UNSAFE_CHARS_RE = re.compile(r"[^a-z0-9-]+")
_REPEAT_HYPHEN_RE = re.compile(r"-{2,}")


def sanitize_topic(raw: str) -> str:
    """Filesystem-safe topic slug: lowercase, hyphenated, ASCII-only.

    Also strips a leading YYYY-MM-DD date (the run directory already gets
    its own timestamp, so a date-prefixed input filename shouldn't produce
    a doubled-up date in the topic).
    """
    text = (raw or "").strip().lower()
    text = _LEADING_DATE_RE.sub("", text)
    text = text.replace(" ", "-")
    text = _UNSAFE_CHARS_RE.sub("-", text)
    text = _REPEAT_HYPHEN_RE.sub("-", text)
    text = text.strip("-")
    text = text[:_MAX_TOPIC_LEN].rstrip("-")
    return text or "run"


def derive_topic(run_input, source_input_path: Optional[Path] = None) -> str:
    """Topic for a run's directory name: explicit RunInput.topic, else the
    source input filename, else a slice of the objective as a last resort."""
    explicit = getattr(run_input, "topic", None)
    if explicit and explicit.strip():
        return sanitize_topic(explicit)
    if source_input_path is not None:
        return sanitize_topic(source_input_path.stem)
    return sanitize_topic(run_input.original_task.objective[:40])


def build_run_dir_name(topic: str, run_id: str, when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    stamp = when.strftime("%Y-%m-%d_%H%M")
    return f"{stamp}_{topic}__{run_id}"


def next_run_id(runs_root: Path = DEFAULT_RUNS_ROOT) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"CR-{today}-"
    runs_root.mkdir(parents=True, exist_ok=True)
    # Search anywhere in the directory name, not just a prefix match — run
    # directories are named "<timestamp>_<topic>__<run_id>", so the run_id
    # is a suffix rather than the whole name.
    pattern = re.compile(re.escape(prefix) + r"(\d+)")
    used = set()
    for p in runs_root.iterdir():
        if not p.is_dir():
            continue
        match = pattern.search(p.name)
        if match:
            used.add(int(match.group(1)))
    seq = 1
    while seq in used:
        seq += 1
    return f"{prefix}{seq:03d}"


def run_dir(dir_name: str, runs_root: Path = DEFAULT_RUNS_ROOT) -> Path:
    return runs_root / dir_name


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
