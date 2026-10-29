"""040: the autopilot's artifacts endpoint, status endpoint and its pure decision function (no LLM calls)."""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agent import api  # noqa: E402
import autopilot  # noqa: E402


def test_artifacts_lists_files_written_for_the_case():
    c = TestClient(api.app)
    letters = api.trace.dir / "letters"
    letters.mkdir(parents=True, exist_ok=True)
    (letters / "SC-2026-0001-notary_answer_drafted.md").write_text("# Draft\nrăspuns", encoding="utf-8")
    (letters / "SC-2026-0002-notary_answer_drafted.md").write_text("alt dosar", encoding="utf-8")
    (api.trace.dir / "audit.md").write_text("# Audit\nok", encoding="utf-8")
    r = c.get("/cases/SC-2026-0001/artifacts").json()
    assert [a["file"] for a in r["artifacts"]] == ["letters/SC-2026-0001-notary_answer_drafted.md"]
    assert r["artifacts"][0]["kind"] == "letter" and "răspuns" in r["artifacts"][0]["content"]
    assert r["audit"].startswith("# Audit")


def test_autopilot_status_gives_run_dir_and_heartbeat():
    c = TestClient(api.app)
    (api.trace.dir / "autopilot-status.json").unlink(missing_ok=True)
    st = c.get("/autopilot/status").json()
    assert st["run_dir"] == str(api.trace.dir) and st["running"] is False and st["autopilot"] is None
    hb = {"pid": 1, "state": "idle", "last_poll": autopilot.now()}
    (api.trace.dir / "autopilot-status.json").write_text(json.dumps(hb), encoding="utf-8")
    assert c.get("/autopilot/status").json()["running"] is True


def test_plan_followups_picks_agents_from_the_api_answer():
    case = {"heirs": [{"id": "H1", "name": "Ion Ionescu"}]}
    jobs = autopilot.plan_followups({"case_id": "SC-2026-0001", "actions": ["notary_answer_drafted", "frozen"],
                                     "missing": ["certificatul suplimentar"], "escalation": "ESC-2"}, case)
    assert [j["agent"] for j in jobs] == ["case-investigator", "correspondent", "heir-communicator"]
    # orphan case / no heirs yet -> nobody to message
    assert autopilot.plan_followups({"case_id": "SC-NEIDENTIFICAT", "escalation": "ESC-1", "missing": ["x"]}, None) == [
        {"agent": "case-investigator", "kind": "investigations", "key": "SC-NEIDENTIFICAT-ESC-1", "escalation": "ESC-1",
         "trigger": "escaladare ESC-1"}]


def test_pdf_text_reads_generated_pdfs():
    pdf = Path(__file__).resolve().parent.parent / "registries" / "documents" / "pdf" / "04-certificat-mostenitor-B.pdf"
    text = autopilot.pdf_text(pdf)
    assert "CERTIFICAT DE MOȘTENITOR" in text and "legatar cu titlu universal" in text
    assert autopilot.pdf_text(pdf.with_name("07-certificat-deces-ilizibil.pdf")) == ""   # scan: no text layer


# ---- 057: dedupe, audit modes, event ids, notary deadline at signature
def _pilot(monkeypatch, tmp_path, audit="milestones", cases=None):
    calls, posts = [], []
    monkeypatch.setattr(autopilot, "api", lambda base, method, path, body=None: (
        {"run_dir": str(tmp_path)} if path == "/autopilot/status" else
        {"id": "C1", "heirs": [{"id": "H1", "name": "Ion Ionescu"}], "payment_plan": (cases or {}).get("plan")} if path.startswith("/cases/") else
        ([] if path == "/cases" else (posts.append((path, body)) or {"ok": 1}))))
    monkeypatch.setattr(autopilot, "run_agent", lambda agent, task, ctx, timeout=0: (
        calls.append(agent) or "corp mesaj", {"ok": True}))
    return autopilot.Autopilot("http://x", audit=audit), calls, posts


def test_message_key_ignores_order_and_dedupes(monkeypatch, tmp_path):
    assert autopilot.message_key("T", ["b", "a"]) == autopilot.message_key("T", ["a", "b"])
    p, calls, posts = _pilot(monkeypatch, tmp_path)
    r = {"case_id": "C1", "missing": ["certificatul de moștenitor"], "actions": []}
    p.followups(r); p.followups(r)                      # second identical message is skipped
    p.followups({**r, "missing": ["acordul pentru minor"]})   # different missing set -> new message
    assert calls.count("heir-communicator") == 2 and len(posts) == 2
    assert posts[1][1]["template_id"] == "MINOR_REPRESENTATION"
    # the dedupe state is persisted and reloaded
    assert autopilot.Autopilot("http://x", audit="milestones").messages_sent == p.messages_sent


def test_audit_modes(monkeypatch, tmp_path):
    p, calls, _ = _pilot(monkeypatch, tmp_path)
    assert p.milestone_reached({"case_id": "C1", "escalation": "ESC-1"}) == "escaladare ESC-1"
    assert p.milestone_reached({"case_id": "C1", "escalation": "ESC-1"}) is None      # same escalation: no second audit
    assert p.milestone_reached({"case_id": "C1"}) is None                              # no plan yet
    p2, _, _ = _pilot(monkeypatch, tmp_path, cases={"plan": {"id": "PP-C1"}})
    assert p2.milestone_reached({"case_id": "C1"}) == "plan de plată C1"
    assert p2.milestone_reached({"case_id": "C1"}) is None
    # finish(): closing audit only if something changed since the last one
    p3, calls3, _ = _pilot(monkeypatch, tmp_path)
    p3.finish(); assert "auditor" not in calls3
    p3.dirty = True; p3.finish(); p3.finish(); assert calls3.count("auditor") == 1
    p4, calls4, _ = _pilot(monkeypatch, tmp_path, audit="every")
    p4.dirty = True; p4.finish(); assert "auditor" not in calls4                       # `every` audits per document, not at the end


def test_events_have_stable_ids_and_notary_deadline_closes_at_signature():
    c = TestClient(api.app)
    c.post("/demo/reset")
    for n in (1, 2):
        c.post(f"/demo/step/{n}")
    case = c.get("/cases").json()[0]
    view = c.get(f"/cases/{case['id']}").json()
    ids = [e["id"] for e in view["events"]]
    assert ids == [f"E{i}" for i in range(1, len(ids) + 1)]
    dl = lambda: next(d["status"] for d in c.get(f"/cases/{case['id']}").json()["deadlines"] if d["code"] == "notary_answer")
    assert dl() != "îndeplinit"                                                      # draft only: still open
    assert c.post(f"/cases/{case['id']}/letters/notary/sign", json={}).status_code == 422
    assert c.post("/cases/NU-EXISTA/letters/notary/sign", json={"signer": "x"}).status_code == 404
    assert c.post(f"/cases/{case['id']}/letters/notary/sign", json={"signer": "ops_approver"}).json()["deadline"] == "îndeplinit"
    n_events = len(c.get(f"/cases/{case['id']}").json()["events"])
    c.post(f"/cases/{case['id']}/letters/notary/sign", json={"signer": "ops_approver"})   # idempotent
    assert len(c.get(f"/cases/{case['id']}").json()["events"]) == n_events and dl() == "îndeplinit"


def test_heir_is_not_asked_for_the_insurers_answer():
    case = {"heirs": [{"id": "H1", "name": "Ion Ionescu"}]}
    r = {"case_id": "C1", "missing": ["răspunsul asigurătorului la dosarul de daună"]}
    assert autopilot.plan_followups(r, case) == []
    r["missing"].append("acordul scris al reprezentantului legal pentru X (minor)")
    jobs = autopilot.plan_followups(r, case)
    assert jobs[0]["missing"] == ["acordul scris al reprezentantului legal pentru X (minor)"]


# ---- 072: one run per server (restart / reset), clean inbox, one final folder per file
def test_demo_reset_clears_the_run_and_changes_the_epoch():
    c = TestClient(api.app)
    st = c.get("/autopilot/status").json()
    d = Path(st["run_dir"])
    for kind in ("letters", "messages", "investigations"):
        (d / kind).mkdir(parents=True, exist_ok=True)
        (d / kind / "SC-2026-0001-x.md").write_text("vechi", encoding="utf-8")
    (d / "audit.md").write_text("vechi", encoding="utf-8")
    (d / "outbox.jsonl").write_text('{"case_id": "SC-2026-0001"}\n', encoding="utf-8")
    (d / "autopilot-status.json").write_text(json.dumps({"state": "idle", "last_poll": autopilot.now(),
                                                         "messages_sent": {"SC-2026-0001": "k"}}), encoding="utf-8")
    (api.trace.dir.parent / "latest").unlink(missing_ok=True)
    r = c.post("/demo/reset").json()
    assert r["run_dir"] == str(d) and r["epoch"] != st["epoch"]
    assert c.get("/cases/SC-2026-0001/artifacts").json() == {"case_id": "SC-2026-0001", "artifacts": [], "audit": None, "handoffs": []}
    assert c.get("/messages").json() == [] and c.get("/autopilot/status").json()["autopilot"] is None
    assert (d.parent / "latest").resolve() == d.resolve()
    assert any(json.loads(l)["kind"] == "reset" for l in (d / "trace.jsonl").read_text(encoding="utf-8").splitlines())


def test_demo_reset_with_inbox_archives_waiting_processed_and_failed(tmp_path, monkeypatch):
    from agent import inbox_portal
    monkeypatch.setattr(inbox_portal, "INBOX", tmp_path)
    for rel in ("a.md", "processed/b.md", "failed/c.md", ".tmp-x"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    assert TestClient(api.app).post("/demo/reset?inbox=true").json()["inbox_archived"] == 3
    left = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file() and ".archive" not in p.parts)
    assert left == [".tmp-x"] and len(list((tmp_path / ".archive").rglob("*.md"))) == 3


def test_autopilot_follows_a_new_epoch_and_forgets_its_state(monkeypatch, tmp_path):
    server = {"run_dir": str(tmp_path / "r1"), "epoch": "e1"}
    monkeypatch.setattr(autopilot, "api", lambda base, method, path, body=None: dict(server))
    p = autopilot.Autopilot("http://x")
    assert p.run_dir == tmp_path / "r1" and p.sync_run() is False
    p.messages_sent, p.processed, p.audited_milestones = {"C1": "k"}, [{"file": "a"}], {"C1:plan"}
    server["epoch"] = "e2"                                   # /demo/reset
    assert p.sync_run() is True and (p.messages_sent, p.processed, p.audited_milestones) == ({}, [], set())
    server.update(run_dir=str(tmp_path / "r2"), epoch="e3")  # server restarted on a new RUN_ID
    assert p.sync_run() is True and p.run_dir == tmp_path / "r2"


def test_done_path_never_reuses_a_name_from_processed_or_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(autopilot, "INBOX", tmp_path)
    assert autopilot.done_path("04.md", ok=False) == tmp_path / "failed" / "04.md"
    (tmp_path / "failed" / "04.md").write_text("x", encoding="utf-8")
    assert autopilot.done_path("04.md", ok=True) == tmp_path / "processed" / "04-2.md"


def test_heir_gets_two_messages_in_the_demo_flow(monkeypatch, tmp_path):
    """Missing lists after docs 4, 5, 6 (scenario §3): supplement+minor+claim docs, then supplement+minor, then minor."""
    p, calls, posts = _pilot(monkeypatch, tmp_path)
    supp, minor, claim = "certificat suplimentar pentru: DEP-1", "acordul scris al reprezentantului legal pentru Elena (minor)", "documentele pentru dosarul de daună"
    for missing in ([supp, minor, claim], [supp, minor], [minor]):
        p.followups({"case_id": "C1", "missing": missing, "actions": []})
    assert [b["template_id"] for _, b in posts] == ["SUPPLEMENT_NEEDED", "MINOR_REPRESENTATION"]
    assert autopilot.already_asked(autopilot.message_key("T", ["a"]), "T", ["a", "b"]) is False   # something new
