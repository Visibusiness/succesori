"""HTTP API for the succession agent (contract: kb/tech/api-contract-bank.md §6 + ops-ui needs).

Run:  .venv/bin/uvicorn agent.api:app --reload --port 8000
UI:   http://localhost:8000/ui/  (serves ops-ui/ if present)
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import os
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from agent import contact_ladder, guard, rules
from agent import deficiencies, mailer, portfolio
from agent.case_state import Case
from agent.store import Store, default_path

from agent.core_mock import Bank
from agent.demo_documents import DOCUMENTS, VARIANT_B, scan_file
from agent.pipeline import Pipeline
from agent.trace import Trace

app = FastAPI(title="Agentul de Succesiune", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

bank = Bank()
pipeline = Pipeline(bank)
trace = Trace()


# Side data the pipeline does not keep, so GET /cases/{id} can follow kb/tech/ops-ui-contract.md without touching
# pipeline.py: the extractor output per document (field_confidence, evidence, validation) and the date of the
# document that triggered each event (events.at = document date, not processing time).
_extractions: dict[str, dict[str, Any]] = {}
_event_dates: dict[str, list[str | None]] = {}
_received: dict[str, dict[str, Any]] = {}
_manual = {"on": False}                      # guided demo step by step: the autopilot pauses (agent/ai_jobs.py)   # raw_name -> the last result for that file (guided demo, "scanned" mode)


from agent import handoffs as handoff_table  # noqa: E402


def _receive(doc: dict[str, Any], origin: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every document goes through here so the run trace is complete (audit + retro-learner). `origin` (078): the case
    the file was uploaded for, the upload link's person, the file text and page count (for the deficiency check).
    089: the sync endpoints run in a thread pool; `pipeline.lock` keeps one document (pipeline + trace) at a time."""
    with pipeline.lock:
        return _receive_locked(doc, origin)


def _receive_locked(doc: dict[str, Any], origin: dict[str, Any] | None) -> dict[str, Any]:
    doc.setdefault("id", f"doc-{sum(len(c.documents) for c in pipeline.cases.values()) + 1}")
    _extractions[doc["id"]] = doc
    sender_before = _sender_context(doc, origin)   # before the pipeline: "the last message" means before this document
    before = {cid: len(c.events) for cid, c in pipeline.cases.items()}
    result = pipeline.receive(doc)
    for cid, c in pipeline.cases.items():
        dates = _event_dates.setdefault(cid, [])
        dates.extend([None] * (before.get(cid, 0) - len(dates)))
        dates.extend([doc.get("received_on")] * (len(c.events) - len(dates)))
    trace.document(doc, result)
    _deficiency_check(doc, result, origin or {}, sender_before)
    case = pipeline.cases.get(result.get("case_id"))
    if case is not None:
        trace.snapshot_case(case.to_dict())
    # what the autopilot will hand to which agent (same table as scripts/autopilot.py)
    result["handoffs_planned"] = handoff_table.describe(result, {"heirs": case.heirs} if case is not None else None)
    if doc.get("raw_name"):
        _received[doc["raw_name"]] = {**result, "document_id": doc["id"]}
    return result


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


ORPHAN_ID = "SC-NEIDENTIFICAT"   # pipeline's collector for documents that match no customer
MILESTONE_STATE = {"death_signalled": "DEATH_SIGNALLED", "frozen": "FROZEN", "notary_answered": "NOTARY_ANSWERED",
                   "insurance_claim_open": "INSURANCE_CLAIM_OPEN", "insurance_settled": "INSURANCE_SETTLED",
                   "certificate_received": "HEIR_CERT_RECEIVED", "supplement_requested": "SUPPLEMENT_REQUESTED",
                   "payment_plan_ready": "PLAN_DRAFTED", "payment_pending_approval": "PAYMENT_PENDING_APPROVAL",
                   "paid": "PAID"}
DEADLINE_NAMES = {"succession_option": "Termen opțiune succesorală", "insurance_claim_notice": "Avizare daună asigurător",
                  "notary_answer": "Răspuns către notar (înainte de dezbatere)"}
PRODUCT_LABELS = {"current_account": "Cont curent", "term_deposit": "Depozit la termen", "personal_loan": "Credit",
                  "credit_card": "Card de credit"}
BLOCK_REASONS = {"minor_requires_representation": "minor: lipsesc documentele de reprezentare legală"}


def _payment_id(case_id: str) -> str:
    return f"PAY-{case_id}"


def _case_id_from(pid: str) -> str:
    """Accepts PAY-<case>, PP-<case> (old ids) or the case id itself."""
    return pid.removeprefix("PAY-").removeprefix("PP-")


_clock = {"offset_days": 0}   # POST /demo/advance-clock (DEMO_MODE only): shows the contact ladder without waiting months
_anchor: dict[str, str] = {}   # case -> the portfolio's "today" (registries/portofoliu): its documents are older than that


def _today(c) -> date:
    """Demo clock: the date of the latest document in the case (the demo runs in 2026), plus the demo offset. A case of
    the seeded portfolio counts from the portfolio's date (agent/portfolio.py AS_OF) if that is later."""
    days = [d.received_on for d in c.documents if d.received_on] + ([_anchor[c.id]] if c.id in _anchor else [])
    return (date.fromisoformat(max(days)) if days else date.today()) + timedelta(days=_clock["offset_days"])


def _deadline_status(c, code: str, due: date) -> str:
    # the answer to the notary counts only once it is signed (a draft waiting for a signature is still open)
    done = {"notary_answer": "notary_answer_signed" in c.milestones,
            "insurance_claim_notice": "insurance_claim_open" in c.milestones or bool(c.insurance.get("claim_open")),
            "succession_option": "paid" in c.milestones}.get(code, False)
    if done:
        return "îndeplinit"
    return "depășit" if due < _today(c) else "deschis"


def _products(c) -> list[dict[str, Any]]:
    if c.cif not in bank.customers or c.date_of_death is None:
        return []
    out = []
    raw = {p.id: p for p in bank.products(c.cif)}
    for v in rules.balance_at_death(raw.values(), c.date_of_death):
        p = raw[v.product_id]
        item = {"id": v.product_id, "type": v.type, "label": PRODUCT_LABELS.get(v.type, v.type),
                "accrued_interest": v.accrued_interest}
        if v.type == "current_account":
            item["balance"] = v.principal
        elif v.type == "term_deposit":
            item.update(principal=v.principal, maturity=p.maturity.isoformat() if p.maturity else None)
        else:
            item.update(outstanding=v.principal, insurance=p.insurance_policy_id)
            if c.insurance.get("paid"):
                item["insurance_settled"] = c.insurance["paid"]
        out.append(item)
    return out


def _document(d) -> dict[str, Any]:
    ext = _extractions.get(d.id, {})
    fc, ev = ext.get("field_confidence") or {}, ext.get("evidence") or {}
    g = guard.verdict(ext) if ext else {"risk": "low", "flags": []}
    return {"document_id": d.id, "document_type": d.type, "received_at": d.received_on, "source": d.raw_name or "",
            "confidence": d.confidence, "legibility": "illegible" if d.confidence < 0.8 else "ok",
            "validation": ext.get("validation"), "quarantined": d.type == "quarantined",
            "guard": {"risk": g["risk"], "flags": [f for f in g["flags"] if guard.RISK_ORDER.get(f.get("severity"), 0) >= 1],
                      "declared_type": ext.get("document_type")},
            "fields": [{"name": k, "value": v, "confidence": fc.get(k), "evidence": ev.get(k)} for k, v in d.fields.items()],
            **_deficiency_view(d.id)}


def _plan(c) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    p = c.payment_plan
    if not p:
        return None, []
    heirs = {h["id"]: h for h in c.heirs}
    due = {}
    for l in p["lines"]:
        for tok in (l.get("blocked_reason") or "").split():
            if len(tok) >= 10 and tok[:4].isdigit() and tok[4] == "-":
                due[l["product_id"]] = tok[:10]
    lines = [{"line_id": f"L{i + 1}", "heir_id": l["heir_id"], "name": l["name"], "share": l["fraction_of_product"],
              "product_id": l["product_id"], "amount": l["amount"], "blocked": l["blocked_reason"] is not None,
              "blocked_reason": BLOCK_REASONS.get(l["blocked_reason"], l["blocked_reason"]),
              "minor": bool(heirs.get(l["heir_id"], {}).get("minor")), "pay_on": due.get(l["product_id"], "acum")}
             for i, l in enumerate(p["lines"])]
    testament = any(d.type == "heir_certificate" and d.fields.get("testament") for d in c.documents)
    plan = {"plan_id": p["id"], "status": p["status"], "variant": "B" if testament else "A",
            "variant_label": "4B — testament" if testament else "4A — moștenire legală", "lines": lines,
            "withheld": [{**w, "label": "Pensie necuvenită — retur CNPP" if w["reason"] == "pension_return_CNPP" else w["reason"]}
                         for w in p.get("withheld", [])],
            "net_account": p.get("net_account"), "warnings": []}
    free = [l for l in lines if not l["blocked"]]
    payment = {"payment_id": _payment_id(c.id), "plan_id": p["id"], "status": p["status"],
               "line_ids": [l["line_id"] for l in free], "total": sum(l["amount"] for l in free)}
    return plan, [payment]


def _case_view(c) -> dict[str, Any]:
    """GET /cases/{id} in the shape of kb/tech/ops-ui-contract.md."""
    dates = _event_dates.get(c.id, [])
    events = [{"id": getattr(e, "id", None) or f"E{i + 1}", "at": (dates[i] if i < len(dates) and dates[i] else e.at), "processed_at": e.at, "kind": e.kind,
               "action": {"document": "Document", "action": "Acțiune", "escalation": "Escaladare", "decision": "Decizie"}.get(e.kind, e.kind),
               "detail": e.summary, "rule": e.rule, "document_id": e.data.get("document_id"), "data": e.data}
              for i, e in enumerate(c.events)]
    customer = bank.customers.get(c.cif, {})
    plan, payments = _plan(c)
    return {"case_id": c.id, "id": c.id, "kind": "unmatched" if c.id == ORPHAN_ID else "case", "cif": c.cif,
            "state": c.state(),
            "deceased": {"name": c.customer_name, "cif": c.cif, "cnp": customer.get("cnp"),
                         "date_of_death": c.date_of_death.isoformat() if c.date_of_death else None},
            "opened_at": events[0]["at"] if events else None, "updated_at": events[-1]["at"] if events else None,
            "state_history": [{"state": MILESTONE_STATE[m]} for m in rules_order(c.milestones)],
            "products_as_of": c.date_of_death.isoformat() if c.date_of_death else None, "products": _products(c),
            "heirs": c.heirs, "documents": [_document(d) for d in c.documents], "events": events,
            "deadlines": [{"code": d["code"], "name": DEADLINE_NAMES.get(d["code"], d["code"]), "date": d["due"],
                           "rule": d["basis"], "hypothesis": d.get("hypothesis", False), "status": _deadline_status(c, d["code"], date.fromisoformat(d["due"]))}
                          for d in c.deadlines],
            "open_tasks": c.missing(), "missing": c.missing(),
            "escalations": [{"id": e.id, "code": e.reason, "reason": e.detail, "document_id": e.document_id,
                             "status": "închis" if e.resolved else "deschis", "severity": e.data.get("severity"),
                             "flags": e.data.get("flags") or [], "quarantined": bool(e.data.get("quarantined"))}
                            for e in c.escalations],
            "payment_plan": plan, "payments": payments, "flags": c.flags, "contact_channels": c.contact_channels,
            "deficiencies": [_deficiency_public(r) for r in _deficiency_records(c.id) if r["problems"]]}


def rules_order(milestones: set[str]) -> list[str]:
    order = list(MILESTONE_STATE)
    return sorted((m for m in milestones if m in MILESTONE_STATE), key=order.index)


@app.get("/cases")
def list_cases() -> list[dict[str, Any]]:
    """Queue; `id` is kept as an alias of `case_id` for older consumers. `kind=unmatched` is the collector of
    documents that match no customer (shown in ops-ui as escalations without a case)."""
    return [{"case_id": c.id, "id": c.id, "kind": "unmatched" if c.id == ORPHAN_ID else "case", "cif": c.cif,
             "customer_name": c.customer_name, "deceased": {"name": c.customer_name, "cif": c.cif,
             "date_of_death": c.date_of_death.isoformat() if c.date_of_death else None},
             "state": c.state(), "date_of_death": c.date_of_death.isoformat() if c.date_of_death else None,
             "updated_at": _case_view(c)["updated_at"], "documents": len(c.documents),
             "open_escalations": sum(not e.resolved for e in c.escalations), "missing": c.missing(),
             "portfolio": c.id in _anchor}
            for c in pipeline.cases.values()]


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    if case_id not in pipeline.cases:
        raise HTTPException(404, "dosar inexistent")
    return _case_view(pipeline.cases[case_id])


@app.get("/escalations")
def list_unmatched(unmatched: bool = True) -> list[dict[str, Any]]:
    """Documents that match no customer, as escalations without a case (doc 7)."""
    c = pipeline.cases.get(ORPHAN_ID)
    if not c:
        return []
    docs = {d.id: _document(d) for d in c.documents}
    return [{**docs.get(e.document_id, {"document_id": e.document_id, "fields": []}), "case_id": ORPHAN_ID,
             "escalation_id": e.id, "reason": e.detail, "rule": e.reason, "status": "închis" if e.resolved else "deschis",
             "severity": e.data.get("severity"), "flags": e.data.get("flags") or [],
             "agent_action": ("Carantină: documentul nu a produs nicio acțiune; îl verifică un operator la sursă"
                              if e.data.get("quarantined") else "Escaladare; nicio acțiune automată asupra vreunui client")}
            for e in c.escalations]


@app.post("/documents")
def post_document(doc: dict[str, Any]) -> dict[str, Any]:
    """A document already extracted (JSON). The LLM extractor posts here. 076: the pipeline quarantines it if the
    file inspection (`guard`, set by the autopilot) or the extracted fields say so; the JSON is kept as evidence."""
    _check_document(doc)
    result = _receive(doc)
    if result.get("quarantined") and not doc.get("_quarantine_stored"):
        _quarantine_file(doc.get("raw_name") or doc["id"], json.dumps(doc, ensure_ascii=False, indent=1, default=str).encode(),
                         doc.get("guard") or result.get("guard") or {}, json_doc=True)
    return result


def _quarantine_file(name: str, data: bytes, report: dict[str, Any], json_doc: bool = False) -> str | None:
    """Evidence for the operator in registries/inbox/quarantine/ (never fatal: the decision is already taken)."""
    try:
        stem = name + ".extras.json" if json_doc and not name.endswith(".json") else name
        return str(guard.quarantine_store(stem, data, report).name)
    except OSError:
        return None


def _check_document(doc: Any) -> None:
    """Shape of an extracted document: a bad one is the caller's error (422), never a 500 inside the pipeline."""
    if not isinstance(doc, dict):
        raise HTTPException(422, "documentul trebuie să fie un obiect JSON")
    if not isinstance(doc.get("fields", {}), dict):
        raise HTTPException(422, "`fields` trebuie să fie un obiect")
    try:
        float(doc.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        raise HTTPException(422, "`confidence` trebuie să fie un număr între 0 și 1")


@app.post("/cases/{case_id}/documents")
async def upload_document(case_id: str, file: UploadFile = File(...), document_type: str = Form("auto")) -> dict[str, Any]:
    """Upload a raw file. JSON files are taken as extracted; .md/.txt go through the extractor
    (LLM, see agent.extract) when available, else they are escalated as unreadable."""
    return await _upload(case_id, file, document_type, {"case_id": case_id, "via": "case_upload"})


async def _upload(case_id: str, file: UploadFile, document_type: str, origin: dict[str, Any]) -> dict[str, Any]:
    raw = await file.read(guard.MAX_BYTES + 1)
    name = file.filename or "upload"
    # 076: the gate runs BEFORE the extractor; a high-risk file never reaches the LLM
    report = guard.inspect(raw, name)
    origin = {**origin, "text": report.get("sanitized_text") or "", "page_count": report.get("pages"),
              "sha": hashlib.sha256(raw).hexdigest()[:16]}
    if report["risk"] == "high":
        doc = {"document_type": "unknown", "confidence": 0.0, "fields": {}, "raw_name": name, "guard": guard.summary(report),
               "error": "carantină: " + guard.reasons_ro(report["flags"])}
        result = _receive(doc, origin)
        result["quarantine_file"] = _quarantine_file(name, raw, report)
        return result
    if name.endswith(".json"):
        try:
            doc = json.loads(raw)
        except ValueError as e:
            raise HTTPException(422, f"JSON invalid: {e}")
        _check_document(doc)
    else:
        try:
            from agent.extract import extract
            doc = extract(report["sanitized_text"], name, hint=document_type)
        except Exception as e:  # extractor unavailable -> escalate, never guess
            doc = {"document_type": "unknown", "confidence": 0.0, "fields": {}, "raw_name": name, "error": str(e)}
    doc.setdefault("raw_name", name)
    if not name.endswith(".json"):   # 078: received now; a date the extractor read is not the date it reached the bank
        doc["received_on"] = date.today().isoformat()
    doc["guard"] = guard.summary(report)   # ours, whatever the file said
    result = _receive(doc, origin)
    if result.get("quarantined"):
        result["quarantine_file"] = _quarantine_file(name, raw, {**report, "extracted": doc.get("injection_suspected")})
    return result


@app.post("/payments/{plan_id}/approve")
def approve(plan_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Human approval (ops_approver). Accepts the payment id (PAY-<case>) or the old plan id (PP-<case>)."""
    case_id = _case_id_from(plan_id)
    if case_id not in pipeline.cases:
        raise HTTPException(404, "plan inexistent")
    try:
        plan = pipeline.approve_payment(case_id, (body or {}).get("approver", "ops_approver"))
    except ValueError as e:
        raise HTTPException(409, str(e))
    trace.operator("approve_payment", case_id=case_id, plan_id=plan_id, approver=plan["approved_by"])
    trace.snapshot_case(pipeline.cases[case_id].to_dict())
    return plan


@app.post("/payments/{plan_id}/reject")
def reject(plan_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Operator rejects the plan with a reason: the reason is a lesson for retro-learner."""
    case_id = _case_id_from(plan_id)
    case = pipeline.cases.get(case_id)
    if not case or not case.payment_plan:
        raise HTTPException(404)
    note = (body or {}).get("reason") or (body or {}).get("note", "")
    if not note.strip():
        raise HTTPException(422, "motivul respingerii e obligatoriu")
    if case.payment_plan["status"] != "pending_approval":
        raise HTTPException(409, f"planul e deja {case.payment_plan['status']}")
    case.payment_plan["status"] = "rejected"
    case.milestones.discard("payment_pending_approval")
    case.log("decision", f"Plan de plată respins de operator: {note}")
    trace.operator("reject_payment", case_id=case_id, note=note, plan=case.payment_plan)
    return {"payment_id": _payment_id(case_id), "status": "rejected"}


@app.post("/operator/feedback")
def operator_feedback(body: dict[str, Any]) -> dict[str, str]:
    """Free-form correction from the operator (wrong extraction, wrong wording, missing rule).
    Lands in runs/<run>/operator.jsonl and feeds the learning loop (scripts/retro.py)."""
    trace.operator("feedback", **body)
    return {"status": "recorded"}


@app.post("/cases/{case_id}/letters/notary/sign")
def sign_notary_answer(case_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """The operator signs the draft answer to the notary: only now the `notary_answer` deadline is met. Body: {signer}."""
    case = pipeline.cases.get(case_id)
    if not case:
        raise HTTPException(404, "dosar inexistent")
    signer = ((body or {}).get("signer") or "").strip()
    if not signer:
        raise HTTPException(422, "numele semnatarului e obligatoriu")
    if "notary_answered" not in case.milestones:
        raise HTTPException(409, "nu există un răspuns către notar de semnat")
    if "notary_answer_signed" not in case.milestones:   # idempotent: a second click changes nothing
        case.milestones.add("notary_answer_signed")
        case.log("action", f"Răspunsul către notar semnat de {signer}; termenul „Răspuns către notar” e îndeplinit.",
                 rule="Legea 36/1995 art. 81 alin. 2", signer=signer)
        trace.operator("sign_notary_answer", case_id=case_id, signer=signer)
        trace.snapshot_case(case.to_dict())
    return {"case_id": case_id, "signed": True, "signer": signer,
            "deadline": next((d["status"] for d in _case_view(case)["deadlines"] if d["code"] == "notary_answer"), None)}


@app.post("/cases/{case_id}/freeze/confirm")
def confirm_freeze(case_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Operator makes a reversible block definitive (D-DGEP). Body: {operator}."""
    if case_id not in pipeline.cases:
        raise HTTPException(404, "dosar inexistent")
    operator = ((body or {}).get("operator") or "").strip()
    if not operator:
        raise HTTPException(422, "numele operatorului e obligatoriu")
    try:
        result = pipeline.confirm_freeze(case_id, operator)
    except ValueError as e:
        raise HTTPException(409, str(e))
    trace.operator("confirm_freeze", case_id=case_id, operator=operator)
    return result


@app.post("/escalations/{case_id}/{esc_id}/resolve")
def resolve(case_id: str, esc_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    case = pipeline.cases.get(case_id)
    if not case:
        raise HTTPException(404)
    for e in case.escalations:
        if e.id == esc_id:
            e.resolved = True
            note = (body or {}).get("note", "")
            case.log("decision", f"Escaladarea {esc_id} rezolvată de operator: {note}")
            trace.operator("resolve_escalation", case_id=case_id, escalation=e.__dict__, note=note)
            return {"resolved": esc_id}
    raise HTTPException(404)


@app.get("/audit")
def audit() -> list[dict[str, Any]]:
    return bank.audit


# ---- 033: messages to heirs (mock outbox) and secure upload links
CHANNELS = {"email": None, "app": 120, "sms": 300, "whatsapp": 300}   # max characters (None = no limit)
# .claude/skills/heir-messaging/SKILL.md. Operational messages (about the case) rest on GDPR art. 6(1)(b)/(c)/(f)
# and need no marketing consent; Legea 506/2004 consent applies only to commercial ones (DECISIONS, 034).
TEMPLATE_KIND = {"MISSING_DOCS_FIRST": "operational", "MISSING_DOCS_REMINDER": "operational",
                 "SUPPLEMENT_NEEDED": "operational", "MINOR_REPRESENTATION": "operational",
                 "PLAN_APPROVED": "operational", "DEADLINE_SOON": "operational",
                 "DOCUMENT_DEFICIENT": "operational"}
TOKEN_DAYS = 7
_tokens: dict[str, dict[str, Any]] = {}


def _outbox() -> Path:
    return trace.dir / "outbox.jsonl"   # runs/<run>/outbox.jsonl (runs/latest points here)


def _new_token(case_id: str, to: str | None = None, asked_types: list[str] | None = None) -> dict[str, Any]:
    tok = secrets.token_urlsafe(24)
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    # `to` and `asked_types` (078): whoever uploads through this link is that person, asked for these documents
    asked = pipeline.cases[case_id].missing() if case_id in pipeline.cases else []
    _tokens[tok] = {"case_id": case_id, "to": to, "expires_at": exp.isoformat(timespec="seconds"),
                    "asked_types": asked_types or deficiencies.expected_types(asked)}
    return {"token": tok, "case_id": case_id, "expires_at": _tokens[tok]["expires_at"], "url": f"/upload?token={tok}"}


def _token_case(token: str) -> str:
    t = _tokens.get(token)
    if not t or datetime.fromisoformat(t["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(403, "link invalid sau expirat")
    if t["case_id"] not in pipeline.cases:
        raise HTTPException(404, "dosar inexistent")
    return t["case_id"]


@app.post("/cases/{case_id}/upload-token")
def upload_token(case_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """A link the heir can use for 7 days to upload documents for this case only."""
    if case_id not in pipeline.cases:
        raise HTTPException(404, "dosar inexistent")
    return _new_token(case_id, (body or {}).get("to"))


@app.post("/messages")
def send_message(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Mock delivery: validates and appends to runs/latest/outbox.jsonl; nothing is really sent.
    {case_id, to, channel: email|sms|whatsapp|app, template_id, body}. `{{UPLOAD_URL}}` and `{{token}}` in the
    body are replaced with a fresh 7-day upload link."""
    case = pipeline.cases.get(body.get("case_id", ""))
    if not case:
        raise HTTPException(404, "dosar inexistent")
    channel, text, to = body.get("channel"), body.get("body") or "", (body.get("to") or "").strip()
    if channel not in CHANNELS:
        raise HTTPException(422, f"canal necunoscut: {channel}; permise: {', '.join(CHANNELS)}")
    if not to or not body.get("template_id"):
        raise HTTPException(422, "to și template_id sunt obligatorii")
    kind = TEMPLATE_KIND.get(body["template_id"], body.get("kind", "commercial"))
    if kind == "commercial" and body.get("consent") is not True:
        raise HTTPException(422, "mesaj comercial fără consimțământ (Legea 506/2004); agentul trimite doar mesaje operaționale")
    known = {h.get("name", "").lower() for h in case.heirs} | {h.get("id", "").lower() for h in case.heirs}
    drec = _deficiency_for_message(case, to, body)   # 078: the sender of a deficient document is a person of the case
    uploader = body.get("to_role") == "uploader" and \
        contact_ladder._name_key(to) in {contact_ladder._name_key(n) for n in _open_senders(case.id)}
    if case.heirs and to.lower() not in known and body.get("to_role") not in ("legal_representative", "notifier") \
            and not drec and not uploader:
        raise HTTPException(422, f"{to} nu e o persoană din dosar (moștenitor, reprezentant legal sau cine a notificat)")
    problems = _output_problems(case, text, str(request.base_url))
    if problems:
        esc = _unsafe_output(case, "message", f"mesaj către {to} ({body['template_id']})", problems)
        raise HTTPException(422, f"mesajul nu pleacă: {guard.reasons_ro(problems)} (escaladare {esc.id}, unsafe_output)")
    link = None
    if "{{token}}" in text or "{{UPLOAD_URL}}" in text:
        link = _new_token(case.id, to, deficiencies.asked_types(drec) if drec else None)
        base = str(request.base_url).rstrip("/")
        text = (text.replace("{{UPLOAD_URL}}/cases/" + case.id + "/upload?token={{token}}", base + link["url"])
                    .replace("{{UPLOAD_URL}}", base).replace("{{token}}", link["token"]))
    limit = CHANNELS[channel]
    if limit and len(text) > limit:
        raise HTTPException(422, f"mesajul are {len(text)} caractere; limita pe {channel} e {limit}")
    msg = {"message_id": f"MSG-{secrets.token_hex(4)}", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "case_id": case.id, "to": to, "channel": channel, "template_id": body["template_id"], "kind": kind, "body": text,
           "upload_token_expires_at": link["expires_at"] if link else None, "status": "queued_mock",
           "case_date": _today(case).isoformat()}   # the demo clock date: the contact ladder counts from it
    # the guided demo addresses every message to its one demo mailbox (agent/ai_jobs.py DEMO_EMAIL); never outside DEMO_MODE
    address = (body.get("address") if os.environ.get("DEMO_MODE") == "1" and channel == "email" else None) \
        or _person_address(case, to, channel)
    if drec:
        msg["deficiency"] = {"document_id": drec["document_id"], "problems": [p["key"] for p in _pending(drec)]}
    try:
        sent = _mailer().send({**msg, "address": address} if address else msg)
    except ValueError as e:   # MAILER misconfigured: nothing leaves, nothing is recorded as sent
        raise HTTPException(503, f"livrarea mesajelor e configurată greșit: {e}")
    except OSError as e:
        raise HTTPException(502, f"livrarea a eșuat: {e}")
    msg["status"] = sent.get("status", msg["status"])
    if drec:
        _mark_notified(case, drec, msg)
    case.log("action", f"Mesaj către {to} pe {channel} ({body['template_id']}), în outbox (mock).",
             rule="heir-messaging: șablon aprobat, destinatar din dosar; fără date financiare pe SMS/WhatsApp")
    return msg


def _case_ibans(case) -> set[str]:
    out = {i for d in case.documents if d.type != "quarantined" for i in (d.fields.get("ibans") or []) if isinstance(i, str)}
    if case.cif in bank.customers:
        out |= {iban for iban, pid in bank._ibans.items() if pid in {p.id for p in bank.products(case.cif)}}
    return out


def _case_cnps(case) -> set[str]:
    out = {bank.customers.get(case.cif, {}).get("cnp")}
    out |= {h.get("cnp") for h in case.heirs if h.get("cnp")}
    out |= {d.fields.get("cnp") for d in case.documents if d.type != "quarantined" and isinstance(d.fields.get("cnp"), str)}
    out |= {h.get("cnp") for d in case.documents if d.type != "quarantined"
            for h in (d.fields.get("heirs") or []) if isinstance(h, dict) and isinstance(h.get("cnp"), str)}
    # a CNP quoted in the evidence of a document of the case is case data, even when the extractor left the field empty
    out |= {m.group(0) for d in case.documents if d.type != "quarantined"
            for s in guard._strings((_extractions.get(d.id) or {}).get("evidence")) for m in guard.CNP_RE.finditer(s)}
    return {c for c in out if c}


def _output_problems(case, text: str, base_url: str = "", kind: str = "message") -> list[dict[str, str]]:
    base = base_url.rstrip("/")
    allowed = [f"{base}/upload?token=", f"{base}/cases/{case.id}/upload?token="] if base else []
    return guard.check_output(text, _case_ibans(case), _case_cnps(case), allowed, kind=kind)


def _unsafe_output(case, kind: str, what: str, problems: list[dict[str, str]]):
    esc = case.escalate("unsafe_output", f"Textul agentului ({what}) a fost oprit înainte de salvare/trimitere: "
                                         f"{guard.reasons_ro(problems)}. Un operator îl verifică; nimic nu a plecat.",
                        data={"severity": "blocking", "flags": problems, "kind": kind})
    trace.snapshot_case(case.to_dict())
    return esc


@app.post("/cases/{case_id}/output-check")
def output_check(case_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
    """076: the autopilot asks before it saves a letter / investigation / message an agent wrote. {text, kind, key}.
    Not ok ⇒ escalation `unsafe_output` in the case and the text does not leave."""
    case = pipeline.cases.get(case_id)
    if not case:
        raise HTTPException(404, "dosar inexistent")
    problems = _output_problems(case, str(body.get("text") or ""), str(request.base_url), str(body.get("kind") or "text"))
    if not problems:
        return {"ok": True, "problems": []}
    esc = _unsafe_output(case, str(body.get("kind") or "text"), str(body.get("key") or body.get("kind") or "text"), problems)
    return {"ok": False, "problems": problems, "escalation": esc.id}


@app.get("/messages")
def list_messages(case_id: str | None = None) -> list[dict[str, Any]]:
    if not _outbox().exists():
        return []
    msgs = [json.loads(l) for l in _outbox().read_text(encoding="utf-8").splitlines() if l.strip()]
    return [m for m in msgs if not case_id or m["case_id"] == case_id]


_UPLOAD_PAGE = """<!doctype html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Încărcare documente</title>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:40px auto;padding:0 16px;color:#1d2433}}
.box{{border:1px solid #e3e6eb;border-radius:8px;padding:16px}} button{{background:#ffe600;border:1px solid #e0c900;
border-radius:6px;padding:8px 14px;font-weight:600}} .muted{{color:#667085;font-size:13px}}</style></head><body>
<h1>Încărcare documente</h1><div class="box">{content}</div>
<p class="muted">Linkul e personal și expiră pe {expires}. Nu afișăm sume sau alte date din dosar.</p></body></html>"""


@app.get("/upload", response_class=HTMLResponse)
def upload_page(token: str) -> str:
    """Public page for the heir: shows only what is missing (allowed by bank secrecy) and an upload form."""
    case = pipeline.cases[_token_case(token)]
    missing = "".join(f"<li>{html.escape(m)}</li>" for m in case.missing()) or "<li>Nimic, momentan.</li>"
    content = (f"<p>Dosar {html.escape(case.id)}. Banca mai are nevoie de:</p><ul>{missing}</ul>"
               f'<form method="post" enctype="multipart/form-data" action="/upload?token={html.escape(token)}">'
               '<p><input type="file" name="file" required></p><button type="submit">Trimite</button></form>')
    return _UPLOAD_PAGE.format(content=content, expires=html.escape(_tokens[token]["expires_at"][:10]))


@app.post("/upload", response_class=HTMLResponse)
async def upload_by_token(token: str, file: UploadFile = File(...)) -> str:
    """The heir's upload lands in POST /cases/{id}/documents (same extraction + pipeline path)."""
    case_id = _token_case(token)
    if (file.filename or "").lower().endswith(".json"):
        # a .json is taken as ALREADY EXTRACTED by POST /cases/{id}/documents: from a public link it would let anyone
        # with the link settle a loan or change shares (QA 2026-10-28). The heir sends scans / photos / PDFs only.
        raise HTTPException(415, "Prin link se încarcă doar documente (PDF, imagine, text), nu fișiere JSON.")
    t = _tokens[token]
    result = await _upload(case_id, file, "auto", {"case_id": case_id, "via": "upload_token", "token_to": t.get("to"),
                                                   "expected_types": t.get("asked_types") or []})
    trace.operator("heir_upload", case_id=case_id, file=file.filename, result=result)
    return _UPLOAD_PAGE.format(content="<p>Am primit documentul. Vă anunțăm pe canalul ales ce urmează.</p>",
                               expires=html.escape(_tokens[token]["expires_at"][:10]))


# ---- demo controls
@app.post("/demo/reset")
def demo_reset(variants: str = "pensie", inbox: bool = False, manual: bool = False, gol: bool = False,
               portofoliu: bool | None = None, case: str | None = None) -> dict[str, Any]:
    """variants: comma list from core_mock.VARIANTS ('pensie' = October pension arrives, default;
    'retragere' = Andrei withdraws 1.000 lei after the death). Empty string = neither.
    084: the bank's portfolio (registries/portofoliu/, agent/portfolio.py) is seeded again, each client in its stage,
    and Maria Ionescu starts from zero (SC-2026-0001 on her first document). gol=1: an empty bank (only Maria in core,
    no case), e.g. for scripts/smoke_e2e.py. MVP_PORTFOLIO=0 (pytest, coordonare/bin/live) makes the empty bank the
    default; portofoliu=1 asks for the portfolio anyway.
    manual=true: the guided demo runs step by step (agent/ai_jobs.py): the autopilot pauses until the next reset.
    Also a clean run: the run's artifacts (letters, messages, audit, outbox, autopilot status) are cleared, runs/latest
    points to this run and the epoch changes, so the autopilot drops its dedupe state. inbox=true also moves
    registries/inbox (waiting, processed, failed) to registries/inbox/.archive/<stamp>/.
    case=<id>: only that case starts again (Maria from zero; a portfolio client from its first step, back in its stage),
    with its guided-demo steps; every other case, the run and its artifacts stay as they are."""
    if case:
        return _reset_case(case, manual)
    try:
        bank.reset({v.strip() for v in variants.split(",") if v.strip()})
    except ValueError as e:
        raise HTTPException(422, str(e))
    pipeline.cases.clear()
    _extractions.clear()
    _event_dates.clear()
    _received.clear()
    _tokens.clear()
    _contact_done.clear()
    _notifiers.clear()
    _deficiency.clear()
    _notified.clear()
    _clock["offset_days"] = 0
    _anchor.clear()
    _manual["on"] = manual
    _ai_jobs.reset_all()
    archived = _archive_inbox() if inbox else None
    trace.reset(variants=sorted(bank.variants), inbox_archived=archived)
    seeded = portfolio.seed(bank, _PortfolioOps()) if (not gol and (portofoliu if portofoliu is not None
                                                                    else portfolio.enabled_by_default())) else []
    return {"status": "reset", "variants": sorted(bank.variants), "run_dir": str(trace.dir), "epoch": trace.epoch,
            "inbox_archived": archived, "manual": manual, "portfolio": [s["case_id"] for s in seeded]}


@app.post("/demo/ai/manual")
def demo_manual() -> dict[str, Any]:
    """The guided demo goes step by step without resetting anything: the autopilot pauses until the next global
    reset (a case of the portfolio continues where it is; POST /demo/reset?case=<id>&manual=true starts one again)."""
    _manual["on"] = True
    return {"manual": True}


def _reset_case(cid: str, manual: bool) -> dict[str, Any]:
    client = None if cid == _ai_jobs.DEMO_CASE else portfolio.client_of(cid)
    if cid != _ai_jobs.DEMO_CASE and client is None:
        raise HTTPException(404, f"dosarul {cid} nu e nici al Mariei, nici din portofoliu")
    cif = client["customer"]["cif"] if client else "RC1001"
    case = pipeline.cases.pop(cid, None)
    doc_ids = {d.id for d in case.documents} if case else set()
    if client is None:   # Maria's documents (her step 7, the illegible certificate, lands in the unmatched collector)
        doc_ids |= {d["id"] for d in DOCUMENTS} | {VARIANT_B["id"]}
    else:                # a client's photo that matched nobody (P01) is in the collector too
        doc_ids |= {st["doc"]["id"] for st in client["steps"] if "doc" in st}
    orphan = pipeline.cases.get(ORPHAN_ID)
    if orphan:
        orphan.documents = [d for d in orphan.documents if d.id not in doc_ids]
        orphan.escalations = [e for e in orphan.escalations if e.document_id not in doc_ids]
    for k in doc_ids:
        _extractions.pop(k, None)
        _deficiency.pop(k, None)
    for side in (_event_dates, _contact_done, _notifiers, _notified, _anchor):
        side.pop(cid, None)
    for name in [k for k, v in _received.items() if v.get("case_id") == cid]:
        _received.pop(name)
    for tok in [k for k, v in _tokens.items() if v.get("case_id") == cid]:
        _tokens.pop(tok)
    for kind in ARTIFACT_KINDS:   # what the agents wrote for this case; the other cases' files stay
        for f in (trace.dir / kind).glob(f"{cid}-*") if (trace.dir / kind).is_dir() else []:
            f.unlink()
    for name in ("outbox.jsonl", "handoffs.jsonl"):
        f = trace.dir / name
        if f.is_file():
            keep = [ln for ln in f.read_text(encoding="utf-8").splitlines() if _line_case(ln) != cid]
            f.write_text("".join(ln + "\n" for ln in keep), encoding="utf-8")
    bank.reset_customer(cif)
    if _ai_jobs.QUEUE.pilot:
        _ai_jobs.QUEUE.pilot.messages_sent.pop(cid, None)
    _ai_jobs.runner_for(cid).reset() if cid in _ai_jobs.RUNNERS else None
    seeded = portfolio.seed_one(bank, _PortfolioOps(), client) if client else None
    _manual["on"] = _manual["on"] or manual
    trace.operator("reset_case", case_id=cid)
    return {"status": "reset", "case": cid, "manual": _manual["on"], "portfolio": [seeded["case_id"]] if seeded else [],
            "cases": sorted(pipeline.cases)}


def _line_case(line: str) -> str | None:
    try:
        return json.loads(line).get("case_id")
    except ValueError:
        return None


@app.get("/demo/documents")
def demo_documents() -> list[dict[str, Any]]:
    return DOCUMENTS


@app.post("/demo/step/{n}")
def demo_step(n: int, variant: str = "A", source: str = "extracted") -> dict[str, Any]:
    """Feed demo document n (1..7). variant=B swaps the heir certificate for the testament one.
    source=extracted: the already-extracted document (*.mvp.json), at once. source=scan: the scanned original
    (registries/documents/scan/) goes to the intake inbox like a document from the counter; the autopilot's extractor
    reads it visually, the pipeline acts and the agents follow. Answers {"queued": file} at once; the result comes
    from GET /demo/received/{file}. Step 1 (the DGEP batch line) is electronic: always fed directly."""
    if not 1 <= n <= len(DOCUMENTS):
        raise HTTPException(404)
    if source not in ("extracted", "scan"):
        raise HTTPException(422, "source = extracted | scan")
    scan = scan_file(n, variant) if source == "scan" else None
    if scan is not None:
        return {"queued": _inbox_store(scan.name, scan.read_bytes()), "step": n, "source": "scan"}
    doc = copy.deepcopy(VARIANT_B if n == 4 and variant.upper() == "B" else DOCUMENTS[n - 1])
    return _receive(doc)


@app.get("/demo/received/{name}")
def demo_received(name: str) -> dict[str, Any]:
    """Where a file put in the inbox by /demo/step?source=scan is: waiting | extracting | failed | done (+ the same
    result as /demo/step, with document_id). The autopilot reads the file and POSTs the document under that name."""
    if name in _received:
        return {"status": "done", "result": _received[name]}
    box = _inbox_list()
    if name in box["failed"]:
        return {"status": "failed"}
    st = autopilot_status()
    current = (st.get("autopilot") or {}).get("current")
    if name == current and (st.get("autopilot") or {}).get("state") == "extracting":
        return {"status": "extracting", "autopilot": st["running"]}
    return {"status": "waiting" if name in box["waiting"] else "unknown", "autopilot": st["running"]}


@app.post("/demo/run")
def demo_run(variant: str = "A", upto: int = 7, variants: str = "pensie") -> list[dict[str, Any]]:
    demo_reset(variants)
    return [demo_step(i, variant) for i in range(1, upto + 1)]


# ---- 077: contact ladder for heirs who do not bring the documents (agent/contact_ladder.py)
_contact_done: dict[str, dict[str, dict[str, Any]]] = {}   # case -> step code -> {at, by, artifact, channel, to}
_notifiers: dict[str, dict[str, Any]] = {}                 # case -> the person who notified the death (operator input)
LADDER_ESCALATION = {"OPTION_EXPIRED": "option_deadline_passed", "NOTARY": "contact_no_notary"}


def _dossier(c) -> dict[str, Any]:
    """What contact_ladder.contact_plan needs, from the case + the bank's KYC contacts (address, app)."""
    heirs = []
    for h in c.heirs:
        cc = c.contact_channels.get(h["id"]) or {}
        kyc = bank.contact(h["name"]) or {}
        own = {} if h.get("minor") else cc   # a minor's entry holds the representative's contact
        address, source = h.get("address"), "certificatul de moștenitor"
        if not address and kyc.get("address"):
            address, source = kyc["address"], "evidența băncii (KYC)"
        heirs.append({"id": h["id"], "name": h["name"], "role": "heir", "minor": bool(h.get("minor")),
                      "representative_id": h.get("legal_representative"),
                      "channels": {"email": own.get("email"), "phone": own.get("sms"), "app": bool(own.get("is_client")),
                                   "verified": bool(own.get("verified"))},
                      "address": address, "address_source": source if address else None})
    notifier = _notifiers.get(c.id) or next((d.fields["notifier"] for d in reversed(c.documents)
                                             if isinstance(d.fields.get("notifier"), dict)), None)
    if notifier and notifier.get("name"):
        heirs.append({"id": "N1", "name": notifier["name"], "role": "notifier", "minor": False,
                      "channels": {"email": notifier.get("email"), "phone": notifier.get("phone"),
                                   "verified": bool(notifier.get("email")), "app": False},
                      "address": notifier.get("address"), "address_source": "declarat de persoana care a notificat"
                      if notifier.get("address") else None})
    known = {contact_ladder._name_key(p["name"]) for p in heirs}
    for i, name in enumerate(_open_senders(c.id)):   # 078: whoever must redo a document is reminded by the ladder too
        k = bank.contact(name) or {}
        if contact_ladder._name_key(name) not in known:
            known.add(contact_ladder._name_key(name))
            heirs.append({"id": f"U{i + 1}", "name": name, "role": "uploader", "minor": False,
                          "channels": {"email": k.get("email"), "phone": k.get("sms"), "app": bool(k.get("is_client")),
                                       "verified": bool(k.get("verified"))},
                          "address": k.get("address"), "address_source": "evidența băncii (KYC)" if k.get("address") else None})
    nd = next((d.fields for d in reversed(c.documents) if d.fields.get("notary_name") or d.fields.get("notary_office")), None)
    cert = next((d.received_on for d in c.documents if d.type == "heir_certificate"), None)
    done = dict(_contact_done.get(c.id, {}))
    msgs = [m for m in list_messages(c.id) if m.get("template_id") not in ("DEADLINE_SOON", "PLAN_APPROVED")]
    msg_days = sorted((m.get("case_date") or m["at"])[:10] for m in msgs)
    if msg_days:   # a message the autopilot already sent for the missing documents is the initial contact
        done.setdefault("INITIAL", {"at": msg_days[0], "by": "mesaj din outbox"})
        later = [d for d in msg_days if cert and d >= cert]
        for h in heirs:
            if h["minor"] and later:
                done.setdefault(f"MINOR_INITIAL:{h['id']}", {"at": later[0], "by": "mesaj din outbox"})
    days = [d.received_on for d in c.documents if d.received_on]
    return {"case_id": c.id, "date_of_death": c.date_of_death, "learned_on": c.learned_on,
            "last_document_on": max(days) if days else None, "certificate_on": cert if "certificate_received" in c.milestones else None,
            "missing": [m for m in c.missing() if not m.startswith("răspunsul asigurătorului")]
                       + deficiencies.ladder_items(_deficiency_records(c.id)),   # 078: open problems, until fixed
            "has_loan": c.cif in bank.customers and any(p.type == "personal_loan" for p in bank.products(c.cif)),
            "persons": heirs, "notary": {"name": nd.get("notary_name"), "office": nd.get("notary_office"),
                                         "case_file": nd.get("case_file")} if nd else None, "done": done}


def _contact_plan(c) -> dict[str, Any]:
    return contact_ladder.contact_plan(_dossier(c), _today(c))


@app.get("/cases/{case_id}/contact-plan")
def contact_plan(case_id: str) -> dict[str, Any]:
    """The contact ladder: steps done (with dates), the next one, what is due today (demo clock), with the basis."""
    c = pipeline.cases.get(case_id)
    if not c or c.id == ORPHAN_ID:
        raise HTTPException(404, "dosar inexistent")
    return _contact_plan(c)


@app.post("/cases/{case_id}/contact-plan/{code}/done")
def contact_step_done(case_id: str, code: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """The autopilot (or an operator) applied a due step: recorded once (a second call changes nothing). Steps
    without a channel and the expired option term become an escalation for the operator."""
    c = pipeline.cases.get(case_id)
    if not c or c.id == ORPHAN_ID:
        raise HTTPException(404, "dosar inexistent")
    if code in _contact_done.get(case_id, {}):
        return {"case_id": case_id, "code": code, "already": True, **_contact_done[case_id][code]}
    step = next((s for s in _contact_plan(c)["steps"] if s["code"] == code), None)
    if not step:
        raise HTTPException(404, f"pasul {code} nu e în scara dosarului")
    if step["status"] != "due":
        raise HTTPException(409, f"pasul {code} nu e scadent ({step['status_label']}, {step['due']})")
    rec = _record_contact_step(c, step, body or {}, _today(c).isoformat())
    trace.snapshot_case(c.to_dict())
    return {"case_id": case_id, "code": code, "already": False, **rec}


def _record_contact_step(c, step: dict[str, Any], b: dict[str, Any], at: str) -> dict[str, Any]:
    code = step["code"]
    rec = {"at": at, "by": b.get("by") or "autopilot", "action": step["action"],
           "artifact": b.get("artifact"), "channel": b.get("channel"),
           "to": b.get("to") or [r["name"] for r in step["recipients"]]}
    _contact_done.setdefault(c.id, {})[code] = rec
    to = ", ".join(rec["to"]) or "operator"
    c.log("action", f"Scara de contact: {step['label']} ({step['action_label']}) → {to}.", rule=step["basis"],
          step=code, artifact=rec["artifact"])
    if step["action"] == "operator":
        esc = c.escalate(LADDER_ESCALATION.get(code.split(":")[0], "contact_no_channel"),
                         f"{step['label']}: {step['note'] or 'pas fără canal de contact'}")
        rec["escalation"] = esc.id
    if code == "OPTION_EXPIRED" and not any(f.get("code") == "presumed_renunciation" for f in c.flags):
        c.flags.append({"code": "presumed_renunciation", "label": "Prezumată renunțarea / posibil vacantă (C.civ. "
                        "art. 1.112, 1.135); fonduri păstrate fără comisioane, operatorul decide", "since": rec["at"]})
    return rec


@app.post("/cases/{case_id}/notifier")
def set_notifier(case_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """The person who notified the death (name, email, phone, address): a contact for the ladder before the
    certificate names the heirs. Only operational messages, nothing about the accounts (bank secrecy)."""
    c = pipeline.cases.get(case_id)
    if not c or c.id == ORPHAN_ID:
        raise HTTPException(404, "dosar inexistent")
    if not (body.get("name") or "").strip():
        raise HTTPException(422, "numele e obligatoriu")
    _notifiers[case_id] = {k: body.get(k) for k in ("name", "email", "phone", "address")}
    c.log("decision", f"Persoana care a notificat decesul: {body['name']} (contact pentru scara de contact).")
    return {"case_id": case_id, "notifier": _notifiers[case_id]}


def _demo_only() -> None:
    if os.environ.get("DEMO_MODE") != "1":
        raise HTTPException(403, "doar în DEMO_MODE=1")


@app.get("/demo/clock")
def demo_clock() -> dict[str, Any]:
    return {"offset_days": _clock["offset_days"],
            "today": {cid: _today(c).isoformat() for cid, c in pipeline.cases.items() if cid != ORPHAN_ID}}


@app.post("/demo/advance-clock")
def advance_clock(days: int) -> dict[str, Any]:
    """DEMO_MODE only: moves every case's clock N days forward, so the ladder (14 / 30 / 60 days, 10 months, 1 year)
    can be shown live. /demo/reset puts it back to 0."""
    _demo_only()
    if not 1 <= days <= 800:
        raise HTTPException(422, "days între 1 și 800")
    _clock["offset_days"] += days
    return demo_clock()


# ---- 078: documents with problems -> a message to whoever sent them (agent/deficiencies.py, pure)
_deficiency: dict[str, dict[str, Any]] = {}   # document id -> record {case_id, sender, problems [+status, notified_at]}
_notified: dict[str, set[str]] = {}           # case -> dedupe keys "<subject>|<problem>" already told to the sender
DEFICIENCY_ESCALATION = {None: "document_deficient_no_sender", "institution": "document_deficient_institution",
                         "no_channel": "document_deficient_no_channel"}
# the pipeline's own escalations about the document itself: the operator already has it, with the reason
DOCUMENT_ESCALATIONS = {"document_illegible", "cnp_mismatch", "customer_not_found", "identity_unconfirmed",
                        "suspicious_document", "shares_invalid", "product_unknown", "product_ambiguous"}


def _mailer() -> mailer.Mailer:
    return mailer.get_mailer(_outbox)   # MAILER=outbox (default) | smtp (explicit only)


def _sender_context(doc: dict[str, Any], origin: dict[str, Any] | None) -> dict[str, str]:
    """Per case, the recipient of the last message sent BEFORE this document arrived."""
    last: dict[str, str] = {}
    for m in list_messages():
        last[m["case_id"]] = m["to"]
    return last


def _deficiency_records(case_id: str) -> list[dict[str, Any]]:
    return [r for r in _deficiency.values() if r["case_id"] == case_id]


def _open_senders(case_id: str) -> list[str]:
    """People told about a problem that is still open (the contact ladder reminds them until a document fixes it)."""
    out: list[str] = []
    for r in _deficiency_records(case_id):
        name = (r.get("sender") or {}).get("name")
        if name and name not in out and deficiencies.ladder_items([r]):
            out.append(name)
    return out


def _pending(rec: dict[str, Any]) -> list[dict[str, Any]]:
    return deficiencies.pending_notice(rec, _notified.get(rec["case_id"], set()))


def _contact_of(c, name: str | None) -> dict[str, Any]:
    """The sender's permitted channel (contact_ladder.permitted_channel: verified e-mail, app, SMS only with consent)."""
    if not name:
        return {}
    key = contact_ladder._name_key(name)
    for p in _dossier(c)["persons"]:
        if contact_ladder._name_key(p["name"]) == key and not p.get("minor"):
            return {"channel": contact_ladder.permitted_channel(p), "address": p["channels"].get("email"),
                    "role": p.get("role"), "is_heir": p.get("role") == "heir"}
    k = bank.contact(name) or {}
    person = {"channels": {"email": k.get("email"), "verified": bool(k.get("verified")), "app": bool(k.get("is_client")),
                           "phone": k.get("sms"), "consent": {"sms": bool(k.get("consent_sms"))}}}
    return {"channel": contact_ladder.permitted_channel(person), "address": k.get("email"), "role": "uploader",
            "is_heir": False}


def _person_address(c, to: str, channel: str) -> str | None:
    return (_contact_of(c, to).get("address") or None) if channel == "email" else None


def _gap_labels(c) -> list[str]:
    types = {p.id: p.type for p in bank.products(c.cif)} if c.cif in bank.customers else {}
    names = {"current_account": "contul curent", "term_deposit": "depozitul la termen", "personal_loan": "creditul"}
    return sorted({names.get(types.get(g, ""), "un cont") for g in c.coverage_gaps})


def _deficiency_check(doc: dict[str, Any], result: dict[str, Any], origin: dict[str, Any], last_to: dict[str, str]) -> None:
    """After the pipeline: the problems of this document, its sender, and what follows (a message through the
    autopilot, or an escalation when we do not know whom to write). Closes what this document fixed."""
    if result.get("duplicate"):
        return
    doc_case = result.get("case_id")
    target = origin.get("case_id") or doc_case
    c = pipeline.cases.get(target)
    if c is None:
        return
    on_case = target != ORPHAN_ID
    dtype = doc.get("document_type") or "unknown"
    expected = origin.get("expected_types") or []
    quarantined = bool(result.get("quarantined"))
    notifier = _notifiers.get(target) or next((d.fields["notifier"] for d in reversed(c.documents)
                                               if isinstance(d.fields.get("notifier"), dict)), None)
    sender = deficiencies.resolve_sender(dtype, origin.get("token_to"), notifier, last_to.get(target)) if on_case else None
    if quarantined and not origin.get("token_to"):
        sender = None   # a suspicious file from the intake may come from anyone (BEC): only the link proves who sent it
    contact = _contact_of(c, sender.get("name")) if sender and sender.get("name") else {}
    if sender and contact:
        sender.update(channel=contact.get("channel"), role=sender.get("role") or contact.get("role"))
    ctx = {"quarantined": quarantined, "pipeline_reason": result.get("escalation_reason"), "on_case": on_case,
           "deceased_cnp": bank.customers.get(c.cif, {}).get("cnp") if on_case else None, "expected_types": expected,
           "coverage_gaps": _gap_labels(c) if "supplement_requested" in (result.get("actions") or []) else [],
           "sender_is_heir": bool(contact.get("is_heir")), "text": origin.get("text"), "page_count": origin.get("page_count")}
    problems = deficiencies.detect(doc, ctx)
    at = _today(c).isoformat() if on_case else (doc.get("received_on") or date.today().isoformat())
    rec = {"document_id": doc["id"], "case_id": target, "document_case_id": doc_case, "via": origin.get("via") or "inbox",
           "name": doc.get("raw_name"), "received_on": doc.get("received_on") or at, "document_type": dtype,
           "intended_type": deficiencies.intended_type({**doc, "declared_type": (result.get("guard") or {}).get("declared_type")},
                                                       expected),
           "sender": sender, "accepted": on_case and doc_case == target and not quarantined,
           "problems": [{**p, "status": "open"} for p in problems], "status": "open" if problems else "ok"}
    rec["subject"] = deficiencies.subject({**doc, "intended_type": rec["intended_type"]})
    if origin.get("sha"):   # the very same file sent again is the same document
        same = next((r for r in _deficiency.values() if r.get("sha") == origin["sha"] and r["case_id"] == target), None)
        rec["sha"] = origin["sha"]
        if same:
            rec["subject"] = same["subject"]
    for p in rec["problems"]:   # the same problem on the same document, already told: shown as such, never re-sent
        if deficiencies.dedupe_key(rec, p) in _notified.get(target, set()):
            p["already_notified"] = True
    _deficiency[doc["id"]] = rec
    closed = deficiencies.reconcile(_deficiency_records(target), rec,
                                    _gap_labels(c) if "certificate_received" in c.milestones else None, at)
    if closed:
        c.log("decision", f"Probleme închise de documentul {doc.get('raw_name') or doc['id']}: {', '.join(closed)}.",
              rule="078: documentul refăcut închide problema", document_id=doc["id"])
    if not on_case or not problems:
        return
    c.log("decision", f"Probleme găsite la {doc.get('raw_name') or doc['id']}: "
          + "; ".join(p["code"] for p in problems) + ". Expeditor: "
          + (f"{sender.get('name') or sender.get('institution')} ({sender['label']})" if sender else "necunoscut") + ".",
          rule="078: detectare deterministă (agent/deficiencies.py)", document_id=doc["id"],
          problems=[p["key"] for p in problems])
    if all(p.get("handled_by_bank") for p in problems) and not (sender and sender.get("name")):
        return   # the bank already asked the notary for the supplement; nobody else to tell
    kind = None if not sender else "institution" if sender.get("source") == "institution" else         "no_channel" if not sender.get("channel") else "message"
    if kind == "message":
        return   # the autopilot writes it (heir-communicator), GET /cases/{id}/deficiencies -> pending
    already = any(e.document_id == doc["id"] and e.reason in DOCUMENT_ESCALATIONS
                  for cc in (c, pipeline.cases.get(doc_case)) if cc for e in cc.escalations)
    if already and kind is None:
        return   # the pipeline already handed this document to the operator
    what = "; ".join(p["text"] if not p.get("neutral") else "document suspect (vezi escaladarea gărzii)" for p in problems)
    detail = {None: "Nu știm cine a trimis documentul (nici link de încărcare, nici persoana care a notificat, nici un "
                    "mesaj anterior): nu scriem nimănui la ghicire. Operatorul identifică expeditorul.",
              "institution": f"Documentul vine de la {sender and sender.get('institution')}: operatorul cere instituției "
                             "un exemplar corect.",
              "no_channel": f"{sender and sender.get('name')} nu are un canal permis (e-mail verificat, aplicație, SMS cu "
                            "consimțământ): operatorul îl contactează."}[kind]
    esc = c.escalate(DEFICIENCY_ESCALATION[kind], f"Document cu probleme ({doc.get('raw_name') or doc['id']}): {what} {detail}",
                     doc["id"])
    rec["escalation"] = esc.id


def _deficiency_for_message(case, to: str, body: dict[str, Any]) -> dict[str, Any] | None:
    """A DOCUMENT_DEFICIENT message names its document; it goes only to that document's sender, once per problem."""
    ref = body.get("deficiency") or {}
    if body.get("template_id") != "DOCUMENT_DEFICIENT" and not ref:
        return None
    rec = _deficiency.get(str(ref.get("document_id") or ""))
    if not rec or rec["case_id"] != case.id:
        raise HTTPException(422, "DOCUMENT_DEFICIENT cere `deficiency.document_id` al unui document cu probleme din dosar")
    if not rec.get("sender") or contact_ladder._name_key(rec["sender"].get("name") or "") != contact_ladder._name_key(to):
        raise HTTPException(422, f"{to} nu e expeditorul documentului {rec['document_id']}")
    if not _pending(rec):
        raise HTTPException(409, "problemele acestui document au fost deja comunicate (sau s-au închis)")
    text = str(body.get("body") or "")
    if re.search(r"\{\{(?!UPLOAD_URL\}\}|token\}\})[^}]*\}\}", text):
        raise HTTPException(422, "mesajul are un câmp de completat nerezolvat ({{…}}); nu pleacă așa")
    if any(p.get("neutral") for p in _pending(rec)) and ("{{token}}" in text or "upload?token=" in text):
        raise HTTPException(422, "documentul suspect se aduce în original la agenție: mesajul nu are link de încărcare")
    return rec


def _mark_notified(case, rec: dict[str, Any], msg: dict[str, Any]) -> None:
    keys = _notified.setdefault(case.id, set())
    for p in _pending(rec):
        p.update(notified_at=msg["case_date"], message_id=msg["message_id"], notified_to=msg["to"], channel=msg["channel"])
        keys.add(deficiencies.dedupe_key(rec, p))
    trace.snapshot_case(case.to_dict())


def _deficiency_public(r: dict[str, Any]) -> dict[str, Any]:
    return {k: r.get(k) for k in ("document_id", "document_case_id", "via", "name", "received_on", "document_type",
                                  "intended_type", "sender", "status", "escalation")} | {
        "problems": [{k: p.get(k) for k in ("code", "key", "text", "ask", "ask_role", "status", "closed_by", "closed_at",
                                             "notified_at", "notified_to", "channel", "message_id", "handled_by_bank",
                                             "already_notified")}
                     for p in r["problems"]]}


def _deficiency_view(doc_id: str) -> dict[str, Any]:
    r = _deficiency.get(doc_id)
    return {"problems": _deficiency_public(r)["problems"], "sender": r.get("sender")} if r and r["problems"] else {}


@app.get("/cases/{case_id}/deficiencies")
def case_deficiencies(case_id: str) -> dict[str, Any]:
    """Documents with problems in this case, and the DOCUMENT_DEFICIENT messages still to write (`pending`): to whom,
    on which channel, and the public view of the problems (what heir-communicator may see)."""
    c = pipeline.cases.get(case_id)
    if not c or c.id == ORPHAN_ID:
        raise HTTPException(404, "dosar inexistent")
    recs = [r for r in _deficiency_records(case_id) if r["problems"]]
    pending = []
    for r in recs:
        todo = _pending(r)
        s = r.get("sender") or {}
        if todo and s.get("name") and s.get("channel"):
            view = deficiencies.public_view({**r, "problems": todo})
            pending.append({"document_id": r["document_id"], "to": s["name"], "channel": s["channel"],
                            "to_role": s.get("role") or "uploader", "sender_source": s.get("source"), **view})
    return {"case_id": case_id, "records": [_deficiency_public(r) for r in recs], "pending": pending}


# ---- autopilot (scripts/autopilot.py writes into this server's run directory)
ARTIFACT_KINDS = ("letters", "messages", "investigations")


@app.get("/cases/{case_id}/artifacts")
def case_artifacts(case_id: str) -> dict[str, Any]:
    """What the autopilot's agents wrote for this case (drafts, messages, investigations) + the latest audit."""
    items = []
    for kind in ARTIFACT_KINDS:
        d = trace.dir / kind
        for p in sorted(d.glob(f"{case_id}-*.md")) if d.is_dir() else []:
            items.append({"kind": kind[:-1], "file": f"{kind}/{p.name}", "content": p.read_text(encoding="utf-8"),
                          "modified_at": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")})
    audit = trace.dir / "audit.md"
    return {"case_id": case_id, "artifacts": items,
            "audit": audit.read_text(encoding="utf-8") if audit.is_file() else None,
            "handoffs": [h for h in _handoffs() if h.get("case_id") == case_id]}


def _handoffs() -> list[dict[str, Any]]:
    f = trace.dir / "handoffs.jsonl"
    out = []
    for line in f.read_text(encoding="utf-8").splitlines() if f.is_file() else []:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


@app.get("/handoffs")
def handoffs() -> list[dict[str, Any]]:
    """Every handoff the autopilot made in this run (document -> agent -> artifact, ok / failed / skipped)."""
    return _handoffs()


@app.get("/autopilot/status")
def autopilot_status() -> dict[str, Any]:
    """`run_dir` tells the autopilot where to write, `epoch` when to forget its state (it changes at /demo/reset);
    `autopilot` is its last heartbeat (None if it never ran); `paused`: the guided demo runs step by step, and
    `ai_jobs` are the AI calls the operator started there (queued / running)."""
    f = trace.dir / "autopilot-status.json"
    st = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None
    running = False
    if st:
        last = datetime.fromisoformat(st["last_poll"])
        running = st.get("state") != "stopped" and (datetime.now(timezone.utc) - last) < timedelta(seconds=60)
    return {"run_dir": str(trace.dir), "epoch": trace.epoch, "running": running, "autopilot": st,
            "paused": _manual["on"], "ai_jobs": _ai_jobs.QUEUE.running()}


# ---- 084: the bank's worklist (ops-ui "Dosare"): one row per case, what follows, the nearest term, human decisions
STATE_RO = {"NEW": "Nou", "DEATH_SIGNALLED": "Deces semnalat", "FROZEN": "Blocat", "NOTARY_ANSWERED": "Răspuns la notar",
            "INSURANCE_CLAIM_OPEN": "Daună deschisă", "SUPPLEMENT_REQUESTED": "Supliment cerut",
            "INSURANCE_SETTLED": "Daună închisă", "PLAN_DRAFTED": "Plan întocmit",
            "PAYMENT_PENDING_APPROVAL": "Plată de aprobat", "PAID": "Plătit", "CLOSED": "Închis"}
DOC_RO = {"dgep_signal": "Semnal DGEP", "notary_request": "Adresa notarului", "insurance_certificate": "Certificat de asigurare",
          "heir_certificate": "Certificat de moștenitor", "insurer_response": "Răspunsul asigurătorului",
          "supplementary_certificate": "Certificat suplimentar", "death_certificate": "Certificat de deces",
          "quarantined": "Document în carantină", "unknown": "Document neclasificat"}
ESC_RO = {"minor_heir": "moștenitor minor", "insurance_refused": "asigurătorul a refuzat", "suspicious_document":
          "document suspect", "document_illegible": "document ilizibil", "shares_invalid": "cote invalide",
          "policy_mismatch": "poliță nepotrivită", "post_death_mandate_withdrawal": "retragere după deces",
          "indemnity_mismatch": "indemnizație nepotrivită", "unsafe_output": "text de agent oprit"}
FILTERS = {"toate": "Toate", "de_aprobat": "De aprobat", "escaladari": "Escaladări", "documente": "Așteaptă documente",
           "termene": "Termene în 7 zile"}
SOON_DAYS = 7


def _fold(s: str) -> str:
    s = (s or "").casefold()
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"), ("ț", "t"), ("ţ", "t")):
        s = s.replace(a, b)
    return s


def _lei(bani: int) -> str:
    """12.146,27 lei (Romanian grouping)."""
    return f"{bani / 100:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".") + " lei"


def _decisions(c, view: dict[str, Any], plan: dict[str, Any] | None) -> list[dict[str, str]]:
    """What only a person can do in this case now: approve the plan, sign the answer to the notary, an open escalation,
    a step of the contact ladder that is the operator's."""
    out = []
    if c.payment_plan and c.payment_plan.get("status") == "pending_approval":
        total = sum(l["amount"] for l in c.payment_plan["lines"] if l["blocked_reason"] is None)
        out.append({"kind": "plata", "text": f"Aprobă planul de plată ({_lei(total)})"})
    if "notary_answered" in c.milestones and "notary_answer_signed" not in c.milestones:
        out.append({"kind": "semnatura", "text": "Semnează răspunsul către notar"})
    for e in view["escalations"]:
        if e["status"] != "închis":
            out.append({"kind": "escaladare", "text": f"Escaladare: {ESC_RO.get(e['code'], e['code'].replace('_', ' '))}"})
    for st in (plan or {}).get("due_now") or []:
        if st["action"] == "operator":
            out.append({"kind": "scara", "text": f"Scara de contact: {st['label']}"})
    return out


def _worklist_row(c) -> dict[str, Any]:
    view = _case_view(c)
    today = _today(c)
    plan = _contact_plan(c) if c.date_of_death else None
    decisions = _decisions(c, view, plan)
    docs = [d for d in c.documents if d.received_on]
    last = max(docs, key=lambda d: d.received_on) if docs else None
    # the insurer's notice term counts only for a client with an insured loan (rules.deadlines adds it to every case)
    insured = c.cif in bank.customers and any(p.insurance_policy_id for p in bank.products(c.cif))
    open_terms = sorted((d for d in view["deadlines"] if d["status"] != "îndeplinit"
                         and (insured or d["code"] != "insurance_claim_notice")), key=lambda d: d["date"])
    term = None
    if open_terms:
        t = open_terms[0]
        term = {"name": t["name"], "date": t["date"], "status": t["status"],
                "days": (date.fromisoformat(t["date"]) - today).days}
    if decisions:
        nxt = {"text": decisions[0]["text"], "due": None, "source": "decizie"}
    elif plan and plan.get("next"):
        n = plan["next"]
        nxt = {"text": n["label"], "due": n["due"], "source": "scara de contact", "status": n["status_label"]}
    elif c.missing():
        nxt = {"text": "Așteptăm " + c.missing()[0], "due": None, "source": "documente"}
    elif "paid" in c.milestones:
        blocked = [l for l in c.payment_plan["lines"] if l["blocked_reason"]] if c.payment_plan else []
        nxt = {"text": f"Plătit; {len(blocked)} linii rămân blocate până la scadență / acord" if blocked
               else "Plătit; dosarul se poate închide", "due": None, "source": "plată"}
    else:
        nxt = {"text": "Nimic de făcut acum", "due": None, "source": None}
    waiting = [m for m in c.missing()] if "paid" not in c.milestones else []
    return {"case_id": c.id, "kind": "case", "name": c.customer_name, "cif": c.cif, "cnp": view["deceased"]["cnp"],
            "date_of_death": view["deceased"]["date_of_death"], "state": c.state(),
            "state_label": STATE_RO.get(c.state(), c.state()), "today": today.isoformat(), "portfolio": c.id in _anchor,
            "last_document": {"document_id": last.id, "type": last.type, "label": DOC_RO.get(last.type, last.type),
                              "date": last.received_on} if last else None,
            "next": nxt, "deadline": term, "decisions": decisions, "decisions_count": len(decisions),
            "open_escalations": sum(e["status"] != "închis" for e in view["escalations"]), "missing": waiting,
            "filters": {"de_aprobat": any(d["kind"] in ("plata", "semnatura") for d in decisions),
                        "escaladari": any(d["kind"] == "escaladare" for d in decisions),
                        "documente": bool(waiting),
                        "termene": bool(term and term["days"] <= SOON_DAYS)}}


def _unmatched_row(c) -> dict[str, Any]:
    open_esc = [e for e in c.escalations if not e.resolved]
    docs = [d for d in c.documents if d.received_on]
    last = max(docs, key=lambda d: d.received_on) if docs else None
    decisions = [{"kind": "escaladare", "text": f"Document fără client: {ESC_RO.get(e.reason, e.reason.replace('_', ' '))}"}
                 for e in open_esc]
    return {"case_id": c.id, "kind": "unmatched", "name": "Documente neidentificate", "cif": "-", "cnp": None,
            "date_of_death": None, "state": "ESCALATED" if open_esc else "CLOSED",
            "state_label": "De verificat" if open_esc else "Verificate", "today": None, "portfolio": False,
            "last_document": {"document_id": last.id, "type": last.type, "label": DOC_RO.get(last.type, last.type),
                              "date": last.received_on} if last else None,
            "next": {"text": decisions[0]["text"] if decisions else "Nimic de făcut acum", "due": None,
                     "source": "decizie" if decisions else None},
            "deadline": None, "decisions": decisions, "decisions_count": len(decisions), "open_escalations": len(open_esc),
            "missing": [], "filters": {"de_aprobat": False, "escaladari": bool(open_esc), "documente": False,
                                       "termene": False}}


@app.get("/worklist")
def worklist(filtru: str = "toate", q: str = "") -> dict[str, Any]:
    """The bank's worklist: every case (and the documents that match no client) with its state in Romanian, the last
    document, what follows (a human decision, else the contact ladder, else what is missing), the nearest open term and
    the decisions waiting. filtru = toate | de_aprobat | escaladari | documente | termene; q = name, CNP, case or CIF."""
    if filtru not in FILTERS:
        raise HTTPException(422, f"filtru necunoscut: {filtru}; permise: {', '.join(FILTERS)}")
    rows = [_unmatched_row(c) if c.id == ORPHAN_ID else _worklist_row(c) for c in list(pipeline.cases.values())]
    counts = {k: (len(rows) if k == "toate" else sum(r["filters"][k] for r in rows)) for k in FILTERS}
    decisions = sum(r["decisions_count"] for r in rows)
    if q.strip():
        needle = _fold(q.strip())
        rows = [r for r in rows if any(needle in _fold(str(r.get(k) or "")) for k in ("name", "cnp", "case_id", "cif"))]
    if filtru != "toate":
        rows = [r for r in rows if r["filters"][filtru]]
    order = list(STATE_RO)
    rows.sort(key=lambda r: (-r["decisions_count"] if r["decisions_count"] else 1,
                             r["deadline"]["days"] if r["deadline"] else 10 ** 6,
                             -order.index(r["state"]) if r["state"] in order else 0, r["case_id"]))
    return {"filter": filtru, "q": q, "filters": [{"key": k, "label": v, "count": counts[k]} for k, v in FILTERS.items()],
            "decisions_waiting": decisions, "count": len(rows), "rows": rows}


# ---- 084: persistence (agent/store.py, docs/PERSISTENTA.md). Everything the API knows, after every request that may
# change it; reloaded at start. The run's artifact files (letters, messages, outbox ...) go along, so a restart with a
# new run directory (scripts/test-instance.sh start) still shows them.
SAVED_ARTIFACTS = ("letters", "messages", "investigations", "audits", "outbox.jsonl", "handoffs.jsonl", "audit.md")
store = Store(default_path(trace.run_id))


def _artifact_files(base: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in SAVED_ARTIFACTS:
        p = base / name
        files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p] if p.is_file() else []
        for f in files:
            try:
                out[str(f.relative_to(base))] = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
    return out


def _snapshot() -> tuple[dict[str, Any], dict[str, Any]]:
    for _ in range(5):   # another thread (guided demo jobs) may be adding to a dict right now: take it again
        try:
            cases = {cid: c.to_dict() for cid, c in list(pipeline.cases.items())}
            side = {"extractions": _extractions, "event_dates": _event_dates, "received": _received, "tokens": _tokens,
                    "contact_done": _contact_done, "notifiers": _notifiers, "deficiency": _deficiency,
                    "notified": _notified, "clock": _clock, "manual": _manual, "anchor": _anchor}
            side = json.loads(json.dumps(side, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)))
            state = {"bank": bank.to_dict(), "api": side, "run": {"run_id": trace.run_id, "epoch": trace.epoch},
                     "artifacts": _artifact_files(trace.dir)}
            return cases, json.loads(json.dumps(state, default=str))
        except RuntimeError:
            continue
    raise RuntimeError("starea s-a schimbat în timpul salvării de 5 ori la rând")


_persist_lock = threading.Lock()


def persist() -> int:
    """Snapshot + write under one lock: two requests ending together can't write their snapshots in the wrong order."""
    with _persist_lock:
        cases, state = _snapshot()
        return store.save(cases, state)


def _restore(saved: dict[str, Any]) -> None:
    bank.load(saved["bank"])
    pipeline.cases.clear()
    pipeline.cases.update({cid: Case.from_dict(d) for cid, d in saved["cases"].items()})
    side = saved.get("api") or {}
    for target, key in ((_extractions, "extractions"), (_event_dates, "event_dates"), (_received, "received"),
                        (_tokens, "tokens"), (_contact_done, "contact_done"), (_notifiers, "notifiers"),
                        (_deficiency, "deficiency"), (_anchor, "anchor")):
        target.clear()
        target.update(side.get(key) or {})
    _notified.clear()
    _notified.update({k: set(v) for k, v in (side.get("notified") or {}).items()})
    _clock.update(side.get("clock") or {})
    _manual.update(side.get("manual") or {})
    run = saved.get("run") or {}
    if run.get("run_id") == trace.run_id and run.get("epoch"):
        trace.epoch = run["epoch"]   # the same run after a restart: the autopilot keeps its state
    from agent.trace import RUNS
    old = RUNS / run["run_id"] if run.get("run_id") and run["run_id"] != trace.run_id else None
    files = {**(saved.get("artifacts") or {}), **(_artifact_files(old) if old and old.is_dir() else {})}
    for rel, text in files.items():
        dest = trace.dir / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")


class _PortfolioOps:
    """What agent/portfolio.py needs to bring a seeded client to its stage: the API's own paths (documents through
    `_receive`, the operator's actions through their endpoints), with every event dated on the day it happened."""

    def receive(self, doc: dict[str, Any], origin: dict[str, Any] | None = None) -> dict[str, Any]:
        return _receive(doc, origin)

    def _dated(self, cid: str, on: str, fn):
        before = len(pipeline.cases[cid].events)
        out = fn()
        dates = _event_dates.setdefault(cid, [])
        dates.extend([None] * (before - len(dates)))
        dates.extend([on] * (len(pipeline.cases[cid].events) - len(dates)))
        return out

    def sign_notary_answer(self, cid: str, signer: str, on: str) -> None:
        self._dated(cid, on, lambda: sign_notary_answer(cid, {"signer": signer}))

    def approve(self, cid: str, approver: str, on: str) -> None:
        self._dated(cid, on, lambda: approve(_payment_id(cid), {"approver": approver}))

    def notifier(self, cid: str, person: dict[str, Any], on: str) -> None:
        self._dated(cid, on, lambda: set_notifier(cid, person))

    def anchor(self, cid: str, as_of: str) -> None:
        _anchor[cid] = as_of

    def contact_history(self, cid: str, by: str) -> list[str]:
        """The steps of the contact ladder already due by the portfolio's date, done on their due day (history): the
        seeded case starts with nothing overdue, like a case the bank has been working on."""
        c, done = pipeline.cases[cid], []
        for _ in range(40):
            # the earliest step not made yet whose day has come; seen on its own day, when it was the one due
            late = sorted((s for s in _contact_plan(c)["steps"] if s["status"] in ("due", "skipped")), key=lambda s: s["due"])
            if not late:
                break
            day = date.fromisoformat(late[0]["due"])
            st = next((s for s in contact_ladder.contact_plan(_dossier(c), day)["due_now"] if s["code"] == late[0]["code"]), None)
            if st is None:
                break
            self._dated(cid, st["due"], lambda: _record_contact_step(c, st, {"by": by}, st["due"]))
            done.append(st["code"])
        return done

    def case(self, cid: str) -> dict[str, Any]:
        return _case_view(pipeline.cases[cid])


@app.middleware("http")
async def _persist_after_change(request: Request, call_next):
    """One request that may change state = one SQLite transaction after it (also after a 4xx: a refused message
    still leaves an `unsafe_output` escalation)."""
    response = await call_next(request)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(persist)
    return response


@app.get("/store/status")
def store_status() -> dict[str, Any]:
    """Where the state is kept and when it was last written."""
    return store.status()


def _receive_and_persist(doc: dict[str, Any], origin: dict[str, Any] | None = None) -> dict[str, Any]:
    """The guided demo's pipeline threads post documents outside an HTTP request: they save right away."""
    result = _receive(doc, origin)
    persist()
    return result


from agent.doc_preview import make_router as _preview_router  # read-only: source file of a received document
app.include_router(_preview_router(lambda: pipeline))
from agent.inbox_portal import archive as _archive_inbox, make_router as _inbox_router  # operator intake: files -> registries/inbox/ -> autopilot
from agent.inbox_portal import listing as _inbox_list, store as _inbox_store
from agent import ai_jobs as _ai_jobs  # guided demo step by step: every AI call started by the operator
app.include_router(_ai_jobs.make_router(_receive_and_persist, lambda cid: _case_view(pipeline.cases[cid]) if cid in pipeline.cases else None))
app.include_router(_inbox_router())
from agent import generated_docs as _generated  # every document the bank generated for a case: list + PDF / md / txt
app.include_router(_generated.make_router(_generated.Sources(
    run_dir=lambda: trace.dir,
    case_view=lambda cid: _case_view(pipeline.cases[cid]) if cid in pipeline.cases else None,
    saved_files=lambda: {k: v for k, v in (store.saved("artifacts") or {}).items() if not (trace.dir / k).exists()},
    contact_plan=lambda cid: _contact_plan(pipeline.cases[cid]) if cid in pipeline.cases and cid != ORPHAN_ID else None,
    gates=lambda: [g for r in list(_ai_jobs.RUNNERS.values()) for g in list(r.gates.values())],   # every case's gates
    gate_pdf=_ai_jobs.gate_pdf)))



def _boot() -> None:
    """At start: the saved state if there is one, else a fresh bank (with the portfolio, unless MVP_PORTFOLIO=0)."""
    saved = store.load()
    if saved:
        _restore(saved)
    else:
        demo_reset()
    persist()


_boot()

_ui = Path(__file__).resolve().parent.parent / "ops-ui"
if _ui.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_ui), html=True), name="ui")
