"""084: the seeded portfolio (registries/portofoliu, agent/portfolio.py) and the worklist that feeds ops-ui "Dosare".
Every client lands in its declared stage through the real pipeline; the plans are checked against rules.py; Maria
Ionescu's demo is unchanged next to the portfolio."""
import json
from datetime import date
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from agent import api, portfolio, rules
from agent.core_mock import _movement_in, _person_key, _product_in

CLIENTS = portfolio.clients()
BY_CASE = {c["case_id"]: c for c in CLIENTS}
W = "279146358279"


@pytest.fixture(scope="module")
def client():
    c = TestClient(api.app)
    assert c.post("/demo/reset?portofoliu=1").json()["portfolio"] == [x["case_id"] for x in CLIENTS]
    yield c
    c.post("/demo/reset")


def _cnp_ok(cnp: str) -> bool:
    if len(cnp) != 13 or not cnp.isdigit() or cnp[0] not in "12":
        return False
    c = sum(int(a) * int(b) for a, b in zip(cnp, W)) % 11
    return int(cnp[12]) == (1 if c == 10 else c)


def _iban_ok(iban: str) -> bool:
    s = iban.replace(" ", "")
    return len(s) == 24 and int("".join(str(int(ch, 36)) for ch in s[4:] + s[:4])) % 97 == 1


def test_the_data_is_fictitious_but_consistent():
    assert 10 <= len(CLIENTS) <= 14
    cnps = [c["customer"]["cnp"] for c in CLIENTS]
    assert all(_cnp_ok(x) for x in cnps) and len(set(cnps)) == len(cnps)
    for c in CLIENTS:   # the CNP encodes the birth date of the customer
        y, m, d = c["customer"]["birth_date"].split("-")
        assert c["customer"]["cnp"][1:7] == y[2:] + m + d, c["id"]
        assert all(s["doc"]["expected_fields"].get("cnp") in (c["customer"]["cnp"], None) for s in c["steps"] if "doc" in s)
    ibans = [p["iban"] for c in CLIENTS for p in c["products"] if p.get("iban")]
    assert all(_iban_ok(i) for i in ibans) and len(set(ibans)) == len(ibans)
    assert len({c["case_id"] for c in CLIENTS}) == len(CLIENTS) and "SC-2026-0001" not in BY_CASE
    types = {p["type"] for c in CLIENTS for p in c["products"]}
    assert types == {"current_account", "term_deposit", "personal_loan", "credit_card"}
    assert any(p.get("estate_fraction") == "1/2" for c in CLIENTS for p in c["products"])            # cont comun
    heirs = [len(s["doc"]["expected_fields"].get("heirs") or []) for c in CLIENTS for s in c["steps"]
             if "doc" in s and s["doc"]["expected_type"] == "heir_certificate"]
    assert min(heirs) == 1 and max(heirs) == 5
    assert any(s["doc"]["expected_fields"].get("testament") for c in CLIENTS for s in c["steps"] if "doc" in s)
    assert any("Germania" in (k.get("address") or "") for c in CLIENTS for k in (c.get("contacts") or {}).values())


@pytest.mark.parametrize("cid", list(BY_CASE))
def test_every_client_is_in_its_stage(client, cid):
    spec = BY_CASE[cid]
    case = client.get(f"/cases/{cid}").json()
    exp = spec["expected"]
    assert case["state"] == exp["state"]
    assert sorted(e["code"] for e in case["escalations"] if e["status"] == "deschis") == sorted(exp["escalations"])
    assert case["deceased"]["cnp"] == spec["customer"]["cnp"] and case["deceased"]["name"] == spec["customer"]["name"]
    assert bool(case["payment_plan"]) == bool(exp["plan"])
    row = next(r for r in client.get("/worklist").json()["rows"] if r["case_id"] == cid)
    assert sorted(d["kind"] for d in row["decisions"]) == sorted(exp.get("decisions", []))
    assert row["portfolio"] is True and row["state_label"] == api.STATE_RO[exp["state"]]
    # a freshly seeded bank has nothing overdue for the autopilot: no ladder step due, no deficiency notice pending
    assert client.get(f"/cases/{cid}/contact-plan").json()["due_now"] == []
    assert client.get(f"/cases/{cid}/deficiencies").json()["pending"] == []
    plan = client.get(f"/cases/{cid}/contact-plan").json()
    done = [s["code"] for s in plan["steps"] if s["status"] == "done"]
    if "contact_done" in exp:
        assert done == exp["contact_done"] and plan["next"]["code"] == exp["contact_next"]


def test_the_illegible_photo_waits_among_the_unmatched_documents(client):
    # 090: + the two notary letters of P13/P14 in the real notari.pro wording, without the hearing date: their real
    # extraction is 0,5 (hearing_date is mandatory for the extractor), so they wait for an operator as well
    escs = client.get("/escalations").json()
    assert [(e["rule"], e["document_id"]) for e in escs] == [("document_illegible", "P01-D2"),
                                                             ("document_illegible", "P13-D4"), ("document_illegible", "P14-D4")]


def _expected_plan(spec):
    """The plan recomputed straight from rules.py, from the portfolio file's reference values (not from the pipeline,
    which gets the extraction of the documents: equal plans = the extraction is right where it matters)."""
    products = [_product_in({k: v for k, v in p.items() if k not in ("iban", "loan_contract", "installment")})
                for p in spec["products"]]
    movements = [_movement_in(m) for m in spec.get("movements") or []]
    docs = [{"document_type": s["doc"]["expected_type"], "fields": s["doc"]["expected_fields"]} for s in spec["steps"] if "doc" in s]
    dod = date.fromisoformat(next(d["fields"]["date_of_death"] for d in docs if d["document_type"] == "dgep_signal"))
    cert = next(d for d in docs if d["document_type"] == "heir_certificate")
    heirs = [rules.Heir(h["id"], h["name"], Fraction(h["share"]), bool(h.get("minor")), h.get("legal_representative"))
             for h in cert["fields"]["heirs"]]
    paid = sum(d["fields"]["amount"] for d in docs if d["document_type"] == "insurer_response"
               and d["fields"]["decision"] == "approved")
    valued = rules.balance_at_death(products, dod)
    net = rules.net_of_debts(valued, movements, dod, insurance_paid=paid)
    spouse = "H1" if not heirs[0].minor else None
    lines = []
    for p in products:
        if p.type == "current_account":
            lines += rules.split_by_shares(heirs, p.id, net.net, p.estate_fraction, surviving_spouse_id=spouse)
        elif p.type == "term_deposit":
            gross = p.principal + rules.accrued_simple_interest(p.principal, p.rate_pct, (p.maturity - p.start).days)
            lines += rules.split_by_shares(heirs, p.id, gross, p.estate_fraction, surviving_spouse_id=spouse)
    return net, [(l.name, l.product_id, l.amount) for l in lines]


PLANS = [cid for cid, c in BY_CASE.items() if c["expected"]["plan"]]


@pytest.mark.parametrize("cid", PLANS)
def test_plan_amounts_match_the_rules(client, cid):
    net, lines = _expected_plan(BY_CASE[cid])
    plan = client.get(f"/cases/{cid}").json()["payment_plan"]
    assert plan["net_account"]["net"] == net.net and plan["net_account"]["debts_deducted"] == net.debts_deducted
    # the names are the extractor's, as written in the certificate („GEORGESCU MARIA”): same person, any order/case
    assert [(_person_key(l["name"]), l["product_id"], l["amount"]) for l in plan["lines"]] == \
        [(_person_key(n), p, a) for n, p, a in lines]
    assert sum(l["amount"] for l in plan["lines"] if l["product_id"].endswith("-CC")) == net.net


def test_plan_amounts_by_hand(client):
    """The figures of registries/portofoliu/README.md."""
    p06 = client.get("/cases/SC-2026-0106").json()["payment_plan"]
    # card de credit: 3.420,00 lei + dobânda 24% pe 15 zile (5 iunie -> 20 iunie) = 33,73 lei, scăzute din cont
    assert p06["net_account"] == {"product_id": "P06-CC", "gross": 1560000, "debts_deducted": 345373, "withheld": 0,
                                  "net": 1214627, "unpaid_debt": 0}
    assert [l["amount"] for l in p06["lines"]] == [809751, 404876]                    # testament: 2/3 și 1/3
    p07 = client.get("/cases/SC-2026-0107").json()["payment_plan"]
    assert p07["net_account"]["debts_deducted"] == 13313                               # dobânda creditului neacoperită
    sofia = next(l for l in p07["lines"] if _person_key(l["name"]) == _person_key("Sofia Petrescu"))
    assert sofia["blocked"] and sofia["minor"] and sofia["amount"] == 319452
    p08 = client.get("/cases/SC-2026-0108").json()
    assert p08["payment_plan"]["status"] == "approved"
    paid = [e for e in client.get("/audit").json() if e.get("action") == "pay" and e["cif"] == "RC3108"]
    assert [(e["count"], e["total"]) for e in paid] == [(2, 2194000)]


def test_maria_is_unchanged_next_to_the_portfolio(client):
    try:
        for n in range(1, 8):
            client.post(f"/demo/step/{n}")
        case = client.get("/cases/SC-2026-0001").json()
        assert case["state"] == "PAYMENT_PENDING_APPROVAL" and case["payment_plan"]["net_account"]["net"] == 527337
        assert len(case["documents"]) == 6
        assert [e["document_id"] for e in client.get("/escalations").json()] == ["P01-D2", "P13-D4", "P14-D4", "doc-07"]
    finally:
        client.post("/demo/reset?portofoliu=1")


def test_reset_gol_is_an_empty_bank_and_the_default_follows_the_env(monkeypatch):
    c = TestClient(api.app)
    try:
        r = c.post("/demo/reset?gol=1").json()
        assert r["portfolio"] == [] and c.get("/cases").json() == [] and set(api.bank.customers) == {"RC1001", "RC2002"}
        monkeypatch.setenv("MVP_PORTFOLIO", "1")
        assert len(c.post("/demo/reset").json()["portfolio"]) == len(CLIENTS)
        monkeypatch.setenv("MVP_PORTFOLIO", "0")
        assert c.post("/demo/reset").json()["portfolio"] == []
    finally:
        c.post("/demo/reset?portofoliu=1")


# ---------------------------------------------------------------- the worklist (GET /worklist)
def _names(client, **params):
    return {r["name"] for r in client.get("/worklist", params=params).json()["rows"]}


def test_worklist_filters(client):
    w = client.get("/worklist").json()
    assert w["count"] == len(CLIENTS) + 1                                             # + the unmatched documents
    assert _names(client, filtru="de_aprobat") == {"Ioan Georgescu", "Florica Niculescu", "Vasile Petrescu",
                                                    "Elisabeta Dumitrescu", "Cristian Neagu", "Marin Petrescu"}
    assert _names(client, filtru="escaladari") == {"Vasile Petrescu", "Doina Ilie", "Nicolae Stan",
                                                    "Documente neidentificate", "Marin Petrescu", "Cristian Neagu"}
    assert _names(client, filtru="termene") == {"Elisabeta Dumitrescu", "Aurelia Matei"}
    docs = _names(client, filtru="documente")
    assert "Constantin Marinescu" in docs and "Ana Stoica" in docs and "Elena Radu" not in docs
    counts = {f["key"]: f["count"] for f in w["filters"]}
    assert counts == {"toate": 15, "de_aprobat": 6, "escaladari": 6, "documente": len(docs), "termene": 2}
    assert w["decisions_waiting"] == sum(r["decisions_count"] for r in w["rows"]) == 18
    assert w["rows"][0]["decisions_count"] == max(r["decisions_count"] for r in w["rows"])  # decisions first
    assert client.get("/worklist", params={"filtru": "x"}).status_code == 422


def test_worklist_row_says_what_follows(client):
    rows = {r["case_id"]: r for r in client.get("/worklist").json()["rows"]}
    assert rows["SC-2026-0102"]["next"]["text"] == "Semnează răspunsul către notar"
    assert rows["SC-2026-0102"]["deadline"] == {"name": "Răspuns către notar (înainte de dezbatere)", "date": "2026-11-03",
                                                "status": "deschis", "days": 6}
    assert rows["SC-2025-0187"]["deadline"]["date"] == "2026-11-02" and rows["SC-2025-0187"]["deadline"]["days"] == 5
    assert rows["SC-2026-0111"]["next"] == {"text": "Cerere prin notarul din dosar", "due": "2026-11-25",
                                            "source": "scara de contact", "status": "urmează"}
    assert rows["SC-2026-0105"]["next"]["text"].startswith("Aprobă planul de plată (")
    assert rows["SC-2026-0110"]["last_document"] == {"document_id": "P10-D6", "type": "insurer_response",
                                                     "label": "Răspunsul asigurătorului", "date": "2026-10-19"}
    # no insured loan, no insurer's notice term in the worklist (the case keeps it in GET /cases/{id})
    assert rows["SC-2026-0102"]["deadline"]["name"] != "Avizare daună asigurător"


def test_worklist_search(client):
    p05 = BY_CASE["SC-2026-0105"]["customer"]
    assert _names(client, q=p05["cnp"]) == {"Ioan Georgescu"}
    assert _names(client, q="stefan") == set() and _names(client, q="STOICA") == {"Ana Stoica"}
    assert _names(client, q="niculescu") == {"Florica Niculescu"}
    assert _names(client, q="SC-2025") == {"Aurelia Matei"}
    assert _names(client, q="petrescu", filtru="escaladari") == {"Vasile Petrescu", "Marin Petrescu"}
    assert "Gheorghe Popescu" in _names(client, q="Popescu Gheorghe".split()[0])


def test_worklist_follows_an_operator_action(client):
    try:
        assert client.post("/cases/SC-2026-0102/letters/notary/sign", json={"signer": "Test"}).status_code == 200
        w = client.get("/worklist").json()
        assert "Elisabeta Dumitrescu" not in _names(client, filtru="de_aprobat") and w["decisions_waiting"] == 17
    finally:
        client.post("/demo/reset?portofoliu=1")
