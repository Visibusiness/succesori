"""The bank's portfolio of fictitious clients (task 084), next to Maria Ionescu: registries/portofoliu/P*.json.

Each file is one client: the core data (customer, products, movements, the heirs' KYC contacts) and the case history as
`steps`, in order: a document (`doc`) or an operator action (`op`: sign | approve | notifier).
090: a `doc` step is a real file in registries/portofoliu/documente/ (`file`: what the bank received, also the preview's
`raw_name` "portofoliu/<file>") with the reference values (`expected_type`, `expected_fields`, ground truth for the eval).
What the pipeline gets is NOT the reference: it is the real extraction of that file (agent/extract.py on the -scan.pdf,
after the file inspection of agent/guard.py, as the autopilot does), memoized in <stem>.extras.json by
scripts/portfolio_extract.py so that a reset stays fast and deterministic; PORTFOLIO_EXTRACT=1 extracts again, live.
A document with `"pending": true` has not come yet: the replay stops before it (it is not part of the stage, it has no
memoized extraction) and the guided demo (agent/ai_jobs.py CaseRunner) feeds it when the operator processes it: the
extractor reads its `file`, live.
`seed()` puts the clients in the mock core and replays the steps through the real path (the API's `_receive` = guard +
pipeline + deficiency check, and the operator endpoints), so every client lands in its stage
(`expected`, checked by tests/test_portfolio.py). After the steps, the contact ladder steps already due by AS_OF are
recorded as done on their day (history), so a freshly seeded bank has nothing overdue for the autopilot.
The stories are in registries/portofoliu/README.md.
"""
from __future__ import annotations

import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from agent import guard
from agent.core_mock import Bank, _movement_in, _product_in

DIR = Path(__file__).resolve().parent.parent / "registries" / "portofoliu"
DOCS = DIR / "documente"
RAW_PREFIX = "portofoliu/"     # agent/doc_preview.py resolves it to DOCS
CONCURRENCY = 10               # live extractions at once (Bedrock)
AS_OF = "2026-10-28"          # the portfolio's "today": the cases' clock counts from here (api._today)
HISTORY_BY = "istoric (portofoliu)"
_CORE_KEYS = ("iban", "loan_contract", "installment")


class Ops(Protocol):   # agent/api.py::_PortfolioOps
    def receive(self, doc: dict[str, Any], origin: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def sign_notary_answer(self, cid: str, signer: str, on: str) -> None: ...
    def approve(self, cid: str, approver: str, on: str) -> None: ...
    def notifier(self, cid: str, person: dict[str, Any], on: str) -> None: ...
    def anchor(self, cid: str, as_of: str) -> None: ...
    def contact_history(self, cid: str, by: str) -> list[str]: ...


def enabled_by_default() -> bool:
    """MVP_PORTFOLIO=0: an empty bank on the first start and on POST /demo/reset (pytest, coordonare/bin/live)."""
    return os.environ.get("MVP_PORTFOLIO", "1") != "0"


def clients() -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("P*.json"))]


def install(bank: Bank, client: dict[str, Any]) -> None:
    """The client in the mock core: customer (with its case number), products, IBANs, loan contracts, KYC contacts."""
    products = [_product_in({k: v for k, v in p.items() if k not in _CORE_KEYS}) for p in client["products"]]
    bank.add_customer({**client["customer"], "case_id": client["case_id"]}, products,
                      [_movement_in(m) for m in client.get("movements") or []],
                      ibans={p["iban"]: p["id"] for p in client["products"] if p.get("iban")},
                      loan_contracts={p["loan_contract"]: p["id"] for p in client["products"] if p.get("loan_contract")},
                      installments={p["id"]: p.get("installment") for p in client["products"] if p["type"] == "personal_loan"},
                      contacts=client.get("contacts"))


def received_file(step_doc: dict[str, Any]) -> Path:
    return DOCS / step_doc["file"]


def scan_file(step_doc: dict[str, Any]) -> Path:
    """The scan the extractor reads: <stem>-scan.pdf (for the DGEP line and the e-mail attachment, next to the .pdf)."""
    f = step_doc["file"]
    return DOCS / (f if f.endswith("-scan.pdf") else f.removesuffix(".pdf") + "-scan.pdf")


def extras_file(step_doc: dict[str, Any]) -> Path:
    return DOCS / (step_doc["file"].removesuffix(".pdf").removesuffix("-scan") + ".extras.json")


def extract(step_doc: dict[str, Any]) -> dict[str, Any]:
    """The real path for one portfolio file (agent/api.py::_upload, the autopilot): the file inspection first; a
    high-risk file never reaches the LLM (quarantine), otherwise agent/extract.py reads the scan. LLM (Bedrock)."""
    from agent.extract import extract_file
    report = guard.inspect(received_file(step_doc))
    meta = {"file": step_doc["file"], "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if report["risk"] == "high":
        return {"document_type": "unknown", "confidence": 0.0, "fields": {}, "guard": guard.summary(report),
                "error": "carantină: " + guard.reasons_ro(report["flags"]), "extractor": {"skipped": "guard", **meta}}
    path = scan_file(step_doc)
    doc = extract_file(path, path.name)
    doc.pop("raw_name", None)
    doc["guard"] = guard.summary(report)
    doc["extractor"] = {**doc.get("extractor", {}), "model_id": _model_id(doc), **meta, "read": path.name}
    return doc


def _model_id(doc: dict[str, Any]) -> str | None:
    alias = (doc.get("extractor") or {}).get("model")
    return os.environ.get(f"ANTHROPIC_DEFAULT_{str(alias).upper()}_MODEL") or alias


def live() -> bool:
    """PORTFOLIO_EXTRACT=1: every reset extracts the portfolio's files again (LLM, ~2 min), instead of the .extras.json."""
    return os.environ.get("PORTFOLIO_EXTRACT") == "1"


def _extract_all(clients_: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    docs = [s["doc"] for c in clients_ for s in history(c) if "doc" in s]

    def one(d: dict[str, Any]) -> dict[str, Any]:
        try:
            return extract(d)
        except Exception as e:  # noqa: BLE001 - one failed LLM call keeps the memoized extraction, and says so
            ex = json.loads(extras_file(d).read_text(encoding="utf-8"))
            ex["extractor"] = {**ex.get("extractor", {}), "live_failed": str(e)[:200]}
            return ex

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        return dict(zip([d["id"] for d in docs], pool.map(one, docs)))


def _document(step: dict[str, Any], extracted: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """What the pipeline receives: the extraction of the file (memoized or live), never the reference values."""
    d = step["doc"]
    ex = extracted[d["id"]] if extracted else json.loads(extras_file(d).read_text(encoding="utf-8"))
    doc = {k: copy.deepcopy(v) for k, v in ex.items() if k in guard.ENVELOPE_KEYS and k not in ("id", "raw_name", "received_on")}
    doc.update(id=d["id"], received_on=d["received_on"], raw_name=RAW_PREFIX + d["file"])
    return doc


def seed(bank: Bank, ops: Ops) -> list[dict[str, Any]]:
    """Every client of the portfolio, in its stage. Returns [{client, case_id, stage, contact_history}]."""
    all_clients = clients()
    for c in all_clients:
        install(bank, c)
    extracted = _extract_all(all_clients) if live() else None
    return [replay(c, ops, extracted) for c in all_clients]


def client_of(case_id: str) -> dict[str, Any] | None:
    return next((c for c in clients() if c["case_id"] == case_id), None)


def history(c: dict[str, Any]) -> list[dict[str, Any]]:
    """The steps done by the portfolio's date: every step before the first pending document."""
    out = []
    for step in c["steps"]:
        if step.get("pending"):
            break
        out.append(step)
    return out


def pending(c: dict[str, Any]) -> list[dict[str, Any]]:
    """The documents that have not come yet, in order (the guided demo's steps to run)."""
    return c["steps"][len(history(c)):]


def seed_one(bank: Bank, ops: Ops, client: dict[str, Any]) -> dict[str, Any]:
    """One client again, from its first step (POST /demo/reset?case=): the others are not touched."""
    install(bank, client)
    return replay(client, ops)


def replay(c: dict[str, Any], ops: Ops, extracted: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """The client's steps through the real path (documents, operator actions), then its contact history."""
    cid = c["case_id"]
    for step in history(c):
        if "doc" in step:
            r = ops.receive(_document(step, extracted))
            if r.get("case_id") not in (cid, "SC-NEIDENTIFICAT"):
                raise RuntimeError(f"portofoliu {c['id']}: documentul {step['doc']['id']} a ajuns în {r.get('case_id')}")
        elif step["op"] == "sign":
            ops.sign_notary_answer(cid, step["by"], step["on"])
        elif step["op"] == "approve":
            ops.approve(cid, step["by"], step["on"])
        elif step["op"] == "notifier":
            ops.notifier(cid, step["person"], step["on"])
        else:
            raise ValueError(f"portofoliu {c['id']}: pas necunoscut {step}")
    ops.anchor(cid, AS_OF)
    return {"client": c["id"], "case_id": cid, "stage": c["stage"], "contact_history": ops.contact_history(cid, HISTORY_BY)}
