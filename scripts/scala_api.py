#!/usr/bin/env python3
"""083 · Scalability of the API layer (no LLM): POST /documents with pre-extracted documents, C concurrent clients.

Run only against a test instance (coordonare/bin/test-instance start 8060), never :8000/:8001: every level starts
with POST /demo/reset. The API's core mock knows only the demo customer, so the documents are the 7 demo documents
for Maria Ionescu, each request with its own id and document number (no duplicates): the one case grows with every
request, so the script also reports latency in the first vs. the last 10% of requests; --batch N resets every N
requests so the case stays the size of a few real ones.

  .venv/bin/python scripts/scala_api.py --api http://127.0.0.1:8060 --levels 1,10,50 --requests 700 \
      --out runs/scala/api.json
"""
from __future__ import annotations

import argparse
import copy
import http.client
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.demo_documents import DOCUMENTS  # noqa: E402

_local = threading.local()


def conn(host: str, port: int) -> http.client.HTTPConnection:
    if not hasattr(_local, "c"):
        _local.c = http.client.HTTPConnection(host, port, timeout=60)
    return _local.c


def post(host: str, port: int, path: str, body: dict | None) -> tuple[int, float, str]:
    data = json.dumps(body or {}).encode()
    t = time.perf_counter()
    try:
        c = conn(host, port)
        c.request("POST", path, body=data, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        text = r.read().decode(errors="replace")
        return r.status, time.perf_counter() - t, text[:200] if r.status >= 400 else ""
    except Exception as e:  # noqa: BLE001 -- a dropped connection is a measured error
        if hasattr(_local, "c"):
            _local.c.close()
            del _local.c
        return 0, time.perf_counter() - t, repr(e)[:200]


def doc(j: int, level: int) -> dict:
    d = copy.deepcopy(DOCUMENTS[j % 7])
    d["id"] = f"L{level}-R{j}"
    for key in ("reference", "document_number"):
        if d["fields"].get(key):
            d["fields"][key] = f"{d['fields'][key]}-L{level}-R{j}"
    return d


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def reset(host: str, port: int) -> None:
    c = http.client.HTTPConnection(host, port, timeout=60)   # own connection: a pooled one may have timed out
    c.request("POST", "/demo/reset?variants=pensie")
    r = c.getresponse()
    r.read()
    c.close()
    if r.status != 200:
        raise SystemExit(f"reset eșuat: {r.status}")


def level_run(host: str, port: int, c: int, n: int, batch: int) -> dict:
    """n requests at concurrency c; with batch > 0, a /demo/reset every `batch` requests (the case stays small)."""
    docs = [doc(j, c) for j in range(n)]
    out: list[tuple[int, int, float, str]] = []
    lock = threading.Lock()
    batch = batch or n

    def one(j: int) -> None:
        s, dt, e = post(host, port, "/documents", docs[j])
        with lock:
            out.append((j, s, dt, e))

    wall = 0.0
    with ThreadPoolExecutor(max_workers=c) as ex:
        for b in range(0, n, batch):
            reset(host, port)
            t0 = time.perf_counter()
            list(ex.map(one, range(b, min(n, b + batch))))
            wall += time.perf_counter() - t0
    out.sort()
    lat = [dt * 1000 for _, s, dt, _ in out if s == 200]
    errs = [(s, e) for _, s, _, e in out if s != 200]
    tenth = max(1, n // 10)
    first = [dt * 1000 for j, s, dt, _ in out[:tenth] if s == 200]
    last = [dt * 1000 for j, s, dt, _ in out[-tenth:] if s == 200]
    kinds: dict[str, int] = {}
    for s, e in errs:
        k = f"{s} {e[:80]}"
        kinds[k] = kinds.get(k, 0) + 1
    return {"concurrency": c, "requests": n, "reset_every": batch, "ok": len(lat), "errors": len(errs), "error_kinds": kinds,
            "wall_s": round(wall, 2), "req_per_s": round(n / wall, 1),
            "p50_ms": round(pct(lat, 50), 1) if lat else None, "p95_ms": round(pct(lat, 95), 1) if lat else None,
            "p99_ms": round(pct(lat, 99), 1) if lat else None, "max_ms": round(max(lat), 1) if lat else None,
            "first10pct_median_ms": round(statistics.median(first), 1) if first else None,
            "last10pct_median_ms": round(statistics.median(last), 1) if last else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--levels", default="1,10,50")
    ap.add_argument("--requests", type=int, default=700)
    ap.add_argument("--batch", type=int, default=0, help="reset every N requests (0 = one case for the whole level)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    u = urlparse(a.api)
    if u.port in (8000, 8001):
        raise SystemExit("nu pe :8000/:8001 (MVP-ul viu); pornește test-instance start 8060")
    res = {"level": "api", "date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "api": a.api,
           "source": "scripts/scala_api.py (POST /documents, documente pre-extrase, uvicorn 1 proces, instanță de test)",
           "levels": []}
    for c in [int(x) for x in a.levels.split(",")]:
        r = level_run(u.hostname, u.port, c, a.requests, a.batch)
        print(json.dumps(r, ensure_ascii=False))
        res["levels"].append(r)
    reset(u.hostname, u.port)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
