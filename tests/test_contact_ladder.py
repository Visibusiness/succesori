"""077: the contact ladder (agent/contact_ladder.py), its API (contact-plan, step done, advance-clock) and the autopilot
step. Every threshold, the minor's track, the escalation without a channel and the dedupe."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import api
from agent.contact_ladder import add_months, contact_plan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import autopilot  # noqa: E402

D = date(2026, 10, 22)   # last document = certificate
DOD = date(2026, 9, 3)
ION = {"id": "H1", "name": "Ion Ionescu", "role": "heir", "channels": {"email": "ion@x.invalid", "verified": True},
       "address": "Str. Fictivă nr. 1", "address_source": "certificatul de moștenitor"}
ELENA = {"id": "H3", "name": "Elena Ionescu", "role": "heir", "minor": True, "representative_id": "H1"}
SUPPL = "certificat suplimentar pentru: DEP-1"
MINOR = "acordul scris al reprezentantului legal pentru Elena Ionescu (minor)"
NOTARY = {"name": "Ana EXEMPLU", "office": "BIN Exemplu", "case_file": "123/2026"}


def dossier(**kw):
    base = {"case_id": "C1", "date_of_death": DOD, "learned_on": date(2026, 9, 20), "last_document_on": D,
            "certificate_on": D, "missing": [SUPPL], "persons": [ION], "notary": NOTARY, "done": {}}
    return {**base, **kw}


def step(plan, code):
    return next(s for s in plan["steps"] if s["code"] == code)


def done_at(*codes_days):
    return {c: {"at": (D + timedelta(days=n)).isoformat()} for c, n in codes_days}


# ---- thresholds
def test_initial_message_on_day_0_on_a_permitted_channel():
    p = contact_plan(dossier(), D)
    s = step(p, "INITIAL")
    assert s["status"] == "due" and s["action"] == "message" and s["template_id"] == "MISSING_DOCS_FIRST"
    assert s["recipients"] == [{"id": "H1", "name": "Ion Ionescu", "role": "heir", "channel": "email"}]
    assert "GDPR art. 6" in s["basis"] and p["next"]["code"] == "INITIAL" and p["due_now"] == [s]


def test_reminder_at_14_days_without_answer():
    d = dossier(done=done_at(("INITIAL", 0)))
    assert step(contact_plan(d, D + timedelta(days=13)), "REMINDER")["status"] == "upcoming"
    s = step(contact_plan(d, D + timedelta(days=14)), "REMINDER")
    assert s["status"] == "due" and s["template_id"] == "MISSING_DOCS_REMINDER"


def test_registered_letter_at_30_days_to_the_domicile():
    d = dossier(done=done_at(("INITIAL", 0), ("REMINDER", 14)))
    assert step(contact_plan(d, D + timedelta(days=29)), "REGISTERED_LETTER")["status"] == "upcoming"
    s = step(contact_plan(d, D + timedelta(days=30)), "REGISTERED_LETTER")
    assert s["status"] == "due" and s["action"] == "registered_letter"
    assert s["recipients"][0]["address"] == "Str. Fictivă nr. 1" and s["recipients"][0]["channel"] == "posta_recomandata"
    # nobody with an address: the step goes to the operator
    no_addr = dossier(persons=[{**ION, "address": None}], done=d["done"])
    assert step(contact_plan(no_addr, D + timedelta(days=30)), "REGISTERED_LETTER")["action"] == "operator"


def test_notary_request_at_60_days():
    d = dossier(done=done_at(("INITIAL", 0), ("REMINDER", 14), ("REGISTERED_LETTER", 30)))
    assert step(contact_plan(d, D + timedelta(days=59)), "NOTARY")["status"] == "upcoming"
    s = step(contact_plan(d, D + timedelta(days=60)), "NOTARY")
    assert s["status"] == "due" and s["action"] == "notary_request" and s["recipients"][0]["case_file"] == "123/2026"
    assert "art. 105" in s["basis"]
    # no notary in the file: the operator, with the creditor's right to open the procedure when there is a loan
    s = step(contact_plan(dossier(notary=None, has_loan=True, done=d["done"]), D + timedelta(days=60)), "NOTARY")
    assert s["action"] == "operator" and "art. 103 alin. 3" in s["note"]


def test_deadline_warning_at_10_months_and_expiry_at_1_year_only_without_certificate():
    d = dossier(certificate_on=None, missing=["certificatul de moștenitor (de la notar)"], persons=[], notary=None)
    p = contact_plan(d, date(2027, 7, 2))
    assert step(p, "DEADLINE_WARNING")["due"] == "2027-07-03" and step(p, "DEADLINE_WARNING")["status"] == "upcoming"
    p = contact_plan(d, date(2027, 7, 3))
    w = step(p, "DEADLINE_WARNING")
    assert w["status"] == "due" and w["action"] == "operator"   # nobody to warn: the operator
    assert "2027-09-03" in w["note"] and "art. 1.103" in w["basis"]
    p = contact_plan({**d, "done": {"DEADLINE_WARNING": {"at": "2027-07-03"}}}, date(2027, 9, 3))
    e = step(p, "OPTION_EXPIRED")
    assert e["status"] == "due" and e["action"] == "operator" and "art. 1.112" in e["basis"] and "fără comisioane" in e["note"]
    # with a heir certificate the heirs accepted: no option deadline on the ladder
    assert not [s for s in contact_plan(dossier(), date(2027, 9, 3))["steps"] if s["track"] == "termen"]


def test_deadline_warning_goes_to_known_people_when_there_are_any():
    d = dossier(certificate_on=None, persons=[{**ION, "role": "notifier", "id": "N1"}])
    w = step(contact_plan(d, date(2027, 7, 3)), "DEADLINE_WARNING")
    assert w["action"] == "message" and w["template_id"] == "DEADLINE_SOON" and w["recipients"][0]["role"] == "notifier"


def test_add_months_follows_art_2552():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2027, 12, 31), 2) == date(2028, 2, 29)
    assert add_months(date(2026, 9, 3), 12) == date(2027, 9, 3)


# ---- order, channels, minor
def test_a_clock_jump_makes_only_the_latest_step_due():
    p = contact_plan(dossier(), D + timedelta(days=45))
    assert [(s["code"], s["status"]) for s in p["steps"]] == [
        ("INITIAL", "skipped"), ("REMINDER", "skipped"), ("REGISTERED_LETTER", "due"), ("NOTARY", "upcoming")]


def test_steps_count_from_the_last_document():
    later = D + timedelta(days=10)
    s = step(contact_plan(dossier(last_document_on=later, done=done_at(("INITIAL", 0))), D + timedelta(days=14)), "REMINDER")
    assert s["status"] == "upcoming" and s["due"] == (later + timedelta(days=14)).isoformat()


def test_no_channel_waits_on_day_0_then_goes_to_the_operator():
    d = dossier(certificate_on=None, persons=[], missing=["certificatul de moștenitor (de la notar)"])
    p = contact_plan(d, D)
    assert step(p, "INITIAL")["status"] == "waiting" and p["due_now"] == []
    s = step(contact_plan(d, D + timedelta(days=14)), "REMINDER")
    assert s["status"] == "due" and s["action"] == "operator" and "Nicio persoană" in s["note"]


def test_sms_only_with_consent_and_app_for_clients():
    phone_only = {**ION, "channels": {"phone": "+40 700"}}
    assert step(contact_plan(dossier(persons=[phone_only]), D), "INITIAL")["recipients"] == []
    consent = {**ION, "channels": {"phone": "+40 700", "consent": {"sms": True}}}
    assert step(contact_plan(dossier(persons=[consent]), D), "INITIAL")["recipients"][0]["channel"] == "sms"
    client = {**ION, "channels": {"app": True}}
    assert step(contact_plan(dossier(persons=[client]), D), "INITIAL")["recipients"][0]["channel"] == "app"


def test_minor_is_blocked_and_gets_a_monthly_reminder_to_the_representative():
    d = dossier(missing=[MINOR], persons=[ION, ELENA])
    p = contact_plan(d, D)
    assert [s["code"] for s in p["steps"]] == ["MINOR_INITIAL:H3"]   # the minor's papers never go to letter / notary
    s = p["steps"][0]
    assert s["status"] == "due" and s["recipients"][0]["name"] == "Ion Ionescu" and s["template_id"] == "MINOR_REPRESENTATION"
    assert p["blocked"][0]["heir"] == "Elena Ionescu" and "149" in p["blocked"][0]["basis"]
    d["done"] = {"MINOR_INITIAL:H3": {"at": D.isoformat()}}
    nxt = step(contact_plan(d, D), "MINOR_REMINDER_1:H3")
    assert nxt["status"] == "upcoming" and nxt["due"] == "2026-11-22"
    d["done"]["MINOR_REMINDER_1:H3"] = {"at": "2026-11-22"}
    assert step(contact_plan(d, date(2026, 12, 22)), "MINOR_REMINDER_2:H3")["status"] == "due"


def test_representative_named_by_the_extractor_instead_of_an_id():
    ion = {**ION, "name": "IONESCU ION"}
    elena = {**ELENA, "name": "IONESCU ELENA", "representative_id": "Ion Ionescu"}
    p = contact_plan(dossier(missing=["acordul scris al reprezentantului legal pentru IONESCU ELENA (minor)"],
                             persons=[ion, elena]), D)
    s = p["steps"][0]
    assert s["action"] == "message" and s["recipients"][0]["name"] == "IONESCU ION"


def test_nothing_missing_means_no_ladder_but_history_is_kept():
    assert contact_plan(dossier(missing=[]), D)["steps"] == []
    p = contact_plan(dossier(missing=[], done=done_at(("INITIAL", 0))), D)
    assert [(s["code"], s["status"]) for s in p["steps"]] == [("INITIAL", "done")] and p["next"] is None


# ---- API
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    c = TestClient(api.app)
    c.post("/demo/reset")
    yield c
    c.post("/demo/reset")


def test_advance_clock_only_in_demo_mode(client, monkeypatch):
    client.post("/demo/step/1")
    monkeypatch.delenv("DEMO_MODE")
    assert client.post("/demo/advance-clock?days=14").status_code == 403
    monkeypatch.setenv("DEMO_MODE", "1")
    r = client.post("/demo/advance-clock?days=14").json()
    assert r["offset_days"] == 14 and r["today"]["SC-2026-0001"] == "2026-10-04"
    client.post("/demo/reset")
    assert client.get("/demo/clock").json()["offset_days"] == 0


def test_api_ladder_dedupe_escalation_and_flag(client):
    for n in (1, 2):
        client.post(f"/demo/step/{n}")
    plan = client.get("/cases/SC-2026-0001/contact-plan").json()
    assert plan["next"]["code"] == "INITIAL" and plan["next"]["status"] == "waiting"   # DGEP gives no heirs
    assert client.post("/cases/SC-2026-0001/contact-plan/REMINDER/done").status_code == 409   # not due yet
    client.post("/demo/advance-clock?days=14")
    r1 = client.post("/cases/SC-2026-0001/contact-plan/REMINDER/done", json={"by": "test"}).json()
    r2 = client.post("/cases/SC-2026-0001/contact-plan/REMINDER/done", json={"by": "test"}).json()
    assert r1["already"] is False and r1["escalation"] == "ESC-1" and r2["already"] is True
    case = client.get("/cases/SC-2026-0001").json()
    assert [e["code"] for e in case["escalations"]] == ["contact_no_channel"]   # once, not twice
    assert any("Scara de contact" in e["detail"] for e in case["events"])
    client.post("/demo/advance-clock?days=350")
    plan = client.get("/cases/SC-2026-0001/contact-plan").json()
    assert {s["code"] for s in plan["due_now"]} == {"NOTARY", "OPTION_EXPIRED"}
    client.post("/cases/SC-2026-0001/contact-plan/OPTION_EXPIRED/done")
    case = client.get("/cases/SC-2026-0001").json()
    assert any(f["code"] == "presumed_renunciation" for f in case["flags"])
    assert case["escalations"][-1]["code"] == "option_deadline_passed"


def test_a_message_already_sent_counts_as_the_initial_contact(client):
    for n in (1, 2, 3, 4):
        client.post(f"/demo/step/{n}")
    assert client.get("/cases/SC-2026-0001/contact-plan").json()["next"]["code"] == "INITIAL"
    client.post("/messages", json={"case_id": "SC-2026-0001", "to": "Ion Ionescu", "channel": "email",
                                   "template_id": "SUPPLEMENT_NEEDED", "body": "Lipsește suplimentul."})
    plan = client.get("/cases/SC-2026-0001/contact-plan").json()
    assert step(plan, "INITIAL")["status"] == "done" and step(plan, "MINOR_INITIAL:H3")["status"] == "done"
    assert plan["next"]["code"] == "REMINDER"
    # the registered letter uses the domicile the bank knows (KYC) when the certificate's was not extracted
    client.post("/demo/advance-clock?days=30")
    s = step(client.get("/cases/SC-2026-0001/contact-plan").json(), "REGISTERED_LETTER")
    assert {r["name"] for r in s["recipients"]} == {"Ion Ionescu", "Andrei Ionescu"}
    assert s["recipients"][0]["address_source"] == "evidența băncii (KYC)"


def test_notifier_is_a_contact_before_the_certificate(client):
    client.post("/demo/step/1")
    assert client.post("/cases/SC-2026-0001/notifier", json={}).status_code == 422
    client.post("/cases/SC-2026-0001/notifier", json={"name": "Vecina Exemplu", "email": "v@x.invalid"})
    s = step(client.get("/cases/SC-2026-0001/contact-plan").json(), "INITIAL")
    assert s["status"] == "due" and s["recipients"][0] == {"id": "N1", "name": "Vecina Exemplu", "role": "notifier",
                                                           "channel": "email"}


# ---- autopilot
def _fake_server(monkeypatch, tmp_path, due):
    """A server that keeps the step due until it is marked done (like the API)."""
    done, posts = set(), []

    def fake(base, method, path, body=None):
        if path == "/autopilot/status":
            return {"run_dir": str(tmp_path)}
        if path == "/cases":
            return [{"id": "C1"}, {"id": "SC-NEIDENTIFICAT", "kind": "unmatched"}]
        if path == "/cases/C1/contact-plan":
            return {"due_now": [s for s in due if s["code"] not in done]}
        if path.endswith("/done"):
            code = path.split("/")[-2]
            posts.append(("done", code, body))
            done.add(code)
            return {"already": False}
        if path.startswith("/cases/"):
            return {"id": "C1"}
        posts.append((path, body))
        return {"ok": 1}
    monkeypatch.setattr(autopilot, "api", fake)
    return posts


def test_autopilot_applies_a_due_step_once(monkeypatch, tmp_path):
    msg = {"code": "REMINDER", "label": "Reminder", "action": "message", "template_id": "MISSING_DOCS_REMINDER",
           "basis": "b", "missing": [SUPPL], "recipients": [{"id": "H1", "name": "Ion Ionescu", "channel": "email"}]}
    letter = {"code": "MINOR_REMINDER_1:H3", "label": "Scrisoare", "action": "registered_letter", "basis": "b",
              "recipients": [{"name": "Ion Ionescu", "address": "Str. 1"}]}
    posts = _fake_server(monkeypatch, tmp_path, [msg, letter])
    calls = []
    monkeypatch.setattr(autopilot, "run_agent", lambda agent, task, ctx, timeout=0: (calls.append(agent) or "text", {"ok": True}))
    p = autopilot.Autopilot("http://x")
    assert p.contact_ladder() == 2 and p.contact_ladder() == 0   # second poll: nothing due any more
    assert calls == ["heir-communicator", "correspondent"]
    sent = [x[1] for x in posts if x[0] == "/messages"]
    assert len(sent) == 1 and sent[0]["template_id"] == "MISSING_DOCS_REMINDER" and sent[0]["channel"] == "email"
    dones = [(x[1], x[2]) for x in posts if x[0] == "done"]
    assert [c for c, _ in dones] == ["REMINDER", "MINOR_REMINDER_1:H3"]
    assert dones[1][1]["artifact"] == "letters/C1-contact-MINOR_REMINDER_1-H3.md"
    assert (tmp_path / "letters" / "C1-contact-MINOR_REMINDER_1-H3.md").is_file()


def test_autopilot_does_not_retry_a_failed_step_and_sends_operator_steps_without_agent(monkeypatch, tmp_path):
    msg = {"code": "INITIAL", "label": "Mesaj", "action": "message", "template_id": "MISSING_DOCS_FIRST", "basis": "b",
           "recipients": [{"id": "H1", "name": "Ion Ionescu", "channel": "email"}]}
    op = {"code": "OPTION_EXPIRED", "label": "Termen", "action": "operator", "basis": "b", "recipients": []}
    posts = _fake_server(monkeypatch, tmp_path, [msg, op])
    calls = []
    monkeypatch.setattr(autopilot, "run_agent", lambda agent, task, ctx, timeout=0: (
        calls.append(agent) or "", {"ok": False, "error": "timeout"}))
    p = autopilot.Autopilot("http://x")
    assert p.contact_ladder() == 1 and p.contact_ladder() == 0
    assert calls == ["heir-communicator", "heir-communicator"]   # one retry inside call(), then not again
    assert [x[1] for x in posts if x[0] == "done"] == ["OPTION_EXPIRED"]
