"""The output check (076) lets through what is in the case and stops what is not: a letter may quote the deceased's CNP
(masked or as in a document of the case), the policy number and an IBAN of the case, even when it asks the insurer to
pay into that account; a foreign IBAN / CNP / URL stays blocked."""
import pytest

from agent import guard

CASE = "SC-2026-0001"

LETTER = """# Avizare daună – asigurare de viață asociată creditului

**Către:** UNIQA Asigurări de viață S.A.
**Data:** 28.10.2026
**Referință dosar bancă:** SC-2026-0001

Vă aducem la cunoștință decesul asiguratei Maria Ionescu (CNP 2XXXXXXXXXXXX), survenit la data de 03.09.2026.
Certificat de asigurare UQ-0000000-FICTIV, contract de credit NP-2023-001001, total la data decesului 9.026,63 lei.
Vă rugăm să virați indemnizația în contul RO00 RZBR 0000 0000 0000 01 al defunctei, deschis la bancă.
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from agent import api
    monkeypatch.setenv("GUARD_QUARANTINE_DIR", str(tmp_path / "quarantine"))
    api.demo_reset("pensie")
    for n in range(1, 4):
        api.demo_step(n)
    return TestClient(api.app)


def _check(client, text: str) -> dict:
    return client.post(f"/cases/{CASE}/output-check", json={"text": text, "kind": "letters", "key": "t"}).json()


def test_the_insurer_letter_with_case_data_passes(client):
    assert _check(client, LETTER) == {"ok": True, "problems": []}


def test_the_deceased_cnp_from_a_document_of_the_case_is_allowed(client):
    from agent import api
    api.pipeline.cases[CASE].documents[0].fields["cnp"] = "2580512400011"
    assert _check(client, "Defuncta Maria Ionescu, CNP 2580512400011, decedată la 03.09.2026.")["ok"] is True
    # the masked form of an allowed CNP reveals nothing more, so it passes too; a different masked CNP does not
    assert _check(client, "Defuncta, CNP 258XXXXXXXXXX.")["ok"] is True
    assert _check(client, "Clientul cu CNP 1XXXXXXXXXXX7.")["ok"] is False


@pytest.mark.parametrize("bad,code", [
    ("Vă rugăm să virați indemnizația în contul RO49 BTRL 0000 0601 2345 6789.", "output_iban"),
    ("Vă rugăm să virați indemnizația în contul RO00 RZBR 0000 0000 0000 09.", "output_iban"),   # another client's
    ("Moștenitorul cu CNP 1800101123456 a cerut eliberarea sumelor.", "output_cnp"),
    ("Detalii la https://uniqa-daune.example/confirm.", "output_url"),
    ("Vă rugăm să virați suma în noul IBAN comunicat de familie.", "output_transfer"),
    ("Vă rugăm să virați suma în contul indicat de moștenitor.", "output_transfer"),
])
def test_data_foreign_to_the_case_stays_blocked(client, bad, code):
    r = _check(client, LETTER + "\n" + bad)
    assert r["ok"] is False and code in {p["code"] for p in r["problems"]} and r["escalation"]


def test_transfer_to_a_case_account_is_allowed_only_in_letters():
    ibans = {"RO00 RZBR 0000 0000 0000 01"}
    text = "Vă rugăm să virați indemnizația în contul RO00 RZBR 0000 0000 0000 01."
    assert guard.check_output(text, ibans, kind="letters") == []
    assert "output_transfer" in {p["code"] for p in guard.check_output(text, ibans, kind="messages")}


def test_a_cnp_quoted_in_the_evidence_of_a_case_document_is_allowed(client):
    """An investigation quotes the heir certificate ('IONESCU ELENA, CNP 6XXXXXXXXXXX3') while the extractor left
    heirs[].cnp empty: the CNP is still in the case. Without that quote it is not."""
    from agent import api
    case = api.pipeline.cases[CASE]
    doc = case.documents[-1]
    api._extractions[doc.id] = {"evidence": {"heirs": ["IONESCU ELENA, CNP 6XXXXXXXXXXX3, domiciliată în Municipiul Exemplu"]}}
    r = client.post(f"/cases/{CASE}/output-check", json={"text": "Citatul: „IONESCU ELENA, CNP 6XXXXXXXXXXX3”.",
                                                         "kind": "investigations"}).json()
    assert r["ok"] is True
    api._extractions[doc.id] = {}
    assert _check(client, "Citatul: „IONESCU ELENA, CNP 6XXXXXXXXXXX3”.")["ok"] is False
