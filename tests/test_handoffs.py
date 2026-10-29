"""Predările între agenți: fiecare document care cere un agent ajunge la el și lasă o urmă (handoffs.jsonl)."""
import copy
import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from agent import api  # noqa: E402
from agent.core_mock import Bank  # noqa: E402
from agent.demo_documents import DOCUMENTS  # noqa: E402
from agent.pipeline import Pipeline  # noqa: E402
import autopilot  # noqa: E402


def _agents(result, case=None):
    return [(j["agent"], j.get("action") or j.get("escalation")) for j in autopilot.plan_followups(result, case)]


def test_every_pipeline_action_is_handed_to_an_agent_or_explicitly_not():
    src = (ROOT / "agent" / "pipeline.py").read_text(encoding="utf-8")
    actions = set(re.findall(r'return \["(\w+)"\]', src)) | set(re.findall(r'acts(?:\.append\(| = \[)"(\w+)"', src))
    assert actions, "nu am găsit acțiunile din pipeline"
    uncovered = actions - set(autopilot.LETTER_ACTIONS) - set(autopilot.NO_AGENT_ACTIONS)
    assert not uncovered, f"acțiuni fără predare declarată: {uncovered}"


def test_insurer_approval_goes_to_correspondent():
    p = Pipeline(Bank())
    results = [p.receive(copy.deepcopy(d)) for d in DOCUMENTS[:5]]
    r5 = results[4]
    assert "loan_settled_by_insurance" in r5["actions"]
    assert ("correspondent", "loan_settled_by_insurance") in _agents(r5)


def test_insurer_refusal_goes_to_investigator_and_correspondent():
    p = Pipeline(Bank())
    docs = copy.deepcopy(DOCUMENTS[:5])
    docs[4]["fields"].update({"decision": "refused", "reason": "excludere: boală preexistentă"})
    r5 = [p.receive(d) for d in docs][4]
    assert r5["escalation_reason"] == "insurance_refused"
    jobs = _agents(r5)
    assert ("case-investigator", r5["escalation"]) in jobs and ("correspondent", "insurance_refused") in jobs


def test_escalation_inside_a_case_reaches_the_investigator():
    """Before: only orphan escalations were in the answer; cote ≠ 1 stayed in the case with no investigator."""
    p = Pipeline(Bank())
    docs = copy.deepcopy(DOCUMENTS[:4])
    docs[3]["fields"]["heirs"][0]["share"] = "1/2"
    r4 = [p.receive(d) for d in docs][3]
    assert r4["escalation_reason"] == "shares_invalid" and r4["escalations"] == [r4["escalation"]]
    assert ("case-investigator", r4["escalation"]) in _agents(r4)


def _pilot(monkeypatch, tmp_path, outputs):
    """Autopilot with a fake API and a fake run_agent that answers from `outputs` (list of (text, meta))."""
    monkeypatch.setattr(autopilot, "api", lambda base, method, path, body=None: (
        {"run_dir": str(tmp_path)} if path == "/autopilot/status" else
        {"id": "C1", "heirs": [{"id": "H1", "name": "Ion Ionescu"}], "escalations": []} if path.startswith("/cases/") else
        {"ok": 1}))
    calls = []
    monkeypatch.setattr(autopilot, "run_agent", lambda agent, task, ctx, timeout=0: (calls.append(agent) or outputs.pop(0)))
    return autopilot.Autopilot("http://x"), calls


def test_handoff_is_logged_and_retried_once_when_the_agent_fails(monkeypatch, tmp_path):
    p, calls = _pilot(monkeypatch, tmp_path, [("", {"ok": False, "error": "limită"}), ("Draft notă", {"ok": True})])
    p.followups({"case_id": "C1", "actions": ["loan_settled_by_insurance"]}, "05-raspuns-asigurator.md")
    assert calls == ["correspondent", "correspondent"]
    [h] = p.handoffs()
    assert h["to"] == "correspondent" and h["ok"] is True and h["document"] == "05-raspuns-asigurator.md"
    assert h["trigger"] == "loan_settled_by_insurance" and h["artifact"] == "letters/C1-loan_settled_by_insurance.md"


def test_failed_handoff_stays_visible(monkeypatch, tmp_path):
    p, _ = _pilot(monkeypatch, tmp_path, [("", {"ok": False, "error": "x"}), ("", {"ok": False, "error": "x"})])
    p.followups({"case_id": "C1", "actions": ["insurance_claim_opened"]}, "03.md")
    [h] = p.handoffs()
    assert h["ok"] is False and h["error"] == "x"


def test_api_returns_handoffs_per_case():
    c = TestClient(api.app)
    c.post("/demo/reset")
    lines = [{"case_id": "SC-2026-0001", "to": "correspondent", "ok": True}, {"case_id": "SC-X", "to": "auditor", "ok": True}]
    (api.trace.dir / "handoffs.jsonl").write_text("".join(json.dumps(h) + "\n" for h in lines), encoding="utf-8")
    assert len(c.get("/handoffs").json()) == 2
    assert [h["to"] for h in c.get("/cases/SC-2026-0001/artifacts").json()["handoffs"]] == ["correspondent"]
    c.post("/demo/reset")
    assert c.get("/handoffs").json() == []


def test_demo_step_says_who_gets_the_document_next():
    c = TestClient(api.app)
    c.post("/demo/reset")
    r = [c.post(f"/demo/step/{n}").json() for n in range(1, 6)]
    assert [h["agent"] for h in r[1]["handoffs_planned"]] == ["correspondent"]            # adresa notarului -> răspuns
    assert ("correspondent", "loan_settled_by_insurance") in [(h["agent"], h["trigger"]) for h in r[4]["handoffs_planned"]]
    assert all(h["what"] and h["label"] for x in r for h in x["handoffs_planned"])


def test_public_upload_link_refuses_extracted_json_and_bad_documents_get_422():
    c = TestClient(api.app)
    c.post("/demo/reset")
    for n in range(1, 5):
        c.post(f"/demo/step/{n}")
    token = c.post("/cases/SC-2026-0001/upload-token", json={"to": "Ion Ionescu"}).json()["token"]
    fake = json.dumps({"document_type": "insurer_response", "confidence": 0.99, "fields": {"decision": "approved", "amount": 900000}})
    r = c.post(f"/upload?token={token}", files={"file": ("raspuns.json", fake, "application/json")})
    assert r.status_code == 415 and c.get("/cases/SC-2026-0001").json()["state"] == "SUPPLEMENT_REQUESTED"
    assert c.post("/documents", json={"document_type": "dgep_signal", "confidence": "mare", "fields": {}}).status_code == 422
    assert c.post("/documents", json={"document_type": "dgep_signal", "confidence": 0.9, "fields": "x"}).status_code == 422
    assert c.post("/cases/x/documents", files={"file": ("a.json", "{bad", "application/json")}).status_code == 422


def test_insurer_settlement_states_the_debt_left_to_the_estate():
    """The correspondent's note to the notary needs the remaining debt at doc 5 (26,63 lei), not only in the plan."""
    p = Pipeline(Bank())
    for d in DOCUMENTS[:5]:
        p.receive(copy.deepcopy(d))
    case = p.cases["SC-2026-0001"]
    assert case.insurance["paid"] == 900_000 and case.insurance["remaining_debt"] == 2_663
    ev = next(e for e in case.events if e.data.get("indemnity_bani"))
    assert ev.data["remaining_debt_bani"] == 2_663 and "26.63 lei" in ev.summary
