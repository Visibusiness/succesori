"""Studiul de timp om vs. agent pe dosarul Mariei Ionescu (sarcina 082, docs/studiu-timp/).

Citește tabelele completate de colegi (docs/studiu-timp/date/*.csv: participant,sarcina,start,stop,camp,valoare),
le corectează cu docs/studiu-timp/cheie.json (sumele la ban, cotele ca fracții, datele exact, `v_*` = da/nu de la
corector) și pune alături agentul: răspunsurile lui, citite din rularea cap-coadă (registries/simulare/e2e/<run>/:
dosarul, scrisoarea către notar, mesajul către moștenitor), punctate cu aceeași cheie, și timpii lui de la sosirea
documentului în inbox la rezultat. Fără tabele completate, rezultatul e „în așteptare”.

    .venv/bin/python scripts/impact_studiu.py [--date docs/studiu-timp/date] [--run registries/simulare/e2e/<run>]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STUDY = ROOT / "docs" / "studiu-timp"
KEY = json.loads((STUDY / "cheie.json").read_text(encoding="utf-8"))
TASKS = [t for t in KEY if t.startswith("T")]


# ---------------------------------------------------------------- corectarea
def norm_lei(v: str) -> int | None:
    s = str(v).strip().replace(" ", "").replace("lei", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+,\d{2}", s):   # 5.273,37
        s = s.replace(".", "").replace(",", ".")
    s = s.replace(",", ".")
    try:
        return round(float(s) * 100)
    except ValueError:
        return None


def grade(kind: str, expected: str | None, value: str | None) -> bool | None:
    """True/False; None = câmp care nu se notează (text liber)."""
    v = (value or "").strip()
    if kind == "text":
        return None
    if not v:
        return False
    if kind == "lei":
        return norm_lei(v) == norm_lei(expected)
    if kind == "fractie":
        try:
            return Fraction(v.replace(" ", "")) == Fraction(expected)
        except (ValueError, ZeroDivisionError):
            return False
    if kind == "data":
        parts = sorted(p.strip() for p in v.split(";") if p.strip())
        return parts == sorted(expected.split(";"))
    if kind in ("da_nu",):
        return v.lower() == expected
    if kind == "v":
        return v.lower() == "da"
    raise ValueError(kind)


def score(answers: dict[str, dict[str, str]]) -> dict:
    """answers[sarcina][camp] = valoare → pe sarcină: câmpuri notate, corecte, greșite (cu ce s-a scris)."""
    out = {}
    for t in TASKS:
        rows, ok, wrong = 0, 0, []
        for c, (kind, exp) in KEY[t]["campuri"].items():
            g = grade(kind, exp, answers.get(t, {}).get(c))
            if g is None:
                continue
            rows += 1
            ok += g
            if not g:
                wrong.append({"camp": c, "scris": answers.get(t, {}).get(c) or "", "corect": exp})
        out[t] = {"campuri": rows, "corecte": ok, "greseli": len(wrong), "detalii": wrong}
    return out


def seconds(hms: str) -> int | None:
    g = re.fullmatch(r"\s*(\d{1,2}):(\d\d)(?::(\d\d))?\s*", hms or "")
    return int(g[1]) * 3600 + int(g[2]) * 60 + int(g[3] or 0) if g else None


def read_participant(path: Path) -> dict:
    answers: dict[str, dict[str, str]] = {}
    spans: dict[str, int] = {}
    name = path.stem
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = (r.get("sarcina") or "").strip()
            if not t:
                continue
            name = (r.get("participant") or "").strip() or name
            a, b = seconds(r.get("start", "")), seconds(r.get("stop", ""))
            if a is not None and b is not None:
                spans[t] = spans.get(t, 0) + (b - a if b >= a else b + 86400 - a)
            if r.get("camp"):
                answers.setdefault(t, {})[r["camp"].strip()] = (r.get("valoare") or "").strip()
    sc = score(answers)
    return {"participant": name, "sursa": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "secunde_pe_sarcina": spans, "secunde_total": sum(spans.values()), "scor": sc,
            "greseli_total": sum(s["greseli"] for s in sc.values()), "campuri_total": sum(s["campuri"] for s in sc.values())}


# ---------------------------------------------------------------- agentul, din rularea cap-coadă
def lei(bani: int) -> str:
    return f"{bani / 100:.2f}"


def agent_answers(run: Path) -> tuple[dict, dict, dict]:
    """Răspunsurile agentului la T1–T6 (din dosarul rulării) + timpii (s) de la sosirea documentului la rezultat."""
    cases = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (run / "cases").glob("*.json")}
    c = next(v for k, v in cases.items() if k != "SC-NEIDENTIFICAT")
    orphan = cases.get("SC-NEIDENTIFICAT", {"escalations": [], "documents": []})
    arrivals = {k: datetime.fromisoformat(v) for k, v in
                json.loads((run / "inbox-sosiri.json").read_text(encoding="utf-8"))["sosiri"].items()}
    handoffs = [json.loads(l) for l in (run / "handoffs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ev = {e["id"]: e for e in c["events"]}

    def first(prefix: str) -> dict | None:
        return next((e for e in c["events"] if e["summary"].startswith(prefix)), None)

    def since(at: str | None, doc_prefix: str) -> float | None:
        arr = next((v for k, v in arrivals.items() if k.startswith(doc_prefix)), None)
        return round((datetime.fromisoformat(at) - arr).total_seconds(), 1) if at and arr else None

    def artifact(sub: str) -> dict | None:
        return next((h for h in handoffs if sub in (h.get("artifact") or "")), None)

    ans: dict[str, dict[str, str]] = {t: {} for t in TASKS}
    times: dict[str, float | None] = {}
    src: dict[str, str] = {}
    na = first("Răspuns către notar generat")
    prods = {p["product_id"]: p for p in (na or {}).get("data", {}).get("answer", {}).get("products", [])}
    if prods:
        ans["T1"] = {"sold_cc": lei(prods["CC-1"]["total"]), "dep_principal": lei(prods["DEP-1"]["principal"]),
                     "dep_dobanda": lei(prods["DEP-1"]["accrued_interest"]),
                     "credit_principal": lei(-prods["CRD-1"]["principal"]), "credit_dobanda": lei(-prods["CRD-1"]["accrued_interest"])}
    times["T1"], src["T1"] = since(na and na["at"], "02"), f"{c['id']}:{na['id']}" if na else ""
    letter = artifact("notary_answer_drafted")
    text = (run / letter["artifact"]).read_text(encoding="utf-8") if letter else ""
    ans["T2"] = {"scrisoare": letter["artifact"] if letter else "",
                 "v_solduri": yes(all(x in text for x in ("3.200,00", "20.000,00", "692,38", "9.000,00", "26,63"))),
                 "v_iban_valuta": yes("RZBR" in text and ("RON" in text or "lei" in text)),
                 "v_credit_asigurare": yes("UQ-0000000-FICTIV" in text),
                 "v_pensie_sept": yes("15.09.2026" in text and "2.100,00" in text),
                 "v_cutii": yes(bool(re.search(r"cutii|cutie|casete? de valori|safe", text, re.I))),
                 "v_imputerniciti": yes(bool(re.search(r"andrei", text, re.I)))}
    times["T2"], src["T2"] = since(letter and letter["at"], "02"), letter["artifact"] if letter else ""
    fees = [f for f in c["flags"] if f["code"] == "fee_to_reverse"]
    ans["T3"] = {"comision_stornat": lei(sum(f["amount"] for f in fees)), "comision_data": ";".join(f["date"] for f in fees)}
    e = first("Comisioane după deces stornate")
    times["T3"], src["T3"] = since(e and e["at"], "01"), f"{c['id']}:{e['id']}" if e else ""
    ret = [f for f in c["flags"] if f["code"] == "pension_return_CNPP"]
    kept = [f for f in c["flags"] if f["code"] == "post_death_credit"]
    ans["T4"] = {"pensie_retur": lei(sum(f["amount"] for f in ret)), "pensie_retur_data": ";".join(f["date"] for f in ret),
                 "pensie_pastrata": lei(sum(f["amount"] for f in kept))}
    e = first("Pensie necuvenită")
    times["T4"], src["T4"] = since(e and e["at"], "01"), f"{c['id']}:{e['id']}" if e else ""
    plan = c.get("payment_plan") or {}

    def line(who: str, pid: str) -> dict:
        return next((l for l in plan.get("lines", []) if l["product_id"] == pid and who in l["name"].lower().split()), {})

    if plan:
        ans["T5"] = {"net_cc": lei(plan["net_account"]["net"]),
                     **{f"cota_{w}": line(w, "CC-1").get("fraction_of_product", "") for w in ("ion", "andrei", "elena")},
                     **{f"cc_{w}": lei(line(w, "CC-1").get("amount", 0)) for w in ("ion", "andrei", "elena")},
                     "elena_blocat": yes(line("elena", "CC-1").get("blocked_reason") is not None),
                     **{f"dep_{w}": lei(line(w, "DEP-1").get("amount", 0)) for w in ("ion", "andrei", "elena")},
                     "depozit_plata_data": (re.search(r"\d{4}-\d\d-\d\d", line("ion", "DEP-1").get("blocked_reason") or "") or [""])[0],
                     "platibil_acum": lei(sum(l["amount"] for l in plan["lines"] if l["blocked_reason"] is None))}
    e = first("Plan de plată generat")
    times["T5"], src["T5"] = since(e and e["at"], "06"), f"{c['id']}:{e['id']}" if e else ""
    msg = next((h for h in reversed(handoffs) if h.get("to") == "heir-communicator" and h.get("artifact")), None)
    mtext = (run / msg["artifact"]).read_text(encoding="utf-8") if msg else ""
    doc7 = next((x for x in orphan["escalations"] if x["reason"] == "document_illegible"), None)
    ans["T6"] = {"lipseste": "; ".join(c.get("missing", [])), "mesaj": msg["artifact"] if msg else "",
                 "doc7": doc7["detail"][:120] if doc7 else "",
                 "v_lipseste_acord_elena": yes(any("reprezentantului legal" in m and "ELENA" in m.upper() for m in c.get("missing", []))),
                 "v_mesaj_cere_acord": yes("acord" in mtext.lower() and ("link" in mtext.lower() or "încărca" in mtext.lower())),
                 "v_mesaj_fara_solduri": yes(not re.search(r"\d[\d.]*,\d\d\s*lei", mtext)),
                 "v_doc7_escaladat": yes(doc7 is not None and not any("07" in (d.get("raw_name") or "") for d in c["documents"]))}
    times["T6"], src["T6"] = since(msg and msg["at"], "06"), msg["artifact"] if msg else ""
    return ans, times, src


def yes(b: bool) -> str:
    return "da" if b else "nu"


def agent_total_seconds(run: Path) -> float:
    """Timpul de lucru al agentului pe dosar: pe fiecare document, de la sosire până la ultimul lucru făcut pentru el
    (acțiunea pipeline-ului sau ultimul artefact al agenților), adunat. Pauzele dintre documente (cât a așteptat smoke-ul
    între ele) nu intră."""
    arrivals = {k: datetime.fromisoformat(v) for k, v in
                json.loads((run / "inbox-sosiri.json").read_text(encoding="utf-8"))["sosiri"].items()}
    trace = [json.loads(l) for l in (run / "trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    handoffs = [json.loads(l) for l in (run / "handoffs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    total = 0.0
    for t in trace:
        name = (t.get("document") or {}).get("raw_name")
        if t.get("kind") != "document" or name not in arrivals:
            continue
        ends = [datetime.fromisoformat(t["at"])] + [datetime.fromisoformat(h["at"]) for h in handoffs if h.get("document") == name]
        total += (max(ends) - arrivals[name]).total_seconds()
    return round(total, 1)


def latest_run() -> Path:
    e2e = ROOT / "registries" / "simulare" / "e2e"
    return sorted(p for p in e2e.iterdir() if p.is_dir() and (p / "trace.jsonl").exists())[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default=str(STUDY / "date"))
    ap.add_argument("--run", default=None)
    ap.add_argument("--out", default=str(STUDY / "rezultat.json"))
    a = ap.parse_args()
    run = Path(a.run).resolve() if a.run else latest_run()
    ans, times, src = agent_answers(run)
    sc = score(ans)
    agent = {"rulare": str(run.relative_to(ROOT)) if run.is_relative_to(ROOT) else str(run), "raspunsuri": ans, "scor": sc,
             "greseli_total": sum(s["greseli"] for s in sc.values()), "campuri_total": sum(s["campuri"] for s in sc.values()),
             "secunde_pe_sarcina": times, "dovezi": src, "secunde_total": agent_total_seconds(run),
             "nota": "timpul pe sarcină = de la sosirea documentului care o declanșează în inbox până la rezultat (include "
                     "extracția LLM); total = timpul de lucru pe cele 7 documente, fără pauzele dintre ele"}
    files = sorted(Path(a.date).glob("*.csv")) if Path(a.date).is_dir() else []
    people = [read_participant(p) for p in files]
    people = [p for p in people if p["secunde_total"] > 0 or any(s["corecte"] for s in p["scor"].values())]
    res = {"generat": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cheie": "docs/studiu-timp/cheie.json",
           "stare": "gata" if people else "în așteptare", "participanti": people, "agent": agent}
    if people:
        h = [p["secunde_total"] for p in people]
        res["comparatie"] = {"om_secunde_medie": round(sum(h) / len(h)), "agent_secunde": agent["secunde_total"],
                             "raport": round(sum(h) / len(h) / agent["secunde_total"], 1) if agent["secunde_total"] else None,
                             "om_greseli_medie": round(sum(p["greseli_total"] for p in people) / len(people), 1),
                             "agent_greseli": agent["greseli_total"],
                             "pe_sarcina": {t: {"om_secunde_medie": round(sum(p["secunde_pe_sarcina"].get(t, 0) for p in people) / len(people)),
                                                "om_greseli": sum(p["scor"][t]["greseli"] for p in people),
                                                "agent_secunde": times.get(t), "agent_greseli": sc[t]["greseli"]} for t in TASKS}}
    else:
        res["motiv"] = f"niciun tabel completat în {Path(a.date).relative_to(ROOT) if Path(a.date).is_relative_to(ROOT) else a.date}/"
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"studiu: {res['stare']} ({len(people)} participanți) · agent: {agent['greseli_total']}/{agent['campuri_total']} "
          f"câmpuri greșite, {agent['secunde_total']} s de lucru pe dosar")
    for t in TASKS:
        s = sc[t]
        print(f"  {t} agent: {s['corecte']}/{s['campuri']} corecte, {times.get(t)} s · "
              + ", ".join(f"{w['camp']}={w['scris']!r}" for w in s["detalii"]))
    for p in people:
        print(f"  {p['participant']}: {p['secunde_total']} s, {p['greseli_total']}/{p['campuri_total']} greșite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
