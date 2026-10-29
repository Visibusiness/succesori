"""Expected values from kb/scenariu-demo/maria-ionescu.md (v1.1). Amounts in bani."""
from datetime import date
from fractions import Fraction

import pytest

from agent.rules import (
    Heir, Movement, Product,
    balance_at_death, coverage_gaps, deadlines, fees_to_reverse, largest_remainder,
    mandate_withdrawals, net_of_debts, pension_flags, split_by_shares, validate_shares,
)

D = date(2026, 9, 3)

CURRENT = Product("CC-1", "current_account", balance=320_000, estate_fraction=Fraction(1, 2))
DEPOSIT = Product("DEP-1", "term_deposit", principal=2_000_000, rate_pct=5.20,
                  start=date(2026, 1, 3), maturity=date(2027, 1, 3), estate_fraction=Fraction(1, 2))
LOAN = Product("CRD-1", "personal_loan", outstanding=900_000, rate_pct=12.0,
               last_interest_paid=date(2026, 8, 25), insurance_policy_id="POL-55")
PRODUCTS = [CURRENT, DEPOSIT, LOAN]

MOVEMENTS = [
    Movement(date(2026, 9, 5), -6_000, "fee", fee_code="PREMIUM"),
    Movement(date(2026, 9, 15), 210_000, "pension_credit"),
    Movement(date(2026, 10, 15), 210_000, "pension_credit"),
]

ION, ANDREI, ELENA = "H1", "H2", "H3"
HEIRS_A = [Heir(ION, "Ion Ionescu", Fraction(1, 4)),
           Heir(ANDREI, "Andrei Ionescu", Fraction(3, 8)),
           Heir(ELENA, "Elena Ionescu", Fraction(3, 8), minor=True, legal_representative=ION)]
HEIRS_B = [Heir(ION, "Ion Ionescu", Fraction(1, 2)),
           Heir(ANDREI, "Andrei Ionescu", Fraction(1, 4)),
           Heir(ELENA, "Elena Ionescu", Fraction(1, 4), minor=True, legal_representative=ION)]


# 2.1 balance at death
def test_balance_at_death():
    v = {x.product_id: x for x in balance_at_death(PRODUCTS, D)}
    assert v["CC-1"].total == 320_000
    assert v["DEP-1"].principal == 2_000_000
    assert v["DEP-1"].accrued_interest == 69_238          # 20.000 x 5,20% x 243/365
    assert v["CRD-1"].principal == -900_000
    assert v["CRD-1"].accrued_interest == -2_663          # 9.000 x 12% x 9/365


# 2.2 movements after death
def test_fees_to_reverse_only_after_death():
    flags = fees_to_reverse(MOVEMENTS, D)
    assert [(f.movement.date, f.amount) for f in flags] == [(date(2026, 9, 5), 6_000)]
    assert fees_to_reverse([Movement(date(2026, 8, 5), -6_000, "fee", fee_code="PREMIUM")], D) == []


def test_pension_of_death_month_is_kept_later_month_returned():
    flags = {f.movement.date: f.code for f in pension_flags(MOVEMENTS, D)}
    assert flags[date(2026, 9, 15)] == "post_death_credit"
    assert flags[date(2026, 10, 15)] == "pension_return_CNPP"


def test_mandate_withdrawal_after_death_is_flagged():
    mv = MOVEMENTS + [Movement(date(2026, 9, 10), -100_000, "withdrawal", by_mandate_holder=True)]
    flags = mandate_withdrawals(mv, D)
    assert len(flags) == 1 and flags[0].amount == 100_000


# 2.3 net of debts
def test_net_of_debts_with_insurance_covering_principal():
    net = net_of_debts(balance_at_death(PRODUCTS, D), MOVEMENTS, D, insurance_paid=900_000)
    assert net.gross == 530_000            # 3.200 + pensia de septembrie
    assert net.debts_deducted == 2_663     # dobânda neacoperită de asigurare
    assert net.withheld == 210_000         # pensia de octombrie, retur CNPP
    assert net.net == 527_337


def test_net_of_debts_without_insurance():
    net = net_of_debts(balance_at_death(PRODUCTS, D), MOVEMENTS, D, insurance_paid=0)
    # 089: the debt above the account is not taken below 0 (C.civ. art. 1114); the rest goes to the deposit
    assert net.debts_deducted == 530_000
    assert net.net == 0
    assert net.unpaid_debt == 902_663 - 530_000


# 2.4 shares
def test_shares_must_sum_to_one():
    with pytest.raises(ValueError):
        validate_shares([Heir("a", "A", Fraction(1, 2)), Heir("b", "B", Fraction(1, 4))])


def test_largest_remainder_sums_exactly_and_is_deterministic():
    assert sum(largest_remainder(527_337, [Fraction(5, 8), Fraction(3, 16), Fraction(3, 16)])) == 527_337
    assert largest_remainder(100, [Fraction(1, 3)] * 3) == [34, 33, 33]


@pytest.mark.parametrize("heirs,expected_cur,expected_dep", [
    (HEIRS_A, {ION: 329_585, ANDREI: 98_876, ELENA: 98_876}, {ION: 1_315_000, ANDREI: 394_500, ELENA: 394_500}),
    (HEIRS_B, {ION: 395_503, ANDREI: 65_917, ELENA: 65_917}, {ION: 1_578_000, ANDREI: 263_000, ELENA: 263_000}),
])
def test_split_by_shares_variants(heirs, expected_cur, expected_dep):
    cur = split_by_shares(heirs, "CC-1", 527_337, Fraction(1, 2), surviving_spouse_id=ION)
    assert {l.heir_id: l.amount for l in cur} == expected_cur
    assert sum(l.amount for l in cur) == 527_337
    dep = split_by_shares(heirs, "DEP-1", 2_104_000, Fraction(1, 2), surviving_spouse_id=ION)
    assert {l.heir_id: l.amount for l in dep} == expected_dep
    assert next(l for l in cur if l.heir_id == ELENA).blocked_reason == "minor_requires_representation"
    assert next(l for l in cur if l.heir_id == ION).blocked_reason is None


def test_fractions_of_product_variant_A():
    cur = split_by_shares(HEIRS_A, "CC-1", 527_337, Fraction(1, 2), surviving_spouse_id=ION)
    assert [l.fraction_of_product for l in cur] == [Fraction(5, 8), Fraction(3, 16), Fraction(3, 16)]


# 2.5 coverage
def test_coverage_gap_when_certificate_omits_deposit():
    assert coverage_gaps(["CC-1", "DEP-1", "CRD-1"], ["CC-1", "CRD-1"]) == ["DEP-1"]
    assert coverage_gaps(["CC-1", "DEP-1"], ["CC-1", "DEP-1"]) == []


# deadlines
def test_deadlines():
    dl = {d.code: d.due for d in deadlines(D, learned_on=date(2026, 9, 20), notary_hearing=date(2026, 10, 20))}
    assert dl["succession_option"] == date(2027, 9, 3)
    assert dl["insurance_claim_notice"] == date(2026, 10, 20)
    assert dl["notary_answer"] == date(2026, 10, 20)


# insurers (task 073): rules per insurer, not a hardcoded UNIQA 30 days
def test_deadline_uniqa_is_marked_hypothesis():
    d = {x.code: x for x in deadlines(D, learned_on=date(2026, 9, 20), insurer="UNIQA Asigurări de viață S.A.")}["insurance_claim_notice"]
    assert d.due == date(2026, 10, 20) and d.hypothesis and "ipoteză, de confirmat" in d.basis


def test_deadline_allianz_90_days_from_death_capped_at_2_years():
    d = {x.code: x for x in deadlines(D, learned_on=date(2026, 9, 20), insurer="Allianz-Țiriac Asigurări")}["insurance_claim_notice"]
    assert d.due == date(2026, 12, 2) and not d.hypothesis      # 3 Sep + 90 days
    late = {x.code: x for x in deadlines(D, learned_on=date(2030, 1, 1), insurer="Allianz")}["insurance_claim_notice"]
    assert late.due == date(2026, 12, 2)                          # counted from death, never later than 2 years
    from agent.rules import insurance_notice_deadline
    assert insurance_notice_deadline(D, date(2026, 9, 20), "Allianz").due <= date(2028, 9, 3)


def test_deadline_nn_30_days_confirmed_and_unknown_insurer_has_none():
    d = {x.code: x for x in deadlines(D, learned_on=date(2026, 9, 20), insurer="NN Asigurări de Viață")}["insurance_claim_notice"]
    assert d.due == date(2026, 10, 3) and not d.hypothesis
    assert "insurance_claim_notice" not in {x.code for x in deadlines(D, date(2026, 9, 20), insurer="Necunoscuta SA")}


def test_insurer_checklists_come_from_the_structure():
    from agent.insurers import lookup
    assert lookup("UNIQA Asigurări de viață S.A.").key == "uniqa" and lookup(None).key == "uniqa"
    assert lookup("Allianz-Țiriac").key == "allianz" and lookup("NN Asigurări de Viață").key == "nn"
    assert lookup("Altceva SA").key == "necunoscut"
    assert any("F1" in t for t in lookup("UNIQA").heir_documents())
    assert not any("graficul" in t for t in lookup("UNIQA").heir_documents())          # the bank holds it
    assert any("datele bancare" in t for t in lookup("Allianz").heir_documents())
    assert any("fișa medicală" in t for t in lookup("NN").heir_documents(cause="boală"))
    assert not any("fișa medicală" in t for t in lookup("NN").heir_documents(cause="accident"))
    assert lookup("NN").payment.label.startswith("10 de zile lucrătoare")
