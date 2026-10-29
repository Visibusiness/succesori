#!/usr/bin/env python3
"""083 · Scalability of the AI layer: agent.extract on 20 demo documents, at concurrency 1/5/10/20, on Bedrock.

Run with the Bedrock environment (the same exports as coordonare/bin/claude-bedrock):
  sh -c '. <fișierul cu tokenul Bedrock>; export CLAUDE_CODE_USE_BEDROCK=1 AWS_REGION=us-west-2 \
     CLAUDE_CONFIG_DIR=~/.claude-bedrock ANTHROPIC_DEFAULT_SONNET_MODEL=us.anthropic.claude-sonnet-5-5 \
     DEMO_MODE=1 EXTRACT_RETRIES=0; .venv/bin/python scripts/scala_ai.py --levels 1,5,10,20 --out runs/scala/ai.json'
EXTRACT_RETRIES=0 so that every throttling / failed call is counted (production keeps agent.extract's 2 retries).
Every call is one `claude -p` process (≈250 MB): a level is skipped if the machine lacks the memory for it.
Cost: ≈ 0,05 $ per document (cost-per-dosar.md), ≈ 4 $ for the four levels. Do not raise the concurrency above 20.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent import extract as X  # noqa: E402

DOCS = ROOT / "registries" / "documents"
MAX_CONCURRENCY = 20
MB_PER_CALL = 300


def corpus() -> list[tuple[Path, str]]:
    """20 documents: the 7 text ones of the demo, the 10 hard ones, 3 PDFs (read visually). With the truth type."""
    items = sorted(DOCS.glob("0*.md")) + sorted((DOCS / "hard").glob("H*.md"))
    items += [DOCS / "pdf" / f for f in ("02-adresa-notar.pdf", "03-certificat-asigurare.pdf", "05-raspuns-asigurator.pdf")]
    out = []
    for p in items[:20]:
        truth = p.parent.parent / f"{p.stem}.mvp.json" if p.suffix == ".pdf" else p.with_name(f"{p.stem}.mvp.json")
        out.append((p, json.loads(truth.read_text(encoding="utf-8")).get("document_type") if truth.exists() else None))
    return out


def mem_available_mb() -> int:
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


def one(p: Path, truth: str | None) -> dict:
    t = time.perf_counter()
    try:
        doc = X.extract_file(p, p.name) if p.suffix == ".pdf" else X.extract(p.read_text(encoding="utf-8"), p.name)
        return {"doc": p.name, "ok": True, "s": round(time.perf_counter() - t, 1), "type_ok": doc.get("document_type") == truth,
                "cost_usd": (doc.get("extractor") or {}).get("cost_usd")}
    except Exception as e:  # noqa: BLE001 -- a failed call is a measurement
        msg = str(e)
        kind = "throttling" if any(k in msg.lower() for k in ("throttl", "429", "rate limit", "too many")) else \
               "timeout" if "timed out" in msg.lower() or "timeout" in msg.lower() else "other"
        return {"doc": p.name, "ok": False, "s": round(time.perf_counter() - t, 1), "error_kind": kind, "error": msg[-200:]}


def level(c: int, items: list[tuple[Path, str | None]]) -> dict:
    avail = mem_available_mb()
    if avail < c * MB_PER_CALL:
        return {"concurrency": c, "skipped": f"memorie disponibilă {avail} MB < {c} × {MB_PER_CALL} MB"}
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=c) as ex:
        res = list(ex.map(lambda it: one(*it), items))
    wall = time.perf_counter() - t0
    ok = [r for r in res if r["ok"]]
    lat = sorted(r["s"] for r in ok)
    costs = [r["cost_usd"] for r in ok if r.get("cost_usd") is not None]
    kinds: dict[str, int] = {}
    for r in res:
        if not r["ok"]:
            kinds[r["error_kind"]] = kinds.get(r["error_kind"], 0) + 1
    return {"concurrency": c, "documents": len(items), "ok": len(ok), "errors": len(res) - len(ok), "error_kinds": kinds,
            "type_correct": sum(1 for r in ok if r["type_ok"]), "wall_s": round(wall, 1),
            "docs_per_hour": round(len(ok) / wall * 3600), "latency_p50_s": statistics.median(lat) if lat else None,
            "latency_max_s": max(lat) if lat else None, "latency_min_s": min(lat) if lat else None,
            "cost_usd_total": round(sum(costs), 3), "cost_usd_per_doc": round(statistics.mean(costs), 4) if costs else None,
            "mem_available_mb_before": avail, "calls": res}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="1,5,10,20")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    levels = [int(x) for x in a.levels.split(",")]
    if max(levels) > MAX_CONCURRENCY:
        raise SystemExit(f"concurența maximă permisă: {MAX_CONCURRENCY}")
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") != "1":
        raise SystemExit("rulează cu mediul Bedrock (vezi docstring)")
    items = corpus()
    res = {"level": "ai", "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "source": "scripts/scala_ai.py (agent.extract / extract_file, claude -p pe Bedrock us-west-2)",
           "model": X.MODEL, "model_id": os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL"),
           "retries": X.RETRIES, "documents": [p.name for p, _ in items], "levels": []}
    for c in levels:
        r = level(c, items)
        print(json.dumps({k: v for k, v in r.items() if k != "calls"}, ensure_ascii=False), flush=True)
        res["levels"].append(r)
        if a.out:   # after every level: a crash later keeps what was measured
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
