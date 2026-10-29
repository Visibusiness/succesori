"""Implementarea de referință pentru simularea la scară (sarcina 082): ce ar trebui să iasă dintr-un dosar generat.

Scrisă de la zero din regulile din kb/ (nu importă agent/rules.py, ca simularea să nu verifice codul cu el însuși):
- comisioane debitate după data decesului ⇒ stornate toate, oricare ar fi codul lor (BRIEF §2: „oprire + stornare
  comisioane de la data decesului”; cazul Bragadiru);
- pensia lunii decesului, virată după deces, se cuvine și intră în masă; pensiile lunilor următoare se rețin pentru
  CNPP (Legea 360/2023 art. 100 alin. 1 lit. a, art. 156 alin. 8);
- retragerile împuternicitului după deces ⇒ semnalate și escaladate; suma nu se scade din masă (e de recuperat,
  maria-ionescu.md §4);
- datoria = principal + dobânda de la ultima rată la D (Act/365, rotunjire la ban, jumătatea în sus), minus indemnizația
  aprobată; se scade din contul curent înainte de împărțire (maria-ionescu.md §2.3) și, dacă nu ajunge, din depozit
  (C.civ. art. 1114: moștenitorii răspund în limita activului, nu peste el);
- bun comun ⇒ 1/2 revine soțului ca proprietar, 1/2 intră în masă; soțul e cel numit „soț supraviețuitor” în
  certificat, nu cel de pe primul rând (C.civ. art. 339, 343);
- rotunjire: cea mai mare rămășiță, la egalitate ordinea din certificat (maria-ionescu.md §2.4);
- depozitul se plătește la scadență, cu dobânda integrală; dacă scadența a trecut la data planului, e plătibil acum;
- minorul: partea lui e calculată, dar blocată până la reprezentare (C.civ. art. 41, 144–146);
- plata nu pleacă fără aprobare umană.
"""
from __future__ import annotations

from datetime import date
from fractions import Fraction


def _d(s: str) -> date:
    return date.fromisoformat(s)


def interest(principal: int, rate_pct: float, days: int) -> int:
    """Dobândă simplă exactă (Fraction), Act/365, rotunjită la ban, jumătatea în sus."""
    if days <= 0 or principal <= 0:
        return 0
    x = Fraction(principal) * Fraction(str(rate_pct)) / 100 * days / 365
    return int(x + Fraction(1, 2))


def split(amount: int, fractions: list[Fraction]) -> list[int]:
    """Cea mai mare rămășiță pe numărători întregi; la egalitate câștigă poziția mai mică."""
    den = 1
    for f in fractions:
        den = den * f.denominator // _gcd(den, f.denominator)
    nums = [f.numerator * (den // f.denominator) for f in fractions]
    base = [amount * n // den for n in nums]
    rem = [amount * n % den for n in nums]
    extra = amount - sum(base)
    for idx in sorted(range(len(nums)), key=lambda k: (-rem[k], k))[:extra]:
        base[idx] += 1
    return base


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def expected(case: dict) -> dict:
    dod = _d(case["date_of_death"])
    prods = {p["id"]: p for p in case["products"]}
    mv = case["movements"]
    feat = case["features"]
    docs = [d for d in case["documents"] if not d["id"].endswith("-x")]

    fees = sum(-m["amount"] for m in mv if m["kind"] == "fee" and _d(m["date"]) > dod)
    pens_after = [m for m in mv if m["kind"] == "pension_credit" and _d(m["date"]) > dod]
    kept = sum(m["amount"] for m in pens_after if (_d(m["date"]).year, _d(m["date"]).month) == (dod.year, dod.month))
    returned = sum(m["amount"] for m in pens_after) - kept
    withdrawals = sum(-m["amount"] for m in mv if m.get("by_mandate_holder") and m["amount"] < 0 and _d(m["date"]) > dod)

    debt = 0
    crd = prods.get("CRD-1")
    if crd:
        debt = crd["outstanding"] + interest(crd["outstanding"], crd["rate_pct"], (dod - _d(crd["last_interest_paid"])).days)
        if feat["insured"] and not feat["refused"]:
            debt -= crd["outstanding"]

    cc = prods["CC-1"]
    gross = cc["balance"] + kept
    from_cc = min(debt, gross)
    net_cc = gross - from_cc
    excess = debt - from_cc

    # data planului: ultimul dintre documentele care îl condiționează (acoperirea completă, răspunsul asigurătorului)
    gating = [d for d in docs if d["document_type"] in ("heir_certificate", "supplementary_certificate", "insurer_response")]
    plan_date = max(_d(d["received_on"]) for d in gating)

    heirs = next(d for d in docs if d["document_type"] == "heir_certificate")["fields"]["heirs"]
    spouse_id = case["spouse_id"]
    lines = []
    for pid, amount in (("CC-1", net_cc), ("DEP-1", None)):
        p = prods.get(pid)
        if not p:
            continue
        if pid == "DEP-1":
            value = p["principal"] + interest(p["principal"], p["rate_pct"], (_d(p["maturity"]) - _d(p["start"])).days)
            amount = max(value - excess, 0)
            excess = max(excess - value, 0)
        ef = Fraction(p.get("estate_fraction", "1"))
        fr = [ef * Fraction(h["share"]) + ((1 - ef) if h["id"] == spouse_id else 0) for h in heirs]
        assert sum(fr) == 1
        for h, a in zip(heirs, split(amount, fr)):
            blocked = bool(h.get("minor")) or (pid == "DEP-1" and _d(p["maturity"]) > plan_date)
            lines.append({"heir": h["id"], "name": h["name"], "product_id": pid, "amount": a, "blocked": blocked})

    esc = ["minor_heir"] * sum(1 for h in heirs if h.get("minor"))
    if withdrawals:
        esc.append("post_death_mandate_withdrawal")
    if feat["refused"]:
        esc.append("insurance_refused")
    for n in feat["noise"]:
        esc.append("document_illegible" if n["kind"] == "illegible" else "suspicious_document")

    return {"fees_reversed": fees, "pension_kept": kept, "pension_return": returned, "mandate_withdrawals": withdrawals,
            "remaining_debt": debt, "net_account": net_cc, "unpaid_debt": excess, "plan_date": plan_date.isoformat(),
            "supplement_requested": bool(feat["omitted"]), "escalations": sorted(esc), "lines": lines,
            "payable_now": sum(l["amount"] for l in lines if not l["blocked"])}
