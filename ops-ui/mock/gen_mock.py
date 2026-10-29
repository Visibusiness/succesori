#!/usr/bin/env python3
"""Generează ops-ui/mock-data.json din valorile fixe din kb/scenariu-demo/maria-ionescu.md (v1.1).

Nu calculează nimic nou: cifrele de mai jos sunt copiate din §2 și §3 ale scenariului. Dacă scenariul se schimbă,
se schimbă aici și se rulează din nou:  python3 ops-ui/mock/gen_mock.py
Forma fiecărui dosar urmează GET /cases/{id} din kb/tech/ops-ui-contract.md.
"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "mock-data.json"

CASE_ID = "SC-2026-0001"
D = "2026-09-03"
DECEASED = {"name": "Maria Ionescu", "cnp": "2XXXXXXXXXXXX", "cif": "RC1001", "date_of_death": D}
HEIRS = [
    {"heir_id": "H1", "name": "Ion Ionescu", "relation": "soț supraviețuitor"},
    {"heir_id": "H2", "name": "Andrei Ionescu", "relation": "fiu"},
    {"heir_id": "H3", "name": "Elena Ionescu", "relation": "fiică, minoră (15 ani)", "minor": True,
     "legal_representative": "H1"},
]

# §2.1 balance_at_death
PRODUCTS = [
    {"id": "RO..CUR", "type": "current_account", "label": "Cont curent", "iban": "RO00 RZBR 0000 0000 0000 01",
     "balance": 320000, "accrued_interest": 0},
    {"id": "DEP-1", "type": "term_deposit", "label": "Depozit la termen 12 luni, 5,20%", "iban": "RO00 RZBR 0000 0000 0000 02",
     "principal": 2000000, "accrued_interest": 69238, "maturity": "2027-01-03",
     "note": "dobânda la scadență 1.040,00 lei brut; lichidare anticipată ⇒ dobânda pierdută"},
    {"id": "CRD-1", "type": "personal_loan", "label": "Credit nevoi personale nr. 000/2024", "outstanding": -900000,
     "accrued_interest": -2663, "insurance": "UNIQA, certificat UQ-0000000-FICTIV"},
]

# §2.4 — fracțiile din bun și sumele pe moștenitor, pentru varianta A (legală) și B (testament)
SHARES = {
    "A": {"label": "4A — moștenire legală (C.civ. art. 972, 975)",
          "cert_shares": {"H1": "1/4", "H2": "3/8", "H3": "3/8"},
          "fraction": {"H1": "5/8", "H2": "3/16", "H3": "3/16"},
          "cur": {"H1": 329585, "H2": 98876, "H3": 98876},
          "dep": {"H1": 1315000, "H2": 394500, "H3": 394500}},
    "B": {"label": "4B — testament autentic nr. 000/2024 (C.civ. art. 1055, 1088)",
          "cert_shares": {"H1": "1/2", "H2": "1/4", "H3": "1/4"},
          "fraction": {"H1": "3/4", "H2": "1/8", "H3": "1/8"},
          "cur": {"H1": 395503, "H2": 65917, "H3": 65917},
          "dep": {"H1": 1578000, "H2": 263000, "H3": 263000}},
}


def f(name, value, conf):
    return {"name": name, "value": value, "confidence": conf}


def documents(variant):
    s = SHARES[variant]
    heirs_field = "; ".join(f"{h['name']} – {s['cert_shares'][h['heir_id']]}" for h in HEIRS)
    return [
        {"document_id": "doc-001", "document_type": "semnal_dgep", "received_at": "2026-09-20", "source": "DGEP (fișier săptămânal DGEP-2026-W38)",
         "legibility": "ok", "confidence": 0.99, "fields": [
            f("cnp", "2XXXXXXXXXXXX", 0.99), f("nume", "IONESCU MARIA", 0.99), f("data_decesului", D, 0.99),
            f("tip_modificare", "deces", 0.99), f("potrivire_client", "RC1001", 0.99)]},
        {"document_id": "doc-002", "document_type": "adresa_notar", "received_at": "2026-09-28", "source": "Notar (e-mail, PDF)",
         "legibility": "ok", "confidence": 0.95, "fields": [
            f("nr_dosar_succesoral", "123/2026", 0.97), f("notar", "BIN „Notar Exemplu”", 0.93),
            f("cnp_defunct", "2XXXXXXXXXXXX", 0.98), f("data_decesului", D, 0.97),
            f("temei", "Legea 36/1995 art. 81 alin. (2)", 0.91), f("termen_dezbatere", "2026-10-20", 0.96)]},
        {"document_id": "doc-003", "document_type": "polita_asigurare", "received_at": "2026-09-30", "source": "Familie (agenție)",
         "legibility": "ok", "confidence": 0.93, "fields": [
            f("asigurator", "UNIQA Asigurări de viață S.A.", 0.97), f("nr_certificat", "UQ-0000000-FICTIV", 0.92),
            f("cnp_asigurat", "2XXXXXXXXXXXX", 0.96), f("contract_credit", "000/2024", 0.90),
            f("data_inceput", "2023-05-10", 0.94), f("beneficiar", "Raiffeisen Bank S.A.", 0.95)]},
        {"document_id": "doc-004", "document_type": "certificat_mostenitor", "received_at": "2026-10-22", "source": "Notar",
         "legibility": "ok", "confidence": 0.94, "variant": variant, "fields": [
            f("nr_dosar_succesoral", "123/2026", 0.97), f("cnp_defunct", "2XXXXXXXXXXXX", 0.97),
            f("tip_mostenire", "legală" if variant == "A" else "testamentară (testament autentic nr. 000/2024)", 0.93),
            f("regim_matrimonial", "comunitate legală; cont curent bun comun, 1/2 fiecare soț", 0.88),
            f("mostenitori_si_cote", heirs_field, 0.95), f("suma_cotelor", "1", 0.99),
            f("produse_in_masa", "1/2 din cont curent RO00 RZBR …01; pasiv: credit 000/2024", 0.91),
            f("minor", "Elena Ionescu, 15 ani, cu acordul reprezentantului legal", 0.86)]},
        {"document_id": "doc-005", "document_type": "raspuns_asigurator", "received_at": "2026-10-27", "source": "UNIQA (e-mail)",
         "legibility": "ok", "confidence": 0.96, "fields": [
            f("nr_dosar_dauna", "DV-000/2026", 0.95), f("decizie", "aprobat", 0.98),
            f("indemnizatie", 900000, 0.97), f("contract_credit", "000/2024", 0.94)]},
        {"document_id": "doc-006", "document_type": "certificat_suplimentar", "received_at": "2026-11-10", "source": "Notar",
         "legibility": "ok", "confidence": 0.94, "fields": [
            f("completeaza", "certificatul din 2026-10-22, dosar 123/2026", 0.95),
            f("produs_adaugat", "1/2 din depozitul la termen RO00 RZBR …02", 0.92),
            f("cote", "neschimbate față de certificatul inițial", 0.90)]},
    ]


def ev(at, action, rule, detail, document_id=None, amount=None, audit_id=None):
    e = {"at": at, "action": action, "rule": rule, "detail": detail}
    if document_id: e["document_id"] = document_id
    if amount is not None: e["amount"] = amount
    if audit_id: e["audit_id"] = audit_id
    return e


def events(variant):
    s = SHARES[variant]
    return [
        [ev("2026-09-20T10:02:11Z", "Dosar deschis", "POST /cases — un singur dosar per CIF", "Semnal DGEP potrivit pe CNP ⇒ client RC1001", "doc-001"),
         ev("2026-09-20T10:02:12Z", "Blocare reversibilă (freeze)", "D-DGEP (DECISIONS); C.civ. art. 2030; CGB PF 3.2.5 b, 5.10.4 c",
            "Debit blocat; mandatul lui Andrei Ionescu suspendat; carduri și debitări directe suspendate; comision Premium suspendat. Definitiv doar după certificatul de deces / confirmare operator.",
            "doc-001", audit_id="A-0001"),
         ev("2026-09-20T10:02:13Z", "Stornare comision", "fees_to_reverse — comision perceput după data decesului",
            "Premium 2026-09-05", "doc-001", amount=6000, audit_id="A-0002"),
         ev("2026-09-20T10:02:14Z", "Pensie septembrie păstrată", "Legea 360/2023 art. 100 alin. (1) lit. a",
            "+2.100 lei pe 2026-09-15: pensia lunii decesului se cuvine; raportată notarului ca încasare după deces", "doc-001", amount=210000),
         ev("2026-09-20T10:02:15Z", "Termen programat", "C.civ. art. 1103 — opțiune succesorală 1 an", "Termen opțiune 2027-09-03", "doc-001")],
        [ev("2026-09-28T09:14:00Z", "Produse la data decesului", "GET /customers/RC1001/products?as_of=2026-09-03 + balance_at_death",
            "Cont 3.200,00 lei; depozit 20.000,00 + 692,38 lei dobândă; credit −9.000,00 − 26,63 lei", "doc-002"),
         ev("2026-09-28T09:14:30Z", "Răspuns către notar generat", "Legea 36/1995 art. 81 alin. (2)",
            "Tabel solduri la D + pensia din septembrie ca încasare după deces + credit cu asigurare UNIQA; trimis la semnare umană", "doc-002")],
        [ev("2026-09-30T11:40:00Z", "Poliță validată", "Potrivire CNP + nr. contract credit", "CNP și credit 000/2024 coincid; poliță > 24 luni ⇒ fără excluderi", "doc-003"),
         ev("2026-09-30T11:40:20Z", "Dosar de daună deschis", "kb/bank-procedures/asigurare-viata-credit.md — avizare în 30 zile",
            "Checklist F1 trimis către UNIQA; termen avizare 2026-10-20", "doc-003"),
         ev("2026-10-15T06:00:00Z", "Pensie octombrie marcată pentru retur", "Legea 360/2023 art. 156 alin. (8); post_death_credits",
            "+2.100 lei pe 2026-10-15 necuvenită ⇒ flag pension_return_CNPP; reținută din calcul", amount=210000)],
        [ev("2026-10-22T14:05:00Z", "Cote extrase și verificate", "Cotele se citesc din certificat, nu se deduc din lege; verificare sumă = 1",
            "Variantă " + s["label"] + ": " + ", ".join(f"{h['name']} {s['cert_shares'][h['heir_id']]}" for h in HEIRS), "doc-004"),
         ev("2026-10-22T14:05:10Z", "Lipsă de acoperire detectată", "coverage_gaps(products, heir_certificate)",
            "DEP-1 (depozit la termen) nu apare în certificat", "doc-004"),
         ev("2026-10-22T14:05:20Z", "Cerere de supliment trimisă notarului", "Legea 36/1995 — certificat suplimentar", "Pentru DEP-1", "doc-004"),
         ev("2026-10-22T14:05:30Z", "Minor detectat", "Reprezentare legală a minorului (C.civ.)",
            "Cerere: acordul scris al reprezentantului legal + cont pe numele Elenei; partea ei rămâne blocată", "doc-004")],
        [ev("2026-10-27T10:20:00Z", "Credit stins de asigurător", "Răspuns UNIQA: indemnizație = principal la D",
            "CRD-1 principal 9.000,00 lei acoperit", "doc-005", amount=900000, audit_id="A-0003"),
         ev("2026-10-27T10:20:05Z", "Datorie reziduală a masei", "net_of_debts — C.civ. art. 1114 (limita activului)",
            "Dobânda curentă neacoperită de asigurare", "doc-005", amount=-2663)],
        [ev("2026-11-10T15:30:00Z", "Acoperire completă", "coverage_gaps = []", "Certificatul suplimentar adaugă DEP-1", "doc-006"),
         ev("2026-11-10T15:30:05Z", "Masa netă calculată", "net_of_debts", "Cont: 3.200,00 + 2.100,00 (pensie sept.) − 26,63 = 5.273,37 lei", "doc-006", amount=527337),
         ev("2026-11-10T15:30:10Z", "Împărțire pe moștenitori", "split_by_shares — fracție din bun × cotă; rotunjire determinist (cea mai mare rămășiță)",
            ", ".join(f"{h['name']} {s['fraction'][h['heir_id']]}" for h in HEIRS), "doc-006"),
         ev("2026-11-10T15:30:15Z", "Recomandare depozit: așteptarea scadenței", "C.civ. art. 2187 — lichidarea anticipată cere acordul tuturor",
            "Plata depozitului programată la 2027-01-03 (dobânda integrală 1.040,00 lei brut)", "doc-006"),
         ev("2026-11-10T15:30:20Z", "Instrucțiune de plată creată", "POST /payments — doar pending_approval; aprobarea e umană (ops_approver)",
            "PAY-1 pentru contul curent, fără partea Elenei (blocată)", "doc-006")],
    ]


def plan(variant):
    s = SHARES[variant]
    lines = []
    n = 1
    for prod, key, when in (("RO..CUR", "cur", "acum"), ("DEP-1", "dep", "2027-01-03")):
        for h in HEIRS:
            hid = h["heir_id"]
            line = {"line_id": f"L{n}", "heir_id": hid, "name": h["name"], "share": s["fraction"][hid],
                    "product_id": prod, "amount": s[key][hid], "pay_on": when, "iban": None, "blocked": False}
            if h.get("minor"):
                line.update(blocked=True, minor=True, legal_representative="H1", requires_court_authorization=True,
                            blocked_reason="minoră: lipsesc documentele de reprezentare legală și contul pe numele ei")
            elif key == "dep":
                line.update(blocked=True, blocked_reason="depozit nescadent: plata la scadență, 2027-01-03")
            lines.append(line)
            n += 1
    return {"plan_id": "PP-1", "status": "draft", "variant": variant, "variant_label": s["label"],
            "basis_documents": ["doc-004", "doc-006"], "lines": lines,
            "withheld": [{"reason": "pension_return_CNPP", "label": "Pensie octombrie — retur CNPP", "amount": 210000}],
            "warnings": ["minor_requires_authorization", "deposit_paid_at_maturity"]}


STEPS = [
    # (stare după document, data, nr. documente, termene)
    ("FROZEN", "2026-09-20"),
    ("NOTARY_ANSWERED", "2026-09-28"),
    ("INSURANCE_CLAIM_OPEN", "2026-09-30"),
    ("SUPPLEMENT_REQUESTED", "2026-10-22"),
    ("INSURANCE_SETTLED", "2026-10-27"),
    ("PAYMENT_PENDING_APPROVAL", "2026-11-10"),
]


def deadlines(step):
    dl = [{"name": "Termen opțiune succesorală", "date": "2027-09-03", "rule": "C.civ. art. 1103 (1 an de la deces)", "status": "deschis"}]
    if step >= 2:
        dl.append({"name": "Dezbatere succesiune la notar (răspunsul trebuie să ajungă înainte)", "date": "2026-10-20",
                   "rule": "Adresa notarului nr. 123/2026", "status": "îndeplinit" if step >= 3 else "deschis"})
    if step >= 3:
        dl.append({"name": "Avizare daună UNIQA", "date": "2026-10-20", "rule": "30 zile de la aflarea decesului",
                   "status": "îndeplinit" if step >= 3 else "deschis"})
    if step >= 4:
        dl.append({"name": "Certificat suplimentar (DEP-1)", "date": None, "rule": "coverage_gaps",
                   "status": "îndeplinit" if step >= 6 else "în așteptare"})
        dl.append({"name": "Documente de reprezentare pentru Elena", "date": None, "rule": "minor — reprezentant legal",
                   "status": "în așteptare"})
    if step >= 6:
        dl.append({"name": "Scadența depozitului DEP-1 (plată)", "date": "2027-01-03", "rule": "C.civ. art. 2187", "status": "programat"})
    return dl


def open_tasks(step):
    t = []
    if step == 2:
        t.append("Semnare umană a răspunsului către notar")
    if step >= 4:
        t.append("Așteaptă acordul reprezentantului legal + cont pe numele Elenei")
    if 4 <= step < 6:
        t.append("Așteaptă certificatul suplimentar pentru DEP-1")
    if step >= 6:
        t.append("Aprobare plată PAY-1 (ops_approver)")
    return t


def build_variant(variant):
    docs, evs = documents(variant), events(variant)
    cases, history = [], []
    for i, (state, at) in enumerate(STEPS, start=1):
        history.append({"state": state, "at": at, "by_document": f"doc-00{i}"})
        c = {"case_id": f"{CASE_ID}~{i}", "snapshot_of": CASE_ID, "demo_step": i,
             "demo_label": f"Pasul {i}/7 — după {docs[i - 1]['document_type']}",
             "deceased": DECEASED, "state": state, "opened_at": "2026-09-20", "updated_at": at,
             "state_history": copy.deepcopy(history), "products_as_of": D,
             "products": copy.deepcopy(PRODUCTS), "heirs": copy.deepcopy(HEIRS) if i >= 4 else [],
             "documents": copy.deepcopy(docs[:i]),
             "events": [e for group in evs[:i] for e in group],
             "deadlines": deadlines(i), "open_tasks": open_tasks(i), "escalations": [],
             "payment_plan": None, "payments": []}
        if i >= 5:
            c["products"][2]["insurance_settled"] = 900000
        if i >= 6:
            c["payment_plan"] = plan(variant)
            c["payment_plan"]["status"] = "submitted"
            c["payments"] = [{"payment_id": "PAY-1", "plan_id": "PP-1", "status": "pending_approval",
                              "line_ids": [l["line_id"] for l in c["payment_plan"]["lines"] if not l["blocked"]],
                              "total": sum(l["amount"] for l in c["payment_plan"]["lines"] if not l["blocked"])}]
        cases.append(c)
    return cases


# Doc 7: certificat de deces ilizibil, alt client — doar în coada de escaladări, fără dosar
UNMATCHED = [{
    "escalation_id": "ESC-0007", "document_id": "doc-007", "document_type": "certificat_deces",
    "received_at": "2026-11-12", "source": "Agenție (scanare)", "legibility": "illegible", "confidence": 0.31,
    "fields": [f("nume", "POP█████", 0.42), f("prenume", "GHEOR███", 0.38), f("cnp", "1█████████ ██", 0.12),
               f("data_decesului", "██.██.2026", 0.10), f("serie_numar", "XX 0000000", 0.55)],
    "reason": "Document ilizibil: CNP și data decesului necitibile (scor 0,31 sub prag 0,80)",
    "agent_action": "Escaladare; niciun freeze, niciun dosar deschis, dosarul Mariei neatins",
    "rule": "Nu se blochează pe un document nesigur (POST /freeze → 422 sub prag)", "status": "deschis"}]


data = {
    "_sursa": "generat de ops-ui/mock/gen_mock.py din kb/scenariu-demo/maria-ionescu.md v1.1 + documente-demo.md",
    "confidence_threshold": 0.80,
    "variants": {v: {"label": SHARES[v]["label"], "cases": build_variant(v)} for v in ("A", "B")},
    "unmatched_documents": UNMATCHED,
}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"scris {OUT}")
