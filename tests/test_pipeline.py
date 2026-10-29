"""End-to-end: the 7 demo documents, in order and out of order (maria-ionescu.md §3-§4)."""
import copy

from agent.core_mock import Bank
from agent.demo_documents import DOCUMENTS, VARIANT_B_HEIRS
from agent.pipeline import Pipeline


def run(docs):
    p = Pipeline(Bank())
    results = [p.receive(copy.deepcopy(d)) for d in docs]
    return p, results


def amounts(case):
    return {l["heir_id"]: l["amount"] for l in case.payment_plan["lines"] if l["product_id"] == "CC-1"}


def test_full_scenario_variant_A():
    p, r = run(DOCUMENTS)
    case = p.cases["SC-2026-0001"]
    assert [x["state"] for x in r[:6]] == ["FROZEN", "NOTARY_ANSWERED", "INSURANCE_CLAIM_OPEN",
                                            "SUPPLEMENT_REQUESTED", "INSURANCE_SETTLED", "PAYMENT_PENDING_APPROVAL"]
    assert any(f["code"] == "fee_to_reverse" and f["amount"] == 6_000 for f in case.flags)
    assert any(f["code"] == "pension_return_CNPP" and f["amount"] == 210_000 for f in case.flags)
    assert case.payment_plan["net_account"]["net"] == 527_337
    assert amounts(case) == {"H1": 329_585, "H2": 98_876, "H3": 98_876}
    elena = next(l for l in case.payment_plan["lines"] if l["heir_id"] == "H3" and l["product_id"] == "CC-1")
    assert elena["blocked_reason"] == "minor_requires_representation"
    # document 7: illegible -> separate orphan case, escalated, Maria's case untouched
    assert r[6]["case_id"] == "SC-NEIDENTIFICAT" and r[6]["escalation"]
    assert case.state() == "PAYMENT_PENDING_APPROVAL"
    # approval pays only unblocked lines
    plan = p.approve_payment(case.id, "ops_approver")
    assert plan["status"] == "approved" and case.state() == "PAID"
    assert sum(x["amount"] for x in p.bank.payments) == 329_585 + 98_876


def test_variant_B_testament():
    docs = copy.deepcopy(DOCUMENTS)
    docs[3]["fields"]["heirs"] = VARIANT_B_HEIRS
    docs[3]["fields"]["testament"] = True
    p, _ = run(docs)
    assert amounts(p.cases["SC-2026-0001"]) == {"H1": 395_503, "H2": 65_917, "H3": 65_917}


def test_out_of_order_notary_before_dgep_same_result():
    docs = [DOCUMENTS[1], DOCUMENTS[0]] + DOCUMENTS[2:6]
    p, r = run(docs)
    assert r[0]["state"] == "NOTARY_ANSWERED" and "frozen" in r[0]["actions"]
    assert amounts(p.cases["SC-2026-0001"]) == {"H1": 329_585, "H2": 98_876, "H3": 98_876}


def test_dgep_twice_is_idempotent():
    p, r = run([DOCUMENTS[0], DOCUMENTS[0]])
    assert r[1].get("duplicate") is True
    assert sum(1 for a in p.bank.audit if a["action"] == "freeze") == 1
    assert sum(1 for a in p.bank.audit if a["action"] == "reverse_fees") == 1


def test_invalid_shares_escalate_without_plan():
    docs = copy.deepcopy(DOCUMENTS[:4])
    docs[3]["fields"]["heirs"][0]["share"] = "1/2"  # 1/2 + 3/8 + 3/8 != 1
    p, r = run(docs)
    case = p.cases["SC-2026-0001"]
    assert any(e.reason == "shares_invalid" for e in case.escalations)
    assert case.payment_plan is None


def test_unknown_cnp_escalates():
    doc = copy.deepcopy(DOCUMENTS[0])
    doc["fields"]["cnp"] = "1999999999999"
    p, r = run([doc])
    assert r[0]["case_id"] == "SC-NEIDENTIFICAT"
    assert "SC-2026-0001" not in p.cases


# ---------------------------------------------------------------- 037: identifiers §0, hard cases, variants
from agent.demo_documents import HARD  # noqa: E402


def test_hard_H4_cnp_mismatch_never_attached():
    p, r = run(DOCUMENTS[:3] + [HARD["H4"]])
    assert r[3]["case_id"] == "SC-NEIDENTIFICAT" and r[3]["escalation_reason"] == "cnp_mismatch"
    assert not p.cases["SC-2026-0001"].heirs


def test_hard_H5_match_without_iban():
    h5 = copy.deepcopy(HARD["H5"])
    # the account is cited only by type + amount (H5.json masa_activ: cont curent, 530.000 bani, no IBAN)
    h5["fields"].setdefault("unidentified_products", [{"type": "current_account", "amount": 530_000}])
    p, r = run(DOCUMENTS[:3] + [h5])
    case = p.cases["SC-2026-0001"]
    assert any(f["code"] == "matched_without_iban" and f["product_id"] == "CC-1" for f in case.flags)
    assert case.coverage_gaps == ["DEP-1"] and r[3]["state"] == "SUPPLEMENT_REQUESTED"


def test_hard_H10_identity_by_name_and_birth_date():
    p, r = run([DOCUMENTS[0], HARD["H10"]])
    assert r[1]["case_id"] == "SC-2026-0001" and "freeze_definitive" in r[1]["actions"]
    assert any(e.data.get("flag") == "identity_by_name_birthdate" for e in p.cases["SC-2026-0001"].events)


def test_hard_H11_homonym_is_not_attached():
    p, r = run([DOCUMENTS[0], HARD["H11"]])
    assert r[1]["case_id"] == "SC-NEIDENTIFICAT" and r[1]["escalation_reason"] == "identity_unconfirmed"
    assert p.cases["SC-2026-0001"].date_of_death.isoformat() == "2026-09-03"


def test_variant_withdrawal_by_mandate_holder_is_flagged_and_escalated():
    p = Pipeline(Bank({"pensie", "retragere"}))
    p.receive(copy.deepcopy(DOCUMENTS[0]))
    case = p.cases["SC-2026-0001"]
    assert any(f["code"] == "post_death_mandate_withdrawal" and f["amount"] == 100_000 for f in case.flags)
    assert sum(e.reason == "post_death_mandate_withdrawal" for e in case.escalations) == 1
    p.receive(copy.deepcopy(DOCUMENTS[1]))   # the notary answer reports it, without a second escalation
    assert sum(e.reason == "post_death_mandate_withdrawal" for e in case.escalations) == 1


def test_variant_without_october_pension_has_no_cnpp_return():
    p = Pipeline(Bank(set()))
    p.receive(copy.deepcopy(DOCUMENTS[0]))
    assert not any(f["code"] == "pension_return_CNPP" for f in p.cases["SC-2026-0001"].flags)


def test_contacts_minor_reached_through_representative():
    p, _ = run(DOCUMENTS[:4])
    cc = p.cases["SC-2026-0001"].contact_channels
    assert cc["H1"]["verified"] and cc["H2"]["preferred"] == "sms"
    assert cc["H3"]["via"] == "H1" and cc["H3"]["email"] == cc["H1"]["email"]


def test_rejected_plan_returns_to_plan_drafted():
    from fastapi.testclient import TestClient
    from agent import api
    c = TestClient(api.app)
    c.post("/demo/run?upto=6")
    assert c.post("/payments/PAY-SC-2026-0001/reject", json={}).status_code == 422
    assert c.post("/payments/PAY-SC-2026-0001/reject", json={"reason": "IBAN lipsă"}).status_code == 200
    assert c.get("/cases/SC-2026-0001").json()["state"] == "PLAN_DRAFTED"


def test_hard_H1_notary_before_dgep():
    p, r = run([HARD["H1"], DOCUMENTS[0]] + DOCUMENTS[2:6])
    assert r[0]["state"] == "NOTARY_ANSWERED" and "frozen" in r[0]["actions"]
    assert amounts(p.cases["SC-2026-0001"]) == {"H1": 329_585, "H2": 98_876, "H3": 98_876}


def test_hard_H2_dgep_duplicate_from_next_batch():
    p, r = run([DOCUMENTS[0], HARD["H2"]])
    assert sum(1 for a in p.bank.audit if a["action"] == "freeze") == 1
    assert sum(1 for a in p.bank.audit if a["action"] == "reverse_fees") == 1


def test_hard_H3_shares_not_one():
    p, r = run(DOCUMENTS[:3] + [HARD["H3"]])
    case = p.cases["SC-2026-0001"]
    assert any(e.reason == "shares_invalid" for e in case.escalations) and case.payment_plan is None


def test_indemnity_mismatch_is_escalated_not_applied():
    docs = copy.deepcopy(DOCUMENTS[:5])
    docs[4]["fields"]["amount"] = 850_000   # insurer pays less than the principal at D (900.000)
    p, r = run(docs)
    case = p.cases["SC-2026-0001"]
    assert r[4]["actions"] == ["indemnity_mismatch"]
    assert any(e.reason == "indemnity_mismatch" for e in case.escalations)
    assert "insurance_settled" not in case.milestones and not case.insurance.get("paid")


def test_indemnity_with_overdue_instalments_within_limit():
    bank = Bank()
    bank._installments["CRD-1"] = 30_000   # hypothetical instalment, only for this test
    p = Pipeline(bank)
    docs = copy.deepcopy(DOCUMENTS[:5])
    docs[4]["fields"]["amount"] = 900_000 + 2 * 30_000
    for d in docs:
        p.receive(d)
    assert p.cases["SC-2026-0001"].insurance.get("paid") == 960_000


def _freeze_events(case):
    return [e.summary for e in case.events if e.summary.startswith("Blocare")]


def test_freeze_event_states_reason_dgep_then_death_certificate():
    p, _ = run([DOCUMENTS[0], HARD["H10"]])
    ev = _freeze_events(p.cases["SC-2026-0001"])
    assert ev[0].startswith("Blocare reversibilă: semnal DGEP DGEP-MOCK-2026-09-20-000123 (GDPR art. 22")
    assert ev[1].startswith("Blocare confirmată definitiv de certificat de deces EMD nr. 0000000")
    assert p.bank.customers["RC1001"]["frozen"]["reversible"] is False


def test_freeze_on_notary_request_is_reversible_with_reason():
    p, _ = run([DOCUMENTS[1]])
    ev = _freeze_events(p.cases["SC-2026-0001"])
    assert ev == [e for e in ev if e.startswith("Blocare reversibilă: adresa notarului nr. 412/2026")] and ev
    assert p.bank.customers["RC1001"]["frozen"]["reversible"] is True


def test_operator_confirms_freeze():
    p, _ = run([DOCUMENTS[0]])
    p.confirm_freeze("SC-2026-0001", "Ana Popescu")
    assert _freeze_events(p.cases["SC-2026-0001"])[-1].startswith("Blocare confirmată definitiv de operator Ana Popescu")
    with __import__("pytest").raises(ValueError):
        p.confirm_freeze("SC-2026-0001", "Ana Popescu")


def test_death_certificate_first_is_definitive_at_once():
    h10 = copy.deepcopy(HARD["H10"])
    h10["fields"]["cnp"] = "2XXXXXXXXXXXX"
    p, _ = run([h10])
    ev = _freeze_events(p.cases["SC-2026-0001"])
    assert len(ev) == 1 and ev[0].startswith("Blocare definitivă: certificat de deces EMD nr. 0000000")


def test_heir_certificate_without_ids_from_llm_extractor():
    """The LLM extractor returns heirs without ids; the pipeline numbers them in certificate order."""
    docs = copy.deepcopy(DOCUMENTS[:4])
    for h in docs[3]["fields"]["heirs"]:
        h.pop("id", None)
    p, r = run(docs)
    case = p.cases["SC-2026-0001"]
    assert [h["id"] for h in case.heirs] == ["H1", "H2", "H3"]
    assert r[3]["state"] == "SUPPLEMENT_REQUESTED"


def _claim_case(insurer):
    docs = copy.deepcopy(DOCUMENTS[:3])
    docs[2]["fields"]["insurer"] = insurer
    p, _ = run(docs)
    case = p.cases["SC-2026-0001"]
    deadline = next((d for d in case.deadlines if d["code"] == "insurance_claim_notice"), None)
    event = next(e for e in case.events if e.summary.startswith("Dosar de daună"))
    return case, deadline, event


def test_claim_uniqa_keeps_30_days_marked_as_hypothesis():
    case, deadline, event = _claim_case("UNIQA Asigurări de viață S.A.")
    assert deadline["due"] == "2026-10-20" and deadline["hypothesis"]
    assert "ipoteză, de confirmat" in deadline["basis"] and "ipoteză, de confirmat" in event.rule
    assert any("F1" in m for m in case.missing())            # checklist for the heirs comes from the structure


def test_claim_allianz_and_nn_use_their_own_terms():
    case, deadline, event = _claim_case("Allianz-Țiriac Asigurări")
    assert deadline["due"] == "2026-12-02" and not deadline["hypothesis"] and "ipoteză" not in event.rule
    assert any("datele bancare" in m for m in case.missing())
    case, deadline, _ = _claim_case("NN Asigurări de Viață")
    assert deadline["due"] == "2026-10-03" and not deadline["hypothesis"]


def test_claim_unknown_insurer_has_no_invented_deadline():
    case, _, event = _claim_case("Altceva SA")
    assert not any(d["code"] == "insurance_claim_notice" for d in case.deadlines)
    assert "necunoscut, de confirmat cu banca" in event.summary
