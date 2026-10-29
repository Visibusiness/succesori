#!/usr/bin/env python3
"""Browser check after scripts/smoke_e2e.py: ops-ui shows Maria's case with the smoke's values in every tab, and the
console stays clean (no errors, no failed requests). Screenshots in runs/e2e/.

Usage:  .venv/bin/python scripts/ui_e2e.py [--api http://localhost:8001] [--out runs/e2e] [--prefix ui]
Needs Playwright (in .venv) and /usr/bin/chromium. Read-only: the page only does GETs (any other request is a FAIL).
Exit code 0 only if every check passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CASE = "SC-2026-0001"
# what each tab must show after the smoke (values from kb/scenariu-demo/maria-ionescu.md, formatted as in ops-ui)
TABS = {
    "Cronologie": ["Plata aprobată"],
    "Documente": ["Semnal DGEP", "Certificat de moștenitor", "Certificat suplimentar"],
    "Plan de plată": ["3.295,85 lei", "988,76 lei", "13.150,00 lei", "3.945,00 lei", "5.273,37 lei", "2.100,00 lei"],
    "Corespondență": ["notar", "supliment", "asigur"],
    "Audit": ["Audit"],
}
VIEWS = [("cases", "dosare", [CASE, "Maria"]), ("intake", "intrare", []), ("agents", "agenti", []), ("impact", "impact", [])]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8001")
    ap.add_argument("--out", default=str(ROOT / "runs" / "e2e"))
    ap.add_argument("--prefix", default="ui")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, bool, str]] = []
    console: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, ok, detail[:160]))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  {'' if ok else detail}", flush=True)

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: m.type == "error" and console.append(f"console: {m.text}"))
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: console.append(f"requestfailed: {r.method} {r.url} {r.failure}"))
        page.on("response", lambda r: r.status >= 400 and console.append(f"http {r.status}: {r.request.method} {r.url}"))
        page.on("request", lambda r: r.method not in ("GET", "HEAD") and console.append(f"non-GET: {r.method} {r.url}"))
        page.goto(a.api.rstrip("/") + "/ui/", wait_until="networkidle")
        page.wait_for_timeout(1500)
        for view, name, expect in VIEWS:
            page.evaluate(f"showView('{view}')")
            page.wait_for_timeout(900)
            text = page.inner_text(f"#view-{view}")
            missing = [e for e in expect if e not in text]
            check(f"ecran {name}", page.is_visible(f"#view-{view}") and not missing, f"lipsește {missing}")
            page.screenshot(path=str(out / f"{a.prefix}-{name}.png"), full_page=True)
        page.evaluate("showView('cases')")
        row = page.locator("#queue tr.row", has_text=CASE).first
        row.click()
        page.wait_for_timeout(1500)
        head = page.inner_text("#detail")
        check("dosar deschis: Maria Ionescu, PAID", "Maria" in head and CASE in head and ("Plătit" in head or "PAID" in head),
              head[:200])
        for tab, expect in TABS.items():
            page.locator(".tabs .tab", has_text=tab).first.click()
            page.wait_for_timeout(1200)
            text = page.inner_text("#detail .tabpanel")
            missing = [e for e in expect if e.lower() not in text.lower()]
            check(f"tab {tab}", not missing, f"lipsește {missing}")
            slug = tab.lower().replace(" ", "-").translate(str.maketrans("ăâîșțţş", "aaistts"))
            page.screenshot(path=str(out / f"{a.prefix}-dosar-{slug}.png"), full_page=True)
        b.close()
    check("consolă fără erori, fără cereri eșuate, doar GET", not console, "; ".join(console))
    (out / f"{a.prefix}-log.json").write_text(json.dumps({"rows": rows, "console": console}, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    failed = sum(not ok for _, ok, _ in rows)
    print(f"\n{len(rows) - failed}/{len(rows)} PASS · capturi în {out}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
