#!/usr/bin/env python3
"""083 · docs/scalabilitate.json from the measurements in runs/scala/ and the volume / cost assumptions.

  .venv/bin/python scripts/scala_report.py
Target: kb/data/estimare-volum-cost.md (I1 × I4), 7 documents per case (demo scenario), ×5 peak (083).
Cost: docs/pitch/cost-per-dosar.md (2,35 $ measured, 1,4–2,4 $ range, ≈ 1 $ optimized).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs" / "scala"
OUT = ROOT / "docs" / "scalabilitate.json"

DEATHS_YEAR = 240_000                 # INS, I1
PEAK_MONTH = 23_600                   # INS, ian 2025 (kb/data/ins-decese.md)
SHARE = {"prudent": 0.07, "central": 0.10, "optimist": 0.14}   # I4
DOCS_PER_CASE = 7
LLM_DOCS_PER_CASE = 6                 # the DGEP line is a structured feed, it needs no extraction
WORK_HOURS_YEAR = 250 * 8
PEAK = 5
USD_PER_CASE = {"masurat": 2.35, "interval_min": 1.4, "interval_max": 2.4, "optimizat": 1.0}
LEI_PER_USD = 4.5


def load(name: str) -> dict:
    p = RUNS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    target = {}
    for k, share in SHARE.items():
        cases = round(DEATHS_YEAR * share)
        docs = cases * DOCS_PER_CASE
        avg_h = docs / WORK_HOURS_YEAR
        dgep_week_peak = PEAK_MONTH * share / (30.4 / 7)
        target[k] = {"dosare_an": cases, "documente_an": docs, "documente_zi_lucratoare": round(docs / 250),
                     "documente_ora_medie": round(avg_h), "documente_ora_varf_x5": round(avg_h * PEAK),
                     "documente_llm_ora_varf_x5": round(cases * LLM_DOCS_PER_CASE / WORK_HOURS_YEAR * PEAK),
                     "semnale_dgep_saptamana_medie": round(cases / 52),
                     "semnale_dgep_lot_varf": round(dgep_week_peak),
                     "semnale_dgep_lot_varf_x5": round(dgep_week_peak * PEAK)}
    logic = {n: load(f"logic-{n}.json") for n in (1000, 10000)}
    api = load("api-batch70.json")
    api_one = load("api-700-un-dosar.json")
    race = load("race-implicit.json")
    ai = load("ai.json")
    ai_levels = [{k: v for k, v in lv.items() if k != "calls"} for lv in ai.get("levels", [])]
    best_ai = max((lv for lv in ai_levels if lv.get("ok")), key=lambda lv: lv["docs_per_hour"], default=None)
    w = target["optimist"]["documente_llm_ora_varf_x5"]
    out = {
        "generat": date.today().isoformat(), "sursa": "scripts/scala_report.py din runs/scala/*.json (sarcina 083)",
        "masina": "1 VM, 6 vCPU, 16 GB RAM (aceeași cu MVP-ul și sesiunile echipei)",
        "tinta": {"ipoteze": {"decese_an": DEATHS_YEAR, "luna_varf_INS": PEAK_MONTH, "cota_clienti": SHARE,
                              "documente_dosar": DOCS_PER_CASE, "documente_cu_llm_dosar": LLM_DOCS_PER_CASE,
                              "ore_lucru_an": WORK_HOURS_YEAR, "factor_varf": PEAK,
                              "sursa": "kb/data/estimare-volum-cost.md, kb/data/ins-decese.md, kb/bank-procedures/dgep-arb-acord.md"},
                  "scenarii": target},
        "logica": {n: {k: v for k, v in d.items() if k != "buckets"} for n, d in logic.items() if d},
        "api": {"loturi_resetate_la_70": api.get("levels"), "un_singur_dosar_700_documente": api_one.get("levels"),
                "date": api.get("date"), "sursa": api.get("source")},
        "concurenta_fara_lock": race,
        "ai": {"levels": ai_levels, "model_id": ai.get("model_id"), "retries": ai.get("retries"), "date": ai.get("date"),
               "sursa": ai.get("source")},
        "concluzie": {
            "logica_dosare_pe_s_10000": logic[10000].get("cases_per_s") if logic[10000] else None,
            "logica_dosare_pe_s_1000": logic[1000].get("cases_per_s") if logic[1000] else None,
            "api_cereri_pe_s_max": max((lv["req_per_s"] for lv in api.get("levels", [])), default=None),
            "ai_documente_ora_max": best_ai and best_ai["docs_per_hour"],
            "ai_concurenta_la_max": best_ai and best_ai["concurrency"],
            "tinta_documente_llm_ora_varf_x5_optimist": w,
            "rezerva_ai_x": round(best_ai["docs_per_hour"] / w, 1) if best_ai else None,
        },
        "cost": {s: {"dosare_an": target[s]["dosare_an"],
                     **{f"usd_an_{k}": round(target[s]["dosare_an"] * v) for k, v in USD_PER_CASE.items()},
                     "lei_an_masurat": round(target[s]["dosare_an"] * USD_PER_CASE["masurat"] * LEI_PER_USD)}
                 for s in SHARE} | {"sursa": "docs/pitch/cost-per-dosar.md", "curs_lei_usd": LEI_PER_USD},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"tinta": target, "concluzie": out["concluzie"], "cost": out["cost"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
