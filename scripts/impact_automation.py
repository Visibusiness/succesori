"""Gradul de automatizare, măsurat din jurnalul unei rulări cap-coadă a dosarului demo (sarcina 082).

Citește o rulare a smoke-ului (scripts/smoke_e2e.py pe o instanță izolată, coordonare/bin/test-instance) copiată în
registries/simulare/e2e/<run>/: trace.jsonl (documentele și rezultatul pipeline-ului), cases/*.json (evenimentele
dosarului, cu ora), handoffs.jsonl + autopilot-status.json (apelurile agenților AI, cu durată și cost), operator.jsonl
(deciziile umane) și inbox-sosiri.json (ora la care fiecare fișier a ajuns în inbox).

Clasifică fiecare operațiune: automat (cod determinist), agent AI (extracție, scrisoare, mesaj, investigație, audit),
decizie umană (executată în rulare sau cerută de proiect și încă deschisă). Măsoară timpul de reacție de la sosirea
documentului la acțiune și pune alături cele 12 operațiuni manuale din BRIEF §2, fiecare cu ce o face acum.

    .venv/bin/python scripts/impact_automation.py [registries/simulare/e2e/<run>]
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E2E = ROOT / "registries" / "simulare" / "e2e"

# BRIEF §2 „Soluția”: cele 11 operațiuni din „Face singur” + plata efectivă din „NU face singur” = 12 operațiuni
# pe care azi le face un om. Fiecare: ce eveniment din dosar o dovedește și ce agent (dacă e cazul) scrie textul.
TWELVE = [
    (1, "Blocarea debitului și a cardurilor la aflarea decesului", "automat", ("action", "Blocare "), None),
    (2, "Încetarea împuterniciților (mandatul încetează la deces)", "automat", ("action", "Blocare "), None),
    (3, "Oprirea și stornarea comisioanelor de după deces", "automat", ("action", "Comisioane după deces stornate"), None),
    (4, "Încasările de după deces: pensia de returnat la CNPP", "automat", ("action", "Pensie necuvenită"), None),
    (5, "Soldurile la data decesului, cu dobânda acumulată", "automat", ("action", "Răspuns către notar generat"), None),
    (6, "Răspunsul scris către notar", "agent AI + semnătură umană", ("action", "Răspuns către notar generat"),
     "notary_answer_drafted"),
    (7, "Dosarul de daună la asigurător (avizare, documente)", "automat + agent AI", ("action", "Dosar de daună deschis"),
     "insurance_claim_opened"),
    (8, "Cotele din certificatul de moștenitor (citire + verificare sumă = 1)", "agent AI (extracție) + automat",
     ("document", "Certificat de moștenitor:"), None),
    (9, "Produsele omise din certificat ⇒ cererea de certificat suplimentar", "automat + agent AI",
     ("action", "Certificatul nu acoperă"), "supplement_requested"),
    (10, "Planul de plată: net de datorii, pe cote, minor blocat", "automat", ("action", "Plan de plată generat"), None),
    (11, "Urmărirea termenelor (opțiune 1 an, avizare asigurător, dezbatere)", "automat", ("deadlines", ""), None),
    (12, "Plata efectivă către moștenitori", "decizie umană (aprobare) + execuție automată", ("decision", "Plata aprobată"), None),
]


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def latest_run() -> Path:
    runs = sorted(p for p in E2E.iterdir() if p.is_dir() and (p / "trace.jsonl").exists())
    if not runs:
        raise SystemExit(f"nicio rulare în {E2E}")
    return runs[-1]


def classify_event(ev: dict) -> str:
    s = ev["summary"]
    if ev["kind"] == "decision" and s.startswith("Plata aprobată"):
        return "uman"
    if s.startswith("Mesaj către"):   # mesajul scris de heir-communicator: numărat la agenți, din handoffs
        return "agent_logat"
    return "automat"


def analyse(run: Path) -> dict:
    trace = load_jsonl(run / "trace.jsonl")
    handoffs = [h for h in load_jsonl(run / "handoffs.jsonl") if h.get("artifact") and h.get("ok")]
    operator = [o for o in load_jsonl(run / "operator.jsonl") if o.get("kind") == "operator"]
    status = json.loads((run / "autopilot-status.json").read_text(encoding="utf-8"))
    arrivals = {k: ts(v) for k, v in json.loads((run / "inbox-sosiri.json").read_text(encoding="utf-8"))["sosiri"].items()}
    cases = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "cases").glob("*.json"))}
    client = next(c for c in cases.values() if c["id"] != "SC-NEIDENTIFICAT")
    docs = [t for t in trace if t.get("kind") == "document"]

    # --- operațiunile
    ops = []
    for d in docs:
        doc = d["document"]
        ops.append({"categorie": "agent_ai", "agent": "extractor", "ce": f"citire + extracție {doc.get('raw_name')}",
                    "at": d["at"], "document": doc.get("raw_name"), "cost_usd": (doc.get("extractor") or {}).get("cost_usd")})
    calls = {c["file"]: c for c in status.get("agent_calls", [])}
    for h in handoffs:
        c = calls.get(h["artifact"], {})
        ops.append({"categorie": "agent_ai", "agent": h["to"], "ce": h["artifact"], "at": h["at"], "document": h.get("document"),
                    "secunde": c.get("seconds"), "cost_usd": c.get("cost_usd")})
    doc_of_event: dict[str, str] = {}
    for c in cases.values():
        cur = None
        for ev in c["events"]:
            did = (ev.get("data") or {}).get("document_id")
            if did:
                cur = next((t["document"]["raw_name"] for t in docs if t["document"].get("id") == did), cur)
            doc_of_event[f"{c['id']}:{ev['id']}"] = cur
            cat = classify_event(ev)
            if cat == "agent_logat":
                continue
            ops.append({"categorie": cat, "ce": ev["summary"][:140], "at": ev["at"], "eveniment": f"{c['id']}:{ev['id']}",
                        "tip": ev["kind"], "regula": ev.get("rule"), "document": cur})
    # deciziile umane cerute de proiect, încă deschise la final (nu se fac automat, prin design)
    pending = []
    for ev in client["events"]:
        ans = (ev.get("data") or {}).get("answer")
        if ans and ans.get("status") == "draft_pending_signature":
            pending.append({"ce": "semnarea răspunsului către notar (doi oameni, ARCHITECTURE §7)", "eveniment": f"{client['id']}:{ev['id']}"})
    for c in cases.values():
        for e in c["escalations"]:
            if not e.get("resolved"):
                pending.append({"ce": f"rezolvarea escaladării {e['reason']} ({c['id']} {e['id']})", "eveniment": f"{c['id']}:{e['id']}"})
    executed_human = [o for o in operator]

    # --- timpul de reacție: de la sosirea în inbox la acțiunea pipeline-ului și la ultimul artefact al agenților
    reaction = []
    for d in docs:
        name = d["document"].get("raw_name")
        arr = arrivals.get(name)
        if not arr:
            continue
        agent_ats = [ts(h["at"]) for h in handoffs if h.get("document") == name]
        reaction.append({"document": name, "sosit": arr.isoformat(timespec="seconds"),
                         "pipeline_s": round((ts(d["at"]) - arr).total_seconds(), 1),
                         "agenti_s": round((max(agent_ats) - arr).total_seconds(), 1) if agent_ats else None,
                         "actiuni": d["result"].get("actions", []), "stare": d["result"].get("state"),
                         "escaladare": d["result"].get("escalation_reason")})

    # --- cele 12 operațiuni manuale
    twelve = []
    for n, label, who, (kind, prefix), trigger in TWELVE:
        if kind == "deadlines":
            ev = next((e for e in client["events"] if e["summary"].startswith("Blocare ")), None)
            evidence = f"{len(client['deadlines'])} termene în dosar: " + ", ".join(f"{d['code']} {d['due']}" for d in client["deadlines"])
        else:
            ev = next((e for e in client["events"] if e["kind"] == kind and e["summary"].startswith(prefix)), None)
            evidence = ev["summary"][:160] if ev else "nu apare în rulare"
        doc = doc_of_event.get(f"{client['id']}:{ev['id']}") if ev else None
        row = {"nr": n, "operatiune": label, "acum": who, "dovada": evidence, "eveniment": f"{client['id']}:{ev['id']}" if ev else None,
               "document": doc, "facut": ev is not None}
        if ev and doc in arrivals and n != 12:   # 12: aprobarea vine când decide omul, nu e un timp de reacție al sistemului
            row["reactie_s"] = round((ts(ev["at"]) - arrivals[doc]).total_seconds(), 1)
        if trigger:
            h = next((h for h in handoffs if trigger in h["artifact"]), None)
            row["artefact_ai"] = h["artifact"] if h else None
            if h and doc in arrivals:
                row["reactie_ai_s"] = round((ts(h["at"]) - arrivals[doc]).total_seconds(), 1)
        if n == 12:
            row["nota"] = "în smoke aprobă scriptul de test (approver smoke-e2e); în producție, un operator"
        twelve.append(row)

    count = {k: sum(1 for o in ops if o["categorie"] == k) for k in ("automat", "agent_ai", "uman")}
    total = sum(count.values()) + len(pending)
    pr = [r["pipeline_s"] for r in reaction]
    ag = [r["agenti_s"] for r in reaction if r["agenti_s"] is not None]
    smoke = (run / "smoke.log").read_text(encoding="utf-8") if (run / "smoke.log").exists() else ""
    return {
        "rulare": run.name, "sursa": str(run.relative_to(ROOT)), "dosar": client["id"], "stare_finala": client["state"],
        "smoke": next((l for l in smoke.splitlines() if l.endswith("PASS") and "/" in l and l[0].isdigit()), None),
        "documente": len(docs),
        "operatiuni": {"total": total, "automat": count["automat"], "agent_ai": count["agent_ai"],
                       "uman_executat": count["uman"], "uman_deschis": len(pending),
                       "uman_total": count["uman"] + len(pending),
                       "pondere_fara_om_pct": round(100 * (count["automat"] + count["agent_ai"]) / total, 1)},
        "agenti": {a: sum(1 for o in ops if o.get("agent") == a) for a in sorted({o.get("agent") for o in ops if o.get("agent")})},
        "decizii_umane_executate": executed_human, "decizii_umane_deschise": pending,
        "reactie": {"pe_document": reaction, "pipeline_mediana_s": statistics.median(pr) if pr else None,
                    "pipeline_max_s": max(pr) if pr else None, "agenti_mediana_s": statistics.median(ag) if ag else None,
                    "agenti_max_s": max(ag) if ag else None,
                    "nota": "pipeline_s = de la scrierea fișierului în inbox la acțiunea pe dosar (include extracția LLM); "
                            "agenti_s = până la ultimul artefact al agenților (scrisori, mesaje, investigații) pentru acel document"},
        "douasprezece": twelve,
        "douasprezece_sumar": {"complet_automat": sum(r["acum"] == "automat" for r in twelve),
                               "cu_agent_ai": sum("agent AI" in r["acum"] for r in twelve),
                               "fara_om": sum("uman" not in r["acum"] for r in twelve),
                               "cu_om": sum("uman" in r["acum"] for r in twelve), "facute_in_rulare": sum(r["facut"] for r in twelve)},
        "operatiuni_detaliu": sorted(ops, key=lambda o: o["at"]),
    }


def main() -> int:
    run = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else latest_run()
    res = analyse(run)
    out = E2E / f"automatizare-{run.name}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    o = res["operatiuni"]
    print(f"rulare {res['rulare']} ({res['smoke']}), dosar {res['dosar']} → {res['stare_finala']}, {res['documente']} documente")
    print(f"operațiuni: {o['total']} = {o['automat']} automate + {o['agent_ai']} agent AI + {o['uman_executat']} umane executate "
          f"+ {o['uman_deschis']} umane deschise ({o['pondere_fara_om_pct']}% fără om)")
    r = res["reactie"]
    print(f"reacție: pipeline mediana {r['pipeline_mediana_s']} s (max {r['pipeline_max_s']}), agenți mediana "
          f"{r['agenti_mediana_s']} s (max {r['agenti_max_s']})")
    for t in res["douasprezece"]:
        print(f"  {t['nr']:>2}. {t['operatiune']}: {t['acum']} · {t.get('reactie_s', '—')} s · {t['eveniment']}")
    print(f"scris {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
