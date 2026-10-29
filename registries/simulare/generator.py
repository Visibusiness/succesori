"""Generator determinist de dosare de succesiune pentru simularea la scară (sarcina 082).

Pornește de la clienta demo (kb/scenariu-demo/maria-ionescu.md) și variază ce variază în viața reală: 2–5 moștenitori
cu cote legale sau testamentare, 0–2 minori, bunuri comune sau proprii, depozit (scadent sau nu la data planului),
credit cu/fără asigurare (aprobată/refuzată), comisioane și pensii după deces, retrageri ale împuternicitului, certificat
care omite un produs, ordinea documentelor, documente ilizibile sau suspecte.

Fiecare dosar e un dict JSON: clientul, produsele și mișcările din core, documentele deja extrase (forma pipeline-ului,
fără LLM) în ordinea sosirii, plus `features` (ce capcane conține). Ground truth-ul îl calculează `referinta.py`, care nu
importă nimic din agent/.

    python -m registries.simulare.generator --seed 82 --n 200     # scrie registries/simulare/dosare-seed82.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSURER = "UNIQA Asigurări de viață S.A."
FIRST = {"F": ["Maria", "Elena", "Ioana", "Ana", "Georgeta", "Florica", "Daniela", "Cristina", "Mihaela", "Rodica"],
         "M": ["Ion", "Andrei", "Mihai", "Vasile", "Gheorghe", "Nicolae", "Dan", "Radu", "Florin", "Constantin"]}
LAST = ["Ionescu", "Popescu", "Popa", "Stan", "Dumitru", "Stoica", "Gheorghe", "Matei", "Ciobanu", "Rusu", "Marin",
        "Tudor", "Florea", "Lazăr", "Moldovan", "Barbu", "Nistor", "Dinu", "Ene", "Toma"]

# probabilitățile variantelor (alese ca să apară fiecare capcană de zeci de ori în 200 de dosare)
P = {"spouse": 0.7, "common_goods": 0.7, "testament": 0.3, "spouse_not_first": 0.2, "deposit": 0.6, "deposit_matured": 0.35,
     "credit": 0.5, "insured": 0.7, "refused": 0.25, "premium": 0.55, "other_fee": 0.25, "pension": 0.55,
     "mandate_withdrawal": 0.15, "omit_product": 0.4, "dgep_late": 0.35, "death_certificate": 0.3, "illegible": 0.06,
     "suspicious": 0.05}


def cnp_check(first12: str) -> str:
    key = "279146358279"
    s = sum(int(a) * int(b) for a, b in zip(first12, key)) % 11
    return first12 + ("1" if s == 10 else str(s))


def make_cnp(rng: random.Random, female: bool, birth: date) -> str:
    sex = ("6" if female else "5") if birth.year >= 2000 else ("2" if female else "1")
    return cnp_check(f"{sex}{birth:%y%m%d}{rng.randint(1, 46):02d}{rng.randint(1, 999):03d}")


def rand_date(rng: random.Random, a: date, b: date) -> date:
    return a + timedelta(days=rng.randint(0, (b - a).days))


def add_months(d: date, n: int, day: int | None = None) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, day or min(d.day, 28))


def legal_shares(spouse: bool, n_children: int) -> list[Fraction]:
    """C.civ. art. 972 (soțul în concurs cu descendenții: 1/4) și art. 975 (descendenții, în părți egale)."""
    if spouse:
        return [Fraction(1, 4)] + [Fraction(3, 4) / n_children] * n_children
    return [Fraction(1, n_children)] * n_children


def testament_shares(rng: random.Random, n: int) -> list[Fraction]:
    w = [rng.randint(1, 4) for _ in range(n)]
    return [Fraction(x, sum(w)) for x in w]


def valid_order(rng: random.Random, docs: list[str]) -> list[str]:
    """O ordine aleatoare care respectă doar cauzalitatea reală: notarul cere soldurile înainte de certificat, suplimentul
    vine după certificat, răspunsul asigurătorului după avizarea daunei. Semnalul DGEP și certificatul de deces pot
    sosi oricând."""
    before = {"heir_certificate": "notary_request", "supplementary_certificate": "heir_certificate",
              "insurer_response": "insurance_certificate"}
    out, left = [], list(docs)
    while left:
        ready = [d for d in left if before.get(d) not in left]
        pick = rng.choice(ready)
        out.append(pick)
        left.remove(pick)
    return out


def generate_case(rng: random.Random, i: int) -> dict:
    cid = f"SIM-{i:03d}"
    female = rng.random() < 0.5
    last = rng.choice(LAST)
    name = f"{rng.choice(FIRST['F' if female else 'M'])} {last}"
    birth = rand_date(rng, date(1935, 1, 1), date(1968, 12, 31))
    dod = rand_date(rng, date(2026, 1, 10), date(2026, 8, 28))
    feat: dict = {}

    # ---- familia și cotele
    spouse = rng.random() < P["spouse"]
    n_heirs = rng.randint(2, 5)
    n_children = n_heirs - 1 if spouse else n_heirs
    n_minors = min(rng.choice([0, 0, 0, 1, 1, 2]), n_children)
    people = []
    if spouse:
        people.append({"name": f"{rng.choice(FIRST['M' if female else 'F'])} {last}", "relationship": "soț supraviețuitor",
                       "minor": False, "spouse": True})
    used = {name.split()[0]} | {p["name"].split()[0] for p in people}
    for k in range(n_children):
        sex = rng.choice("FM")
        first = rng.choice([f for f in FIRST[sex] if f not in used] or FIRST[sex])
        used.add(first)
        minor = k >= n_children - n_minors
        people.append({"name": f"{first} {last}", "relationship": "fiică" if sex == "F" else "fiu", "minor": minor,
                       "spouse": False})
    testament = rng.random() < P["testament"]
    shares = testament_shares(rng, n_heirs) if testament else legal_shares(spouse, n_children)
    for p, s in zip(people, shares):
        p["share"] = s
    if spouse and rng.random() < P["spouse_not_first"]:
        rest = people[1:]
        rng.shuffle(rest)
        people = rest[:1] + [people[0]] + rest[1:]
        feat["spouse_not_first"] = True
    heirs = []
    for k, p in enumerate(people):
        h = {"id": f"H{k + 1}", "name": p["name"], "share": str(p["share"]), "relationship": p["relationship"]}
        if p["minor"]:
            h["minor"] = True
            rep = next((f"H{j + 1}" for j, q in enumerate(people) if q["spouse"]), None)
            if rep:
                h["legal_representative"] = rep
        heirs.append(h)
    spouse_id = next((h["id"] for h, p in zip(heirs, people) if p["spouse"]), None)
    feat.update(testament=testament, n_heirs=n_heirs, n_minors=n_minors, spouse=spouse)

    # ---- când află banca: primul document; restul la câteva zile unul de altul
    learn_delay = rng.randint(25, 70) if rng.random() < P["dgep_late"] else rng.randint(6, 20)
    learned = dod + timedelta(days=learn_delay)

    # ---- produse
    common = spouse and rng.random() < P["common_goods"]
    ef = "1/2" if common else "1"
    feat["common_goods"] = common
    products = [{"id": "CC-1", "type": "current_account", "balance": rng.randint(30, 2500) * 1000 + rng.randint(0, 99),
                 "estate_fraction": ef}]
    docs_kinds = ["notary_request", "heir_certificate"]
    if rng.random() < P["deposit"]:
        start = rand_date(rng, dod - timedelta(days=330), dod - timedelta(days=20))
        months = rng.choice([3, 6, 12])
        maturity = add_months(start, months)
        while maturity <= dod:
            months += 6
            maturity = add_months(start, months)
        products.append({"id": "DEP-1", "type": "term_deposit", "principal": rng.randint(20, 1200) * 10000,
                         "rate_pct": rng.choice([2.5, 3.1, 4.0, 4.75, 5.2, 5.85, 6.3]), "start": start.isoformat(),
                         "maturity": maturity.isoformat(), "estate_fraction": ef})
    credit = rng.random() < P["credit"]
    insured = credit and rng.random() < P["insured"]
    refused = insured and rng.random() < P["refused"]
    if credit:
        products.append({"id": "CRD-1", "type": "personal_loan", "outstanding": rng.randint(10, 600) * 5000,
                         "rate_pct": rng.choice([8.5, 9.9, 11.0, 12.0, 14.5]),
                         "last_interest_paid": (dod - timedelta(days=rng.randint(1, 30))).isoformat(),
                         "insurance_policy_id": f"UQ-{i:07d}-SIM" if insured else None, "loan_contract": f"NP-SIM-{i:04d}"})
        if insured:
            docs_kinds += ["insurance_certificate", "insurer_response"]
    feat.update(deposit=any(p["type"] == "term_deposit" for p in products), credit=credit, insured=insured, refused=refused)

    # ---- mișcări în core
    mv = []
    fee_codes = []
    if rng.random() < P["premium"]:
        fee_codes.append(("PREMIUM", rng.choice([2500, 6000])))
    if rng.random() < P["other_fee"]:
        fee_codes.append(("ADMIN_CONT", rng.choice([500, 900, 1500])))
    for code, amount in fee_codes:
        for k in range(-1, 4):
            d = add_months(dod.replace(day=1), k, 5)
            if d < learned and d != dod:
                mv.append({"date": d.isoformat(), "amount": -amount, "kind": "fee", "fee_code": code})
    feat["fee_codes"] = [c for c, _ in fee_codes]
    if rng.random() < P["pension"]:
        amount = rng.randint(120, 450) * 1000
        for k in range(-1, 4):
            d = add_months(dod.replace(day=1), k, 15)
            if d < learned and d != dod:
                mv.append({"date": d.isoformat(), "amount": amount, "kind": "pension_credit"})
    mandates = []
    majors = [h for h in heirs if not h.get("minor") and h["id"] != spouse_id]
    if majors and rng.random() < 0.6:
        mandates.append({"id": "M-1", "holder": majors[0]["name"]})
        if rng.random() < P["mandate_withdrawal"] / 0.6 and learn_delay > 2:
            d = dod + timedelta(days=rng.randint(1, learn_delay - 1))
            mv.append({"date": d.isoformat(), "amount": -rng.randint(2, 30) * 5000, "kind": "withdrawal",
                       "by_mandate_holder": True})
    mv.sort(key=lambda m: m["date"])

    # ---- certificatul (poate omite un produs) și suplimentul
    assets = [p["id"] for p in products if p["type"] != "personal_loan"]
    omitted = []
    if rng.random() < P["omit_product"]:
        omitted = [rng.choice(assets)] if len(assets) > 1 else []
        if len(assets) > 1 and "DEP-1" in assets and rng.random() < 0.8:
            omitted = ["DEP-1"]
    if omitted:
        docs_kinds.append("supplementary_certificate")
    if rng.random() < P["death_certificate"]:
        docs_kinds.append("death_certificate")
    dgep_first = learn_delay <= 20
    docs_kinds.append("dgep_signal")
    order = valid_order(rng, docs_kinds)
    if dgep_first:   # semnalul DGEP vine săptămânal: când întârzierea e mică, el deschide dosarul
        order.remove("dgep_signal")
        order.insert(0, "dgep_signal")
    elif order[0] == "dgep_signal":   # întârziat: îl precede cel puțin un alt document
        order.remove("dgep_signal")
        order.insert(rng.randint(1, len(order)), "dgep_signal")
    feat["omitted"] = omitted
    feat["order"] = order

    cnp = make_cnp(rng, female, birth)
    case_file = f"{rng.randint(10, 999)}/2026"
    received = learned
    documents = []
    for n, kind in enumerate(order):
        f: dict = {"cnp": cnp}
        if kind in ("dgep_signal", "notary_request", "death_certificate"):
            f["date_of_death"] = dod.isoformat()
        if kind == "dgep_signal":
            f["document_number"] = f"DGEP-SIM-{i:03d}"
        elif kind == "notary_request":
            f.update(case_file=case_file, document_number=str(rng.randint(100, 999)),
                     hearing_date=(received + timedelta(days=rng.randint(20, 40))).isoformat())
        elif kind == "insurance_certificate":
            f.update(policy_id=f"UQ-{i:07d}-SIM", insurer=INSURER, loan_contract=f"NP-SIM-{i:04d}",
                     document_number=f"UQ-{i:07d}-SIM")
        elif kind == "insurer_response":
            crd = next(p for p in products if p["type"] == "personal_loan")
            f.update(policy_id=f"UQ-{i:07d}-SIM", decision="refused" if refused else "approved",
                     amount=0 if refused else crd["outstanding"], document_number=f"DV-{i:04d}",
                     claim_number=f"DV-{i:04d}/2026", loan_contract=f"NP-SIM-{i:04d}")
            if refused:
                f["reason"] = "excludere: afecțiune preexistentă (primele 24 de luni)"
        elif kind == "heir_certificate":
            f.update(case_file=case_file, document_number=str(rng.randint(10, 99)), testament=testament, heirs=heirs,
                     products=[a for a in assets if a not in omitted])
        elif kind == "supplementary_certificate":
            f.update(case_file=case_file, document_number=str(rng.randint(100, 199)), products=omitted)
        elif kind == "death_certificate":
            f.update(document_series="DZ", document_number=str(rng.randint(100000, 999999)))
        doc = {"id": f"{cid}-d{n + 1}", "raw_name": f"{cid}-{kind}.json", "document_type": kind,
               "received_on": received.isoformat(), "confidence": round(rng.uniform(0.84, 0.99), 2), "fields": f}
        documents.append(doc)
        received += timedelta(days=rng.randint(2, 18))

    # ---- capcane de document: o copie ilizibilă sau una suspectă înaintea celei bune (banca o cere din nou)
    noise = []
    for kind, p in (("illegible", P["illegible"]), ("suspicious", P["suspicious"])):
        if rng.random() < p:
            k = rng.randrange(1, len(documents)) if len(documents) > 1 else 0
            good = documents[k]
            bad = json.loads(json.dumps(good))
            bad["id"] += "-x"
            bad["raw_name"] = bad["raw_name"].replace(".json", f"-{kind}.json")
            if kind == "illegible":
                bad.update(confidence=0.42)
                bad["fields"] = {"cnp": None, "date_of_death": None, "document_number": None}
            else:
                bad["injection_suspected"] = {"value": True, "reason": "textul cere plata imediată într-un IBAN nou"}
            documents.insert(k, bad)
            noise.append({"kind": kind, "document_type": good["document_type"]})
    feat["noise"] = noise

    return {"id": cid, "customer": {"cif": f"SIM{i:03d}", "name": name, "cnp": cnp, "birth_date": birth.isoformat(),
                                    "spouse": next((p["name"] for p in people if p["spouse"]), None),
                                    "mandates": mandates, "cards": ["C-1"]},
            "date_of_death": dod.isoformat(), "products": products, "movements": mv, "documents": documents,
            "spouse_id": spouse_id, "features": feat}


def maria_case() -> dict:
    """Dosarul demo (maria-ionescu.md, varianta A, cu pensia din octombrie) în forma simulării: verifică referința pe
    valorile cunoscute din KB. Documentele sunt cele 7 .mvp.json ale demo-ului; IBAN-urile mascate se înlocuiesc cu
    id-urile produselor (core-ul simulat nu are registrul de IBAN-uri), doc 07 e documentul ilizibil (alt client)."""
    root = HERE.parent.parent / "ops-ui" / "_documente-demo"
    names = ["01-dgep-semnal", "02-adresa-notar", "03-certificat-asigurare", "04-certificat-mostenitor-A",
             "05-raspuns-asigurator", "06-certificat-suplimentar", "07-certificat-deces-ilizibil"]
    docs = []
    for n in names:
        d = json.loads((root / f"{n}.mvp.json").read_text(encoding="utf-8"))
        d.pop("_deprecated_fields", None)
        d["fields"].pop("ibans", None)
        if n.startswith("07"):
            d["id"] += "-x"
        docs.append(d)
    heirs = docs[3]["fields"]["heirs"]
    return {"id": "MARIA-A", "customer": {"cif": "RC1001", "name": "Maria Ionescu", "cnp": "2XXXXXXXXXXXX",
                                          "birth_date": "1958-05-12", "spouse": "Ion Ionescu",
                                          "mandates": [{"id": "M-7", "holder": "Andrei Ionescu"}], "cards": ["C-1", "C-2"]},
            "date_of_death": "2026-09-03",
            "products": [{"id": "CC-1", "type": "current_account", "balance": 320_000, "estate_fraction": "1/2"},
                         {"id": "DEP-1", "type": "term_deposit", "principal": 2_000_000, "rate_pct": 5.20, "start": "2026-01-03",
                          "maturity": "2027-01-03", "estate_fraction": "1/2"},
                         {"id": "CRD-1", "type": "personal_loan", "outstanding": 900_000, "rate_pct": 12.0,
                          "last_interest_paid": "2026-08-25", "insurance_policy_id": "UQ-0000000-FICTIV",
                          "loan_contract": "NP-2023-001001"}],
            "movements": [{"date": "2026-08-05", "amount": -6_000, "kind": "fee", "fee_code": "PREMIUM"},
                          {"date": "2026-08-15", "amount": 210_000, "kind": "pension_credit"},
                          {"date": "2026-09-05", "amount": -6_000, "kind": "fee", "fee_code": "PREMIUM"},
                          {"date": "2026-09-15", "amount": 210_000, "kind": "pension_credit"},
                          {"date": "2026-10-15", "amount": 210_000, "kind": "pension_credit"}],
            "documents": docs, "spouse_id": "H1",
            "features": {"testament": False, "n_heirs": len(heirs), "n_minors": 1, "spouse": True, "common_goods": True,
                         "deposit": True, "credit": True, "insured": True, "refused": False, "fee_codes": ["PREMIUM"],
                         "omitted": ["DEP-1"], "order": [d["document_type"] for d in docs[:6]],
                         "noise": [{"kind": "illegible", "document_type": "death_certificate"}]}}


def generate(seed: int = 82, n: int = 200) -> list[dict]:
    rng = random.Random(seed)
    return [generate_case(rng, i + 1) for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=82)
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    out = HERE / f"dosare-seed{a.seed}.jsonl"
    cases = generate(a.seed, a.n)
    out.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    print(f"{len(cases)} dosare → {out.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
