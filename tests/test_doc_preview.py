"""GET /cases/{id}/documents/{doc}/preview: serves only corpus files, by the raw_name the pipeline recorded."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent import doc_preview


def _client(*raw_names):
    docs = [SimpleNamespace(id=f"doc-{i}", raw_name=n) for i, n in enumerate(raw_names, 1)]
    pipe = SimpleNamespace(cases={"SC-1": SimpleNamespace(documents=docs)})
    app = FastAPI()
    app.include_router(doc_preview.make_router(lambda: pipe))
    return TestClient(app)


def test_pdf_and_json_are_served_inline():
    c = _client("pdf/02-adresa-notar.pdf", "01-dgep-semnal.json")
    r = c.get("/cases/SC-1/documents/doc-1/preview")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert "inline" in r.headers["content-disposition"] and r.headers["x-content-type-options"] == "nosniff"
    r = c.get("/cases/SC-1/documents/doc-2/preview")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")


def test_text_is_served_as_plain_text():
    r = _client("02-adresa-notar.md").get("/cases/SC-1/documents/doc-1/preview")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain") and "IONESCU MARIA" in r.text


@pytest.mark.parametrize("raw", ["../agent/api.py", "../../etc/passwd", "/etc/passwd", "pdf/../../agent/api.py", "pdf/nu-exista.pdf",
                                 "", None, "pdf", "02-adresa-notar.exe"])
def test_nothing_outside_the_corpus_or_unknown(raw):
    assert _client(raw).get("/cases/SC-1/documents/doc-1/preview").status_code == 404


def test_unknown_case_and_document_are_404():
    c = _client("pdf/02-adresa-notar.pdf")
    assert c.get("/cases/NU/documents/doc-1/preview").status_code == 404
    assert c.get("/cases/SC-1/documents/doc-9/preview").status_code == 404


def test_portal_files_win_over_the_corpus_and_failed_ones_are_found(tmp_path, monkeypatch):
    processed, failed = tmp_path / "processed", tmp_path / "failed"
    processed.mkdir(); failed.mkdir()
    (processed / "02-adresa-notar.md").write_text("DIN PORTAL", encoding="utf-8")
    (failed / "scan.md").write_text("ESUAT", encoding="utf-8")
    (tmp_path / "in-afara.md").write_text("SECRET", encoding="utf-8")
    monkeypatch.setattr(doc_preview, "SOURCE_DIRS", [processed.resolve(), failed.resolve(), doc_preview.CORPUS])
    c = _client("02-adresa-notar.md", "scan.md", "../in-afara.md")
    assert c.get("/cases/SC-1/documents/doc-1/preview").text == "DIN PORTAL"
    assert c.get("/cases/SC-1/documents/doc-2/preview").text == "ESUAT"
    assert c.get("/cases/SC-1/documents/doc-3/preview").status_code == 404
