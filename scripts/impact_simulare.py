"""Simularea la scară (sarcina 082): 200 de dosare generate determinist, trecute prin pipeline în proces, comparate la ban
cu o implementare de referință independentă (registries/simulare/referinta.py, care nu importă agent/).

Documentele sunt deja extrase (fără LLM): e testul logicii de dosar, nu al extractorului. Fiecare dosar are core-ul lui
(un `Bank` populat din dosarul generat) și un `Pipeline` nou. Ieșire: registries/simulare/rezultat-seed<N>.json și
registries/simulare/RAPORT-seed<N>.md (nepotrivirile, cu exemplul minim).

    .venv/bin/python scripts/impact_simulare.py [--seed 82] [--n 200]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.core_mock import Bank  # noqa: E402
from agent.pipeline import Pipeline  # noqa: E402
from agent.rules import Movement, Product  # noqa: E402
from registries.simulare import generator, referinta  # noqa: E402

OUT_DIR = ROOT / "registries" / "simulare"

TRAPS = [  # (cheie, eticheta, ce dosare o conțin)
    ("fee_after_death", "comision după deces stornat", lambda c, e: e["fees_reversed"] > 0),
    ("pension_return", "pensie de returnat la CNPP", lambda c, e: e["pension_return"] > 0),
    ("omitted_product", "produs omis ⇒ supliment", lambda c, e: e["supplement_requested"]),
    ("minor_blocked", "minor: parte blocată", lambda c, e: c["features"]["n_minors"] > 0),
    ("mandate_withdrawal", "retragere a împuternicitului după deces", lambda c, e: e["mandate_withdrawals"] > 0),
    ("insurance_refused", "asigurare refuzată", lambda c, e: c["features"]["refused"]),
    ("bad_document", "document ilizibil / suspect", lambda c, e: bool(c["features"]["noise"])),
]


class SimBank(Bank):
    """Core-ul unui dosar generat, cu aceleași metode ca mock-ul demo (nicio schimbare în agent/)."""

    def __init__(self, case: dict) -> None:
        self.case = case
        super().__init__()

    def reset(self, variants=frozenset()) -> None:  # noqa: D401 - suprascrie seed-ul demo
        c = self.case
        cu = c["customer"]
        self.variants = frozenset()
        self.customers = {cu["cif"]: {**cu, "frozen": None}}
        prods = []
        for p in c["products"]:
            kw = {k: p[k] for k in ("balance", "principal", "rate_pct", "outstanding", "insurance_policy_id") if p.get(k) is not None}
            for k in ("start", "maturity", "last_interest_paid"):
                if p.get(k):
                    kw[k] = date.fromisoformat(p[k])
            if p.get("estate_fraction"):
                kw["estate_fraction"] = Fraction(p["estate_fraction"])
            prods.append(Product(p["id"], p["type"], **kw))
        self._products = {cu["cif"]: prods}
        self._ibans = {}
        self._loan_contracts = {p["loan_contract"]: p["id"] for p in c["products"] if p.get("loan_contract")}
        self._installments = {p["id"]: None for p in c["products"] if p["type"] == "personal_loan"}
        self.contacts = {}
        self._movements = {cu["cif"]: [Movement(date.fromisoformat(m["date"]), m["amount"], m["kind"], m.get("fee_code"),
                                                bool(m.get("by_mandate_holder"))) for m in c["movements"]]}
        self.audit, self.reversed_fees, self.payments = [], set(), []


def run_case(case: dict) -> dict:
    bank = SimBank(case)
    pipe = Pipeline(bank)
    t0 = time.perf_counter()
    errors = []
    for doc in case["documents"]:
        try:
            pipe.receive(json.loads(json.dumps(doc)))
        except Exception as e:  # noqa: BLE001 - o excepție în pipeline e un bug de raportat, nu oprește simularea
            errors.append(f"{doc['document_type']}: {type(e).__name__}: {e}".strip())
    seconds = time.perf_counter() - t0
    client = next((c for c in pipe.cases.values() if c.cif == case["customer"]["cif"]), None)
    paid_before = list(bank.payments)
    plan = client.payment_plan if client else None
    got = {"plan": plan is not None, "plan_status": plan["status"] if plan else None, "paid_before_approval": len(paid_before),
           "seconds": seconds, "state": client.state() if client else None, "errors": errors}
    if client:
        fl = client.flags
        got["fees_reversed"] = sum(f["amount"] for f in fl if f["code"] == "fee_to_reverse")
        got["pension_return"] = sum(f["amount"] for f in fl if f["code"] == "pension_return_CNPP")
        got["mandate_withdrawals"] = sum(f["amount"] for f in fl if f["code"] == "post_death_mandate_withdrawal")
        got["supplement_requested"] = "supplement_requested" in client.milestones
        got["bad_docs_acted_on"] = sum(1 for d in client.documents if d.id.endswith("-x") and d.type != "quarantined")
    got["escalations"] = sorted(e.reason for c in pipe.cases.values() for e in c.escalations
                                if not (e.data or {}).get("severity") == "info")
    if plan:
        got["net_account"] = plan["net_account"]["net"]
        got["withheld"] = sum(w["amount"] for w in plan["withheld"])
        got["lines"] = [{"heir": l["heir_id"], "product_id": l["product_id"], "amount": l["amount"],
                         "blocked": l["blocked_reason"] is not None, "blocked_reason": l["blocked_reason"]} for l in plan["lines"]]
        if plan["status"] == "pending_approval":
            pipe.approve_payment(client.id, "sim-operator")
            got["paid_after_approval"] = sum(p["amount"] for p in bank.payments)
            got["paid_lines"] = len(bank.payments)
    return got


def compare(case: dict, exp: dict, got: dict) -> dict:
    """Ce s-a potrivit și, pentru ce nu, o etichetă de cauză (pentru a grupa nepotrivirile în bug-uri)."""
    issues: list[dict] = []

    def bad(tag: str, detail: str) -> None:
        issues.append({"tag": tag, "detail": detail})

    feat = case["features"]
    for err in got["errors"]:
        bad("exceptie", err)
    if got["paid_before_approval"]:
        bad("plata_fara_aprobare", f"{got['paid_before_approval']} plăți executate înainte de aprobare")
    if not got["plan"] and not got["errors"]:
        if feat["refused"]:
            bad("refuz_asigurare_fara_plan", f"niciun plan de plată după refuzul asigurătorului (stare {got['state']}, "
                                            f"ordinea {feat['order']})")
        else:
            bad("fara_plan", f"niciun plan de plată (stare {got['state']})")
    if got.get("fees_reversed", 0) != exp["fees_reversed"]:
        tag = "comision_alt_cod" if any(c != "PREMIUM" for c in feat["fee_codes"]) else "comision"
        bad(tag, f"stornat {got.get('fees_reversed', 0)} ≠ așteptat {exp['fees_reversed']} (coduri {feat['fee_codes']})")
    if got.get("pension_return", 0) != exp["pension_return"]:
        bad("pensie", f"retur CNPP {got.get('pension_return', 0)} ≠ {exp['pension_return']}")
    if got.get("mandate_withdrawals", 0) != exp["mandate_withdrawals"]:
        bad("retragere", f"retrageri semnalate {got.get('mandate_withdrawals', 0)} ≠ {exp['mandate_withdrawals']}")
    if got.get("supplement_requested") != exp["supplement_requested"]:
        bad("supliment", f"supliment cerut {got.get('supplement_requested')} ≠ {exp['supplement_requested']}")
    if got.get("bad_docs_acted_on"):
        bad("document_rau_procesat", f"{got['bad_docs_acted_on']} documente ilizibile/suspecte procesate ca bune")
    if got["escalations"] != exp["escalations"]:
        extra = list((Counter(got["escalations"]) - Counter(exp["escalations"])).elements())
        miss = list((Counter(exp["escalations"]) - Counter(got["escalations"])).elements())
        bad("escaladari", f"în plus {extra}, lipsă {miss}")
    line_ok = line_total = 0
    if got["plan"]:
        if got["withheld"] != exp["pension_return"]:
            bad("pensie", f"reținut în plan {got['withheld']} ≠ {exp['pension_return']}")
        if got["net_account"] != exp["net_account"]:
            if exp["remaining_debt"] > case["products"][0]["balance"] + exp["pension_kept"]:
                bad("datorie_peste_cont", f"net {got['net_account']} ≠ {exp['net_account']} (datoria {exp['remaining_debt']} "
                                          f"> contul {case['products'][0]['balance'] + exp['pension_kept']})")
            else:
                bad("net", f"net {got['net_account']} ≠ {exp['net_account']}")
        g = {(l["heir"], l["product_id"]): l for l in got["lines"]}
        for e in exp["lines"]:
            line_total += 1
            l = g.pop((e["heir"], e["product_id"]), None)
            if l is None:
                bad("linie_lipsa", f"lipsește linia {e['heir']} {e['product_id']}")
                continue
            ok = True
            if l["amount"] != e["amount"]:
                ok = False
                spouse_issue = feat.get("spouse_not_first") and feat["common_goods"]
                if spouse_issue:
                    tag = "sot_identificat_dupa_pozitie"
                elif exp["unpaid_debt"] or exp["remaining_debt"] > case["products"][0]["balance"] + exp["pension_kept"]:
                    tag = "datorie_peste_cont"
                elif abs(l["amount"] - e["amount"]) <= len(exp["lines"]):
                    tag = "rotunjire"
                else:
                    tag = "suma"
                bad(tag, f"{e['heir']} {e['product_id']}: {l['amount']} ≠ {e['amount']} (Δ {l['amount'] - e['amount']})")
            if l["blocked"] != e["blocked"]:
                ok = False
                tag = "depozit_scadent_blocat" if e["product_id"] == "DEP-1" and not e["blocked"] else "blocare"
                bad(tag, f"{e['heir']} {e['product_id']}: blocat {l['blocked']} ≠ {e['blocked']} ({l['blocked_reason']})")
            line_ok += ok
        for k in g:
            bad("linie_in_plus", f"linie neașteptată {k}")
        if got.get("paid_after_approval") is not None:
            payable_got = sum(l["amount"] for l in got["lines"] if not l["blocked"])
            if got["paid_after_approval"] != payable_got:
                bad("plata_diferita_de_plan", f"plătit {got['paid_after_approval']} ≠ plan {payable_got}")
            if any(l["blocked"] for l in got["lines"]) and got["paid_lines"] != sum(not l["blocked"] for l in got["lines"]):
                bad("linie_blocata_platita", "o linie blocată a fost plătită")
            if any(l["amount"] < 0 for l in got["lines"]):
                bad("suma_negativa", f"linii cu sumă negativă: {[l['amount'] for l in got['lines'] if l['amount'] < 0]}")
    return {"issues": issues, "lines_ok": line_ok, "lines_total": line_total}


def trap_caught(key: str, cmp: dict) -> bool:
    tags = {i["tag"] for i in cmp["issues"]}
    need = {"fee_after_death": {"comision", "comision_alt_cod"}, "pension_return": {"pensie"},
            "omitted_product": {"supliment", "linie_lipsa"}, "minor_blocked": {"blocare", "escaladari"},
            "mandate_withdrawal": {"retragere", "escaladari"}, "insurance_refused": {"escaladari"},
            "bad_document": {"document_rau_procesat", "escaladari"}}[key]
    return not (tags & need)


def complexity(case: dict) -> int:
    return case["features"]["n_heirs"] * 3 + len(case["products"]) * 2 + len(case["documents"]) + len(case["movements"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=82)
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    t_gen = time.perf_counter()
    cases = generator.generate(a.seed, a.n)
    (OUT_DIR / f"dosare-seed{a.seed}.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases),
                                                        encoding="utf-8")
    t_gen = time.perf_counter() - t_gen
    t0 = time.perf_counter()
    rows = []
    for c in cases:
        exp = referinta.expected(c)
        got = run_case(c)
        rows.append({"case": c, "exp": exp, "got": got, "cmp": compare(c, exp, got)})
    total = time.perf_counter() - t0

    n = len(rows)
    correct = [r for r in rows if not r["cmp"]["issues"]]
    planned = [r for r in rows if r["got"]["plan"]]
    plan_ok = [r for r in planned if not any(i["tag"] not in ("escaladari",) for i in r["cmp"]["issues"])]
    tags = Counter(i["tag"] for r in rows for i in r["cmp"]["issues"])
    cases_by_tag: dict[str, list] = {}
    for r in rows:
        for t in {i["tag"] for i in r["cmp"]["issues"]}:
            cases_by_tag.setdefault(t, []).append(r)
    traps = []
    for key, label, has in TRAPS:
        with_trap = [r for r in rows if has(r["case"], r["exp"])]
        caught = [r for r in with_trap if trap_caught(key, r["cmp"])]
        traps.append({"cheie": key, "eticheta": label, "dosare": len(with_trap), "prinse": len(caught)})
    esc_exp = sum(len(r["exp"]["escalations"]) for r in rows)
    esc_ok = sum(len(r["exp"]["escalations"]) for r in rows if r["got"]["escalations"] == r["exp"]["escalations"])
    lines_ok = sum(r["cmp"]["lines_ok"] for r in rows)
    lines_total = sum(r["cmp"]["lines_total"] for r in rows)
    examples = {}
    for t, rs in cases_by_tag.items():
        r = min(rs, key=lambda r: complexity(r["case"]))
        examples[t] = {"dosar": r["case"]["id"], "dosare_afectate": len(rs),
                       "detalii": [i["detail"] for i in r["cmp"]["issues"] if i["tag"] == t][:4],
                       "features": r["case"]["features"], "produse": r["case"]["products"],
                       "mostenitori": next(d for d in r["case"]["documents"] if d["document_type"] == "heir_certificate" and not d["id"].endswith("-x"))["fields"]["heirs"],
                       "asteptat_linii": r["exp"]["lines"], "obtinut_linii": r["got"].get("lines"),
                       "asteptat_net": r["exp"]["net_account"], "obtinut_net": r["got"].get("net_account")}
    per_case = [r["got"]["seconds"] for r in rows]
    res = {
        "generat": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": a.seed, "dosare": n,
        "documente": sum(len(r["case"]["documents"]) for r in rows),
        "generator": "registries/simulare/generator.py", "referinta": "registries/simulare/referinta.py",
        "secunde_total": round(total, 3), "secunde_generare": round(t_gen, 3),
        "ms_pe_dosar": {"medie": round(1000 * total / n, 2), "max": round(1000 * max(per_case), 2)},
        "dosare_corecte_complet": len(correct), "dosare_cu_plan": len(planned), "dosare_plan_corect": len(plan_ok),
        "linii_plata_exacte": lines_ok, "linii_plata_total": lines_total,
        "plati_fara_aprobare": sum(r["got"]["paid_before_approval"] for r in rows),
        "escaladari_asteptate": esc_exp, "escaladari_in_dosare_corecte": esc_ok,
        "dosare_cu_escaladari_exacte": sum(r["got"]["escalations"] == r["exp"]["escalations"] for r in rows),
        "capcane": traps, "nepotriviri_pe_cauza": dict(tags.most_common()),
        "dosare_pe_cauza": {t: len(v) for t, v in cases_by_tag.items()}, "exemple_din_set": examples,
        "exemple_minime": minimal_examples(),
        "variante": {k: sum(1 for c in cases if v(c)) for k, v in {
            "testament": lambda c: c["features"]["testament"], "bunuri_comune": lambda c: c["features"]["common_goods"],
            "depozit": lambda c: c["features"]["deposit"], "credit": lambda c: c["features"]["credit"],
            "credit_asigurat": lambda c: c["features"]["insured"], "soț_nu_e_primul": lambda c: c["features"].get("spouse_not_first", False),
            "dgep_nu_e_primul": lambda c: c["features"]["order"][0] != "dgep_signal",
            "comision_alt_cod": lambda c: any(x != "PREMIUM" for x in c["features"]["fee_codes"]),
            "cu_minori": lambda c: c["features"]["n_minors"] > 0}.items()},
        "pe_dosar": [{"id": r["case"]["id"], "ok": not r["cmp"]["issues"], "cauze": sorted({i["tag"] for i in r["cmp"]["issues"]}),
                      "ms": round(1000 * r["got"]["seconds"], 2)} for r in rows],
    }
    out = OUT_DIR / f"rezultat-seed{a.seed}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_report(res, OUT_DIR / f"RAPORT-seed{a.seed}.md")
    print(f"{n} dosare, {res['documente']} documente în {total:.2f} s ({res['ms_pe_dosar']['medie']} ms/dosar)")
    print(f"corecte complet: {len(correct)}/{n} · cu plan: {len(planned)} · plan corect: {len(plan_ok)} · "
          f"linii exacte: {lines_ok}/{lines_total} · plăți fără aprobare: {res['plati_fara_aprobare']}")
    for t in traps:
        print(f"  capcană {t['eticheta']}: {t['prinse']}/{t['dosare']}")
    for t, k in tags.most_common():
        print(f"  nepotrivire {t}: {k} ({len(cases_by_tag[t])} dosare)")
    print(f"scris {out.relative_to(ROOT)}")
    return 0


def mini_case(heirs: list[dict], products: list[dict], movements: list[dict] | None = None, refused: bool = False,
              insured: bool = False, order: list[str] | None = None, dod: str = "2026-03-10") -> dict:
    """Un dosar minim, scris de mână, în forma generatorului (pentru exemplele minime din raport)."""
    cnp = generator.cnp_check("260010112345"[:12])
    order = order or ["dgep_signal", "notary_request", "heir_certificate"]
    spouse_id = next((h["id"] for h in heirs if h.get("relationship") == "soț supraviețuitor"), None)
    docs, day = [], date.fromisoformat(dod)
    for n, kind in enumerate(order):
        day = day.fromordinal(day.toordinal() + 10)
        f = {"cnp": cnp, "document_number": f"MIN-{n}"}
        if kind in ("dgep_signal", "notary_request"):
            f["date_of_death"] = dod
        if kind == "heir_certificate":
            f.update(heirs=heirs, products=[p["id"] for p in products if p["type"] != "personal_loan"], testament=False)
        if kind == "insurance_certificate":
            f.update(policy_id="UQ-MIN", insurer=generator.INSURER, loan_contract="NP-MIN")
        if kind == "insurer_response":
            f.update(policy_id="UQ-MIN", decision="refused" if refused else "approved", amount=0, reason="excludere")
        docs.append({"id": f"MIN-d{n}", "raw_name": f"MIN-{kind}.json", "document_type": kind, "received_on": day.isoformat(),
                     "confidence": 0.95, "fields": f})
    return {"id": "MIN", "customer": {"cif": "MIN1", "name": "Ana Minim", "cnp": cnp, "birth_date": "1950-01-01",
                                      "spouse": None, "mandates": [], "cards": []},
            "date_of_death": dod, "products": products, "movements": movements or [], "documents": docs, "spouse_id": spouse_id,
            "features": {"testament": False, "n_heirs": len(heirs), "n_minors": sum(bool(h.get("minor")) for h in heirs),
                         "spouse": bool(spouse_id), "common_goods": any(p.get("estate_fraction") == "1/2" for p in products),
                         "deposit": any(p["type"] == "term_deposit" for p in products), "credit": any(p["type"] == "personal_loan" for p in products),
                         "insured": insured, "refused": refused, "fee_codes": sorted({m.get("fee_code") for m in movements or [] if m.get("fee_code")}),
                         "omitted": [], "order": order, "noise": [], "spouse_not_first": spouse_id not in (None, "H1")}}


CC = {"id": "CC-1", "type": "current_account", "balance": 100_000}
SON, SPOUSE = {"id": "H1", "name": "Dan Minim", "share": "3/4", "relationship": "fiu"}, \
    {"id": "H2", "name": "Ion Minim", "share": "1/4", "relationship": "soț supraviețuitor"}
MINIMAL = {
    "sot_identificat_dupa_pozitie": (
        "Soțul e identificat după poziție (H1), nu după calitate",
        "`_try_payment_plan` (agent/pipeline.py) ia ca soț supraviețuitor primul moștenitor major din certificat. Când "
        "certificatul îl trece întâi pe un copil, jumătatea de proprietar a soțului din bunurile comune ajunge la copil.",
        lambda: mini_case([SON, SPOUSE], [{**CC, "estate_fraction": "1/2"}])),
    "exceptie": (
        "Excepție (AssertionError) când primul moștenitor e minor și bunurile sunt comune",
        "Același cod: dacă H1 e minor, nu e ales nimeni ca soț, fracțiile dau 1/2 în loc de 1 și `split_by_shares` "
        "oprește procesarea certificatului cu `assert` (prin API: HTTP 500, dosarul rămâne fără plan).",
        lambda: mini_case([{**SON, "minor": True, "legal_representative": "H2"}, SPOUSE], [{**CC, "estate_fraction": "1/2"}])),
    "datorie_peste_cont": (
        "Datoria mai mare decât contul curent dă un net și linii de plată negative",
        "`net_of_debts` scade toată datoria din contul curent, fără plafon la 0 și fără să treacă la depozit (C.civ. art. "
        "1114: moștenitorii răspund în limita activului). Apare la credit fără asigurare sau cu asigurare refuzată.",
        lambda: mini_case([{**SON, "share": "1/2"}, {"id": "H2", "name": "Ana Fiică", "share": "1/2", "relationship": "fiică"}],
                          [CC, {"id": "CRD-1", "type": "personal_loan", "outstanding": 500_000, "rate_pct": 10.0,
                                "last_interest_paid": "2026-03-10", "loan_contract": "NP-MIN"}])),
    "depozit_scadent_blocat": (
        "Depozitul ajuns la scadență înainte de plan rămâne blocat „până la scadență”",
        "`_try_payment_plan` pune `blocked_reason` pe orice depozit, fără să compare scadența cu data planului.",
        lambda: mini_case([{**SON, "share": "1"}], [CC, {"id": "DEP-1", "type": "term_deposit", "principal": 1_000_000,
                                                         "rate_pct": 5.0, "start": "2025-10-01", "maturity": "2026-04-01"}])),
    "comision_alt_cod": (
        "Se stornează doar comisionul cu codul PREMIUM",
        "`rules.fees_to_reverse(..., fee_codes=(\"PREMIUM\",))`: un comision de administrare cu alt cod (ex. pachet standard) "
        "debitat după deces rămâne încasat (exact tiparul cazului Bragadiru).",
        lambda: mini_case([{**SON, "share": "1"}], [CC], [{"date": "2026-04-05", "amount": -900, "kind": "fee", "fee_code": "ADMIN_CONT"}])),
    "refuz_asigurare_fara_plan": (
        "Refuzul asigurătorului, sosit după un certificat complet, lasă dosarul fără plan",
        "`_on_insurer_response` nu mai cheamă `_try_payment_plan` pe ramura de refuz; planul fusese amânat „așteptăm "
        "răspunsul asigurătorului”, deci nu se mai face niciodată (stare INSURANCE_CLAIM_OPEN). În ordinea inversă "
        "(refuz înainte de certificat) planul se face: rezultatul depinde de ordinea documentelor.",
        lambda: mini_case([{**SON, "share": "1"}], [{**CC, "balance": 900_000}, {"id": "CRD-1", "type": "personal_loan",
                          "outstanding": 300_000, "rate_pct": 10.0, "last_interest_paid": "2026-03-10", "insurance_policy_id": "UQ-MIN",
                          "loan_contract": "NP-MIN"}], insured=True, refused=True,
                          order=["dgep_signal", "notary_request", "insurance_certificate", "heir_certificate", "insurer_response"])),
}
MINIMAL["suma_negativa"] = MINIMAL["datorie_peste_cont"]


def minimal_examples() -> dict:
    out = {}
    for tag, (title, why, build) in MINIMAL.items():
        c = build()
        exp, got = referinta.expected(c), run_case(c)
        cmp = compare(c, exp, got)
        out[tag] = {"titlu": title, "cauza": why, "reprodus": tag in {i["tag"] for i in cmp["issues"]},
                    "probleme": [i["detail"] for i in cmp["issues"]], "erori": got["errors"],
                    "asteptat": {"net": exp["net_account"], "linii": [(l["heir"], l["product_id"], l["amount"], l["blocked"]) for l in exp["lines"]]},
                    "obtinut": {"net": got.get("net_account"), "stare": got["state"],
                                "linii": [(l["heir"], l["product_id"], l["amount"], l["blocked"]) for l in got.get("lines", [])]},
                    "intrare": {"produse": c["products"], "mostenitori": c["documents"][-1]["fields"].get("heirs")
                                or next(d["fields"]["heirs"] for d in c["documents"] if d["document_type"] == "heir_certificate"),
                                "miscari": c["movements"], "ordine": c["features"]["order"]}}
    return out


def write_report(res: dict, path: Path) -> None:
    L = [f"# Simularea la scară: seed {res['seed']}, {res['dosare']} dosare", "",
         f"Generat de `scripts/impact_simulare.py` la {res['generat']}. Referința: `{res['referinta']}` (nu importă agent/).", "",
         f"- {res['documente']} documente în {res['secunde_total']} s ({res['ms_pe_dosar']['medie']} ms/dosar)",
         f"- dosare complet corecte: **{res['dosare_corecte_complet']}/{res['dosare']}**; cu plan de plată: {res['dosare_cu_plan']}; "
         f"plan corect: {res['dosare_plan_corect']}",
         f"- linii de plată exacte la ban: {res['linii_plata_exacte']}/{res['linii_plata_total']}",
         f"- plăți executate fără aprobare: **{res['plati_fara_aprobare']}**",
         f"- dosare cu escaladările exacte: {res['dosare_cu_escaladari_exacte']}/{res['dosare']}", "",
         "## Capcane", "", "| Capcană | Dosare | Prinse |", "|---|---|---|"]
    L += [f"| {t['eticheta']} | {t['dosare']} | {t['prinse']} |" for t in res["capcane"]]
    L += ["", "## Bug-uri găsite: cauza, câte dosare, exemplul minim", "",
          "Codul din agent/ nu e modificat (regula proiectului); fiecare exemplu minim e rulat prin `Pipeline` în proces și "
          "comparat cu referința. Cel mai mic dosar din set cu aceeași cauză e în `rezultat-seed*.json` → `exemple_din_set`.", ""]
    if not res["dosare_pe_cauza"]:
        L.append("Niciuna.")
    for tag, k in sorted(res["dosare_pe_cauza"].items(), key=lambda x: -x[1]):
        ex = res["exemple_minime"].get(tag)
        L += [f"### `{tag}`: {k} dosare din {res['dosare']}", ""]
        if not ex:
            L += [f"Exemplu din set: `{res['exemple_din_set'][tag]['dosar']}`", ""]
            continue
        L += [f"**{ex['titlu']}.** {ex['cauza']}", "",
              f"Exemplu minim ({'reprodus' if ex['reprodus'] else 'NU s-a reprodus'}): produse `{json.dumps(ex['intrare']['produse'], ensure_ascii=False)}`, "
              f"moștenitori `{json.dumps(ex['intrare']['mostenitori'], ensure_ascii=False)}`"
              + (f", mișcări `{json.dumps(ex['intrare']['miscari'], ensure_ascii=False)}`" if ex["intrare"]["miscari"] else "")
              + f", ordinea {ex['intrare']['ordine']}.", "",
              f"- așteptat: net {ex['asteptat']['net']}, linii {ex['asteptat']['linii']}",
              f"- obținut: net {ex['obtinut']['net']}, stare {ex['obtinut']['stare']}, linii {ex['obtinut']['linii']}"
              + (f", erori {ex['erori']}" if ex["erori"] else ""),
              f"- diferențe găsite de comparație: {'; '.join(ex['probleme'])}", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
