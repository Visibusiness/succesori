#!/usr/bin/env python3
"""083 · Scalability of the logic layer (no LLM): the pipeline in process, on N cases of 7 pre-extracted documents.

Each case is the demo scenario (agent/demo_documents.py) for its own customer: a Bank (core_mock, unchanged) gets
N clones of the demo customer here, with distinct CIF/CNP, and the 7 documents get that CNP and distinct
references (notary file, certificate numbers). Document 07 (illegible, no CNP) goes to the orphan case, as in the demo.
Documents are fed interleaved by step (all DGEP signals, then all notary letters, ...), like a weekly DGEP batch
followed by mail over the weeks, so the case table is full from the start.

  .venv/bin/python scripts/scala_logic.py --cases 1000 --out runs/scala/logic-1000.json
Measures: total time, cases/s, documents/s, RSS, time per document by bucket (does it grow with N?).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "1")

from agent.core_mock import Bank  # noqa: E402
from agent.demo_documents import DOCUMENTS  # noqa: E402
from agent.pipeline import Pipeline  # noqa: E402


def rss_mb() -> float:
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2**20


def build_bank(n: int) -> Bank:
    """N customers shaped like Maria Ionescu (same products and movements), each with its own CIF and CNP."""
    bank = Bank()
    tpl_c, tpl_p, tpl_m = bank.customers["RC1001"], bank._products["RC1001"], bank._movements["RC1001"]
    for i in range(n):
        cif = f"RS{i:06d}"
        bank.customers[cif] = {**copy.deepcopy(tpl_c), "cif": cif, "cnp": f"2{i:012d}", "name": f"Client{i} Test"}
        bank._products[cif] = copy.deepcopy(tpl_p)
        bank._movements[cif] = list(tpl_m)
    return bank


def docs_for(i: int) -> list[dict]:
    cnp, out = f"2{i:012d}", []
    for k, d in enumerate(DOCUMENTS, 1):
        d = copy.deepcopy(d)
        d["id"] = f"S{i}-{k}"
        f = d["fields"]
        if f.get("cnp"):
            f["cnp"] = cnp
        for key in ("reference", "case_file", "document_number"):
            if f.get(key):
                f[key] = f"{f[key]}-S{i}"
        out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=1000)
    ap.add_argument("--buckets", type=int, default=10)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    rss0 = rss_mb()
    t = time.perf_counter()
    bank = build_bank(a.cases)
    pipe = Pipeline(bank)
    all_docs = [docs_for(i) for i in range(a.cases)]
    setup_s = time.perf_counter() - t
    rss_setup = rss_mb()

    order = [all_docs[i][k] for k in range(7) for i in range(a.cases)]   # by step, across all cases
    n = len(order)
    per = max(1, n // a.buckets)
    buckets, outcomes, errors = [], {}, 0
    t0 = time.perf_counter()
    tb = t0
    for j, doc in enumerate(order, 1):
        try:
            r = pipe.receive(doc)
            key = "orphan" if r.get("case_id") == "SC-NEIDENTIFICAT" else ("escalation" if r.get("escalation") else "ok")
            outcomes[key] = outcomes.get(key, 0) + 1
        except Exception as e:  # noqa: BLE001 -- counted, the run goes on
            errors += 1
            if errors <= 3:
                print(f"eroare la {doc['id']}: {e!r}", file=sys.stderr)
        if j % per == 0 or j == n:
            now = time.perf_counter()
            cnt = j - (len(buckets) * per)
            buckets.append({"docs_done": j, "step": (j - 1) // a.cases + 1, "us_per_doc": round((now - tb) / cnt * 1e6, 1),
                            "rss_mb": round(rss_mb(), 1)})
            tb = now
    total = time.perf_counter() - t0

    paid = sum(1 for c in pipe.cases.values() if c.cif != "-" and any("payment" in m for m in c.milestones))
    res = {
        "level": "logic", "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "scripts/scala_logic.py (Pipeline.receive în proces, core_mock cu N clienți, documente pre-extrase)",
        "cases": a.cases, "documents": n, "errors": errors, "outcomes": outcomes,
        "cases_opened": len(pipe.cases), "cases_with_payment_milestone": paid,
        "setup_s": round(setup_s, 2), "total_s": round(total, 3),
        "cases_per_s": round(a.cases / total, 1), "docs_per_s": round(n / total, 1),
        "us_per_doc_avg": round(total / n * 1e6, 1),
        "us_per_doc_first_bucket": buckets[0]["us_per_doc"], "us_per_doc_last_bucket": buckets[-1]["us_per_doc"],
        "rss_mb_start": round(rss0, 1), "rss_mb_after_setup": round(rss_setup, 1), "rss_mb_end": round(rss_mb(), 1),
        "rss_mb_peak": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "kb_per_case": round((rss_mb() - rss0) * 1024 / a.cases, 1),
        "buckets": buckets,
    }
    print(json.dumps({k: v for k, v in res.items() if k != "buckets"}, ensure_ascii=False, indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
