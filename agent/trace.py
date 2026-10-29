"""Run traces: everything the agents and the operator did, as JSONL, for audit and for retro-learner.
runs/<run_id>/trace.jsonl     one line per document received (input, result)
runs/<run_id>/operator.jsonl  one line per human action (approve, resolve, correction)
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = Path(os.environ.get("RUNS_DIR") or ROOT / "runs")   # tests point this at a temp dir (tests/conftest.py)
# what the autopilot and the API write for the run; POST /demo/reset clears them (trace/operator JSONL stay, with a marker)
RUN_ARTIFACTS = ("letters", "messages", "investigations", "cases", "audit.md", "outbox.jsonl", "autopilot-status.json",
                 "handoffs.jsonl", "audits")


class Trace:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or os.environ.get("RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.dir = RUNS / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.epoch = uuid.uuid4().hex[:12]   # changes on every reset: the autopilot drops its in-memory state when it does
        self._link_latest()

    def _link_latest(self) -> None:
        (RUNS / "latest").unlink(missing_ok=True)
        try:
            (RUNS / "latest").symlink_to(self.run_id)
        except OSError:
            pass

    def reset(self, **data: Any) -> None:
        """Demo reset: a clean run in the same directory (artifacts gone, runs/latest -> this run, new epoch)."""
        for name in RUN_ARTIFACTS:
            p = self.dir / name
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        self.epoch = uuid.uuid4().hex[:12]
        self._link_latest()
        self._write("trace.jsonl", {"kind": "reset", "epoch": self.epoch, **data})
        self._write("operator.jsonl", {"kind": "reset", "epoch": self.epoch, **data})

    def _write(self, name: str, record: dict[str, Any]) -> None:
        record = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
        with (self.dir / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def document(self, doc: dict[str, Any], result: dict[str, Any]) -> None:
        self._write("trace.jsonl", {"kind": "document", "document": doc, "result": result})

    def operator(self, action: str, **data: Any) -> None:
        self._write("operator.jsonl", {"kind": "operator", "action": action, **data})

    def snapshot_case(self, case: dict[str, Any]) -> None:
        d = self.dir / "cases"
        d.mkdir(exist_ok=True)
        (d / f"{case['id']}.json").write_text(json.dumps(case, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
