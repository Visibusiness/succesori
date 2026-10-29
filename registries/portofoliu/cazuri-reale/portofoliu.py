"""085 faza B: cei doi clienți pe cazuri reale în portofoliul lui 084 (registries/portofoliu/P13, P14).

Citește client.json + NN-*.mvp.json din A-petrescu-marin/ și B-neagu-cristian/ și scrie ../P13-*.json, ../P14-*.json în
formatul lui agent/portfolio.py: id-urile produselor P13-CC, P13-CRD, ..., IBAN-uri cu cifra de control corectă (în
portofoliu, spre deosebire de documentele de aici, cu „00”), un pas `sign` după adresa notarului (dacă are termenul de dezbatere), `expected` = etapa din
`etapa_demo`. Documentele-suport (`_pipeline: false`, cererea de despăgubire UNIQA) nu devin pași.
Fiecare pas-document e în formatul 090: `file` (fișierul primit, în registries/portofoliu/documente/P13/, făcut de
documente/genereaza.py din .md-urile de aici), `expected_type` + `expected_fields` (adevărul de referință = .mvp.json, cu
IBAN-urile corectate); câmpurile date pipeline-ului vin din extracția reală (`.extras.json`), nu de aici.
Determinist; din rădăcina repo-ului (sau din worktree): .venv/bin/python registries/portofoliu/cazuri-reale/portofoliu.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
SIGNER = "Ioana Marin (back-office succesiuni)"
# tipul documentului -> numele fișierului din documente/<Pxx>/ (ca la P01..P12)
SLUG = {"dgep_signal": "semnal-dgep", "death_certificate": "certificat-deces", "notary_request": "adresa-notar",
        "insurance_certificate": "certificat-asigurare", "heir_certificate": "certificat-mostenitor",
        "insurer_response": "raspuns-asigurator"}


def doc_file(client_id: str, n: int, mvp: dict) -> str:
    """Fișierul primit de bancă pentru al n-lea document: semnalul DGEP e o linie de lot (redată .pdf), restul scanări."""
    t = mvp["document_type"]
    slug = SLUG[t] + ("-refuz" if t == "insurer_response" and mvp["fields"].get("decision") == "refused" else "")
    return f"{client_id}/{n:02d}-{slug}" + (".pdf" if t == "dgep_signal" else "-scan.pdf")

CLIENTS = [
    {"dir": "A-petrescu-marin", "id": "P13", "case_id": "SC-2026-0113", "file": "P13-marin-petrescu.json",
     "products": {"CC-A1": "P13-CC", "CRD-A1": "P13-CRD"},
     "stage": "refuz_datorie_peste_activ",
     "stage_label": "Asigurătorul a refuzat, datoria depășește activul: plan de 0 lei de aprobat (caz real: Jud. Târgu Jiu, sent. civ. 825/2013)",
     # 090: adresa notarului fără data dezbaterii (formularea reală notari.pro) nu mai deschide
     # document_deficient_institution: extracția reală îi dă 0,5 (hearing_date e obligatoriu în skill-ul extractorului),
     # deci stă la „documente neidentificate” ca document_illegible și nu există răspuns de semnat
     "expected": {"state": "PAYMENT_PENDING_APPROVAL",
                  "escalations": ["debt_exceeds_estate", "insurance_refused"],
                  "decisions": ["plata", "escaladare", "escaladare"], "plan": True}},
    {"dir": "B-neagu-cristian", "id": "P14", "case_id": "SC-2026-0114", "file": "P14-cristian-neagu.json",
     "products": {"CC-B1": "P14-CC", "CRD-B1": "P14-CRD", "CARD-B1": "P14-CARD"},
     "stage": "plan_de_aprobat",
     "stage_label": "Plan de plată de aprobat, doi minori (caz real: Trib. Alba, dec. civ. 839/A/2015)",
     # + adresa notarului ca la P13; reprezentanții minorilor (curatorul, mama lui Andrei) nu sunt moștenitori,
     # deci scara de contact nu are canal spre ei => contact_no_channel, câte unul pentru fiecare minor
     "expected": {"state": "PAYMENT_PENDING_APPROVAL",
                  "escalations": ["contact_no_channel", "contact_no_channel", "minor_heir", "minor_heir"],
                  "decisions": ["plata"] + ["escaladare"] * 4, "plan": True}},
]


def iban(fake: str) -> str:
    """'RO00 RZBR ...' -> același IBAN cu cifrele de control calculate (ISO 13616, mod 97)."""
    s = fake.replace(" ", "")
    bban = s[4:]
    n = int("".join(str(int(ch, 36)) for ch in bban + s[:2] + "00"))
    s = s[:2] + f"{98 - n % 97:02d}" + bban
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def build(spec: dict) -> dict:
    src = HERE / spec["dir"]
    core = json.loads((src / "client.json").read_text(encoding="utf-8"))
    pid = spec["products"]
    ibans = {iban(k): pid[v] for k, v in core["ibans"].items()}
    by_product = {v: k for k, v in ibans.items()}
    contract = {pid[v]: k for k, v in core["loan_contracts"].items()}
    installment = {pid[k]: v for k, v in core["installments"].items()}
    products = []
    for p in core["products"]:
        p = {**_clean(p), "id": pid[p["id"]]}
        if p["id"] in by_product:
            p["iban"] = by_product[p["id"]]
        if p["id"] in contract:
            p["loan_contract"] = contract[p["id"]]
        if p["id"] in installment:
            p["installment"] = installment[p["id"]]
        products.append(p)
    customer = {k: v for k, v in core["customer"].items() if k in ("cif", "name", "cnp", "birth_date", "spouse", "cards")}
    customer["cards"] = [pid.get(c, c) for c in customer["cards"]]

    steps, n = [], 0
    for name in core["etapa_demo"]["documente_in_ordine"]:
        d = json.loads((src / f"{name}.mvp.json").read_text(encoding="utf-8"))
        if d.get("_pipeline") is False:
            continue
        n += 1
        fields = dict(d["fields"])
        if "ibans" in fields:
            fields["ibans"] = [iban(i) for i in fields["ibans"]]
        steps.append({"doc": {"id": f"{spec['id']}-D{n}", "received_on": d["received_on"], "file": doc_file(spec["id"], n, d),
                              "expected_type": d["document_type"], "expected_fields": fields}})
        # back-office semnează răspunsul a doua zi, ca în P02..P12; 090: doar dacă adresa are termenul de dezbatere (fără
        # el extracția reală cade sub prag, adresa nu ajunge în dosar și banca nu are ce semna)
        if d["document_type"] == "notary_request" and d["fields"].get("hearing_date"):
            day = int(d["received_on"][-2:]) + 1
            steps.append({"op": "sign", "on": f"{d['received_on'][:-2]}{day:02d}", "by": SIGNER})
    return {"id": spec["id"], "case_id": spec["case_id"], "stage": spec["stage"], "stage_label": spec["stage_label"],
            "real_case": core["_caz_real"], "source": f"registries/portofoliu/cazuri-reale/{spec['dir']}/README.md",
            "customer": customer, "products": products, "movements": core.get("movements") or [],
            "contacts": core.get("contacts") or {}, "steps": steps, "expected": spec["expected"]}


def main() -> None:
    for spec in CLIENTS:
        out = OUT / spec["file"]
        out.write_text(json.dumps(build(spec), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(out.relative_to(OUT.parent.parent))


if __name__ == "__main__":
    main()
