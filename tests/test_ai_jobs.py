"""Guided demo step by step (agent/ai_jobs.py): every AI call is a job; the rules run only after the extraction; a
handoff runs only if it was planned; nothing leaves before a human approves it (gates); a step's pipeline runs station
after station, waits at the gates and stops on request. No LLM: the extractor and the agents are faked."""
import copy
import time

import pytest
from fastapi.testclient import TestClient

from agent import ai_jobs, api
from agent.demo_documents import DOCUMENTS


def _wait(c, job_id, timeout=10):
    t = time.time()
    while time.time() - t < timeout:
        job = next(j for j in c.get("/demo/ai/jobs").json() if j["id"] == job_id)
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} still {job['status']}")


def _until(c, n, pred, timeout=10):
    t = time.time()
    while time.time() - t < timeout:
        st = c.get("/demo/ai/steps").json()[str(n)]
        if pred(st):
            return st
        time.sleep(0.05)
    raise AssertionError(f"step {n}: {st['pipeline']} {st['next']}")


@pytest.fixture
def c(monkeypatch):
    def fake_read(path):   # what the extractor reads from the scan: the ground truth of that document
        stem = path.name.removesuffix(".pdf")
        doc = next(d for d in DOCUMENTS if stem in d["raw_name"])
        return {k: copy.deepcopy(v) for k, v in doc.items() if k not in ("id", "raw_name", "received_on")}
    monkeypatch.setattr(ai_jobs.autopilot, "to_document", fake_read)
    calls, sent, posted = [], [], []
    slow = {"s": 0.0}

    class FakePilot:
        agent_calls: list = []
        last_draft = None

        def run_job(self, job, cid, case, document=None, send=True):
            time.sleep(slow["s"])
            calls.append((job["agent"], job["key"], cid, document, case["state"], send))
            self.agent_calls.append({"ok": True, "file": f"letters/{job['key']}.md", "cost_usd": 0.01})
            if job["agent"] == "heir-communicator":
                self.last_draft = {"case_id": cid, "to": "Ion Ionescu", "email": None, "template": "T", "missing": job["missing"], "body": "x"}
            return f"text de la {job['agent']}"

        def send_message(self, draft):
            sent.append(draft["to"])
            return {"ok": True}
    monkeypatch.setattr(ai_jobs.runner, "get_pilot", lambda base: FakePilot())
    real_api = ai_jobs._api
    client = TestClient(api.app)

    def via_client(base, method, path, body=None):   # the gates call the API: here through the test client
        posted.append(path)
        r = client.request(method, path, json=body)
        return r.json() if r.status_code < 400 else {"_http_error": r.status_code, "detail": r.text}
    monkeypatch.setattr(ai_jobs, "_api", via_client)
    client.post("/demo/reset?manual=true")
    client.calls, client.sent, client.posted, client.slow = calls, sent, posted, slow
    yield client
    monkeypatch.setattr(ai_jobs, "_api", real_api)
    client.post("/demo/reset")


def test_manual_reset_pauses_the_autopilot(c):
    assert c.get("/autopilot/status").json()["paused"] is True
    c.post("/demo/reset")
    assert c.get("/autopilot/status").json()["paused"] is False


def test_step_by_step_extract_then_rules_then_agent_then_human_gate(c):
    assert c.post("/demo/ai/apply/1").json()["state"] == "FROZEN"           # DGEP line: rules only, no AI
    assert c.post("/demo/ai/extract/1").status_code == 409
    assert c.post("/demo/ai/apply/2").status_code == 409                     # rules wait for the extractor
    job = _wait(c, c.post("/demo/ai/extract/2").json()["id"])
    assert job["status"] == "done" and job["output"]["raw_name"] == "scan/02-adresa-notar.pdf"
    r = c.post("/demo/ai/apply/2").json()
    assert r["state"] == "NOTARY_ANSWERED" and r["document_id"] == "doc-02"
    assert c.post("/demo/ai/apply/2").json() == r                            # idempotent
    key = r["handoffs_planned"][0]["key"]
    assert c.post("/demo/ai/agent/2/nu-e-planificat").status_code == 404
    assert _wait(c, c.post(f"/demo/ai/agent/2/{key}").json()["id"])["status"] == "done"
    assert c.calls == [("correspondent", key, "SC-2026-0001", "scan/02-adresa-notar.pdf", "NOTARY_ANSWERED", False)]
    g = c.get("/demo/ai/steps").json()["2"]["gates"][key]
    assert g["kind"] == "letter" and g["status"] == "pending" and g["preview"] == "text de la correspondent"
    assert g["to"] == g["email"] == ai_jobs.DEMO_EMAIL and "notarul" in g["recipient"]   # only the address is shown
    pdf = c.get(f"/demo/ai/gate/2/{key}/pdf")   # the letter as the PDF that leaves (to sign)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and pdf.headers["content-type"] == "application/pdf"
    deadline = lambda: next(d for d in c.get("/cases/SC-2026-0001").json()["deadlines"] if d["code"] == "notary_answer")
    assert deadline()["status"] != "îndeplinit"
    g = c.post(f"/demo/ai/gate/2/{key}/approve", json={"by": "Ana Operator"}).json()
    assert g["status"] == "approved" and g["decided_by"] == "Ana Operator"
    mail = [m for m in c.get("/messages").json() if m.get("kind") == "letter"][-1]   # the approved letter left by (mock) e-mail
    assert mail["address"] == ai_jobs.DEMO_EMAIL and mail["attachment_path"].endswith(".pdf") and g["mail"]["pdf"].endswith(".pdf")
    assert deadline()["status"] == "îndeplinit"                              # approving the answer to the notary signs it


def test_heir_message_leaves_only_after_approval(c):
    for n in (1, 2, 3):
        if n > 1:
            _wait(c, c.post(f"/demo/ai/extract/{n}").json()["id"])
        c.post(f"/demo/ai/apply/{n}")
    _wait(c, c.post("/demo/ai/extract/4").json()["id"])
    r = c.post("/demo/ai/apply/4").json()
    key = next(p["key"] for p in r["handoffs_planned"] if p["agent"] == "heir-communicator")
    _wait(c, c.post(f"/demo/ai/agent/4/{key}").json()["id"])
    assert c.sent == [] and c.get("/demo/ai/steps").json()["4"]["gates"][key]["kind"] == "message"
    assert c.post(f"/demo/ai/gate/4/{key}/reject", json={"note": "ton"}).json()["status"] == "rejected"
    assert c.sent == []                                                       # rejected: nothing was sent
    assert c.post(f"/demo/ai/gate/4/{key}/approve").json()["status"] == "rejected"   # the first decision stands
    inv = next(p["key"] for p in r["handoffs_planned"] if p["agent"] == "case-investigator")
    _wait(c, c.post(f"/demo/ai/agent/4/{inv}").json()["id"])
    esc = lambda: next(e for e in c.get("/cases/SC-2026-0001").json()["escalations"] if e["id"] == r["escalation"])
    assert esc()["status"] != "închis"
    c.post(f"/demo/ai/gate/4/{inv}/approve", json={"by": "Ana"})               # proposal accepted: escalation closed
    assert esc()["status"] == "închis"


def test_pipeline_runs_the_step_and_waits_at_each_gate(c):
    c.post("/demo/ai/apply/1")
    p = c.post("/demo/ai/pipeline/2/run").json()
    assert p["status"] == "running"
    st = _until(c, 2, lambda s: s["pipeline"]["status"] == "awaiting")
    key = st["result"]["handoffs_planned"][0]["key"]
    assert st["gates"][key]["status"] == "pending" and st["next"]["do"] == "wait_gate"
    c.post(f"/demo/ai/gate/2/{key}/approve")
    st = _until(c, 2, lambda s: s["pipeline"]["status"] == "done")
    assert st["result"]["state"] == "NOTARY_ANSWERED" and st["next"]["do"] == "done"
    r = c.post("/demo/ai/pipeline/4/run")                                     # documents come in order
    assert r.status_code == 409 and "întâi pasul 3" in r.json()["detail"]


def test_stop_cancels_the_pipeline(c):
    c.post("/demo/ai/apply/1")
    c.slow["s"] = 0.3
    c.post("/demo/ai/pipeline/2/run")
    _until(c, 2, lambda s: s["result"] is not None)                           # rules applied, the agent is on its way
    assert c.post("/demo/ai/pipeline/2/stop").json()["status"] in ("stopping", "stopped")
    st = _until(c, 2, lambda s: s["pipeline"]["status"] == "stopped")
    assert st["pipeline"]["stage"] == "oprit de operator"
    assert c.post("/demo/ai/pipeline/2/stop").status_code == 409
    c.slow["s"] = 0.0
    c.post("/demo/ai/pipeline/2/run")                                          # run again: continues where it stopped
    assert _until(c, 2, lambda s: s["pipeline"]["status"] == "awaiting")["next"]["do"] == "wait_gate"


def test_unsure_extraction_waits_for_a_human(c, monkeypatch):
    real = ai_jobs.autopilot.to_document
    monkeypatch.setattr(ai_jobs.autopilot, "to_document", lambda path: {**real(path), "confidence": 0.4})
    c.post("/demo/ai/apply/1")
    _wait(c, c.post("/demo/ai/extract/2").json()["id"])
    g = c.get("/demo/ai/steps").json()["2"]["gates"]["extract"]
    assert g["kind"] == "extract" and "40%" in g["why"]
    assert c.post("/demo/ai/apply/2").status_code == 409
    c.post("/demo/ai/gate/2/extract/approve")
    r = c.post("/demo/ai/apply/2").json()                                     # approved: the rules decide (here: escalate)
    assert r["document_id"] == "doc-02" and r.get("escalation")


def test_payment_gate_approves_through_the_payments_api(c):
    for n in range(1, 7):
        if n > 1:
            _wait(c, c.post(f"/demo/ai/extract/{n}").json()["id"])
        c.post(f"/demo/ai/apply/{n}")
    g = c.get("/demo/ai/steps").json()["6"]["gates"]["payment"]
    assert g["kind"] == "payment" and g["status"] == "pending"
    assert c.post("/demo/ai/gate/6/payment/reject", json={}).status_code == 422   # a reason is required
    assert c.post("/demo/ai/gate/6/payment/approve", json={"by": "Ana"}).json()["status"] == "approved"
    assert c.get("/cases/SC-2026-0001").json()["state"] == "PAID"


def test_reset_forgets_jobs_steps_and_gates(c):
    _wait(c, c.post("/demo/ai/extract/3").json()["id"])
    assert c.get("/demo/ai/jobs").json()
    c.post("/demo/reset?manual=true")
    st = c.get("/demo/ai/steps").json()
    assert c.get("/demo/ai/jobs").json() == [] and all(not s["result"] and not s["gates"] for s in st.values())


def test_scan_thumbnail(c):
    r = c.get("/demo/scan/4.png?variant=B")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert c.get("/demo/scan/1.png").status_code == 404
