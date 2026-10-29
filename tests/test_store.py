"""084: persistence (agent/store.py). The objects survive to_dict/from_dict exactly; a real API process stopped at
INSURANCE_CLAIM_OPEN and started again has the case exactly where it was and can go on to the payment."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi.testclient import TestClient

from agent import api
from agent.case_state import Case
from agent.core_mock import Bank
from agent.demo_documents import DOCUMENTS
from agent.pipeline import Pipeline
from agent.store import Store, dumps

ROOT = Path(__file__).resolve().parent.parent
CASE = "SC-2026-0001"


def test_case_and_bank_round_trip_exactly():
    bank = Bank({"pensie", "retragere"})
    p = Pipeline(bank)
    for d in DOCUMENTS[:6]:
        p.receive(json.loads(json.dumps(d)))
    p.approve_payment(CASE, "test")
    for c in p.cases.values():
        back = Case.from_dict(json.loads(dumps(c.to_dict())))
        assert back == c, c.id
        assert isinstance(back.milestones, set) and back.date_of_death == c.date_of_death
    again = Bank.from_dict(json.loads(dumps(bank.to_dict())))
    assert again.to_dict() == bank.to_dict()
    assert again.products("RC1001") == bank.products("RC1001")       # Fraction, dates: typed again, not strings
    assert again.movements("RC1001") == bank.movements("RC1001") and again.reversed_fees == bank.reversed_fees


def test_store_writes_only_what_changed_in_one_transaction(tmp_path):
    s = Store(str(tmp_path / "x.sqlite"))
    assert s.load() is None
    assert s.save({"A": {"n": 1}}, {"bank": {"x": 1}}) == 2 and s.writes == 1
    assert s.save({"A": {"n": 1}}, {"bank": {"x": 1}}) == 0 and s.writes == 1      # nothing changed: no write
    assert s.save({"B": {"n": 2}}, {"bank": {"x": 1}}) == 2                       # A deleted, B written
    s.close()
    again = Store(str(tmp_path / "x.sqlite"))
    assert again.load() == {"cases": {"B": {"n": 2}}, "bank": {"x": 1}}
    assert Store(":memory:").load() is None and Store(":memory:").save({"A": {}}, {}) == 0


def test_every_changing_request_is_saved_and_reloads():
    c = TestClient(api.app)
    c.post("/demo/reset?gol=1")
    for n in (1, 2, 3):
        c.post(f"/demo/step/{n}")
    before = c.get(f"/cases/{CASE}").json()
    assert before["state"] == "INSURANCE_CLAIM_OPEN"
    saved = api.store.load()
    assert set(saved["cases"]) == {CASE} and saved["cases"][CASE]["state"] == "INSURANCE_CLAIM_OPEN"
    # what a new process does at start: the saved state replaces the memory
    api.pipeline.cases.clear()
    api.bank.reset()
    api._restore(saved)
    assert c.get(f"/cases/{CASE}").json() == before


# ---------------------------------------------------------------- the real thing: a process stopped and started again
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _call(base: str, method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw and raw[:1] in b"[{" else raw.decode()
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "detail": e.read().decode()}


def _start(tmp: Path, port: int, run_id: str) -> subprocess.Popen:
    env = {**os.environ, "MVP_DB": str(tmp / "mvp.sqlite"), "RUNS_DIR": str(tmp / "runs"), "RUN_ID": run_id,
           "MVP_PORTFOLIO": "1", "DEMO_MODE": "1", "GUARD_QUARANTINE_DIR": str(tmp / "q")}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "agent.api:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(100):
        try:
            if _call(f"http://127.0.0.1:{port}", "GET", "/health") == {"status": "ok"}:
                return proc
        except OSError:
            pass
        if proc.poll() is not None:
            raise RuntimeError(proc.stderr.read().decode()[-2000:])
        time.sleep(0.2)
    proc.kill()
    raise RuntimeError("API-ul nu a pornit")


def test_restart_keeps_the_case_at_insurance_claim_open_and_it_goes_on_to_payment(tmp_path):
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = _start(tmp_path, port, "run-1")
    try:
        assert _call(base, "POST", "/demo/reset")["status"] == "reset"           # portfolio + Maria at zero
        for n in (1, 2, 3):
            _call(base, "POST", f"/demo/step/{n}")
        assert _call(base, "POST", f"/cases/{CASE}/letters/notary/sign", {"signer": "Test"})["signed"]
        tok = _call(base, "POST", f"/cases/{CASE}/upload-token", {"to": "Ion Ionescu"})
        _call(base, "POST", "/demo/advance-clock?days=3")
        case = _call(base, "GET", f"/cases/{CASE}")
        assert case["state"] == "INSURANCE_CLAIM_OPEN"
        work, audit = _call(base, "GET", "/worklist"), _call(base, "GET", "/audit")
        clock = _call(base, "GET", "/demo/clock")
        (tmp_path / "runs" / "run-1" / "letters").mkdir(parents=True, exist_ok=True)
        (tmp_path / "runs" / "run-1" / "letters" / f"{CASE}-notary_answer_drafted.md").write_text("# Răspuns\n", "utf-8")
    finally:
        proc.send_signal(signal.SIGKILL)                                          # no shutdown hook: what was committed stays
        proc.wait(10)

    proc = _start(tmp_path, port, "run-2")                                        # a new run directory, like dev-up
    try:
        assert _call(base, "GET", f"/cases/{CASE}") == case
        assert _call(base, "GET", "/worklist") == work and _call(base, "GET", "/audit") == audit
        assert _call(base, "GET", "/demo/clock") == clock
        assert "Încărcare documente" in _call(base, "GET", f"/upload?token={tok['token']}")   # the heir's link still works
        arts = _call(base, "GET", f"/cases/{CASE}/artifacts")
        assert any(a["file"] == f"letters/{CASE}-notary_answer_drafted.md" for a in arts["artifacts"])
        assert _call(base, "GET", "/autopilot/status")["run_dir"].endswith("run-2")
        for n in (4, 5, 6):
            _call(base, "POST", f"/demo/step/{n}")
        case = _call(base, "GET", f"/cases/{CASE}")
        assert case["state"] == "PAYMENT_PENDING_APPROVAL" and case["payment_plan"]["net_account"]["net"] == 527337
        assert _call(base, "POST", f"/payments/PAY-{CASE}/approve", {"approver": "test"})["status"] == "approved"
        assert _call(base, "GET", f"/cases/{CASE}")["state"] == "PAID"
        paid = [e for e in _call(base, "GET", "/audit") if e.get("action") == "pay" and e["cif"] == "RC1001"]
        assert [(e["count"], e["total"]) for e in paid] == [(2, 428461)]
    finally:
        proc.terminate()
        proc.wait(10)
