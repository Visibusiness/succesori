"""Persistent memory of the MVP: one SQLite file (stdlib sqlite3), docs/PERSISTENTA.md.

  MVP_DB=<path>        where the file lives; `:memory:` (or `off`) = no persistence
  default              $RUNS_DIR/<RUN_ID>/mvp.sqlite when RUNS_DIR is set (test instances: coordonare/bin/test-instance,
                       pytest), else data/mvp.sqlite (the live MVP on :8001; data/ is not in git)

Two tables: `cases` (one row per succession case, the Case as JSON) and `state` (key -> JSON: the mock core, the
API's side data, the run's artifact files). The API calls `save()` after every request that may change state; one
call = one transaction, and only the rows whose JSON changed are written. JSON only, never pickle: dates as ISO
strings, Fraction as "1/2", sets as sorted lists (the objects' own to_dict / from_dict do the typed fields).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = 1


def default_path(run_id: str) -> str:
    if os.environ.get("MVP_DB"):
        return os.environ["MVP_DB"]
    if os.environ.get("RUNS_DIR"):
        return str(Path(os.environ["RUNS_DIR"]) / run_id / "mvp.sqlite")
    return str(ROOT / "data" / "mvp.sqlite")


def _default(o: Any) -> Any:
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Fraction):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    raise TypeError(f"nu se poate salva în SQLite: {type(o).__name__}")


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=_default)   # key order kept: the UI shows fields in document order


class Store:
    def __init__(self, path: str):
        self.path = path
        self.enabled = path not in (":memory:", "off", "")
        self._lock = threading.Lock()
        self._last: dict[tuple[str, str], str] = {}   # (table, key) -> JSON last written: unchanged rows are skipped
        self.writes = 0                                # transactions committed (tests, /store/status)
        self._db: sqlite3.Connection | None = None
        if self.enabled:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=NORMAL")
            self._db.executescript(
                "CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL);")
            self._db.execute("INSERT OR IGNORE INTO state VALUES ('schema', ?, ?)", (str(SCHEMA), _now()))

    # ------------------------------------------------------------------ read
    def load(self) -> dict[str, Any] | None:
        """{"cases": {id: dict}, <key>: value, ...} or None when nothing was ever saved."""
        if not self._db:
            return None
        with self._lock:
            cases = {i: json.loads(d) for i, d in self._db.execute("SELECT id, data FROM cases")}
            state = {k: json.loads(d) for k, d in self._db.execute("SELECT key, data FROM state WHERE key != 'schema'")}
            self._last = {("cases", k): dumps(v) for k, v in cases.items()}
            self._last.update({("state", k): dumps(v) for k, v in state.items()})
        if not state:
            return None
        return {"cases": cases, **state}

    # ------------------------------------------------------------------ write
    def save(self, cases: dict[str, Any], state: dict[str, Any]) -> int:
        """One transaction: rows that changed are written, cases that no longer exist are deleted. Returns how many
        rows changed (0 = nothing to write, no transaction)."""
        if not self._db:
            return 0
        rows = {("cases", k): dumps(v) for k, v in cases.items()}
        rows.update({("state", k): dumps(v) for k, v in state.items()})
        with self._lock:
            changed = {k: v for k, v in rows.items() if self._last.get(k) != v}
            gone = [k for t, k in self._last if t == "cases" and ("cases", k) not in rows]
            if not changed and not gone:
                return 0
            at = _now()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                for (table, key), data in changed.items():
                    col = "id" if table == "cases" else "key"
                    self._db.execute(f"INSERT INTO {table} ({col}, data, updated_at) VALUES (?, ?, ?) "
                                     f"ON CONFLICT({col}) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                                     (key, data, at))
                for key in gone:
                    self._db.execute("DELETE FROM cases WHERE id = ?", (key,))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._last.update(changed)
            for key in gone:
                self._last.pop(("cases", key), None)
            self.writes += 1
            return len(changed) + len(gone)

    def saved(self, key: str) -> Any:
        """The last value written (or loaded) for a `state` row, without reading the file: e.g. "artifacts"."""
        raw = self._last.get(("state", key))
        return json.loads(raw) if raw else None

    def status(self) -> dict[str, Any]:
        if not self._db:
            return {"enabled": False, "path": self.path}
        with self._lock:
            n = self._db.execute("SELECT count(*) FROM cases").fetchone()[0]
            last = self._db.execute("SELECT max(updated_at) FROM (SELECT updated_at FROM cases UNION ALL "
                                    "SELECT updated_at FROM state WHERE key != 'schema')").fetchone()[0]
        return {"enabled": True, "path": self.path, "cases": n, "last_write": last, "writes": self.writes}

    def close(self) -> None:
        if self._db:
            self._db.close()
            self._db = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
