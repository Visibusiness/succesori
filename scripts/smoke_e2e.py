#!/usr/bin/env python3
"""End-to-end smoke test of the live MVP: inbox -> autopilot (LLM extraction + agents) -> pipeline -> payment.

  1. clean start: POST /demo/reset?inbox=true&gol=1 (cases, run artifacts, autopilot state, inbox; an empty bank,
     without the seeded portfolio of 084) and wait for the autopilot to pick up the new epoch
  2. the 7 demo documents (01 json, 02-07 md, variant A) one at a time through POST /inbox; after each, wait until
     the autopilot has processed it and is idle again (its agents are done), and check the case state
  3. the exact values of kb/scenariu-demo/maria-ionescu.md (net 527.337 bani, lines, deposit, pension, doc 07, messages,
     letters), then POST /payments/{id}/approve and PAID

Usage:  .venv/bin/python scripts/smoke_e2e.py [--api http://localhost:8001] [--timeout 600] [--json out.json]
Output: a PASS/FAIL table; exit code 0 only if every check passes (2 = server or autopilot not reachable).
Needs the autopilot running in --watch mode against the same server (scripts/test-instance.sh start does both).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "registries" / "documents"
CASE = "SC-2026-0001"
ORPHAN = "SC-NEIDENTIFICAT"
# (file, state of Maria's case after it) — kb/scenariu-demo/maria-ionescu.md §3; doc 07 must not touch her case
STEPS = [("01-dgep-semnal.json", "FROZEN"), ("02-adresa-notar.md", "NOTARY_ANSWERED"),
         ("03-certificat-asigurare.md", "INSURANCE_CLAIM_OPEN"), ("04-certificat-mostenitor-A.md", "SUPPLEMENT_REQUESTED"),
         ("05-raspuns-asigurator.md", "INSURANCE_SETTLED"), ("06-certificat-suplimentar.md", "PAYMENT_PENDING_APPROVAL"),
         ("07-certificat-deces-ilizibil.md", "PAYMENT_PENDING_APPROVAL")]
LETTERS = ["notary_answer_drafted", "insurance_claim_opened", "supplement_requested"]
# §2.4 variant A: (heir, product) -> (amount in bani, blocked). The heir is matched on the words of the name, not their
# order or case: the LLM extractor keeps the certificate's spelling ("IONESCU ION"), the ground truth says "Ion Ionescu".
LINES = {("Ion Ionescu", "CC-1"): (329585, False), ("Andrei Ionescu", "CC-1"): (98876, False),
         ("Elena Ionescu", "CC-1"): (98876, True),
         ("Ion Ionescu", "DEP-1"): (1315000, True), ("Andrei Ionescu", "DEP-1"): (394500, True),
         ("Elena Ionescu", "DEP-1"): (394500, True)}


def person(name: str) -> frozenset[str]:
    return frozenset(name.casefold().split())


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body: Any = None, files: list[tuple[str, bytes]] | None = None) -> Any:
        headers, data = {}, None
        if files is not None:
            boundary = uuid.uuid4().hex
            parts = []
            for name, content in files:
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\n'
                             "Content-Type: application/octet-stream\r\n\r\n".encode() + content + b"\r\n")
            data = b"".join(parts) + f"--{boundary}--\r\n".encode()
            headers["content-type"] = f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data, headers["content-type"] = json.dumps(body).encode(), "application/json"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return {"_http_error": e.code, "detail": e.read().decode(errors="replace")[:300]}

    def get(self, path: str) -> Any:
        return self.call("GET", path)


class Report:
    def __init__(self):
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: Any = "") -> bool:
        self.rows.append((name, bool(ok), str(detail)[:160]))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  {'' if ok else detail}", flush=True)
        return bool(ok)

    def table(self) -> str:
        w = max(len(r[0]) for r in self.rows)
        out = [f"{'verificare':<{w}}  rezultat  detaliu (la FAIL)", "-" * (w + 30)]
        out += [f"{n:<{w}}  {'PASS' if ok else 'FAIL':<8}  {'' if ok else d}" for n, ok, d in self.rows]
        failed = sum(not ok for _, ok, _ in self.rows)
        out.append(f"\n{len(self.rows) - failed}/{len(self.rows)} PASS" + (f", {failed} FAIL" if failed else ""))
        return "\n".join(out)

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.rows)


def wait(pred, timeout: float, every: float = 2.0) -> Any:
    """Poll pred() until it returns something truthy or the timeout passes (then returns the last value)."""
    end, val = time.time() + timeout, None
    while True:
        val = pred()
        if val or time.time() >= end:
            return val
        time.sleep(every)


def autopilot(api: Api) -> dict[str, Any]:
    st = api.get("/autopilot/status")
    return st if isinstance(st, dict) else {}


def clean_start(api: Api, rep: Report, timeout: float) -> bool:
    # do not reset under an agent call in flight: it would write its artifact into the fresh run
    wait(lambda: (autopilot(api).get("autopilot") or {}).get("state") == "idle", timeout)
    r = api.call("POST", "/demo/reset?inbox=true&gol=1")
    if not rep.check("start curat: POST /demo/reset?inbox=true&gol=1", isinstance(r, dict) and r.get("status") == "reset", r):
        return False
    inbox = api.get("/inbox")
    rep.check("start curat: inbox gol, niciun dosar, nimic în outbox",
              inbox == {"waiting": [], "processed": [], "failed": []} and api.get("/cases") == []
              and api.get("/messages") == [], {"inbox": inbox})
    synced = wait(lambda: (autopilot(api).get("autopilot") or {}).get("epoch") == r["epoch"], 60)
    st = (autopilot(api).get("autopilot") or {})
    return rep.check("autopilotul a preluat run-ul nou (epoch, stare goală)",
                     synced and not st.get("processed") and not st.get("messages_sent"),
                     {"epoch": st.get("epoch"), "expected": r["epoch"], "processed": len(st.get("processed") or [])})


def feed(api: Api, rep: Report, name: str, expected: str, timeout: float) -> dict[str, Any] | None:
    r = api.call("POST", "/inbox", files=[(name, (DOCS / name).read_bytes())])
    saved = (r or {}).get("saved") or []
    if not rep.check(f"{name[:2]}: POST /inbox", saved == [name], r):
        return None

    def done():
        st = autopilot(api)
        a = st.get("autopilot") or {}
        hit = next((p for p in a.get("processed") or [] if p.get("file") == name), None)
        return hit if hit and a.get("state") == "idle" and name not in api.get("/inbox")["waiting"] else None

    t0 = time.time()
    hit = wait(done, timeout)
    secs = round(time.time() - t0)
    if not rep.check(f"{name[:2]}: procesat de autopilot ({secs} s)", hit, f"timeout {timeout} s"):
        return None
    res = hit.get("result") or {}
    case = api.get(f"/cases/{CASE}")
    state = case.get("state") if isinstance(case, dict) else None
    rep.check(f"{name[:2]}: stare dosar {expected}", state == expected,
              {"state": state, "document_type": hit.get("document_type"), "result": res})
    return res


def verify(api: Api, rep: Report, results: list[dict[str, Any] | None]) -> None:
    case = api.get(f"/cases/{CASE}")
    plan = (case or {}).get("payment_plan") or {}
    net = plan.get("net_account") or {}
    rep.check("net cont curent = 527.337 bani", net.get("net") == 527337, net)
    got = {(person(l["name"]), l["product_id"]): (l["amount"], l["blocked"]) for l in plan.get("lines") or []}
    for (who, prod), want in LINES.items():
        rep.check(f"linie {who.split()[0]} {prod} = {want[0]}{' blocată' if want[1] else ''}",
                  got.get((person(who), prod)) == want, got.get((person(who), prod)))
    rep.check("linii plan = exact cele 6 din scenariu", set(got) == {(person(w), p) for w, p in LINES},
              [(" ".join(sorted(w)), p) for w, p in got])
    dep = [l for l in plan.get("lines") or [] if l["product_id"] == "DEP-1"]
    rep.check("depozit: plata la scadență 2027-01-03", dep and all(l["pay_on"] == "2027-01-03" for l in dep),
              [l.get("pay_on") for l in dep])
    rep.check("pensia din octombrie reținută (retur CNPP 210.000)",
              plan.get("withheld") == [{"reason": "pension_return_CNPP", "amount": 210000,
                                        "label": "Pensie necuvenită — retur CNPP"}] and net.get("withheld") == 210000,
              plan.get("withheld"))
    rep.check("plata nu pleacă fără aprobare (pending_approval)", plan.get("status") == "pending_approval", plan.get("status"))

    r7 = results[6] or {}
    cases = api.get("/cases")
    escs = api.get("/escalations")
    rep.check("doc 07: escaladat, fără dosar nou", r7.get("case_id") == ORPHAN and r7.get("escalation")
              and sorted(c["id"] for c in cases) == sorted([CASE, ORPHAN]), {"result": r7, "cases": [c["id"] for c in cases]})
    rep.check("doc 07: o singură escaladare deschisă, fără CNP citit", len(escs) == 1 and escs[0]["status"] == "deschis"
              and "07-certificat-deces" in (escs[0].get("source") or ""), escs)
    rep.check("doc 07: dosarul Mariei neatins (6 documente)", len((case or {}).get("documents") or []) == 6,
              len((case or {}).get("documents") or []))

    msgs = api.get(f"/messages?case_id={CASE}")
    rep.check("mesaje către moștenitor = 2", len(msgs) == 2, [m.get("template_id") for m in msgs])
    arts = api.get(f"/cases/{CASE}/artifacts")
    files = {a["file"]: a["content"] for a in (arts or {}).get("artifacts") or []}
    for a in LETTERS:
        body = files.get(f"letters/{CASE}-{a}.md", "")
        rep.check(f"scrisoare {a}", body and "_Apelul agentului" not in body, body[:120] or "lipsește")
    inv = api.get(f"/cases/{ORPHAN}/artifacts")
    rep.check("investigație doc 07 (case-investigator)",
              any(a["kind"] == "investigation" and "_Apelul agentului" not in a["content"] for a in inv.get("artifacts") or []),
              [a["file"] for a in inv.get("artifacts") or []])
    rep.check("audit scris în run-ul serverului", bool((arts or {}).get("audit")), "audit.md lipsește")
    st = autopilot(api)
    a = st.get("autopilot") or {}
    rep.check("autopilot: fără erori, scrie în run-ul serverului",
              not a.get("errors") and st.get("run_dir") and all(c.get("ok") for c in a.get("agent_calls") or []),
              a.get("errors"))
    inbox = api.get("/inbox")
    rep.check("inbox: 7 în processed, nimic în failed sau în așteptare",
              sorted(inbox["processed"]) == sorted(n for n, _ in STEPS) and not inbox["failed"] and not inbox["waiting"], inbox)

    r = api.call("POST", f"/payments/PAY-{CASE}/approve", {"approver": "smoke-e2e"})
    rep.check("aprobare plată", isinstance(r, dict) and r.get("status") == "approved", r)
    case = api.get(f"/cases/{CASE}")
    rep.check("stare PAID", case.get("state") == "PAID", case.get("state"))
    audit = api.get("/audit")
    paid = [e for e in audit if e.get("action") == "pay"] if isinstance(audit, list) else []
    rep.check("core: o plată de 428.461 bani (Ion + Andrei, cont curent)",
              [(e["count"], e["total"]) for e in paid] == [(2, 428461)], paid)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8001")
    ap.add_argument("--timeout", type=float, default=600, help="secunde per document (extracție + agenți)")
    ap.add_argument("--json", help="scrie rezultatele și în acest fișier")
    a = ap.parse_args()
    api, rep = Api(a.api), Report()
    t0 = time.time()
    try:
        health = api.get("/health")
    except (urllib.error.URLError, OSError) as e:
        print(f"API-ul nu răspunde la {a.api}: {e}", file=sys.stderr)
        return 2
    if health != {"status": "ok"} or not wait(lambda: autopilot(api).get("running"), 30):
        print(f"API sau autopilot oprit la {a.api}: health={health}, autopilot={autopilot(api).get('running')}", file=sys.stderr)
        return 2
    print(f"smoke e2e pe {a.api} · run {autopilot(api).get('run_dir')}", flush=True)
    results: list[dict[str, Any] | None] = []
    if clean_start(api, rep, a.timeout):
        for name, expected in STEPS:
            results.append(feed(api, rep, name, expected, a.timeout))
            if results[-1] is None:
                break
        if len(results) == len(STEPS) and all(r is not None for r in results):
            verify(api, rep, results)
    secs = round(time.time() - t0)
    print("\n" + rep.table() + f"\ndurată: {secs} s")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"api": a.api, "seconds": secs, "ok": rep.ok,
                                            "rows": [{"check": n, "ok": ok, "detail": d} for n, ok, d in rep.rows]},
                                           ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
