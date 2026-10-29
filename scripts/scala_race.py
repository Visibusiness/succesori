#!/usr/bin/env python3
"""083 · Does the in-memory state survive concurrent documents? (what the API does: sync endpoint, thread pool; 089: Pipeline.lock)

For N new customers, the DGEP signal and the notary letter of the same customer are received at the same time by two
threads (Pipeline.receive, in process). Counts the documents that end up in no case (a case created twice with the
same id overwrites the first) and the exceptions.
  .venv/bin/python scripts/scala_race.py --cases 2000 --out runs/scala/race.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# SWITCH=1e-6 (default here) makes a rare interleaving show up in seconds; SWITCH=0.005 is Python's own default
sys.setswitchinterval(float(os.environ.get("SWITCH", "1e-6")))

from scala_logic import Pipeline, build_bank, docs_for  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=2000)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    pipe = Pipeline(build_bank(a.cases))
    errors: list[str] = []

    def feed(k: int) -> None:
        for i in range(a.cases):
            try:
                pipe.receive(docs_for(i)[k])
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e)[:120])

    ts = [threading.Thread(target=feed, args=(k,)) for k in (0, 1)]   # DGEP signal and notary letter, in parallel
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    kept = sum(len(c.documents) for c in pipe.cases.values())
    by_cif: dict[str, int] = {}
    for c in pipe.cases.values():
        by_cif[c.cif] = by_cif.get(c.cif, 0) + 1
    res = {"level": "race", "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "source": "scripts/scala_race.py (2 fire pe Pipeline.receive, ca endpoint-ul sync din API)",
           "documents_sent": 2 * a.cases, "documents_in_cases": kept, "documents_lost": 2 * a.cases - kept,
           "cases": len(pipe.cases), "customers_with_2_cases": sum(1 for v in by_cif.values() if v > 1),
           "exceptions": len(errors), "exception_examples": sorted(set(errors))[:3]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.out:
        a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
