"""Run artifact persistence — Section 19.

runs/<RUN_ID>/
├── input.json
├── independent.json
├── result.json
├── validation.json
├── canonical.md
└── manifest.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_RUNS_ROOT = Path(__file__).resolve().parent.parent.parent / "runs"


def next_run_id(runs_root: Path = DEFAULT_RUNS_ROOT) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"CR-{today}-"
    runs_root.mkdir(parents=True, exist_ok=True)
    existing = [p.name for p in runs_root.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    seq = 1
    used = set()
    for name in existing:
        tail = name[len(prefix) :]
        if tail.isdigit():
            used.add(int(tail))
    while seq in used:
        seq += 1
    return f"{prefix}{seq:03d}"


def run_dir(run_id: str, runs_root: Path = DEFAULT_RUNS_ROOT) -> Path:
    return runs_root / run_id


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
