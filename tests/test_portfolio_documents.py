"""090: the portfolio's documents are real files (registries/portofoliu/documente/) and what the pipeline gets is their
real extraction (.extras.json, agent/portfolio.py), not the reference values of P*.json; the preview serves every one."""
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import api, portfolio
from agent.doc_preview import PORTFOLIO_DOCS, resolve_source

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.portfolio_extract import accuracy  # noqa: E402

CLIENTS = portfolio.clients()
# the documents seeded at reset (a `pending` one has not come yet: the guided demo feeds it, tests/test_case_steps.py)
STEPS = [(c, s["doc"]) for c in CLIENTS for s in portfolio.history(c) if "doc" in s]
THRESHOLD = 0.97
# real extractor errors, noted (registries/portofoliu/documente/README.md), not corrected: the notari.pro letter of
# P13/P14 has no hearing date, a mandatory field for the extractor, so it scores 0,5 although it is perfectly legible
KNOWN_GATE_ERRORS = {"P13-D4", "P14-D4"}


@pytest.fixture(scope="module")
def client():
    c = TestClient(api.app)
    c.post("/demo/reset?portofoliu=1")
    yield c
    c.post("/demo/reset")


def test_every_document_step_has_its_files():
    assert len(STEPS) >= 45
    for c, d in STEPS:
        assert d["file"].startswith(c["id"] + "/") and "fields" not in d and "confidence" not in d, d["id"]
        stem = portfolio.extras_file(d).name.removesuffix(".extras.json")
        for f in (portfolio.received_file(d), portfolio.scan_file(d), portfolio.extras_file(d),
                  portfolio.DOCS / c["id"] / f"{stem}.md", portfolio.DOCS / c["id"] / f"{stem}.pdf"):
            assert f.is_file(), f
        assert portfolio.scan_file(d).read_bytes()[:5] == b"%PDF-"
        if d["expected_type"] == "dgep_signal":   # the batch line itself, with the fields of the DGEP note
            line = json.loads((portfolio.DOCS / c["id"] / f"{stem}.json").read_text(encoding="utf-8"))
            assert line["cnp"] == d["expected_fields"]["cnp"] and line["message_id"] == d["expected_fields"]["document_number"]


def test_every_document_of_every_case_previews_as_pdf(client):
    n = 0
    for c in CLIENTS:
        cid = c["case_id"]
        case = client.get(f"/cases/{cid}").json()
        docs = case["documents"]
        assert docs, cid
        for d in docs:
            r = client.get(f"/cases/{cid}/documents/{d['document_id']}/preview")
            assert r.status_code == 200 and r.headers["content-type"] == "application/pdf", (cid, d["document_id"])
            assert r.content[:5] == b"%PDF-" and d["source"].startswith("portofoliu/" + c["id"] + "/")
            n += 1
    # + the documents that wait among the unmatched ones (P01's photo, P13/P14's notary letters): same preview
    for e in client.get("/escalations").json():
        r = client.get(f"/cases/{api.ORPHAN_ID}/documents/{e['document_id']}/preview")
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf", e["document_id"]
        n += 1
    assert n == len(STEPS)


def test_the_seeded_fields_are_the_extraction_not_the_reference(client):
    differ = 0
    for c, d in STEPS:
        ex = json.loads(portfolio.extras_file(d).read_text(encoding="utf-8"))
        seeded = portfolio._document({"doc": d})
        assert seeded["fields"] == ex["fields"] and seeded["confidence"] == ex["confidence"]
        assert seeded["document_type"] == ex["document_type"] and seeded["raw_name"] == "portofoliu/" + d["file"]
        assert seeded["extractor"].get("model") or seeded["extractor"].get("skipped") == "guard", d["id"]
        assert seeded["extractor"]["extracted_at"] and seeded["extractor"]["file"] == d["file"], d["id"]
        differ += seeded["fields"] != d["expected_fields"]
    assert differ > 0   # the extraction reads more (name, birth date …) or differently than the reference: it is its own
    # what the case shows is what the extractor read
    case = client.get("/cases/SC-2026-0105").json()
    doc = next(x for x in case["documents"] if x["document_id"] == "P05-D4")
    ex = json.loads(portfolio.extras_file(next(d for _, d in STEPS if d["id"] == "P05-D4")).read_text(encoding="utf-8"))
    assert doc["confidence"] == ex["confidence"]
    assert {f["name"]: f["value"] for f in doc["fields"]}["case_file"] == ex["fields"]["case_file"]


def test_the_extraction_matches_the_reference():
    r = accuracy()
    assert r["field_accuracy"] >= THRESHOLD, r["errors"]
    assert r["type_ok"] == r["documents"], r["errors"]
    assert {e["id"] for e in r["errors"] if e["field"].startswith("confidence")} == KNOWN_GATE_ERRORS
    for field, frac in r["by_field"].items():   # no field is systematically wrong (where there are enough of it)
        ok, n = map(int, frac.split("/"))
        assert n < 5 or ok / n >= 0.8, (field, frac)
    assert r["not_extracted"] and all(x.startswith("P09-D4") for x in r["not_extracted"])   # quarantined, by design


def test_the_suspicious_attachment_never_reached_the_extractor():
    d = next(d for _, d in STEPS if d["id"] == "P09-D4")
    ex = json.loads(portfolio.extras_file(d).read_text(encoding="utf-8"))
    assert ex["extractor"]["skipped"] == "guard" and ex["guard"]["risk"] == "high" and ex["fields"] == {}
    assert any(f["code"] == "pdf_hidden_text" for f in ex["guard"]["flags"])


def test_portfolio_extract_1_extracts_again_at_reset(monkeypatch):
    calls = []

    def fake(d):
        calls.append(d["id"])
        return json.loads(portfolio.extras_file(d).read_text(encoding="utf-8"))

    monkeypatch.setattr(portfolio, "extract", fake)
    monkeypatch.setenv("PORTFOLIO_EXTRACT", "1")
    c = TestClient(api.app)
    try:
        assert len(c.post("/demo/reset?portofoliu=1").json()["portfolio"]) == len(CLIENTS)
        assert sorted(calls) == sorted(d["id"] for _, d in STEPS)
    finally:
        monkeypatch.delenv("PORTFOLIO_EXTRACT")
        c.post("/demo/reset")


@pytest.mark.parametrize("raw", ["portofoliu/../P05-ioan-georgescu.json", "portofoliu/P05/../../../agent/api.py",
                                 "portofoliu//etc/passwd", "portofoliu/P05/02-adresa-notar.extras.json/..",
                                 "portofoliu/P05/nu-exista.pdf", "portofoliu/P05/genereaza.py"])
def test_the_portfolio_preview_stays_inside_its_folder(raw):
    p = resolve_source(raw)
    assert p is None or PORTFOLIO_DOCS in p.parents


def test_the_portfolio_prefix_does_not_reach_the_corpus():
    assert resolve_source("portofoliu/P05/02-adresa-notar-scan.pdf") == PORTFOLIO_DOCS / "P05" / "02-adresa-notar-scan.pdf"
    assert resolve_source("scan/02-adresa-notar.pdf") is not None            # the demo corpus is unchanged
