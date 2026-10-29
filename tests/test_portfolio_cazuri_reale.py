"""085: the two portfolio clients built on real court cases (registries/portofoliu/cazuri-reale, P13 and P14).
Each lands in its stage through the real pipeline; the figures are the hand calculations of the READMEs
(A-petrescu-marin §7, B-neagu-cristian §6), not rules.py. The two bugs found on the way are strict xfails."""
import copy
import json
import runpy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import api, portfolio
from agent.core_mock import _person_key

ROOT = Path(__file__).resolve().parent.parent
CLIENTS = {c["id"]: c for c in portfolio.clients()}
A, B = "SC-2026-0113", "SC-2026-0114"


@pytest.fixture()
def client():
    c = TestClient(api.app)
    c.post("/demo/reset?portofoliu=1")
    yield c
    c.post("/demo/reset")


def test_the_portfolio_files_are_generated_from_the_real_case_folders():
    gen = runpy.run_path(str(ROOT / "registries/portofoliu/cazuri-reale/portofoliu.py"))
    for spec in gen["CLIENTS"]:
        assert json.loads((ROOT / "registries/portofoliu" / spec["file"]).read_text(encoding="utf-8")) == \
            json.loads(json.dumps(gen["build"](spec), ensure_ascii=False))
    assert {"P13", "P14"} <= CLIENTS.keys()
    assert "825" in CLIENTS["P13"]["real_case"] and "839/A" in CLIENTS["P14"]["real_case"]


def test_a_petrescu_refused_by_the_insurer_debt_over_the_estate(client):
    # 089: the refusal no longer leaves the case waiting; the whole debt stays in the estate, it exceeds the assets
    # at the bank, so the plan pays 0 lei and an informative escalation says why (C.civ. art. 1114)
    case = client.get(f"/cases/{A}").json()
    assert case["state"] == "PAYMENT_PENDING_APPROVAL"
    assert all(l["amount"] == 0 for l in case["payment_plan"]["lines"])
    over = [e for e in case["escalations"] if e["code"] == "debt_exceeds_estate"]
    assert len(over) == 1 and "54750.16" in over[0]["reason"]
    refused = [e for e in case["escalations"] if e["code"] == "insurance_refused"]
    assert len(refused) == 1 and refused[0]["status"] == "deschis" and refused[0]["document_id"] == "P13-D6"
    # the reason is the extractor's reading of the refusal letter (090), which cites the 12/24-month clause
    assert "24 de luni" in refused[0]["reason"] and "pancreatită" in refused[0]["reason"]
    assert len(case["heirs"]) == 4


def test_b_neagu_plan_equals_the_hand_calculation(client):
    case = client.get(f"/cases/{B}").json()
    assert case["state"] == "PAYMENT_PENDING_APPROVAL"
    plan = case["payment_plan"]
    assert plan["status"] == "pending_approval"
    # §6.3: 18.420,00 − (71,15 dobânda neacoperită + 3.450,00 cardul) = 14.898,85 lei
    assert plan["net_account"] == {"product_id": "P14-CC", "gross": 1842000, "debts_deducted": 352115, "withheld": 0,
                                   "net": 1489885, "unpaid_debt": 0}
    # §6.4: 5/8, 3/16, 3/16 din contul net; cel mai mare rest, primul dintre egali câștigă banul
    assert [(_person_key(l["name"]), l["share"], l["amount"], l["blocked"]) for l in plan["lines"]] == [(_person_key(n), *x) for n, *x in [
        ("Mirela Neagu", "5/8", 931178, False), ("Darius Neagu", "3/16", 279354, True),
        ("Andrei Vlad", "3/16", 279353, True)]]
    assert sum(l["amount"] for l in plan["lines"] if not l["blocked"]) == 931178          # 9.311,78 lei plătibili acum
    minors = sorted(_person_key(e["reason"].split(" este ")[0]) for e in case["escalations"] if e["code"] == "minor_heir")
    assert minors == sorted(map(_person_key, ["Andrei Vlad", "Darius Neagu"]))


def test_no_payment_plan_on_a_negative_net_after_the_refusal(client):
    cert = next(s for s in CLIENTS["P13"]["steps"] if "doc" in s and s["doc"]["expected_type"] == "heir_certificate")
    doc = copy.deepcopy(portfolio._document(cert))   # the certificate as extracted (.extras.json), a second copy
    doc.update(id="X-P13-cert2", received_on="2026-10-28")
    doc["fields"]["document_number"] = "71"
    client.post("/documents", json=doc)
    plan = client.get(f"/cases/{A}").json()["payment_plan"]
    assert plan is None or all(l["amount"] >= 0 for l in plan["lines"])


@pytest.mark.xfail(strict=True, reason="bug 085: un document fără tip în vocabular (cererea de despăgubire UNIQA), cu "
                   "CNP-ul unui client, ajunge la documente neidentificate ca «ilizibil» în loc să fie atașat dosarului")
def test_an_unknown_document_type_of_a_known_client_is_not_illegible(client):
    doc = {"id": "X-P13-cerere", "document_type": "unknown", "received_on": "2026-08-27", "confidence": 0.5,
           "fields": {"cnp": "1640318184124", "policy_id": "UQ-8501001-FICTIV", "date_of_death": "2026-08-11"},
           "raw_name": "cerere-despagubire-uniqa.pdf"}
    r = client.post("/documents", json=doc).json()
    assert r["case_id"] == A and r.get("escalation_reason") != "document_illegible"
