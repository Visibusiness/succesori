"""090: the real extraction of the portfolio's documents, memoized, and its accuracy against the reference values.

  scripts/portfolio_extract.py                 # every document: extractor (Bedrock) -> documente/<Pxx>/<doc>.extras.json
  scripts/portfolio_extract.py P05 P13-D6      # only these clients / documents
  scripts/portfolio_extract.py --report        # no LLM: accuracy of the .extras.json already on disk

Each document goes the autopilot's way (agent/portfolio.py::extract): agent/guard.py on the received file, then
agent/extract.py::extract_file on the -scan.pdf (a high-risk file is quarantined and never reaches the LLM). At most
10 at once. The accuracy is per field (the canonical fields of scripts/eval_extract.py + the death-certificate fields),
per document type, plus the document type and the confidence gate (illegible documents must stay under 0.8).
A wrong field is reported, never corrected: the reference values are not copied over the extraction.
Bedrock: run with the variables of coordonare/bin/claude-bedrock (the script sources them if they are missing).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "0")   # the portfolio's CNPs and IBANs are valid: the real check digits apply

from agent import portfolio  # noqa: E402
from scripts.eval_extract import CANONICAL, FORM_FIELDS, field_ok  # noqa: E402

SCORED = CANONICAL | FORM_FIELDS
TOKEN = Path("<fișierul cu tokenul Bedrock>")


def bedrock_env() -> None:
    """The variables of coordonare/bin/claude-bedrock, for the `claude -p` the extractor runs."""
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or not TOKEN.is_file():
        return
    out = subprocess.run(["sh", "-c", f". {TOKEN} && env"], capture_output=True, text=True, check=True).stdout
    os.environ.update(dict(line.split("=", 1) for line in out.splitlines() if "=" in line))
    os.environ.update({"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_REGION": os.environ.get("AWS_REGION") or "us-west-2",
                       "CLAUDE_CONFIG_DIR": os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude-bedrock"})
    for alias, model in (("SONNET", "us.anthropic.claude-sonnet-5-5"), ("HAIKU", "us.anthropic.claude-haiku-5-5"),
                         ("OPUS", "us.anthropic.claude-opus-5-5")):
        os.environ.setdefault(f"ANTHROPIC_DEFAULT_{alias}_MODEL", model)


def steps(only: list[str]) -> list[tuple[dict, dict]]:
    out = []
    for c in portfolio.clients():
        for s in portfolio.history(c):   # a pending document is read live, in the guided demo
            if "doc" in s and (not only or c["id"] in only or s["doc"]["id"] in only):
                out.append((c, s["doc"]))
    return out


def legible(d: dict) -> bool:
    """The reference says whether the document can be tied to a person: no CNP and no name = illegible (P01-D2)."""
    f = d["expected_fields"]
    return bool(f.get("cnp") or f.get("name"))


def score(d: dict, ex: dict) -> dict:
    fields = {k: {"ok": field_ok(k, v, ex.get("fields", {}).get(k)), "truth": v, "got": ex.get("fields", {}).get(k)}
              for k, v in d["expected_fields"].items() if k in SCORED}
    notes = []
    want = {h.get("name"): h for h in d["expected_fields"].get("heirs") or []}
    for h in ex.get("fields", {}).get("heirs") or []:   # not scored (eval_extract), but the pipeline uses it
        w = next((x for n, x in want.items() if sorted(n.upper().split()) == sorted(str(h.get("name", "")).upper().split())), None)
        if w and w.get("minor") and h.get("legal_representative") != w.get("legal_representative"):
            notes.append(f"legal_representative {h.get('name')}: {h.get('legal_representative')!r} (referință "
                         f"{w.get('legal_representative')!r})")
    return {"id": d["id"], "type": d["expected_type"], "type_ok": ex.get("document_type") == d["expected_type"],
            "gate_ok": (float(ex.get("confidence") or 0) >= 0.8) == legible(d), "confidence": ex.get("confidence"),
            "fields": fields, "notes": notes}


def report(rows: list[dict]) -> dict:
    by_field, by_type = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for r in rows:
        for k, f in r["fields"].items():
            by_field[k][0] += f["ok"]
            by_field[k][1] += 1
            by_type[r["type"]][0] += f["ok"]
            by_type[r["type"]][1] += 1
    ok = sum(v[0] for v in by_field.values())
    n = sum(v[1] for v in by_field.values())
    return {"documents": len(rows), "fields": n, "fields_ok": ok, "field_accuracy": round(ok / n, 4) if n else 1.0,
            "type_ok": sum(r["type_ok"] for r in rows), "gate_ok": sum(r["gate_ok"] for r in rows),
            "by_field": {k: f"{a}/{b}" for k, (a, b) in sorted(by_field.items())},
            "by_type": {k: f"{a}/{b}" for k, (a, b) in sorted(by_type.items())},
            "errors": [{"id": r["id"], "field": k, "truth": f["truth"], "got": f["got"]}
                       for r in rows for k, f in r["fields"].items() if not f["ok"]]
            + [{"id": r["id"], "field": "document_type", "got": "≠ " + r["type"]} for r in rows if not r["type_ok"]]
            + [{"id": r["id"], "field": "confidence (prag 0,8)", "got": r["confidence"]} for r in rows if not r["gate_ok"]],
            "notes": [f"{r['id']}: {n}" for r in rows for n in r["notes"]]}


def accuracy(only: list[str] | None = None) -> dict:
    """No LLM: the .extras.json on disk against expected_fields (tests/test_portfolio_documents.py uses it)."""
    rows, skipped = [], []
    for _, d in steps(only or []):
        ex = json.loads(portfolio.extras_file(d).read_text(encoding="utf-8"))
        if (ex.get("extractor") or {}).get("skipped"):
            skipped.append(f"{d['id']}: {ex.get('error')}")
            continue
        rows.append(score(d, ex))
    return {**report(rows), "not_extracted": skipped}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("only", nargs="*", help="clienți (P05) sau documente (P13-D6); implicit toate")
    ap.add_argument("--report", action="store_true", help="doar acuratețea extracțiilor deja salvate (fără LLM)")
    ap.add_argument("-j", "--jobs", type=int, default=portfolio.CONCURRENCY)
    args = ap.parse_args()
    if not args.report:
        bedrock_env()
        todo = steps(args.only)

        def one(cd):
            c, d = cd
            try:
                ex = portfolio.extract(d)
            except Exception as e:  # noqa: BLE001 - one failed call does not stop the others; rerun with its id
                print(f"  {d['id']}: EȘUAT {e}", flush=True)
                return
            portfolio.extras_file(d).write_text(json.dumps(ex, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"  {d['id']:7} {ex.get('document_type'):22} conf {ex.get('confidence')}  {d['file']}", flush=True)

        with ThreadPoolExecutor(max_workers=min(args.jobs, portfolio.CONCURRENCY)) as pool:
            list(pool.map(one, todo))
    r = accuracy(args.only)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
