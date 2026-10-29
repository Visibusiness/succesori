"""POST/GET /inbox: the intake portal writes only safe, new files into the inbox."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent import inbox_portal


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox_portal, "INBOX", tmp_path / "inbox")
    app = FastAPI()
    app.include_router(inbox_portal.make_router())
    c = TestClient(app)
    c.inbox = tmp_path / "inbox"
    return c


def _post(client, *items):
    return client.post("/inbox", files=[("files", it) for it in items])


def test_saves_text_json_and_pdf_and_lists_them(client):
    r = _post(client, ("02-adresa.md", b"text", "text/markdown"), ("x.json", b"{}", "application/json"), ("s.pdf", b"%PDF-1.4", "application/pdf"))
    assert r.status_code == 200 and sorted(r.json()["saved"]) == ["02-adresa.md", "s.pdf", "x.json"] and r.json()["rejected"] == []
    assert (client.inbox / "02-adresa.md").read_bytes() == b"text"
    assert sorted(client.get("/inbox").json()["waiting"]) == ["02-adresa.md", "s.pdf", "x.json"]


@pytest.mark.parametrize("raw,expected", [("../../etc/x.md", "x.md"), ("a b/ștefan ăș.txt", "tefan.txt"), ("C:\\dir\\doc.JSON", "doc.json"),
                                          (".ascuns.md", "ascuns.md"), ("...md", None), ("run.exe", None), ("fără-extensie", None), (None, None)])
def test_names_are_cleaned(raw, expected):
    assert inbox_portal.safe_name(raw) == expected


def test_rejects_unknown_type_empty_and_oversize(client, monkeypatch):
    monkeypatch.setattr(inbox_portal, "MAX_BYTES", 10)
    r = _post(client, ("run.exe", b"x", "application/octet-stream"), ("gol.md", b"  \n", "text/plain"), ("mare.md", b"x" * 11, "text/plain"),
              ("ok.md", b"x" * 10, "text/plain")).json()
    assert r["saved"] == ["ok.md"] and sorted(x["name"] for x in r["rejected"]) == ["gol.md", "mare.md", "run.exe"]


def test_never_overwrites_waiting_processed_or_failed(client):
    _post(client, ("a.md", b"1", "text/plain"))
    assert _post(client, ("a.md", b"2", "text/plain")).json()["saved"] == ["a-2.md"]
    (client.inbox / "processed").mkdir()
    (client.inbox / "processed" / "b.md").write_text("vechi")
    (client.inbox / "failed").mkdir()
    (client.inbox / "failed" / "c.md").write_text("vechi")
    assert _post(client, ("b.md", b"n", "text/plain"), ("c.md", b"n", "text/plain")).json()["saved"] == ["b-2.md", "c-2.md"]
    assert (client.inbox / "a.md").read_bytes() == b"1" and (client.inbox / "processed" / "b.md").read_text() == "vechi"


def test_no_temp_files_left_and_dotfiles_not_listed(client):
    _post(client, ("a.md", b"1", "text/plain"))
    (client.inbox / ".tmp-ascuns").write_text("x")
    assert [p.name for p in client.inbox.iterdir() if p.name.endswith(".tmp")] == []
    assert client.get("/inbox").json() == {"waiting": ["a.md"], "processed": [], "failed": []}
