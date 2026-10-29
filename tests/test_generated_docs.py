"""GET /cases/{id}/generated (agent/generated_docs.py): every document the bank generated for a case, listed with its
title, author and formats, and served as PDF / Markdown / text, inline or as a download with a clear name. The id is
opaque: nothing outside the list can be reached."""
import json

import pytest
from fastapi.testclient import TestClient

from agent import api, generated_docs

CID = "SC-2026-0001"
LETTER = ('<!-- {"generated_at": "2026-09-28T10:00:00+00:00", "agent": "correspondent", "ok": true} -->\n'
          f"# Draft: răspunsul băncii către notar — {CID}\n\nStimată doamnă notar,\n\n| Produs | Sold |\n|---|---|\n| Cont curent | 1.250,40 lei |\n")
MESSAGE = ('<!-- {"generated_at": "2026-09-29T10:00:00+00:00", "agent": "heir-communicator", "ok": true} -->\n'
           f"# Mesaj către Ion Ionescu (MISSING_DOCS_FIRST) — {CID}\n\nBună ziua. Încărcați aici: "
           "{{UPLOAD_URL}}/cases/" + CID + "/upload?token={{token}}\n")


@pytest.fixture(scope="module")
def c():
    client = TestClient(api.app)
    client.post("/demo/reset")
    client.post("/demo/step/1")
    client.post("/demo/step/2")
    run = api.trace.dir
    for rel, text in ((f"letters/{CID}-notary_answer_drafted.md", LETTER), (f"messages/{CID}-01.md", MESSAGE),
                      (f"investigations/{CID}-ESC-9.md", "# Investigație ESC-9\n\nPropun să acceptați documentul."),
                      ("audits/audit-01.md", f"# Audit\n\n{CID}: toate regulile respectate.\n"),
                      ("audits/audit-02.md", "# Audit\n\nAlt dosar.\n"),
                      ("letters/SC-2026-0999-notary_answer_drafted.md", "# Altul\n\nNu e al Mariei.")):
        (run / rel).parent.mkdir(parents=True, exist_ok=True)
        (run / rel).write_text(text, encoding="utf-8")
    yield client
    client.post("/demo/reset")


def _docs(c):
    r = c.get(f"/cases/{CID}/generated")
    assert r.status_code == 200
    return r.json()


def test_list_has_every_source_with_title_author_and_formats(c):
    docs = _docs(c)
    kinds = {d["kind"] for d in docs}
    assert {"notary_answer", "letter", "message", "investigation", "audit"} <= kinds
    letter = next(d for d in docs if d["kind"] == "letter")
    assert letter["title"] == "Răspunsul către notar" and letter["author"] == "Corespondentul"
    assert letter["created"].startswith("2026-09-28") and "notar" in letter["recipient"]
    assert letter["formats"] == ["pdf", "md", "txt"] and letter["filename"].startswith(CID)
    assert letter["event_id"]   # the journal entry that produced it
    system = next(d for d in docs if d["kind"] == "notary_answer")
    assert system["author"].startswith("Sistemul") and system["filename"] == f"{CID}-raspuns-notar-sistem.pdf"
    assert letter["filename"] == f"{CID}-raspuns-notar.pdf"
    assert next(d for d in docs if d["kind"] == "investigation")["escalation_id"] == "ESC-9"
    assert len([d for d in docs if d["kind"] == "audit"]) == 1          # only the audit that names the case
    assert all(d["case_id"] == CID for d in docs)                         # nothing of another case
    assert len({d["id"] for d in docs}) == len(docs) and len({d["filename"] for d in docs}) == len(docs)


def test_pdf_is_valid_and_inline(c):
    for d in _docs(c):
        r = c.get(d["url"])
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF-")
        assert r.headers["content-disposition"].startswith("inline")


def test_markdown_and_text(c):
    letter = next(d for d in _docs(c) if d["kind"] == "letter")
    md = c.get(letter["urls"]["md"])
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert md.text.startswith("# Răspunsul către notar") and "| Cont curent | 1.250,40 lei |" in md.text and "<!--" not in md.text
    txt = c.get(letter["urls"]["txt"])
    assert txt.headers["content-type"].startswith("text/plain") and "|" not in txt.text and "Cont curent" in txt.text


def test_download_is_an_attachment_with_a_clear_name(c):
    d = next(d for d in _docs(c) if d["kind"] == "notary_answer")
    r = c.get(d["download_url"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")
    assert r.headers["content-disposition"] == f'attachment; filename="{CID}-raspuns-notar-sistem.pdf"'
    r = c.get(d["urls"]["md"] + "&download=1")
    assert r.headers["content-disposition"] == f'attachment; filename="{CID}-raspuns-notar-sistem.md"'


def test_sent_message_replaces_the_draft_and_hides_the_link(c):
    body = "Bună ziua. Încărcați aici: {{UPLOAD_URL}}/cases/" + CID + "/upload?token={{token}}"
    with (api.trace.dir / "outbox.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"message_id": "MSG-1", "at": "2026-09-29T11:00:00+00:00", "case_id": CID, "to": "Ion Ionescu",
                            "channel": "email", "template_id": "MISSING_DOCS_FIRST", "kind": "operational",
                            "body": body.replace("{{UPLOAD_URL}}", "http://h").replace("{{token}}", "SECRETTOKEN"),
                            "status": "queued_mock"}) + "\n")
    msgs = [d for d in _docs(c) if d["kind"] == "message"]
    assert len(msgs) == 1 and msgs[0]["message_id"] == "MSG-1" and msgs[0]["status"].startswith("trimis")
    text = c.get(msgs[0]["urls"]["md"]).text
    assert "SECRETTOKEN" not in text and "[link securizat de încărcare]" in text


def test_unknown_document_or_case_is_404(c):
    assert c.get(f"/cases/{CID}/generated/g0000000000000000").status_code == 404
    assert c.get("/cases/SC-NU-EXISTA/generated").status_code == 404
    d = _docs(c)[0]
    assert c.get(f"/cases/SC-NU-EXISTA/generated/{d['id']}").status_code == 404
    assert c.get(f"{d['url'].split('?')[0]}?format=exe").status_code == 400


@pytest.mark.parametrize("doc_id", ["..%2F..%2Fagent%2Fapi.py", "../../etc/passwd", "letters%2FSC-2026-0001-notary_answer_drafted.md",
                                    "%2E%2E%2Fmvp.sqlite", "letters/SC-2026-0001-notary_answer_drafted"])
def test_path_traversal_is_refused(c, doc_id):
    assert c.get(f"/cases/{CID}/generated/{doc_id}?format=md").status_code in (400, 404)
    assert c.get(f"/cases/..%2F..%2Fetc/generated/{doc_id}").status_code in (400, 404)


def test_pdf_of_a_letter_kept_on_disk_is_served_as_is(c):
    pdf = api.trace.dir / "letters" / f"{CID}-notary_answer_drafted.pdf"
    pdf.write_bytes(b"%PDF-1.7 semnat")
    letter = next(d for d in _docs(c) if d["kind"] == "letter")
    assert c.get(letter["url"]).content == b"%PDF-1.7 semnat" and "trimis" in letter["status"]
    pdf.unlink()


def test_registry_works_on_its_own_sources(tmp_path):
    """No API: a case view and an empty run directory give the documents of the bank's rules (portfolio clients)."""
    view = {"case_id": "SC-X", "deceased": {"name": "Test"}, "products": [], "documents": [], "heirs": [], "missing": [],
            "events": [{"id": "E1", "at": "2026-08-01", "kind": "action", "detail": "Plan de plată generat: 1 linii", "data": {}}],
            "payment_plan": {"plan_id": "PP-X", "status": "pending_approval", "lines": [
                {"name": "A", "product_id": "P1", "share": "1/1", "amount": 1000, "blocked": False, "pay_on": "acum"}]}}
    src = generated_docs.Sources(run_dir=lambda: tmp_path, case_view=lambda cid: view if cid == "SC-X" else None)
    docs = generated_docs.collect("SC-X", src)
    assert [d.kind for d in docs] == ["payment_plan"] and docs[0].extra["event_id"] == "E1"
    assert generated_docs.render(docs[0], "pdf").startswith(b"%PDF-") and generated_docs.collect("SC-Y", src) is None
