"""In-memory core banking mock seeded with the demo customer (kb/scenariu-demo/maria-ionescu.md).
Replace with real adapters behind the same method names (kb/tech/api-contract-bank.md)."""
from __future__ import annotations

from dataclasses import asdict, fields
from datetime import date
from fractions import Fraction
from typing import Any

from agent.rules import Movement, Product


# Scenario variants selectable from /demo/reset?variants=... (docs/pitch/qa-juriu.md, questions 18-19):
#   pensie     - the October pension (2026-10-15, 210.000 bani) arrives -> flag pension_return_CNPP (default: on,
#                as in kb/scenariu-demo/maria-ionescu.md §2.2); the September one stays in the estate
#   retragere  - Andrei, the împuternicit, withdraws 100.000 bani on 2026-09-10 (after D, before DGEP)
#                -> flag post_death_mandate_withdrawal + escalation (maria-ionescu.md §4)
DEFAULT_VARIANTS = frozenset({"pensie"})
VARIANTS = {"pensie", "retragere"}


def _iban_key(iban: str) -> str:
    return iban.replace(" ", "").upper()


def _person_key(name: str) -> str:
    """'IONESCU MARIA' == 'Maria Ionescu' == 'Maria IONESCU' (word order, case and diacritics ignored)."""
    s = name.upper()
    for a, b in (("Ă", "A"), ("Â", "A"), ("Î", "I"), ("Ș", "S"), ("Ş", "S"), ("Ț", "T"), ("Ţ", "T")):
        s = s.replace(a, b)
    return " ".join(sorted(s.split()))



class Bank:
    def __init__(self, variants: set[str] | frozenset[str] = DEFAULT_VARIANTS) -> None:
        self.reset(variants)

    def reset(self, variants: set[str] | frozenset[str] = DEFAULT_VARIANTS) -> None:
        unknown = set(variants) - VARIANTS
        if unknown:
            raise ValueError(f"variante necunoscute: {sorted(unknown)}; permise: {sorted(VARIANTS)}")
        self.variants = frozenset(variants)
        # Identifiers from registries/documents (documente-demo.md §0): masked CNP, CC-1/DEP-1/CRD-1, NP-2023-001001,
        # UQ-0000000-FICTIV. With DEMO_MODE=1 only the check digits of CNP/IBAN are skipped (DECISIONS).
        self.customers: dict[str, dict[str, Any]] = {
            "RC1001": {"cif": "RC1001", "name": "Maria Ionescu", "cnp": "2XXXXXXXXXXXX", "birth_date": "1958-05-12",
                       "spouse": "Ion Ionescu",
                       "mandates": [{"id": "M-7", "holder": "Andrei Ionescu"}], "cards": ["C-1", "C-2"],
                       "frozen": None},
            "RC2002": {"cif": "RC2002", "name": "Vasile Pop", "cnp": "1XXXXXXXXXXX7", "birth_date": "1970-01-01",
                       "spouse": None, "mandates": [], "cards": ["C-9"], "frozen": None},
        }
        self._products: dict[str, list[Product]] = {
            "RC1001": [
                Product("CC-1", "current_account", balance=320_000, estate_fraction=Fraction(1, 2)),
                Product("DEP-1", "term_deposit", principal=2_000_000, rate_pct=5.20, start=date(2026, 1, 3),
                        maturity=date(2027, 1, 3), estate_fraction=Fraction(1, 2)),
                Product("CRD-1", "personal_loan", outstanding=900_000, rate_pct=12.0,
                        last_interest_paid=date(2026, 8, 25), insurance_policy_id="UQ-0000000-FICTIV"),
            ],
            "RC2002": [Product("CC-2", "current_account", balance=50_000)],
        }
        # what the documents cite (IBAN, loan contract number) -> internal product id
        self._ibans: dict[str, str] = {_iban_key("RO00 RZBR 0000 0000 0000 01"): "CC-1",
                                       _iban_key("RO00 RZBR 0000 0000 0000 02"): "DEP-1",
                                       _iban_key("RO00 RZBR 0000 0000 0000 09"): "CC-2"}
        self._loan_contracts: dict[str, str] = {"NP-2023-001001": "CRD-1"}
        # monthly instalment per loan; the scenario does not give one for CRD-1, so overdue instalments can't be
        # added to the expected indemnity (only the exact principal at D is accepted)
        self._installments: dict[str, int | None] = {"CRD-1": None}
        # verified contact data of people the bank knows (KYC); heirs who are not clients have none
        self.contacts: dict[str, dict[str, Any]] = {
            _person_key("Ion Ionescu"): {"email": "ion.ionescu@example.invalid", "sms": "+40 700 000 001", "preferred": "email",
                            "verified": True, "is_client": True, "address": "Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu"},
            _person_key("Andrei Ionescu"): {"email": "andrei.ionescu@example.invalid", "sms": "+40 700 000 002", "preferred": "sms",
                               "verified": True, "is_client": True, "address": "Municipiul Exemplu, Str. Fictivă nr. 7, Jud. Exemplu"},
        }
        movements = [
            Movement(date(2026, 8, 5), -6_000, "fee", fee_code="PREMIUM"),
            Movement(date(2026, 8, 15), 210_000, "pension_credit"),
            Movement(date(2026, 9, 5), -6_000, "fee", fee_code="PREMIUM"),
            Movement(date(2026, 9, 15), 210_000, "pension_credit"),
        ]
        if "pensie" in self.variants:
            movements.append(Movement(date(2026, 10, 15), 210_000, "pension_credit"))
        if "retragere" in self.variants:
            movements.append(Movement(date(2026, 9, 10), -100_000, "withdrawal", by_mandate_holder=True))
        self._movements: dict[str, list[Movement]] = {"RC1001": movements, "RC2002": []}
        self.audit: list[dict[str, Any]] = []
        self.reversed_fees: set[tuple[str, str, int, int]] = set()
        self.payments: list[dict[str, Any]] = []

    def add_customer(self, customer: dict[str, Any], products: list[Product], movements: list[Movement] | None = None,
                     ibans: dict[str, str] | None = None, loan_contracts: dict[str, str] | None = None,
                     installments: dict[str, int | None] | None = None,
                     contacts: dict[str, dict[str, Any]] | None = None) -> None:
        """One more customer of the mock core (the seeded portfolio, agent/portfolio.py). `contacts`: person name -> KYC."""
        cif = customer["cif"]
        self.customers[cif] = {"spouse": None, "mandates": [], "cards": [], "frozen": None, **customer}
        self._products[cif] = list(products)
        self._movements[cif] = list(movements or [])
        self._ibans.update({_iban_key(k): v for k, v in (ibans or {}).items()})
        self._loan_contracts.update(loan_contracts or {})
        self._installments.update(installments or {})
        self.contacts.update({_person_key(n): c for n, c in (contacts or {}).items()})

    # ---- persistence (agent/store.py): explicit, JSON-safe; dates ISO, Fraction as "1/2", sets as lists
    def to_dict(self) -> dict[str, Any]:
        return {"variants": sorted(self.variants), "customers": self.customers,
                "products": {cif: [_product_out(p) for p in ps] for cif, ps in self._products.items()},
                "movements": {cif: [_movement_out(m) for m in ms] for cif, ms in self._movements.items()},
                "ibans": self._ibans, "loan_contracts": self._loan_contracts, "installments": self._installments,
                "contacts": self.contacts, "audit": self.audit,
                "reversed_fees": sorted([list(k) for k in self.reversed_fees]), "payments": self.payments}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Bank":
        b = cls.__new__(cls)
        b.variants = frozenset(d.get("variants") or [])
        b.customers = d["customers"]
        b._products = {cif: [_product_in(p) for p in ps] for cif, ps in d["products"].items()}
        b._movements = {cif: [_movement_in(m) for m in ms] for cif, ms in d["movements"].items()}
        b._ibans, b._loan_contracts = dict(d["ibans"]), dict(d["loan_contracts"])
        b._installments, b.contacts = dict(d["installments"]), dict(d["contacts"])
        b.audit, b.payments = list(d["audit"]), list(d["payments"])
        b.reversed_fees = {tuple(k) for k in d["reversed_fees"]}
        return b

    def load(self, d: dict[str, Any]) -> None:
        """In place (the API, the pipeline and the routers hold this very object)."""
        self.__dict__.update(Bank.from_dict(d).__dict__)

    # ---- queries
    def find_customer(self, cnp: str) -> dict[str, Any] | None:
        """089: via a cnp -> cif index (083: a scan of every customer per document). Same answer as the scan (the first
        customer with this CNP): a hit is checked against the customer, a miss falls back to the scan, and the index is
        rebuilt when `customers` is replaced, grows or shrinks from outside (scripts add customers directly)."""
        idx = getattr(self, "_by_cnp", None)
        if idx is None or self._by_cnp_of != (id(self.customers), len(self.customers)):
            idx = self._by_cnp = {}
            for c in self.customers.values():
                idx.setdefault(c["cnp"], c["cif"])
            self._by_cnp_of = (id(self.customers), len(self.customers))
        c = self.customers.get(idx.get(cnp, ""))
        if c is not None and c["cnp"] == cnp:
            return c
        c = next((c for c in self.customers.values() if c["cnp"] == cnp), None)
        if c is not None:   # a CNP changed in place: the index was stale
            self._by_cnp_of = None
        return c

    def find_by_name_birth(self, name: str, birth_date: str) -> list[dict[str, Any]]:
        """All customers with this name (case/diacritics-insensitive, any word order) and birth date."""
        return [c for c in self.customers.values()
                if _person_key(c["name"]) == _person_key(name) and c.get("birth_date") == birth_date]

    def product_by_iban(self, cif: str, iban: str) -> str | None:
        pid = self._ibans.get(_iban_key(iban))
        return pid if pid and any(p.id == pid for p in self._products.get(cif, [])) else None

    def product_by_loan_contract(self, cif: str, contract: str) -> str | None:
        pid = self._loan_contracts.get(contract.strip())
        return pid if pid and any(p.id == pid for p in self._products.get(cif, [])) else None

    def installment(self, cif: str, product_id: str) -> int | None:
        return self._installments.get(product_id)

    def contact(self, name: str) -> dict[str, Any] | None:
        return self.contacts.get(_person_key(name))

    def products(self, cif: str) -> list[Product]:
        return self._products[cif]

    def movements(self, cif: str) -> list[Movement]:
        return self._movements[cif]

    # ---- commands (all idempotent)
    def reset_customer(self, cif: str) -> None:
        """One customer back to the start, the others untouched (POST /demo/reset?case=): its audit entries, reversed
        fees and payments are dropped; Maria's / Vasile Pop's core data come back as in reset(). A portfolio client is
        reinstalled by agent/portfolio.py right after."""
        self.audit = [a for a in self.audit if a.get("cif") != cif]
        self.reversed_fees = {k for k in self.reversed_fees if k[0] != cif}
        self.payments = [p for p in self.payments if p.get("cif") != cif]
        fresh = Bank(self.variants)
        if cif in fresh.customers:
            self.customers[cif] = fresh.customers[cif]
            self._products[cif] = fresh._products[cif]
            self._movements[cif] = fresh._movements[cif]
        elif cif in self.customers:
            self.customers[cif]["frozen"] = None

    def _log(self, **e: Any) -> str:
        # max + 1: reset_customer may take entries out of the middle
        aid = f"A-{max((int(a['audit_id'].split('-')[-1]) for a in self.audit), default=0) + 1}"
        self.audit.append({"audit_id": aid, **e})
        return aid

    def freeze(self, cif: str, dod: date, reversible: bool) -> dict[str, Any]:
        c = self.customers[cif]
        already = c["frozen"] is not None
        if not already or (c["frozen"]["reversible"] and not reversible):
            c["frozen"] = {"date_of_death": dod.isoformat(), "reversible": reversible}
            self._log(action="freeze", cif=cif, reversible=reversible)
        return {"cif": cif, "already_frozen": already, "reversible": reversible,
                "suspended_mandates": [m["holder"] for m in c["mandates"]], "cards": c["cards"]}

    def reverse_fees(self, cif: str, items: list[tuple[date, int]]) -> int:
        total, seen = 0, {}
        for d, amount in items:
            # 089: every fee code is reversed now, so two fees of the same day must not collapse into one key
            n = seen[(d, amount)] = seen.get((d, amount), 0) + 1
            key = (cif, d.isoformat(), amount, n)
            if key in self.reversed_fees:
                continue
            self.reversed_fees.add(key)
            self._movements[cif].append(Movement(date.today(), amount, "other", fee_code="REVERSAL"))
            total += amount
        if total:
            self._log(action="reverse_fees", cif=cif, total=total)
        return total

    def settle_loan(self, cif: str, amount: int) -> None:
        self._log(action="loan_settled_by_insurer", cif=cif, amount=amount)

    def pay(self, cif: str, lines: list[tuple[str, int]]) -> None:
        for pid, amount in lines:
            self.payments.append({"cif": cif, "product_id": pid, "amount": amount, "status": "executed"})
        self._log(action="pay", cif=cif, count=len(lines), total=sum(a for _, a in lines))


_DATE_FIELDS = {"start", "maturity", "last_interest_paid", "date"}


def _product_out(p: Product) -> dict[str, Any]:
    d = asdict(p)
    for k in _DATE_FIELDS & d.keys():
        d[k] = d[k].isoformat() if d[k] else None
    d["estate_fraction"] = str(p.estate_fraction)
    return d


def _product_in(d: dict[str, Any]) -> Product:
    known = {f.name for f in fields(Product)}
    d = {k: v for k, v in d.items() if k in known}
    for k in _DATE_FIELDS & d.keys():
        d[k] = date.fromisoformat(d[k]) if d[k] else None
    d["estate_fraction"] = Fraction(d.get("estate_fraction") or "1")
    return Product(**d)


def _movement_out(m: Movement) -> dict[str, Any]:
    return {**asdict(m), "date": m.date.isoformat()}


def _movement_in(d: dict[str, Any]) -> Movement:
    return Movement(**{**d, "date": date.fromisoformat(d["date"])})
