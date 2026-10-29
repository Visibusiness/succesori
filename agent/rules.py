"""Deterministic domain rules for the succession agent.

Pure functions only: no I/O, no LLM. Every number is an integer amount in bani (RON x 100)
and every date is a `datetime.date`. The expected values live in
kb/scenariu-demo/maria-ionescu.md and are asserted in tests/test_rules.py.

Legal basis is cited next to each rule (Cod civil = C.civ., Legea 360/2023 = pensions).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from typing import Iterable, Literal

DAYS_IN_YEAR = 365  # Act/365 convention (assumption, see KB "Necunoscut")
# debts of the deceased: valued negative at D and paid from the estate before the heirs (C.civ. art. 1114).
# A credit card is a debt like a loan (used balance + interest since the last statement), never insured here.
DEBT_TYPES = ("personal_loan", "credit_card")


# ---------------------------------------------------------------- data shapes
@dataclass(frozen=True)
class Product:
    id: str
    type: Literal["current_account", "term_deposit", "personal_loan", "credit_card"]
    # current account: balance at date of death
    balance: int = 0
    # term deposit
    principal: int = 0
    rate_pct: float = 0.0
    start: date | None = None
    maturity: date | None = None
    # loan / credit card
    outstanding: int = 0  # positive number, principal still owed (credit card: the balance used)
    last_interest_paid: date | None = None
    insurance_policy_id: str | None = None
    # fraction of the product that belongs to the estate (after liquidating the
    # marital community, C.civ. art. 339/343): 1/2 for common goods, 1 for own goods
    estate_fraction: Fraction = Fraction(1)


@dataclass(frozen=True)
class Movement:
    date: date
    amount: int  # signed: credits positive, debits negative
    kind: Literal["fee", "pension_credit", "salary_credit", "withdrawal", "transfer", "other"]
    fee_code: str | None = None
    by_mandate_holder: bool = False  # executed by an împuternicit (C.civ. art. 2030)


@dataclass(frozen=True)
class Heir:
    id: str
    name: str
    share: Fraction  # share of the estate, as written in the certificate
    minor: bool = False
    legal_representative: str | None = None


@dataclass(frozen=True)
class ValuedProduct:
    product_id: str
    type: str
    principal: int
    accrued_interest: int

    @property
    def total(self) -> int:
        return self.principal + self.accrued_interest


# ---------------------------------------------------------------- 1. balance at death
def _days(a: date, b: date) -> int:
    return (b - a).days


def accrued_simple_interest(principal: int, rate_pct: float, days: int) -> int:
    """Simple interest in bani, rounded half-up to the nearest ban."""
    if days <= 0 or principal == 0:
        return 0
    value = principal * rate_pct / 100 * days / DAYS_IN_YEAR
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


def balance_at_death(products: Iterable[Product], date_of_death: date) -> list[ValuedProduct]:
    """Value of every product exactly at the date of death (what the notary asks for).

    - current account: the balance as given;
    - term deposit: principal + gross interest accrued from start to D (Act/365);
    - loan / credit card: negative outstanding principal + negative interest accrued since the last paid instalment
      (card: since the last statement).
    """
    out: list[ValuedProduct] = []
    for p in products:
        if p.type == "current_account":
            out.append(ValuedProduct(p.id, p.type, p.balance, 0))
        elif p.type == "term_deposit":
            assert p.start is not None
            interest = accrued_simple_interest(p.principal, p.rate_pct, _days(p.start, date_of_death))
            out.append(ValuedProduct(p.id, p.type, p.principal, interest))
        elif p.type in DEBT_TYPES:
            since = p.last_interest_paid or date_of_death
            interest = accrued_simple_interest(p.outstanding, p.rate_pct, _days(since, date_of_death))
            out.append(ValuedProduct(p.id, p.type, -p.outstanding, -interest))
        else:  # pragma: no cover
            raise ValueError(f"unknown product type {p.type}")
    return out


# ---------------------------------------------------------------- 2. post-death movements
@dataclass(frozen=True)
class Flag:
    movement: Movement
    code: Literal["fee_to_reverse", "pension_return_CNPP", "post_death_mandate_withdrawal", "post_death_credit"]
    amount: int  # always positive


def fees_to_reverse(movements: Iterable[Movement], date_of_death: date,
                    fee_codes: tuple[str, ...] | None = None) -> list[Flag]:
    """Administration fees debited after the date of death must be reversed, whatever their code
    (089: before, only PREMIUM was; a standard-package fee stayed charged, the Bragadiru pattern).

    The contract allows fees only while the relationship is alive; after D the bank is
    holding estate money (cazul Bragadiru 2023: 60 lei/lună, 21 de luni). `fee_codes` narrows
    the reversal to some codes (None = every fee).
    """
    return [Flag(m, "fee_to_reverse", -m.amount)
            for m in movements
            if m.kind == "fee" and m.date > date_of_death and (fee_codes is None or m.fee_code in fee_codes)]


def pension_flags(movements: Iterable[Movement], date_of_death: date) -> list[Flag]:
    """Pension credited after death.

    Legea 360/2023 art. 100 alin. 1 lit. a: the pension stops starting with the month
    FOLLOWING the death, so the pension of the month of death is owed and stays in the
    estate. Later months are not owed and are returned to CNPP on request
    (art. 156 alin. 8), without the heirs' consent.
    """
    flags: list[Flag] = []
    for m in movements:
        if m.kind != "pension_credit" or m.date <= date_of_death:
            continue
        same_month = (m.date.year, m.date.month) == (date_of_death.year, date_of_death.month)
        flags.append(Flag(m, "post_death_credit" if same_month else "pension_return_CNPP", m.amount))
    return flags


def mandate_withdrawals(movements: Iterable[Movement], date_of_death: date) -> list[Flag]:
    """Debits made by an împuternicit after D: the mandate ended at death (C.civ. art. 2030,
    CGB 3.2.5 b). They are reported to the notary and escalated, never silently accepted."""
    return [Flag(m, "post_death_mandate_withdrawal", -m.amount)
            for m in movements
            if m.by_mandate_holder and m.amount < 0 and m.date > date_of_death]


# ---------------------------------------------------------------- 3. net of debts
@dataclass(frozen=True)
class NetAccount:
    product_id: str
    gross: int
    debts_deducted: int
    withheld: int
    net: int
    unpaid_debt: int = 0   # debt the account cannot cover: taken from the deposits, then left to the operator


def net_of_debts(valued: list[ValuedProduct], movements: Iterable[Movement], date_of_death: date,
                 insurance_paid: int = 0) -> NetAccount:
    """Amount of the CURRENT ACCOUNT available for distribution.

    Heirs answer for debts within the estate (C.civ. art. 1114). The loan principal is paid
    by the credit life insurance (`insurance_paid`); whatever the insurance does not cover
    (accrued interest) is deducted from the account. Pension credits of the month of death
    are added (they are owed); later pensions are withheld for return to CNPP.
    The account never goes below 0 (089): a debt above it is `unpaid_debt`, which the plan takes
    from the deposits; the heirs answer within the estate, never beyond it (C.civ. art. 1114).
    """
    account = next(v for v in valued if v.type == "current_account")
    loans = [v for v in valued if v.type in DEBT_TYPES]
    loan_total = -sum(v.total for v in loans)  # positive
    remaining_debt = max(loan_total - insurance_paid, 0)

    pflags = pension_flags(movements, date_of_death)
    kept = sum(f.amount for f in pflags if f.code == "post_death_credit")
    withheld = sum(f.amount for f in pflags if f.code == "pension_return_CNPP")

    gross = account.total + kept
    deducted = min(remaining_debt, max(gross, 0))
    return NetAccount(account.product_id, gross, deducted, withheld, gross - deducted, remaining_debt - deducted)


# ---------------------------------------------------------------- 4. shares
@dataclass(frozen=True)
class PaymentLine:
    heir_id: str
    name: str
    product_id: str
    fraction_of_product: Fraction
    amount: int
    blocked_reason: str | None = None


def validate_shares(heirs: list[Heir]) -> None:
    """Shares come from the certificate, never from the law. They must sum to exactly 1."""
    total = sum((h.share for h in heirs), Fraction(0))
    if total != 1:
        raise ValueError(f"shares sum to {total}, expected 1")


def largest_remainder(amount: int, fractions: list[Fraction]) -> list[int]:
    """Split `amount` by `fractions` into integers that sum exactly to `amount`.
    Ties go to the earlier position (the heirs' order in the certificate), deterministic."""
    raw = [amount * f for f in fractions]
    floors = [int(r) for r in raw]  # Fraction -> floor for non-negative
    left = amount - sum(floors)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - floors[i]), i))
    for i in order[:left]:
        floors[i] += 1
    return floors


def split_by_shares(heirs: list[Heir], product_id: str, amount: int,
                    estate_fraction: Fraction = Fraction(1),
                    surviving_spouse_id: str | None = None) -> list[PaymentLine]:
    """Payment lines for one product.

    `estate_fraction` is the part of the product that belongs to the estate (1/2 for a common
    good after liquidating the community). The rest belongs to the surviving spouse as owner,
    not as heir, so it is added to the spouse's line. Each heir then receives
    estate_fraction * share. Minors are blocked until the legal representative's documents
    (C.civ. art. 41, 144-146): the amount is computed but not payable.
    """
    validate_shares(heirs)
    fractions = []
    for h in heirs:
        f = estate_fraction * h.share
        if surviving_spouse_id and h.id == surviving_spouse_id:
            f += 1 - estate_fraction
        fractions.append(f)
    assert sum(fractions, Fraction(0)) == 1
    amounts = largest_remainder(amount, fractions)
    lines = []
    for h, f, a in zip(heirs, fractions, amounts):
        reason = "minor_requires_representation" if h.minor else None
        lines.append(PaymentLine(h.id, h.name, product_id, f, a, reason))
    return lines


# ---------------------------------------------------------------- 5. coverage
def coverage_gaps(bank_product_ids: Iterable[str], certificate_product_ids: Iterable[str]) -> list[str]:
    """Products the bank holds that the certificate does not mention -> a supplementary
    certificate is needed before those can be paid (practica notarială: supliment)."""
    cert = set(certificate_product_ids)
    return [p for p in bank_product_ids if p not in cert]


# ---------------------------------------------------------------- 6. deadlines
@dataclass(frozen=True)
class Deadline:
    code: str
    due: date
    basis: str
    hypothesis: bool = False   # True when the term is not confirmed by a public source (marked in UI via the basis text)


def insurance_notice_deadline(date_of_death: date, learned_on: date, insurer: str | None = None) -> Deadline | None:
    """Notice term to the insurer named on the document (default: UNIQA, Raiffeisen's). None when the term is not public."""
    from agent.insurers import CONFIRMED, lookup
    ins = lookup(insurer)
    term = ins.notice
    if term.days is None:
        return None
    start = date_of_death if ins.notice_from == "death" else learned_on
    due = _add_days(start, term.days)
    if term.max_years:
        due = min(due, _add_years(date_of_death, term.max_years))
    basis = f"{ins.name}: avizare în {term.label} de la {'deces' if ins.notice_from == 'death' else 'deces/aflare'} ({term.source})"
    return Deadline("insurance_claim_notice", due, basis, hypothesis=term.status != CONFIRMED)


def deadlines(date_of_death: date, learned_on: date, notary_hearing: date | None = None,
              insurer: str | None = None) -> list[Deadline]:
    out = [Deadline("succession_option", _add_years(date_of_death, 1), "C.civ. art. 1103: opțiunea succesorală, 1 an de la deces")]
    if (notice := insurance_notice_deadline(date_of_death, learned_on, insurer)):
        out.append(notice)
    if notary_hearing:
        out.append(Deadline("notary_answer", notary_hearing, "Legea 36/1995 art. 81 alin. 2: răspuns înainte de dezbatere"))
    return out


def _add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + n, day=28)


def _add_days(d: date, n: int) -> date:
    from datetime import timedelta
    return d + timedelta(days=n)
