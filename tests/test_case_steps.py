"""Guided demo step by step on any case of the bank (agent/ai_jobs.py CaseRunner, ?case=): a portfolio case has its
documents as steps already made and a step for what it waits on now (agent -> human gate); the state is per case and
independent (a decision on one case, a run on another, Maria's reset: none touches the others); POST /demo/reset?case=
starts only that case again. No LLM: the agents are faked."""
import time

import pytest
from fastapi.testclient import TestClient

from agent import ai_jobs, api


def _until(c, case, n, pred, timeout=10):
    t = time.time()
    while time.time() - t < timeout:
        st = c.get(f"/demo/ai/steps?case={case}").json()
        if str(n) in st and pred(st[str(n)]):
            return st[str(n)]
        time.sleep(0.05)
    raise AssertionError(f"{case} step {n}: {st.get(str(n), {}).get('pipeline')} {st.get(str(n), {}).get('next')}")


def _action_step(c, case):
    st = c.get(f"/demo/ai/steps?case={case}").json()
    n = max(int(k) for k, v in st.items() if v["meta"]["kind"] == "action")
    return n, st[str(n)]


@pytest.fixture
def c(monkeypatch):
    calls, sent = [], []

    class FakePilot:
        agent_calls: list = []
        last_draft = None
        messages_sent: dict = {}

        def run_job(self, job, cid, case, document=None, send=True):
            calls.append((job["agent"], job["key"], cid, send))
            self.agent_calls.append({"ok": True, "file": f"{job['kind']}/{job['key']}.md", "cost_usd": 0.01})
            if job["agent"] == "heir-communicator":
                self.last_draft = {"case_id": cid, "to": "moștenitorul", "email": None, "template": "T", "missing": job["missing"], "body": "x"}
            return f"text de la {job['agent']} pentru {cid}"

        def send_message(self, draft):
            sent.append((draft["case_id"], draft["to"]))
            return {"ok": True}

    pilot = FakePilot()
    monkeypatch.setattr(ai_jobs.QUEUE, "get_pilot", lambda base: pilot)
    monkeypatch.setattr(ai_jobs.runner, "get_pilot", lambda base: pilot)
    client = TestClient(api.app)
    real_api = ai_jobs._api

    def via_client(base, method, path, body=None):
        r = client.request(method, path, json=body)
        return r.json() if r.status_code < 400 else {"_http_error": r.status_code, "detail": r.text}
    monkeypatch.setattr(ai_jobs, "_api", via_client)
    client.post("/demo/reset?portofoliu=1")
    client.calls, client.sent = calls, sent
    yield client
    monkeypatch.setattr(ai_jobs, "_api", real_api)
    client.post("/demo/reset")


def test_portfolio_case_steps_are_its_documents_then_what_it_waits_on(c):
    case = c.get("/cases/SC-2026-0110").json()
    st = c.get("/demo/ai/steps?case=SC-2026-0110").json()
    docs = [v for v in st.values() if v["meta"]["kind"] == "doc"]
    assert [v["result"]["document_id"] for v in docs] == [d["document_id"] for d in case["documents"]]
    assert all(v["next"]["do"] == "done" and v["result"]["history"] for v in docs)       # read and applied at intake
    n, step = _action_step(c, "SC-2026-0110")
    assert n == len(docs) + 1 and step["meta"]["action"] == "case-investigator"
    assert step["next"]["do"] == "agent" and step["result"]["handoffs_planned"][0]["agent"] == "case-investigator"
    assert c.post(f"/demo/ai/extract/1?case=SC-2026-0110").status_code == 409          # nothing to read again
    assert c.get("/demo/ai/steps?case=SC-NU-EXISTA").status_code == 404


def test_investigator_runs_its_proposal_stops_at_the_human_then_the_next_step_appears(c):
    n, step = _action_step(c, "SC-2026-0110")
    assert c.post(f"/demo/ai/pipeline/{n}/run?case=SC-2026-0110").json()["status"] == "running"
    st = _until(c, "SC-2026-0110", n, lambda s: s["pipeline"]["status"] == "awaiting")
    key = step["result"]["handoffs_planned"][0]["key"]
    g = st["gates"][key]
    assert g["kind"] == "investigation" and g["status"] == "pending" and "SC-2026-0110" in g["preview"]
    assert c.calls == [("case-investigator", key, "SC-2026-0110", False)]
    esc = lambda: c.get("/cases/SC-2026-0110").json()["escalations"][0]["status"]
    assert esc() != "închis"
    c.post(f"/demo/ai/gate/{n}/{key}/approve?case=SC-2026-0110", json={"by": "Ana"})
    assert esc() == "închis"                                                            # proposal accepted
    _until(c, "SC-2026-0110", n, lambda s: s["pipeline"]["status"] == "done")
    st = c.get("/demo/ai/steps?case=SC-2026-0110").json()
    if str(n + 1) in st:                                                                # what the case needs next, if anything
        assert st[str(n + 1)]["meta"]["kind"] == "action" and st[str(n + 1)]["next"]["do"] in ("agent", "wait_gate")


def test_heir_message_on_a_portfolio_case_leaves_only_after_approval(c):
    n, step = _action_step(c, "SC-2026-0107")          # the minor's escalation and the payment first
    key = step["result"]["handoffs_planned"][0]["key"]
    c.post(f"/demo/ai/agent/{n}/{key}?case=SC-2026-0107")
    _until(c, "SC-2026-0107", n, lambda s: key in s["gates"])
    c.post(f"/demo/ai/gate/{n}/{key}/approve?case=SC-2026-0107", json={"by": "Ana"})
    c.post(f"/demo/ai/gate/{n}/payment/reject?case=SC-2026-0107", json={"by": "Ana", "note": "întâi reprezentantul Sofiei"})
    st = _until(c, "SC-2026-0107", n + 1, lambda s: True)   # then the heirs: the minor's representative is still missing
    p = st["result"]["handoffs_planned"][0]
    assert st["meta"]["action"] == p["agent"] == "heir-communicator"
    c.post(f"/demo/ai/agent/{n + 1}/{p['key']}?case=SC-2026-0107")
    st = _until(c, "SC-2026-0107", n + 1, lambda s: p["key"] in s["gates"])
    assert st["gates"][p["key"]]["kind"] == "message" and c.sent == []
    c.post(f"/demo/ai/gate/{n + 1}/{p['key']}/approve?case=SC-2026-0107", json={"by": "Ana"})
    assert c.sent == [("SC-2026-0107", "moștenitorul")]


def test_cases_are_independent_and_reset_touches_only_its_case(c):
    # 0107: the minor's escalation first, then the payment
    n, step = _action_step(c, "SC-2026-0107")
    key = step["result"]["handoffs_planned"][0]["key"]
    c.post(f"/demo/ai/agent/{n}/{key}?case=SC-2026-0107")
    _until(c, "SC-2026-0107", n, lambda s: key in s["gates"])
    assert step["gates"]["payment"]["status"] == "pending"                              # the payment, in the same step
    c.post(f"/demo/ai/gate/{n}/{key}/approve?case=SC-2026-0107", json={"by": "Ana"})
    assert c.post(f"/demo/ai/gate/{n}/payment/approve?case=SC-2026-0107", json={"by": "Ana"}).json()["status"] == "approved"
    assert c.get("/cases/SC-2026-0107").json()["state"] == "PAID"
    # another case runs meanwhile; its steps are its own
    m, _ = _action_step(c, "SC-2026-0110")
    c.post(f"/demo/ai/pipeline/{m}/run?case=SC-2026-0110")
    _until(c, "SC-2026-0110", m, lambda s: s["pipeline"]["status"] == "awaiting")
    assert c.get("/demo/ai/steps?case=SC-2026-0107").json()[str(n)]["gates"]["payment"]["status"] == "approved"
    jobs = c.get("/demo/ai/jobs?case=all").json()
    assert {j["case_scope"] for j in jobs} == {"SC-2026-0107", "SC-2026-0110"} and c.get("/demo/ai/jobs").json() == []
    # Maria starts step by step from zero: no global reset
    r = c.post("/demo/reset?case=SC-2026-0001&manual=true").json()
    assert r["case"] == "SC-2026-0001" and c.get("/autopilot/status").json()["paused"] is True
    assert c.post("/demo/ai/apply/1").json()["state"] == "FROZEN"
    assert c.get("/cases/SC-2026-0107").json()["state"] == "PAID"
    assert c.get("/demo/ai/steps?case=SC-2026-0110").json()[str(m)]["pipeline"]["status"] == "awaiting"
    # 0107 again from its first step: back in its stage; 0110 and Maria untouched
    c.post("/demo/reset?case=SC-2026-0107")
    assert c.get("/cases/SC-2026-0107").json()["state"] == "PAYMENT_PENDING_APPROVAL"
    assert _action_step(c, "SC-2026-0107")[1]["next"]["do"] == "agent"
    assert c.get("/cases/SC-2026-0001").json()["state"] == "FROZEN"
    assert c.get("/demo/ai/steps?case=SC-2026-0110").json()[str(m)]["pipeline"]["status"] == "awaiting"
    assert c.post("/demo/reset?case=SC-2099-0001").status_code == 404


# ---------------------------------------------------------------- documents that have not come yet (pending)
@pytest.fixture
def read(monkeypatch):
    """The extractor reads a pending document's file: here, the ground truth of that document (registries/portofoliu)."""
    from agent import portfolio
    truth = {st["doc"]["file"].split("/")[-1]: st["doc"] for cl in portfolio.clients() for st in portfolio.pending(cl)}
    seen = []

    def fake(path):
        seen.append(path.name)
        d = truth[path.name]
        return {"document_type": d["expected_type"], "confidence": 0.95, "fields": dict(d["expected_fields"])}
    monkeypatch.setattr(ai_jobs.autopilot, "to_document", fake)
    return seen


def test_a_pending_document_runs_like_marias_extractor_rules_payment_gate(c, read):
    before = c.get("/cases/SC-2026-0104").json()
    st = c.get("/demo/ai/steps?case=SC-2026-0104").json()
    n = len(before["documents"]) + 1
    step = st[str(n)]
    assert step["meta"]["pending"] and step["meta"]["document_type"] == "supplementary_certificate" and step["result"] is None
    assert step["next"]["do"] == "extract" and str(n + 1) not in st                     # no action step before it is in
    assert c.get(f"/demo/ai/doc/{n}?case=SC-2026-0104").text.startswith("ROMÂNIA")     # the file the extractor reads
    assert c.post(f"/demo/ai/apply/{n}?case=SC-2026-0104").status_code == 409          # the rules wait for the extractor
    c.post(f"/demo/ai/pipeline/{n}/run?case=SC-2026-0104")
    st = _until(c, "SC-2026-0104", n, lambda s: s["pipeline"]["status"] == "awaiting")
    assert read == ["05-certificat-suplimentar.md"]
    assert st["result"]["document_id"] == "P04-D5" and st["result"]["source"] == "portofoliu/P04/05-certificat-suplimentar.md"
    assert st["gates"]["payment"]["status"] == "pending" and st["next"]["do"] == "wait_gate"
    case = c.get("/cases/SC-2026-0104").json()
    assert case["state"] == "PAYMENT_PENDING_APPROVAL" and len(case["documents"]) == n
    assert c.get(f"/cases/SC-2026-0104/documents/P04-D5/preview").status_code == 200   # the source file is kept
    c.post(f"/demo/ai/gate/{n}/payment/approve?case=SC-2026-0104", json={"by": "Ana"})
    _until(c, "SC-2026-0104", n, lambda s: s["pipeline"]["status"] == "done")
    assert c.get("/cases/SC-2026-0104").json()["state"] == "PAID"
    assert c.get("/demo/ai/steps?case=SC-2026-0104").json()[str(n)]["result"]["document_id"] == "P04-D5"   # not a 2nd step


def test_a_pending_insurer_answer_hands_the_note_to_the_notary_to_the_correspondent(c, read):
    n = len(c.get("/cases/SC-2026-0103").json()["documents"]) + 1
    c.post(f"/demo/ai/pipeline/{n}/run?case=SC-2026-0103")
    st = _until(c, "SC-2026-0103", n, lambda s: s["pipeline"]["status"] == "awaiting")
    assert "loan_settled_by_insurance" in st["result"]["actions"]
    g = next(iter(st["gates"].values()))
    assert g["kind"] == "letter" and "Dobre" in g["recipient"] and "305/2026" in g["recipient"]
    assert c.calls[-1][:3] == ("correspondent", "SC-2026-0103-loan_settled_by_insurance", "SC-2026-0103")


def test_reset_of_one_case_puts_back_its_pending_document_and_touches_no_other(c, read):
    n4 = len(c.get("/cases/SC-2026-0104").json()["documents"]) + 1
    n3 = len(c.get("/cases/SC-2026-0103").json()["documents"]) + 1
    for cid, n in (("SC-2026-0104", n4), ("SC-2026-0103", n3)):
        c.post(f"/demo/ai/pipeline/{n}/run?case={cid}")
        _until(c, cid, n, lambda s: s["pipeline"]["status"] == "awaiting")
    c.post(f"/demo/ai/gate/{n4}/payment/approve?case=SC-2026-0104", json={"by": "Ana"})
    assert c.get("/cases/SC-2026-0104").json()["state"] == "PAID"
    other = c.get("/cases/SC-2026-0103").json()
    r = c.post("/demo/reset?case=SC-2026-0104").json()
    assert r["case"] == "SC-2026-0104"
    case = c.get("/cases/SC-2026-0104").json()
    assert case["state"] == "SUPPLEMENT_REQUESTED" and len(case["documents"]) == n4 - 1
    st = c.get("/demo/ai/steps?case=SC-2026-0104").json()
    assert st[str(n4)]["meta"]["pending"] and st[str(n4)]["result"] is None and not st[str(n4)]["gates"]
    assert c.get("/cases/SC-2026-0103").json() == other                                # the other case, as it was
    assert c.get("/demo/ai/steps?case=SC-2026-0103").json()[str(n3)]["pipeline"]["status"] == "awaiting"
    assert {j["case_scope"] for j in c.get("/demo/ai/jobs?case=all").json()} == {"SC-2026-0103"}


def test_maria_with_or_without_case_is_the_same_demo(c):
    assert c.get("/demo/ai/steps").json() == c.get("/demo/ai/steps?case=SC-2026-0001").json()
    assert c.post("/demo/ai/apply/1?case=SC-2026-0001").json()["state"] == "FROZEN"
    assert c.get("/demo/ai/steps").json()["1"]["result"]["case_id"] == "SC-2026-0001"
    assert c.get("/demo/ai/steps?case=SC-2026-0110").json()["1"]["result"]["history"] is True
    assert c.get("/demo/ai/doc/1").status_code == 404                                  # hers: /demo/scan/{n}/file
