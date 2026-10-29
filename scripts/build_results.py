"""Ecranul „Rezultate” pentru juriu: adună cifrele măsurate într-un singur ops-ui/results.json (regenerabil oricând).

Fiecare cifră e {valoare, unitate, sursa, data}; ce lipsește are valoare null și `motiv`. Nimic nu e inventat: totul vine din
runs/ (eval-uri, smoke, rulări cu cost), docs/ (decizia 050, costul per dosar, business case), registries/documents/
adversarial/ (+ poarta deterministă agent/guard.py), kb/_downloads/realsurse/ (doar numărători și agregate),
.claude/skills/ și, pentru „Impact măsurat” (082), registries/simulare/ + docs/studiu-timp/rezultat.json. Scrie și
ops-ui/results-data.js (aceleași date, ca pagina să meargă și deschisă direct din fișier).

    .venv/bin/python scripts/build_results.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "runs"
OUT = ROOT / "ops-ui" / "results.json"
OUT_JS = ROOT / "ops-ui" / "results-data.js"
REALSURSE = ROOT / "kb" / "_downloads" / "realsurse"
ADV = ROOT / "registries" / "documents" / "adversarial"

SETS = [("train", "Antrenare (train)", "eval-latest.json", "eval-20"),
        ("holdout", "Holdout (nevăzut la antrenare)", "eval-holdout-latest.json", "eval-holdout-20"),
        ("holdout-aug", "Holdout augmentat (OCR, fără diacritice, formate)", "eval-holdout-aug-latest.json", "eval-holdout-aug-20"),
        ("real-text", "Texte reale (formulare publice)", "eval-real-text-latest.json", "eval-real-text-20"),
        ("forms", "Certificate de deces din fișier (PDF/scan/foto)", "eval-forms-latest.json", "eval-forms-20"),
        ("forms-holdout", "Certificate de deces, holdout", "eval-forms-holdout-latest.json", "eval-forms-holdout-20"),
        ("adversarial", "Adversarial (extractor)", "eval-adversarial-latest.json", "eval-adversarial-20")]


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def m(valoare, unitate: str, sursa: str | list[str] | None, data: str | None, **extra) -> dict:
    return {"valoare": valoare, "unitate": unitate, "sursa": sursa, "data": data, **extra}


def lipsa(unitate: str, motiv: str, sursa=None) -> dict:
    return {"valoare": None, "unitate": unitate, "sursa": sursa, "data": None, "motiv": motiv}


def pct(x: float | None) -> float | None:
    return None if x is None else round(100 * x, 1)


def load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---------- 1. cât de bine citește ----------

def valid_run(d: dict) -> bool:
    """Rulări de eval care măsoară extractorul: excludem testele parțiale (n < 5) și rulările în care extractorul n-a
    răspuns deloc (tip 0%: fiecare document `unknown`)."""
    return (d.get("n") or 0) >= 5 and (d.get("type_accuracy") or 0) > 0


def eval_history(prefix: str, kind: str) -> list[dict]:
    out = []
    for p in sorted(RUNS.glob(prefix + "*.json")):
        d = load(p)
        if not d or (d.get("kind") or "train") != kind or "latest" in p.name:
            continue
        out.append({"at": d.get("at") or mtime(p), "n": d.get("n"), "field": pct(d.get("field_accuracy")),
                    "type": pct(d.get("type_accuracy")), "gate": pct(d.get("gate_accuracy")),
                    "valid": valid_run(d), "sursa": rel(p)})
    return out


def extraction() -> dict:
    sets = []
    for key, label, latest, prefix in SETS:
        p = RUNS / latest
        d = load(p)
        hist = eval_history(prefix, key)
        if not d:
            motiv = ("nu se măsoară pe extractor: atacurile cu risc mare sunt oprite de poartă înainte de LLM; "
                     "verdictul e în secțiunea „Cât de sigur e”") if key == "adversarial" else f"nu există {rel(p)}"
            sets.append({"set": key, "eticheta": label, "n": None, "campuri": lipsa("%", motiv), "tip": lipsa("%", motiv),
                         "prag": lipsa("%", motiv), "istoric": hist})
            continue
        at = d.get("at") or mtime(p)
        src = rel(p)
        valid = [h for h in hist if h["valid"]]
        sets.append({
            "set": key, "eticheta": label, "n": d.get("n"),
            "campuri": m(pct(d.get("field_accuracy")), "%", src, at),
            "tip": m(pct(d.get("type_accuracy")), "%", src, at),
            "prag": m(pct(d.get("gate_accuracy")), "%", src, at),
            "prima_rulare_valida": m(valid[0]["field"], "%", valid[0]["sursa"], valid[0]["at"]) if valid else None,
            "rulari": m(len(hist), "rulări de eval", f"runs/{prefix}*.json", at,
                        nota=f"{len(valid)} valide (n ≥ 5 și tip > 0%)"),
            "istoric": hist,
        })
    return {"seturi": sets, "antrenare": training_loop(), "ab_haiku_sonnet": ab_test(),
            "nota": "câmpuri = % din câmpurile din ground truth extrase corect; tip = tipul documentului corect; "
                    "prag = decizia „peste/sub pragul de încredere” corectă (sub prag ⇒ la om)"}


TRAIN_LINE = re.compile(r"train ([\d.]+)%(?: -> ([\d.]+)%)? · holdout ([\d.]+)%(?: -> ([\d.]+)%)? · holdout-aug ([\d.]+)%"
                        r"(?: -> ([\d.]+)%)?")


def training_loop() -> dict:
    log = RUNS / "workers" / "bucla-antrenare.log"
    if not log.exists():
        return {"puncte": [], "motiv": f"nu există {rel(log)}"}
    points = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.startswith("== "):
            continue
        g = TRAIN_LINE.search(line)
        if not g:
            continue
        if "înainte" in line:
            points.append({"pas": "pornire", "train": float(g[1]), "holdout": float(g[3]), "holdout_aug": float(g[5])})
        elif (c := re.search(r"după ciclul (\d+)", line)):
            points.append({"pas": f"ciclul {c[1]}", "train": float(g[2]), "holdout": float(g[4]), "holdout_aug": float(g[6])})
    date = mtime(log)
    retros = sorted(p for p in RUNS.glob("retro-20261028T15[23]*Z.md"))
    aug = [h for h in eval_history("eval-holdout-aug-20", "holdout-aug") if h["valid"]]
    res = {"puncte": points, "sursa": rel(log), "data": date, "rapoarte_retro": [rel(p) for p in retros],
           "descriere": "scripts/retro.py: eval → retro-learner scrie lecții în .claude/skills → eval; o lecție se "
                        "păstrează doar dacă holdout + holdout-aug nu scad (garda)"}
    if points:
        a, b = points[0], points[-1]
        res["holdout_aug_pornire"] = m(a["holdout_aug"], "%", rel(log), date)
        res["holdout_aug_acum"] = m(b["holdout_aug"], "%", rel(log), date, nota=f"după {len(points) - 1} cicluri")
        res["cicluri"] = m(len(points) - 1, "cicluri", rel(log), date)
    if aug:
        res["holdout_aug_evaluari"] = [{"at": h["at"], "campuri": h["field"], "sursa": h["sursa"]} for h in aug]
    return res


def ab_test() -> dict:
    dec = ROOT / "docs" / "DECISIONS.md"
    line = next((l for l in dec.read_text(encoding="utf-8").splitlines() if "(050)" in l), None) if dec.exists() else None
    out: dict = {"decizie_sursa": rel(dec), "decizie": None}
    if line:
        out["decizie"] = "Extractorul rămâne pe Sonnet: Haiku pierde 1,6 pct pe holdout (criteriul: cel mult 1 pct)." \
            if "rămâne pe Sonnet" in line else None
        out["decizie_data"] = (re.search(r"(\d{4}-\d{2}-\d{2})", line) or [None])[0]
        cost = re.search(r"Haiku ≈ \$([\d,]+)/document", line)
        out["haiku_cost_document"] = m(float(cost[1].replace(",", ".")), "$/document", rel(dec), out["decizie_data"]) \
            if cost else lipsa("$/document", "nu apare în decizia 050")
    rows = []
    for model, files in (("Sonnet 5.5", ("eval-2026-10-28T135710+0000.json", "eval-holdout-2026-10-28T135710+0000.json")),
                         ("Haiku 5.5", ("eval-haiku-train.json", "eval-haiku-holdout.json"))):
        row = {"model": model}
        for k, f in zip(("train", "holdout"), files):
            d = load(RUNS / f)
            row[k] = m(pct(d["field_accuracy"]), "%", f"runs/{f}", d.get("at")) if d else lipsa("%", f"nu există runs/{f}")
            if d and k == "holdout":
                row["tip"] = m(pct(d["type_accuracy"]), "%", f"runs/{f}", d.get("at"))
        rows.append(row)
    out["modele"] = rows
    return out


# ---------- 2. cât costă și cât durează ----------

def cost() -> dict:
    from scripts.cost_dosar import run_cost
    doc = ROOT / "docs" / "pitch" / "cost-per-dosar.md"
    runs = []
    for p in sorted(x for x in (RUNS.iterdir() if RUNS.is_dir() else ()) if x.is_dir() and not x.is_symlink() and x.name != "latest"):
        r = run_cost(p)
        if r:
            runs.append({"run": r["run"], "documente": r["documents"], "agenti": sorted(r["agents"]),
                         "apeluri_agenti": sum(a["calls"] for a in r["agents"].values()),
                         "cost": m(round(r["total_usd"], 2), "$", f"runs/{r['run']}/", mtime(p / "trace.jsonl")),
                         "extractie_usd": round(r["extract_usd"], 2), "agenti_usd": round(r["agents_usd"], 2),
                         "pe_agent": {k: {"apeluri": a["calls"], "usd": round(a["usd"], 2), "secunde": round(a["seconds"])}
                                      for k, a in r["agents"].items()}})
    # dosarul complet = 7 documente și cei 4 agenți ai autopilotului (rularea de referință din cost-per-dosar.md)
    full = [r for r in runs if r["documente"] == 7 and len(r["agenti"]) >= 4]
    ref = max(full, key=lambda r: r["cost"]["data"]) if full else None
    out = {"rulari": runs, "metoda": "scripts/cost_dosar.py: extractor.cost_usd din trace.jsonl + cost_usd per apel de "
                                      "agent din autopilot-status.json (total_cost_usd raportat de claude -p)",
           "doc": rel(doc), "curs": m(4.5, "lei/$", "docs/pitch/business-case.md", None, nota="estimare proprie")}
    if ref:
        a = ref["pe_agent"].get("auditor", {"usd": 0})
        out["dosar_complet"] = ref["cost"] | {"run": ref["run"], "lei": round(ref["cost"]["valoare"] * 4.5, 1)}
        out["auditor_pondere"] = m(round(100 * a["usd"] / ref["cost"]["valoare"]), "% din cost", ref["cost"]["sursa"],
                                   ref["cost"]["data"])
        out["extractie_dosar"] = m(ref["extractie_usd"], "$", ref["cost"]["sursa"], ref["cost"]["data"],
                                   nota="7 documente")
    else:
        out["dosar_complet"] = lipsa("$", "nicio rulare cu 7 documente și toți agenții în runs/")
    costs = [r["cost"]["valoare"] for r in runs]
    out["interval"] = m([min(costs), max(costs)], "$", "runs/*/ (scripts/cost_dosar.py)",
                        max(r["cost"]["data"] for r in runs), nota="toate rulările cu agenți; cele ieftine au apelat "
                        "mai puțini agenți (vezi tabelul)") if costs else lipsa("$", "nicio rulare cu agenți în runs/")
    txt = doc.read_text(encoding="utf-8") if doc.exists() else ""
    opt = re.search(r"\*\*Total optimizat\*\* \| \*\*≈ ([\d,]+) \$", txt)
    out["optimizat"] = m(float(opt[1].replace(",", ".")), "$", rel(doc), "2026-10-28",
                         nota="estimare proprie: auditor o dată la închidere + extracție pe Haiku; nemăsurat cap-coadă") \
        if opt else lipsa("$", "nu apare în cost-per-dosar.md")
    return out


def manual_estimate() -> dict:
    bc = ROOT / "docs" / "pitch" / "business-case.md"
    txt = bc.read_text(encoding="utf-8") if bc.exists() else ""
    out = {}
    for name in ("Prudent", "Central", "Optimist"):
        g = re.search(rf"\| {name} \| [\d.]+ \| ([\d,]+) \(([^)]*)\) \|", txt)
        out[name.lower()] = m(float(g[1].replace(",", ".")), "ore/dosar", rel(bc), "2026-10-28",
                              nota=f"estimare proprie: {g[2]} (interacțiuni × minute)") if g \
            else lipsa("ore/dosar", "nu apare în business-case.md")
    return out


SMOKE_ROW = re.compile(r"^\s*(PASS|FAIL)\s+(.+?)\s{2,}(.*)$")


def parse_smoke_log(p: Path) -> dict | None:
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    api = next((re.search(r"smoke e2e pe (\S+)", l)[1] for l in lines if "smoke e2e pe" in l), None)
    rows = [(g[1] == "PASS", g[2].strip(), g[3].strip()) for l in lines if (g := SMOKE_ROW.match(l))]
    total = next((re.search(r"(\d+)/(\d+) PASS", l) for l in lines if re.search(r"^\d+/\d+ PASS", l)), None)
    dur = next((int(re.search(r"durată: (\d+) s", l)[1]) for l in lines if l.startswith("durată:")), None)
    if not rows:
        return None
    return {"api": api, "ok": [r[0] for r in rows], "checks": [r[1] for r in rows], "details": [r[2] for r in rows],
            "pass": int(total[1]) if total else sum(r[0] for r in rows), "total": int(total[2]) if total else len(rows),
            "seconds": dur, "complete": total is not None}


def smoke() -> tuple[dict, dict]:
    files = {}
    for p in sorted((RUNS / "e2e").glob("smoke-*")):
        if p.suffix in (".log", ".json"):
            files.setdefault(p.stem, {})[p.suffix] = p
    runs = []
    for stem, fs in files.items():
        r, src = None, None
        if ".log" in fs:
            r, src = parse_smoke_log(fs[".log"]), fs[".log"]
        if not r and ".json" in fs:
            d = load(fs[".json"])
            if d and d.get("rows"):
                rows = d["rows"]
                r = {"api": d.get("api"), "ok": [x["ok"] for x in rows], "checks": [x["check"] for x in rows],
                     "details": [str(x.get("detail", "")) for x in rows], "pass": sum(x["ok"] for x in rows),
                     "total": len(rows), "seconds": d.get("seconds"), "complete": True}
                src = fs[".json"]
        if not r:
            continue
        if not r["complete"]:
            continue    # rulare încă în desfășurare (fără linia finală N/M PASS)
        times = {}
        for ok, check in zip(r["ok"], r["checks"]):
            g = re.match(r"(\d\d): procesat de autopilot \((\d+) s\)", check)
            if g:
                times[g[1]] = int(g[2])
        port = (re.search(r":(\d+)", r["api"] or "") or [None, None])[1]
        runs.append({"rulare": stem, "sursa": rel(src), "data": mtime(src), "api": r["api"],
                     "instanta": "izolată (test-instance)" if port and port != "8001" else "MVP viu :8001",
                     "pass": r["pass"], "total": r["total"], "secunde": r["seconds"], "secunde_pe_document": times,
                     "esecuri": [c for ok, c in zip(r["ok"], r["checks"]) if not ok][:8]})
    runs.sort(key=lambda x: x["data"])
    green = [x for x in runs if x["pass"] == x["total"]]
    last = runs[-5:]
    smoke_out = {"rulari": runs, "ultimele": m(f"{sum(x['pass'] == x['total'] for x in last)}/{len(last)}",
                                                "rulări complet verzi", "runs/e2e/smoke-*", last[-1]["data"] if last else None),
                 "verificari_pe_rulare": m(runs[-1]["total"], "verificări", "scripts/smoke_e2e.py", runs[-1]["data"])
                                         if runs else lipsa("verificări", "nicio rulare smoke în runs/e2e/"),
                 "raport": "coordonare/rapoarte/072-bedrock-e2e.md",
                 "ce_verifica": "start curat, cele 7 documente prin inbox, starea dosarului după fiecare, netul 527.337, "
                                "cele 6 linii de plată, pensia reținută, doc 07 escaladat, mesaje, scrisori, audit, "
                                "aprobarea plății și o singură plată în core"}
    # timpul: doar din rulările complet verzi (cele cu eșec pot fi oprite la jumătate)
    tsrc = [x["sursa"] for x in green]
    per_doc = {}
    for x in green:
        for k, v in x["secunde_pe_document"].items():
            per_doc.setdefault(k, []).append(v)
    tot = [x["secunde"] for x in green if x["secunde"]]
    time_out = {"rulari_verzi": len(green), "sursa": tsrc, "raport": "coordonare/rapoarte/072-bedrock-e2e.md"}
    if tot:
        d = green[-1]["data"]
        time_out["dosar_cap_coada"] = m(round(statistics.median(tot) / 60, 1), "minute (mediană)", tsrc, d,
                                        interval_secunde=[min(tot), max(tot)], nota="7 documente, inclusiv agenții")
        alld = [v for vs in per_doc.values() for v in vs]
        time_out["document"] = m(round(statistics.median(alld)), "secunde (mediană)", tsrc, d,
                                 interval_secunde=[min(alld), max(alld)])
        time_out["pe_document"] = {k: m(round(statistics.median(v)), "s (mediană)", tsrc, d, rulari=len(v))
                                   for k, v in sorted(per_doc.items())}
    else:
        time_out["dosar_cap_coada"] = lipsa("minute", "nicio rulare smoke complet verde în runs/e2e/")
        time_out["document"] = lipsa("secunde", "nicio rulare smoke complet verde în runs/e2e/")
    return smoke_out, time_out


# ---------- 4. cât de sigur e ----------

def safety() -> dict:
    exps = sorted(ADV.glob("*.expected.json"))
    rap = sorted((ROOT / "coordonare" / "rapoarte").glob("076-*.md"))
    out: dict = {"set": rel(ADV), "raport_076": rel(rap[0]) if rap else None,
                 "stare": "gata" if rap else "în lucru",
                 "documente": m(len(exps), "documente", rel(ADV), mtime(exps[-1]) if exps else None)}
    if not exps:
        out["poarta"] = lipsa("documente", "setul adversarial nu există încă")
        return out
    items = [load(p) | {"_p": p} for p in exps]
    out["atacuri"] = m(sum(e["risk"] != "low" for e in items), "documente rău-intenționate", rel(ADV), out["documente"]["data"])
    out["controale"] = m(sum(e["risk"] == "low" for e in items), "documente legitime (trebuie să treacă)", rel(ADV),
                         out["documente"]["data"])
    try:
        from agent import guard
    except Exception as e:  # noqa: BLE001 — guard.py e în lucru la alt agent; dacă nu se importă, spunem
        out["poarta"] = lipsa("documente", f"agent/guard.py nu se poate importa acum: {type(e).__name__}")
        return out
    rows, now = [], datetime.now(timezone.utc).isoformat(timespec="seconds")
    for e in items:
        try:
            r = guard.inspect(ADV / e["file"])
            codes = {f["code"] for f in r["flags"]}
            ok = r["risk"] == e["risk"] and set(e.get("flags_include", [])) <= codes
            got = r["risk"]
        except Exception as ex:  # noqa: BLE001
            ok, got, codes = False, f"eroare: {type(ex).__name__}", set()
        rows.append({"fisier": e["file"], "atac": e.get("attack", ""), "asteptat": e["risk"], "obtinut": got,
                     "decizie": e.get("pipeline"), "ok": ok, "flaguri": sorted(codes)})
    atk = [r for r in rows if r["asteptat"] != "low"]
    out["poarta"] = m(f"{sum(r['ok'] for r in rows)}/{len(rows)}", "documente cu verdictul așteptat",
                      ["agent/guard.py", rel(ADV)], now, nota="măsurat de build_results.py cu poarta deterministă "
                      "(fără LLM); verdictul complet al pipeline-ului e în raportul 076" + ("" if rap else " (în lucru)"))
    out["atacuri_oprite"] = m(f"{sum(r['ok'] for r in atk)}/{len(atk)}", "atacuri detectate cu riscul așteptat",
                              ["agent/guard.py", rel(ADV)], now)
    out["controale_trecute"] = m(f"{sum(r['ok'] for r in rows if r['asteptat'] == 'low')}/"
                                 f"{sum(r['asteptat'] == 'low' for r in rows)}", "controale fără alarmă falsă",
                                 ["agent/guard.py", rel(ADV)], now)
    out["detalii"] = rows
    return out


# ---------- 5. date reale ----------

def index_entries(cat: str) -> tuple[int | None, str | None]:
    """Câte surse listează indexul categoriei (rânduri cu URL), altfel secțiunea ei din INDEX.md-ul comun."""
    own = REALSURSE / cat / "INDEX.md"
    if own.exists():
        n = sum(1 for l in own.read_text(encoding="utf-8").splitlines()
                if "http" in l and re.match(r"^(- |\| *\d|[\w.-]+\.\w+)", l.strip()))
        return n, rel(own)
    root = REALSURSE / "INDEX.md"
    if root.exists():
        sec, n = None, 0
        for l in root.read_text(encoding="utf-8").splitlines():
            if l.startswith("## "):
                sec = l[3:].split()[0]
            elif sec == cat and l.startswith("- "):
                n += 1
        if n:
            return n, rel(root)
    return None, None


LABELS = {"asiguratori": "Asigurători (PID, condiții, formulare)", "banci": "Bănci (CGB, proceduri publice)",
          "date": "Date de piață (rapoarte anuale, INS, Eurostat, CSALB)", "forme": "Formulare oficiale",
          "forum": "Forumuri (întrebări reale)", "jurisprudenta": "Jurisprudență (set 1)",
          "jurisprudenta2": "Jurisprudență (set 2, anonimizată)", "notari": "Notari (UNNPR, proceduri)",
          "portal-just": "Portal instanțe (agregate)", "rejust": "ReJust (hotărâri)", "statistici": "Statistici"}


def real_data() -> dict:
    cats = []
    if REALSURSE.exists():
        for d in sorted(x for x in REALSURSE.iterdir() if x.is_dir()):
            n, src = index_entries(d.name)
            files = sum(1 for f in d.rglob("*") if f.is_file() and f.name != "INDEX.md"
                        and not {"cache", "original", "raw"} & set(f.relative_to(d).parts))
            cats.append({"categorie": d.name, "eticheta": LABELS.get(d.name, d.name),
                         "surse": m(n, "surse în index", src, mtime(Path(ROOT / src)) if src else None) if n is not None
                         else lipsa("surse în index", "categoria nu are index cu surse"),
                         "fisiere": m(files, "fișiere", rel(d), mtime(d))})
    out = {"categorii": cats, "nota": "numărători din INDEX.md (rânduri cu URL); conținutul nu e copiat aici",
           "total_surse": m(sum(c["surse"]["valoare"] or 0 for c in cats), "surse", rel(REALSURSE) + "/*/INDEX.md",
                            max((c["surse"]["data"] for c in cats if c["surse"]["data"]), default=None))}
    out["portal_just"] = portal_just()
    return out


def portal_just() -> dict:
    p = REALSURSE / "portal-just" / "CIFRE.md"
    if not p.exists():
        return {"motiv": f"nu există {rel(p)}"}
    txt = p.read_text(encoding="utf-8")
    src, date = rel(p), mtime(p)
    gen = re.search(r"Generat de .*? la (\d{4}-\d{2}-\d{2} \d\d:\d\d) din (\d+) răspunsuri", txt)
    out: dict = {"sursa": src, "data": date, "perioada": "2023 – 2026-10-28",
                 "raspunsuri_api": m(int(gen[2]), "răspunsuri portalquery.just.ro", src, gen[1]) if gen else None}
    sec1 = txt.split("## 1.")[1].split("###")[0] if "## 1." in txt else ""
    banks = []
    for l in sec1.splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) == 7 and c[5].isdigit():
            banks.append({"banca": c[0], "dosare": m(int(c[5]), "dosare (termeni de succesiune)", src, date)})
    out["pe_banca"] = banks
    nucleu = txt.split("### Nucleul succesoral")[1].split("##")[0] if "### Nucleul succesoral" in txt else ""
    for l in nucleu.splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if c and c[0] == "Raiffeisen" and c[-1].isdigit():
            out["raiffeisen_nucleu"] = m(int(c[-1]), "dosare succesiune/moștenire/indiviziune/deces", src, date)
    g = re.search(r"\| Total \| (\d+) \| (\d+) \| (\d+) \| ([\d.]+)% \|", txt)
    if g:
        out["raiffeisen_toate"] = m(int(g[1]), "dosare cu Raiffeisen parte", src, date)
        out["raiffeisen_termeni"] = m(int(g[2]), "dosare cu termeni de succesiune", src, date)
        out["raiffeisen_pondere"] = m(float(g[4]), "% nucleu succesoral din toate", src, date)
    return out


# ---------- 6. ce au învățat agenții ----------

LEARNED = re.compile(r"capcane|exemple grele|rezolvări acceptate|formulări|corecții", re.I)


def lessons() -> dict:
    skills, examples = [], []
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        sec, items = None, []
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.startswith("## "):
                sec = l[3:].strip()
            elif sec and LEARNED.search(sec) and l.startswith("- ") and l[2:].strip() != "(gol)":
                items.append((sec, l[2:].strip()))
        skills.append({"skill": p.parent.name, "lectii": m(len(items), "lecții", rel(p), mtime(p)),
                       "sectiuni": sorted({s for s, _ in items})})
        if items:
            examples.append({"skill": p.parent.name, "sursa": rel(p), "data": mtime(p), "text": short(items[0][1])})
    # un exemplu pe skill, primele trei skill-uri cu lecții; dacă sunt mai puține, mai luăm din cel mai bogat
    rich = max(skills, key=lambda s: s["lectii"]["valoare"], default=None)
    if rich and len(examples) < 3:
        p = ROOT / rich["lectii"]["sursa"]
        extra = [l[2:].strip() for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- (")]
        for t in extra[1:]:
            if len(examples) >= 3:
                break
            examples.append({"skill": rich["skill"], "sursa": rich["lectii"]["sursa"], "data": rich["lectii"]["data"],
                             "text": short(t)})
    return {"skills": skills, "total": m(sum(s["lectii"]["valoare"] for s in skills), "lecții", ".claude/skills/*/SKILL.md",
                                         max((s["lectii"]["data"] for s in skills), default=None)),
            "exemple": examples[:3],
            "nota": "lecții = punctele din secțiunile scrise de retro-learner (capcane, exemple grele, rezolvări și "
                    "formulări acceptate, corecții ale operatorului)"}


def short(t: str, n: int = 230) -> str:
    t = re.sub(r"\*\*|`", "", t)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"


# ---------- 7. impact măsurat (082) ----------

SIM = ROOT / "registries" / "simulare"
STUDY = ROOT / "docs" / "studiu-timp"


def impact() -> dict:
    """Cele trei dovezi din docs/IMPACT.md: automatizarea pe dosarul demo (jurnalul unei rulări cap-coadă), simularea la
    scară (200 de dosare vs. referința independentă) și studiul de timp om vs. agent (în așteptare până vin datele)."""
    out: dict = {"doc": "docs/IMPACT.md", "raport": "coordonare/rapoarte/082-bedrock-impact.md"}
    autos = sorted((SIM / "e2e").glob("automatizare-*.json"))
    a = load(autos[-1]) if autos else None
    if a:
        src, d = rel(autos[-1]), mtime(autos[-1])
        o, r = a["operatiuni"], a["reactie"]
        out["automatizare"] = {
            "rulare": a["rulare"], "smoke": a["smoke"], "sursa_rulare": a["sursa"], "documente": a["documente"],
            "operatiuni": m(o["total"], "operațiuni pe dosar", src, d),
            "automat": m(o["automat"], "automate (cod)", src, d), "agent_ai": m(o["agent_ai"], "agent AI", src, d),
            "uman": m(o["uman_total"], "decizii umane", src, d,
                      nota=f"{o['uman_executat']} executată în rulare (aprobarea plății) + {o['uman_deschis']} cerute și "
                           "deschise prin design (semnarea răspunsului către notar, escaladările)"),
            "fara_om": m(o["pondere_fara_om_pct"], "%", src, d, nota="operațiuni făcute fără om, din total"),
            "reactie_pipeline": m(r["pipeline_mediana_s"], "s (mediană)", src, d, interval=[min(x["pipeline_s"] for x in r["pe_document"]),
                                  r["pipeline_max_s"]], nota="de la sosirea fișierului în inbox la acțiunea pe dosar, cu extracția LLM"),
            "reactie_agenti": m(r["agenti_mediana_s"], "s (mediană)", src, d, maxim=r["agenti_max_s"],
                                nota="până la ultimul artefact al agenților pentru acel document"),
            "douasprezece": [{k: x.get(k) for k in ("nr", "operatiune", "acum", "eveniment", "reactie_s", "artefact_ai")}
                             for x in a["douasprezece"]],
            "douasprezece_sumar": a["douasprezece_sumar"], "agenti": a["agenti"],
            "decizii_umane": [x["ce"] for x in a["decizii_umane_deschise"]] + ["aprobarea plății (executată în rulare)"],
            "sursa": src, "data": d}
    else:
        out["automatizare"] = {"operatiuni": lipsa("operațiuni", "nu există registries/simulare/e2e/automatizare-*.json "
                                                                "(scripts/impact_automation.py)")}
    sims = sorted(SIM.glob("rezultat-seed*.json"))
    s = load(sims[-1]) if sims else None
    if s:
        src, d = rel(sims[-1]), mtime(sims[-1])
        n = s["dosare"]
        explained = sum(1 for x in s["pe_dosar"] if not x["ok"])
        out["simulare"] = {
            "seed": s["seed"], "dosare": m(n, "dosare", src, d), "documente": m(s["documente"], "documente", src, d),
            "timp_total": m(s["secunde_total"], "s", src, d, nota=f"{s['ms_pe_dosar']['medie']} ms/dosar, fără LLM (documente pre-extrase)"),
            "corecte": m(round(100 * s["dosare_corecte_complet"] / n, 1), "%", src, d,
                         nota=f"{s['dosare_corecte_complet']}/{n}; restul de {explained} au cel puțin una dintre cauzele de mai jos"),
            "cu_plan": m(s["dosare_cu_plan"], "dosare cu plan de plată", src, d),
            "linii_exacte": m(f"{s['linii_plata_exacte']}/{s['linii_plata_total']}", "linii de plată exacte la ban", src, d),
            "plati_fara_aprobare": m(s["plati_fara_aprobare"], "plăți fără aprobare", src, d),
            "escaladari": m(f"{s['dosare_cu_escaladari_exacte']}/{n}", "dosare cu escaladările exacte", src, d),
            "capcane": s["capcane"], "cauze": s["dosare_pe_cauza"], "raport": rel(SIM / f"RAPORT-seed{s['seed']}.md"),
            "referinta": s["referinta"], "generator": s["generator"]}
    else:
        out["simulare"] = {"dosare": lipsa("dosare", "nu există registries/simulare/rezultat-seed*.json (scripts/impact_simulare.py)")}
    st = load(STUDY / "rezultat.json")
    if st:
        src, d = rel(STUDY / "rezultat.json"), mtime(STUDY / "rezultat.json")
        ag = st["agent"]
        out["studiu"] = {"stare": st["stare"], "fisa": rel(STUDY / "README.md"),
                         "agent_timp": m(ag["secunde_total"], "s de lucru pe dosar", src, d, nota=ag["nota"]),
                         "agent_greseli": m(f"{ag['greseli_total']}/{ag['campuri_total']}", "câmpuri greșite (aceeași cheie)", src, d),
                         "agent_pe_sarcina": {t: {"secunde": ag["secunde_pe_sarcina"].get(t), "corecte": v["corecte"],
                                                  "campuri": v["campuri"], "greseli": [w["camp"] for w in v["detalii"]]}
                                              for t, v in ag["scor"].items()}}
        if st["stare"] == "gata":
            c = st["comparatie"]
            out["studiu"]["om_timp"] = m(c["om_secunde_medie"], "s (medie)", src, d, nota=f"{len(st['participanti'])} participanți")
            out["studiu"]["om_greseli"] = m(c["om_greseli_medie"], "câmpuri greșite (medie)", src, d)
            out["studiu"]["raport"] = m(c["raport"], "× mai rapid agentul", src, d)
        else:
            out["studiu"]["om_timp"] = lipsa("s", "în așteptare: colegii n-au completat încă docs/studiu-timp/date/*.csv")
    else:
        out["studiu"] = {"stare": "în așteptare", "om_timp": lipsa("s", "nu există docs/studiu-timp/rezultat.json (scripts/impact_studiu.py)")}
    return out


def main() -> None:
    smoke_out, time_out = smoke()
    data = {"generat": datetime.now(timezone.utc).isoformat(timespec="seconds"), "generator": "scripts/build_results.py",
            "citire": extraction(), "cost": cost(), "timp": time_out | {"manual": manual_estimate()},
            "stabilitate": smoke_out, "siguranta": safety(), "date_reale": real_data(), "invatare": lessons(),
            "impact": impact()}
    text = json.dumps(data, ensure_ascii=False, indent=1)
    OUT.write_text(text + "\n", encoding="utf-8")
    OUT_JS.write_text("// generat de scripts/build_results.py; aceleași date ca results.json (pentru deschidere din fișier)\n"
                      f"window.RESULTS_DATA = {text};\n", encoding="utf-8")
    print(f"scris {rel(OUT)} și {rel(OUT_JS)} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
