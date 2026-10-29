"""089: cele 6 bug-uri găsite de simularea 082 (registries/simulare/RAPORT-seed82.md), fiecare pe exemplul minim din raport,
cu cifrele așteptate scrise de mână (nu luate din referință). Plus marginile reparațiilor (soț neidentificat, datorie peste
toată masa, plată cu sumă negativă)."""
from datetime import date

import pytest

pytest.importorskip("registries.simulare.generator", reason="registries/simulare/ lipsește (ex. repo de predare fără el)")

from scripts import impact_simulare as sim  # noqa: E402
from scripts.impact_simulare import CC, SON, SPOUSE, mini_case, run_case  # noqa: E402

CRD = {"id": "CRD-1", "type": "personal_loan", "outstanding": 500_000, "rate_pct": 10.0, "last_interest_paid": "2026-03-10",
       "loan_contract": "NP-MIN"}


def lines(got):
    return [(l["heir"], l["product_id"], l["amount"], l["blocked"]) for l in got.get("lines", [])]


def run(case):
    got = run_case(case)
    assert got["errors"] == []
    return got


def test_spouse_is_found_by_the_certificate_quality_not_by_position():
    # cont comun 1.000 lei, [H1 fiu 3/4, H2 soț 1/4]: soțul ia 1/2 ca proprietar + 1/4 din 1/2
    got = run(mini_case([SON, SPOUSE], [{**CC, "estate_fraction": "1/2"}]))
    assert lines(got) == [("H1", "CC-1", 37_500, False), ("H2", "CC-1", 62_500, False)]


def test_minor_listed_first_with_common_goods_does_not_crash():
    got = run(mini_case([{**SON, "minor": True, "legal_representative": "H2"}, SPOUSE], [{**CC, "estate_fraction": "1/2"}]))
    assert lines(got) == [("H1", "CC-1", 37_500, True), ("H2", "CC-1", 62_500, False)]


def test_debt_above_the_current_account_is_capped_at_zero():
    got = run(mini_case([{**SON, "share": "1/2"}, {"id": "H2", "name": "Ana Fiică", "share": "1/2", "relationship": "fiică"}],
                        [CC, CRD]))
    assert got["net_account"] == 0
    assert lines(got) == [("H1", "CC-1", 0, False), ("H2", "CC-1", 0, False)]


def test_debt_above_the_account_is_taken_from_the_deposit():
    dep = {"id": "DEP-1", "type": "term_deposit", "principal": 1_000_000, "rate_pct": 5.0, "start": "2025-10-01",
           "maturity": "2026-04-01"}
    got = run(mini_case([{**SON, "share": "1"}], [CC, dep, CRD]))
    # deposit at maturity 1.024.932; debt 500.000 (interest 0 days) − account 100.000 ⇒ 400.000 from the deposit
    assert got["net_account"] == 0
    assert lines(got) == [("H1", "CC-1", 0, False), ("H1", "DEP-1", 624_932, False)]


def test_matured_deposit_is_payable_now():
    dep = {"id": "DEP-1", "type": "term_deposit", "principal": 1_000_000, "rate_pct": 5.0, "start": "2025-10-01",
           "maturity": "2026-04-01"}
    got = run(mini_case([{**SON, "share": "1"}], [CC, dep]))   # the plan is made on 2026-04-09, after maturity
    assert lines(got) == [("H1", "CC-1", 100_000, False), ("H1", "DEP-1", 1_024_932, False)]


def test_deposit_not_yet_matured_stays_blocked():
    dep = {"id": "DEP-1", "type": "term_deposit", "principal": 1_000_000, "rate_pct": 5.0, "start": "2025-10-01",
           "maturity": "2026-10-01"}
    got = run(mini_case([{**SON, "share": "1"}], [CC, dep]))
    assert lines(got)[1][3] is True


def test_every_fee_debited_after_death_is_reversed_whatever_its_code():
    got = run(mini_case([{**SON, "share": "1"}], [CC], [{"date": "2026-04-05", "amount": -900, "kind": "fee", "fee_code": "ADMIN_CONT"},
                                                       {"date": "2026-03-05", "amount": -700, "kind": "fee", "fee_code": "ADMIN_CONT"}]))
    assert got["fees_reversed"] == 900   # the fee before death (03-05) stays


def test_refusal_after_a_complete_certificate_still_makes_the_plan():
    c = sim.MINIMAL["refuz_asigurare_fara_plan"][2]()
    got = run(c)
    assert got["plan"] and got["net_account"] == 600_000
    assert lines(got) == [("H1", "CC-1", 600_000, False)]
    assert "insurance_refused" in got["escalations"]


def test_refusal_gives_the_same_plan_in_either_order():
    a = sim.MINIMAL["refuz_asigurare_fara_plan"][2]()
    b = mini_case([{**SON, "share": "1"}], a["products"], insured=True, refused=True,
                  order=["dgep_signal", "notary_request", "insurance_certificate", "insurer_response", "heir_certificate"])
    assert lines(run(a)) == lines(run(b))


# ---------------------------------------------------------------- edges of the fixes
def _pipe(case):
    from agent.pipeline import Pipeline
    bank = sim.SimBank(case)
    p = Pipeline(bank)
    for d in case["documents"]:
        p.receive(d)
    return p, next(c for c in p.cases.values() if c.cif == case["customer"]["cif"])


def test_common_goods_without_an_identifiable_spouse_escalate_and_make_no_plan():
    heirs = [{"id": "H1", "name": "Dan Minim", "share": "1/2"}, {"id": "H2", "name": "Ion Minim", "share": "1/2"}]
    _, case = _pipe(mini_case(heirs, [{**CC, "estate_fraction": "1/2"}]))
    assert case.payment_plan is None
    assert [e.reason for e in case.escalations] == ["spouse_unidentified"]


def test_without_quality_in_the_certificate_the_spouse_is_the_one_known_in_core():
    # the demo extraction has no `relationship`: the spouse is matched on the name from KYC (customer.spouse)
    heirs = [{"id": "H1", "name": "Dan Minim", "share": "3/4"}, {"id": "H2", "name": "MINIM ION", "share": "1/4"}]
    c = mini_case(heirs, [{**CC, "estate_fraction": "1/2"}])
    c["customer"]["spouse"] = "Ion Minim"
    _, case = _pipe(c)
    assert [(l["heir_id"], l["amount"]) for l in case.payment_plan["lines"]] == [("H1", 37_500), ("H2", 62_500)]


def test_two_heirs_named_spouse_escalate():
    heirs = [{**SPOUSE, "id": "H1", "share": "1/2"}, {**SPOUSE, "id": "H2", "name": "Alt Soț", "share": "1/2"}]
    _, case = _pipe(mini_case(heirs, [{**CC, "estate_fraction": "1/2"}]))
    assert case.payment_plan is None and [e.reason for e in case.escalations] == ["spouse_unidentified"]


def test_own_goods_need_no_spouse():
    heirs = [{"id": "H1", "name": "Dan Minim", "share": "1/2"}, {"id": "H2", "name": "Ion Minim", "share": "1/2"}]
    _, case = _pipe(mini_case(heirs, [CC]))
    assert [l["amount"] for l in case.payment_plan["lines"]] == [50_000, 50_000] and not case.escalations


def test_debt_above_the_whole_estate_is_flagged_for_the_operator():
    big = {**CRD, "outstanding": 5_000_000}
    _, case = _pipe(mini_case([{**SON, "share": "1"}], [CC, big]))
    assert [l["amount"] for l in case.payment_plan["lines"]] == [0]
    esc = [e for e in case.escalations if e.reason == "debt_exceeds_estate"]
    assert len(esc) == 1 and esc[0].data["unpaid_debt"] == 4_900_000 and esc[0].data["severity"] == "info"


def test_approve_payment_refuses_a_negative_line():
    p, case = _pipe(mini_case([{**SON, "share": "1"}], [CC]))
    case.payment_plan["lines"][0]["amount"] = -1
    with pytest.raises(ValueError):
        p.approve_payment(case.id, "op")
    assert p.bank.payments == []


def test_the_demo_case_is_unchanged():
    from agent.core_mock import Bank
    from agent.demo_documents import DOCUMENTS
    from agent.pipeline import Pipeline
    p = Pipeline(Bank())
    for d in DOCUMENTS:
        p.receive(d)
    plan = p.cases["SC-2026-0001"].payment_plan
    got = {(l["heir_id"], l["product_id"]): (l["amount"], l["blocked_reason"] is not None) for l in plan["lines"]}
    assert got[("H1", "CC-1")] == (329_585, False) and got[("H1", "DEP-1")] == (1_315_000, True)
    assert plan["net_account"]["net"] == 527_337
