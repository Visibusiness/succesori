"""Cost măsurat per dosar, din rulările din runs/ (nu din ipoteze).

Extractorul scrie `extractor.cost_usd` pe fiecare document din trace.jsonl, iar autopilotul scrie `cost_usd` pe fiecare apel
de agent în autopilot-status.json; ambele vin din `total_cost_usd` raportat de `claude -p`. Pentru fiecare rulare de demo
(un dosar, Maria Ionescu) adunăm extracția celor 7 documente demo și apelurile agenților.

    .venv/bin/python scripts/cost_dosar.py            # toate rulările cu agenți
    .venv/bin/python scripts/cost_dosar.py 20261028T130938Z
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
DEMO_TYPES = {"dgep_signal", "notary_request", "insurance_certificate", "heir_certificate", "insurer_response",
              "supplementary_certificate", "death_certificate"}


def _agent_calls(o, out: list) -> None:
    if isinstance(o, dict):
        if o.get("agent") and isinstance(o.get("cost_usd"), (int, float)):
            out.append(o)
        for v in o.values():
            _agent_calls(v, out)
    elif isinstance(o, list):
        for v in o:
            _agent_calls(v, out)


def run_cost(run: Path) -> dict | None:
    status = run / "autopilot-status.json"
    if not status.exists() or not (run / "trace.jsonl").exists():
        return None
    calls: list = []
    _agent_calls(json.loads(status.read_text(encoding="utf-8")), calls)
    seen, docs = set(), []
    for line in (run / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = e.get("document") or {}
        cost = (d.get("extractor") or {}).get("cost_usd")
        # un dosar = cele 7 tipuri demo, fiecare o dată (fără reîncărcări și fără documentele de test „unknown”)
        if e.get("kind") == "document" and d.get("document_type") in DEMO_TYPES - seen and cost is not None:
            seen.add(d["document_type"])
            docs.append(cost)
    if not calls:
        return None
    agents = defaultdict(lambda: {"calls": 0, "usd": 0.0, "seconds": 0.0})
    for c in calls:
        a = agents[c["agent"]]
        a["calls"] += 1
        a["usd"] += c["cost_usd"]
        a["seconds"] += c.get("seconds") or 0
    return {"run": run.name, "documents": len(docs), "extract_usd": sum(docs), "agents": dict(agents),
            "agents_usd": sum(a["usd"] for a in agents.values()), "total_usd": sum(docs) + sum(a["usd"] for a in agents.values())}


def main(argv: list[str]) -> None:
    runs = [RUNS / n for n in argv] if argv else sorted(p for p in RUNS.iterdir() if p.is_dir())
    for r in filter(None, map(run_cost, runs)):
        print(f"{r['run']}: {r['documents']} documente, extracție {r['extract_usd']:.2f} $ + agenți {r['agents_usd']:.2f} $"
              f" = {r['total_usd']:.2f} $")
        for name, a in sorted(r["agents"].items(), key=lambda kv: -kv[1]["usd"]):
            print(f"    {name:18} {a['calls']:2} apeluri  {a['usd']:.2f} $  {a['seconds']:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
