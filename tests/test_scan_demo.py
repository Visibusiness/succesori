"""Scanned originals in the guided demo: the scans exist and have no text layer, /demo/step?source=scan queues the scan
in the inbox and /demo/received follows it, the autopilot reads a scan visually (no LLM call here: extract_file is faked)."""
import copy
import sys
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agent import api, inbox_portal  # noqa: E402
from agent.demo_documents import DOCUMENTS, SCAN_DIR, VARIANT_B, scan_file  # noqa: E402
import autopilot  # noqa: E402


@pytest.mark.parametrize("n,variant", [(2, "A"), (3, "A"), (4, "A"), (4, "B"), (5, "A"), (6, "A"), (7, "A")])
def test_every_paper_document_has_a_scan_without_text(n, variant):
    path = scan_file(n, variant)
    assert path is not None and path.parent == SCAN_DIR
    pdf = fitz.open(path)
    assert pdf.page_count >= 1 and all(not page.get_text().strip() for page in pdf)   # only the page images


def test_dgep_line_has_no_scan_and_previews_point_to_the_scans():
    assert scan_file(1) is None
    assert DOCUMENTS[0]["raw_name"] == "01-dgep-semnal.json"
    assert [d["raw_name"] for d in DOCUMENTS[1:]] == [f"scan/{scan_file(n).name}" for n in range(2, 8)]
    assert VARIANT_B["raw_name"] == "scan/04-certificat-mostenitor-B.pdf"


def test_scan_step_queues_the_scan_and_received_follows_it(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox_portal, "INBOX", tmp_path)
    c = TestClient(api.app)
    c.post("/demo/reset")
    assert c.post("/demo/step/1?source=scan").json()["state"] == "FROZEN"     # electronic: fed directly
    q = c.post("/demo/step/2?source=scan").json()
    assert q == {"queued": "02-adresa-notar.pdf", "step": 2, "source": "scan"}
    assert (tmp_path / q["queued"]).read_bytes() == scan_file(2).read_bytes()
    assert c.get(f"/demo/received/{q['queued']}").json()["status"] == "waiting"
    # what the autopilot does once the extractor has read the scan
    doc = {**copy.deepcopy(DOCUMENTS[1]), "raw_name": q["queued"]}
    doc.pop("id")
    c.post("/documents", json=doc)
    st = c.get(f"/demo/received/{q['queued']}").json()
    assert st["status"] == "done" and st["result"]["state"] == "NOTARY_ANSWERED" and st["result"]["document_id"]
    assert c.post("/demo/step/4?source=scan&variant=B").json()["queued"] == "04-certificat-mostenitor-B.pdf"
    assert c.post("/demo/step/2?source=nu").status_code == 422


def test_autopilot_reads_a_scan_visually(tmp_path, monkeypatch):
    import agent.extract
    seen = []
    monkeypatch.setattr(agent.extract, "extract_file", lambda path, name=None, hint="auto": seen.append(Path(path).name) or
                        {"document_type": "notary_request", "confidence": 0.9, "fields": {}, "raw_name": name})
    monkeypatch.setattr(agent.extract, "extract", lambda *a, **k: pytest.fail("a scan has no text to extract"))
    f = tmp_path / "02-adresa-notar.pdf"
    f.write_bytes(scan_file(2).read_bytes())
    doc = autopilot.to_document(f)
    assert seen == ["02-adresa-notar.pdf"] and doc["document_type"] == "notary_request" and doc["raw_name"] == f.name


def test_scan_of_any_step_is_served_before_it_is_processed():
    c = TestClient(api.app)
    c.post("/demo/reset")
    r = c.get("/demo/scan/4/file?variant=B")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content == scan_file(4, "B").read_bytes()
    r = c.get("/demo/scan/1/file")                                   # step 1: the DGEP batch line, not a scan
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json") and b"cnp" in r.content
    assert c.get("/demo/scan/8/file").status_code == 404
