"""078: documents with problems -> a message to whoever sent them (agent/deficiencies.py, API, autopilot, mailer)."""
import copy
import json
from datetime import date
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import api, deficiencies as dfx, mailer
from agent.demo_documents import DOCUMENTS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import autopilot  # noqa: E402

CASE = "SC-2026-0001"
ADV = Path(__file__).resolve().parent.parent / "registries" / "documents" / "adversarial"
ILLEGIBLE = {"document_type": "death_certificate", "confidence": 0.41, "received_on": "2026-10-01",
             "fields": {"cnp": None, "cnp_raw": "2#####", "date_of_death": None, "document_number": None}}
GOOD_DEATH = {"document_type": "death_certificate", "confidence": 0.95, "received_on": "2026-10-02",
              "fields": {"cnp": DOCUMENTS[0]["fields"]["cnp"], "date_of_death": "2026-09-03", "document_number": "123456"}}


# ---- detection (pure)
def codes(problems):
    return [p["code"] for p in problems]


def test_illegible_names_the_zones_that_cannot_be_read():
    p = dfx.detect(ILLEGIBLE, {})
    assert codes(p) == ["illegible"]
    assert "CNP-ul persoanei decedate" in p[0]["text"] and "data decesului" in p[0]["text"]
    assert "scanare clară" in p[0]["text"]


def test_mandatory_fields_per_type_and_who_to_ask():
    doc = {"document_type": "heir_certificate", "confidence": 0.9,
           "fields": {"cnp": "2XXXXXXXXXXXX", "heirs": [{"name": "A", "share": "1"}]}}
    p = dfx.detect(doc, {})
    assert codes(p) == ["field_missing"] and p[0]["field"] == "case_file" and p[0]["ask_role"] == "notary"
    assert "numărul dosarului succesoral" in p[0]["text"] and "notarul" in p[0]["text"]
    death = {"document_type": "death_certificate", "confidence": 0.9, "fields": {"name": "X", "birth_date": "1950-01-01"}}
    p = dfx.detect(death, {})
    assert [(x["code"], x["field"]) for x in p] == [("field_missing", "date_of_death")] and "stare civilă" in p[0]["ask"]


def test_cnp_of_someone_else_shares_and_minor_without_representative():
    doc = {"document_type": "heir_certificate", "confidence": 0.9,
           "fields": {"cnp": "1700101000007", "case_file": "1/2026",
                      "heirs": [{"name": "A", "share": "1/2"}, {"name": "B", "share": "1/4", "minor": True}]}}
    p = dfx.detect(doc, {"deceased_cnp": "2580512000000"})
    assert codes(p) == ["cnp_mismatch", "shares_invalid", "minor_without_representative"]
    assert "2580512000000" not in json.dumps(p) and "1/4" not in json.dumps(p)   # no CNP, no shares in the texts
    assert p[2]["ask_role"] == "legal_representative"
    assert dfx.detect({**doc, "fields": {**doc["fields"], "cnp": "2XXXXXXXXXXXX"}}, {"deceased_cnp": "2580512000000"})[0]["code"] != "cnp_mismatch"


def test_certificate_without_a_product_asks_the_notary_for_a_supplement():
    doc = copy.deepcopy(DOCUMENTS[3])
    p = dfx.detect(doc, {"coverage_gaps": ["depozitul la termen"], "sender_is_heir": True})
    assert codes(p) == ["certificate_incomplete"] and p[0]["handled_by_bank"]
    assert "certificat de moștenitor suplimentar" in p[0]["text"] and "notarul" in p[0]["text"]
    assert "depozitul la termen" in p[0]["text"]
    # not a heir in the certificate: no product named (bank secrecy)
    assert "depozitul" not in dfx.detect(doc, {"coverage_gaps": ["depozitul la termen"]})[0]["text"]


def test_suspicious_document_gets_only_the_neutral_text():
    p = dfx.detect({"document_type": "unknown", "fields": {"cnp": "2XXXXXXXXXXXX"}}, {"quarantined": True})
    assert codes(p) == ["suspicious"] and p[0]["text"] == dfx.NEUTRAL_SUSPICIOUS and p[0]["neutral"]
    assert "agenți" in p[0]["text"]


def test_pages_missing_and_wrong_type():
    text = "CERTIFICAT DE MOȘTENITOR\nPagina 1 din 3\n...\nPagina 3 din 3"
    assert dfx.pages_missing(text, None) == [2]
    assert dfx.pages_missing(text, 3) == []           # the file has 3 pages: a number was simply not read
    doc = copy.deepcopy(DOCUMENTS[2])                 # insurance certificate, while the heir certificate was asked for
    p = dfx.detect(doc, {"expected_types": ["heir_certificate"], "text": text})
    assert codes(p) == ["pages_missing", "wrong_type"] and "certificatul de moștenitor" in p[1]["text"]


def test_the_demo_documents_have_no_problems():
    for d in DOCUMENTS[:6]:
        assert dfx.detect(d, {"deceased_cnp": DOCUMENTS[0]["fields"]["cnp"]}) == [], d["id"]


def test_sender_order_and_unknown():
    assert dfx.resolve_sender("death_certificate", "Andrei", {"name": "Vecina"}, "Ion")["source"] == "upload_token"
    assert dfx.resolve_sender("insurer_response", None, {"name": "Vecina"}, "Ion")["source"] == "institution"
    assert dfx.resolve_sender("death_certificate", None, {"name": "Vecina"}, "Ion")["name"] == "Vecina"
    assert dfx.resolve_sender("death_certificate", None, None, "Ion")["source"] == "last_message"
    assert dfx.resolve_sender("death_certificate", None, None, None) is None


# ---- API
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.delenv("MAILER", raising=False)
    c = TestClient(api.app)
    c.post("/demo/reset")
    yield c
    c.post("/demo/reset")


def fake_extract(monkeypatch, doc):
    import agent.extract
    monkeypatch.setattr(agent.extract, "extract", lambda text, name, hint="auto": {**copy.deepcopy(doc), "raw_name": name})


def link(client, to):
    return client.post(f"/cases/{CASE}/upload-token", json={"to": to}).json()["token"]


def upload(client, token, name, data=b"scan"):
    r = client.post(f"/upload?token={token}", files={"file": (name, data, "text/plain")})
    assert r.status_code == 200, r.text
    return r


def pending(client):
    return client.get(f"/cases/{CASE}/deficiencies").json()["pending"]


def send(client, n, body="Am primit documentul. {{UPLOAD_URL}}/cases/" + CASE + "/upload?token={{token}}"):
    return client.post("/messages", json={"case_id": CASE, "to": n["to"], "channel": n["channel"], "to_role": n["to_role"],
                                          "template_id": "DOCUMENT_DEFICIENT", "body": body,
                                          "deficiency": {"document_id": n["document_id"]}})


def test_illegible_upload_by_link_dedupe_ladder_and_the_corrected_document_closes_it(client, monkeypatch):
    for n in (1, 2, 3):
        client.post(f"/demo/step/{n}")
    tok = link(client, "Andrei Ionescu")
    fake_extract(monkeypatch, ILLEGIBLE)
    upload(client, tok, "certificat-deces-poza.txt")
    [n] = pending(client)
    assert n["to"] == "Andrei Ionescu" and n["channel"] == "email" and n["sender_source"] == "upload_token"
    assert [p["code"] for p in n["problems"]] == ["illegible"] and "data decesului" in n["problems"][0]["text"]
    assert n["document"] == {"label": "certificatul de deces", "name": "certificat-deces-poza.txt",
                             "received_on": date.today().isoformat()}   # the upload date, not one the extractor read
    # someone else than the sender: refused
    assert client.post("/messages", json={**{"case_id": CASE, "to": "Ion Ionescu", "channel": "email", "body": "x",
                                             "template_id": "DOCUMENT_DEFICIENT"},
                                          "deficiency": {"document_id": n["document_id"]}}).status_code == 422
    assert send(client, n, "Sunați la {{CONTACT_PHONE}}.").status_code == 422   # an unresolved field never leaves
    r = send(client, n)
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["template_id"] == "DOCUMENT_DEFICIENT" and "/upload?token=" in msg["body"] and "{{token}}" not in msg["body"]
    assert msg["deficiency"] == {"document_id": n["document_id"], "problems": ["illegible"]}
    out = [json.loads(line) for line in api._outbox().read_text(encoding="utf-8").splitlines()]
    assert out[-1]["address"] == "andrei.ionescu@example.invalid" and out[-1]["status"] == "queued_mock"
    # dedupe: the same problem is not sent twice, and the same file sent again brings nothing new
    assert send(client, n).status_code == 409 and pending(client) == []
    assert msg["body"].count("{{") == 0
    upload(client, tok, "certificat-deces-poza.txt")
    assert pending(client) == []
    again = client.get(f"/cases/{CASE}").json()["deficiencies"][-1]
    assert again["document_id"] != n["document_id"] and again["problems"][0]["already_notified"]
    # the open problem is in the contact ladder until fixed
    plan = client.get(f"/cases/{CASE}/contact-plan").json()
    assert any("certificatul de deces, refăcut" in m for s in plan["steps"] for m in s.get("missing") or [])
    case = client.get(f"/cases/{CASE}").json()
    rec = next(r for r in case["deficiencies"] if r["document_id"] == n["document_id"])
    assert rec["problems"][0]["notified_at"] and rec["problems"][0]["notified_to"] == "Andrei Ionescu"
    # the corrected document closes it (new link, the same person)
    fake_extract(monkeypatch, GOOD_DEATH)   # through the new link from the message (asked: the death certificate)
    upload(client, msg["body"].split("/upload?token=")[1].split()[0], "certificat-deces-bun.txt")
    case = client.get(f"/cases/{CASE}").json()
    rec = next(r for r in case["deficiencies"] if r["document_id"] == n["document_id"])
    assert rec["status"] == "closed" and rec["problems"][0]["status"] == "closed"
    plan = client.get(f"/cases/{CASE}/contact-plan").json()
    assert not any("refăcut" in m for s in plan["steps"] for m in s.get("missing") or [])
    assert pending(client) == []


def test_certificate_without_the_deposit_asks_for_the_supplement_and_the_supplement_closes_it(client, monkeypatch):
    for n in (1, 2, 3):
        client.post(f"/demo/step/{n}")
    fake_extract(monkeypatch, DOCUMENTS[3])
    upload(client, link(client, "Ion Ionescu"), "certificat-mostenitor.txt")
    [n] = pending(client)
    assert n["to"] == "Ion Ionescu" and [p["code"] for p in n["problems"]] == ["certificate_incomplete"]
    text = n["problems"][0]["text"]
    assert "notarul" in text and "suplimentar" in text and "depozitul la termen" in text   # Ion is a heir in it
    assert "20" not in text and "lei" not in text
    msg = send(client, n).json()
    # the document view in the case shows the problem and when the message went
    doc = next(d for d in client.get(f"/cases/{CASE}").json()["documents"] if d["document_id"] == n["document_id"])
    assert doc["problems"][0]["code"] == "certificate_incomplete" and doc["problems"][0]["notified_at"]
    fake_extract(monkeypatch, DOCUMENTS[5])   # the supplement, through the new link: what that link asked for
    upload(client, msg["body"].split("/upload?token=")[1].split()[0], "certificat-suplimentar.txt")
    recs = client.get(f"/cases/{CASE}").json()["deficiencies"]
    assert len(recs) == 1 and recs[0]["status"] == "closed" and "suplimentar" in recs[0]["problems"][0]["closed_by"]
    assert pending(client) == []


def test_suspicious_upload_gets_a_neutral_message_without_details(client):
    pytest.importorskip("agent.guard")   # 076: the gate that quarantines the file
    for n in (1, 2, 3):
        client.post(f"/demo/step/{n}")
    data = (ADV / "A01-pdf-text-alb-aproba-plata.pdf").read_bytes()
    r = client.post(f"/upload?token={link(client, 'Andrei Ionescu')}",
                    files={"file": ("A01-pdf-text-alb-aproba-plata.pdf", data, "application/pdf")})
    assert r.status_code == 200
    [n] = pending(client)
    assert [p["text"] for p in n["problems"]] == [dfx.NEUTRAL_SUSPICIOUS]
    assert n["document"]["name"] is None and n["document"]["label"] == "documentul"   # not even the name or the claimed type
    dumped = json.dumps(n, ensure_ascii=False).lower()
    for word in ("aprob", "suspect", "carantin", "injection", "hidden", "ascuns", "flag"):
        assert word not in dumped, word
    assert send(client, n).status_code == 422   # no upload link: the original goes to an agency
    assert send(client, n, "Nu am putut procesa documentul trimis online. Vă rugăm să îl aduceți la o agenție.").status_code == 200


def test_unknown_sender_goes_to_the_operator_and_nobody_is_written_to(client):
    for n in (1, 2, 3):
        client.post(f"/demo/step/{n}")
    doc = copy.deepcopy(DOCUMENTS[3])
    doc["fields"].pop("case_file")
    doc["fields"].pop("reference")
    client.post("/documents", json=doc)   # through the intake: no link, no notifier, no message before
    assert pending(client) == []
    case = client.get(f"/cases/{CASE}").json()
    esc = [e for e in case["escalations"] if e["code"] == "document_deficient_no_sender"]
    assert len(esc) == 1 and "numărul dosarului succesoral" in esc[0]["reason"] and "ghicire" in esc[0]["reason"]


def test_institution_document_is_for_the_operator_and_the_notifier_is_a_sender(client):
    client.post("/demo/step/1")
    resp = copy.deepcopy(DOCUMENTS[4])
    resp["fields"].pop("decision")
    client.post("/documents", json=resp)
    case = client.get(f"/cases/{CASE}").json()
    assert [e["code"] for e in case["escalations"]][-1] == "document_deficient_institution"
    client.post(f"/cases/{CASE}/notifier", json={"name": "Vecina Exemplu", "email": "v@x.invalid"})
    client.post("/documents", json={**copy.deepcopy(ILLEGIBLE), "id": "doc-x"})
    # an illegible document from the intake went to the unmatched documents: it has no case, so nobody is written to
    assert pending(client) == []


def test_the_smoke_flow_sends_no_deficiency_message_and_no_extra_escalation(client):
    for n in range(1, 8):
        client.post(f"/demo/step/{n}")
    assert pending(client) == []
    case = client.get(f"/cases/{CASE}").json()
    assert not [e for e in case["escalations"] if e["code"].startswith("document_deficient")]
    assert len(client.get("/escalations").json()) == 1


# ---- autopilot
def test_autopilot_sends_each_pending_notice_once_with_only_the_public_view(monkeypatch, tmp_path):
    notice = {"document_id": "doc-9", "to": "Andrei Ionescu", "channel": "email", "to_role": "uploader",
              "document": {"label": "certificatul de deces", "name": "poza.jpg", "received_on": "2026-10-01"},
              "problems": [{"code": "illegible", "text": "Nu am putut citi clar certificatul de deces.", "ask": "dumneavoastră",
                            "ask_role": "sender"}]}
    sent, prompts = [], []

    def fake(base, method, path, body=None):
        if path == "/autopilot/status":
            return {"run_dir": str(tmp_path)}
        if path == "/cases":
            return [{"id": CASE}, {"id": "SC-NEIDENTIFICAT", "kind": "unmatched"}]
        if path.endswith("/deficiencies"):
            return {"pending": [] if sent else [notice]}
        if path == "/messages":
            sent.append(body)
            return {"message_id": "MSG-1"}
        return {"ok": True}
    monkeypatch.setattr(autopilot, "api", fake)
    monkeypatch.setattr(autopilot, "run_agent", lambda agent, task, ctx, timeout=0: (
        prompts.append((agent, task, ctx)) or "Bună ziua, ... {{UPLOAD_URL}}/cases/x/upload?token={{token}}", {"ok": True}))
    p = autopilot.Autopilot("http://x")
    assert p.deficiency_notices() == 1 and p.deficiency_notices() == 0
    [(agent, task, ctx)] = prompts
    assert agent == "heir-communicator" and "DOCUMENT_DEFICIENT" in task and "upload?token={{token}}" in task
    assert set(ctx) == {"case_id", "to", "channel", "document", "problems"}   # no case JSON: no balances, no other heirs
    [m] = sent
    assert m["template_id"] == "DOCUMENT_DEFICIENT" and m["deficiency"] == {"document_id": "doc-9"} and m["to_role"] == "uploader"
    assert (tmp_path / "messages" / f"{CASE}-deficient-doc-9.md").is_file()


def test_autopilot_does_not_retry_a_failed_notice(monkeypatch, tmp_path):
    notice = {"document_id": "doc-9", "to": "A", "channel": "email", "document": {"label": "documentul"}, "problems": [
        {"code": "illegible", "text": "t", "ask": "a", "ask_role": "sender"}]}
    monkeypatch.setattr(autopilot, "api", lambda b, m, path, body=None: {"run_dir": str(tmp_path)} if path == "/autopilot/status"
                        else [{"id": CASE}] if path == "/cases" else {"pending": [notice]})
    calls = []
    monkeypatch.setattr(autopilot, "run_agent", lambda *a, **k: (calls.append(1) or "", {"ok": False, "error": "timeout"}))
    p = autopilot.Autopilot("http://x")
    assert p.deficiency_notices() == 0 and p.deficiency_notices() == 0 and len(calls) == 2   # one retry, then never


# ---- mailer
def test_mailer_is_the_outbox_unless_smtp_is_asked_explicitly(tmp_path):
    out = tmp_path / "outbox.jsonl"
    m = mailer.get_mailer(out, {})
    assert isinstance(m, mailer.OutboxMailer)
    m.send({"to": "A", "channel": "email", "body": "b"})
    assert json.loads(out.read_text())["to"] == "A"
    assert isinstance(mailer.get_mailer(out, {"SMTP_HOST": "smtp.example.invalid"}), mailer.OutboxMailer)   # host alone: off
    with pytest.raises(ValueError):
        mailer.get_mailer(out, {"MAILER": "smtp"})        # explicit, but without a host
    with pytest.raises(ValueError):
        mailer.get_mailer(out, {"MAILER": "fax"})
    assert isinstance(mailer.get_mailer(out, {"MAILER": "smtp", "SMTP_HOST": "h"}), mailer.SmtpMailer)


def test_smtp_mailer_with_a_fake_server(tmp_path):
    """No real SMTP: a stand-in records what would have been sent."""
    seen = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=0):
            seen.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            seen.append(("tls",))

        def login(self, u, p):
            seen.append(("login", u))

        def send_message(self, em):
            seen.append(("send", em["To"], em.get_content().strip()))

    out = tmp_path / "outbox.jsonl"
    m = mailer.SmtpMailer(mailer.OutboxMailer(out), "h", 2525, "u", "p", smtp=FakeSMTP)
    r = m.send({"case_id": "C", "to": "A", "channel": "email", "address": "a@example.invalid", "body": "Bună ziua"})
    assert r["status"] == "sent_smtp" and seen == [("connect", "h", 2525), ("tls",), ("login", "u"),
                                                   ("send", "a@example.invalid", "Bună ziua")]
    r = m.send({"case_id": "C", "to": "A", "channel": "sms", "body": "x"})
    assert r["status"] == "queued_mock" and len(seen) == 4   # no adapter for SMS: stays in the outbox
    assert len(out.read_text().splitlines()) == 2


def test_post_messages_answers_503_when_the_mailer_is_misconfigured(client, monkeypatch):
    client.post("/demo/step/1")
    monkeypatch.setenv("MAILER", "smtp")
    r = client.post("/messages", json={"case_id": CASE, "to": "Ion Ionescu", "channel": "email",
                                       "template_id": "MISSING_DOCS_FIRST", "body": "x"})
    assert r.status_code == 503 and client.get(f"/messages?case_id={CASE}").json() == []


def test_an_open_problem_goes_up_the_contact_ladder_to_its_sender(client, monkeypatch):
    for n in (1, 2, 3):
        client.post(f"/demo/step/{n}")
    fake_extract(monkeypatch, ILLEGIBLE)
    upload(client, link(client, "Andrei Ionescu"), "poza.txt")
    [n] = pending(client)
    assert send(client, n).status_code == 200   # counts as the initial contact of the ladder
    client.post("/demo/advance-clock?days=14")
    s = next(x for x in client.get(f"/cases/{CASE}/contact-plan").json()["steps"] if x["code"] == "REMINDER")
    assert s["status"] == "due" and s["action"] == "message" and s["template_id"] == "MISSING_DOCS_REMINDER"
    assert [(r["name"], r["role"], r["channel"]) for r in s["recipients"]] == [("Andrei Ionescu", "uploader", "email")]
    assert any("certificatul de deces, refăcut" in m for m in s["missing"])
    r = client.post("/messages", json={"case_id": CASE, "to": "Andrei Ionescu", "channel": "email", "to_role": "uploader",
                                       "template_id": "MISSING_DOCS_REMINDER", "body": "Reamintire."})
    assert r.status_code == 200
