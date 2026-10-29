#!/usr/bin/env python3
"""090: ops-ui, Dosare -> client -> Dosarul complet -> Documente -> vizualizatorul (PDF-ul + câmpurile citite), pentru 4 clienți din
portofoliu; capturi și PASS/FAIL (fiecare previzualizare 200 application/pdf, în fereastră, fără erori JS).

  .venv/bin/python scripts/ui_portfolio_docs.py http://127.0.0.1:8078 runs/docs-portofoliu     # doar pe o instanță izolată

Playwright din .venv, /usr/bin/chromium --no-sandbox.
"""
import json, sys
from playwright.sync_api import sync_playwright
API, OUT = sys.argv[1], sys.argv[2]
CLIENTS = [("Ioan Georgescu", "P05-D4"), ("Constantin Marinescu", "P03-D4"), ("Nicolae Stan", "P10-D6"), ("Marin Petrescu", "P13-D2")]
res = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errs, previews = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("response", lambda r: previews.append((r.url, r.status, r.headers.get("content-type"))) if "/preview" in r.url else None)
    page.goto(API + "/ui/", wait_until="networkidle")
    for name, doc_id in CLIENTS:
        # UI-ul de după demo-gestiune: rândul din listă -> fluxul -> „Deschide dosarul complet” -> secțiunea Documente -> vizualizatorul
        page.click("button.nav-btn[data-view=cases]")
        page.wait_for_selector(".wl-row")
        page.click(f".wl-row:has-text('{name}')")
        page.click(".case-cta")
        sec = page.locator("#dsec-docs")
        if sec.get_attribute("open") is None:
            sec.locator("> summary").click()
        n = len(previews)
        page.click(f".doc-row[data-doc='{doc_id}']")
        page.wait_for_selector(".modal iframe", timeout=15000)
        page.wait_for_timeout(2500)
        shot = f"{OUT}/{doc_id}-{name.split()[-1].lower()}.png"
        page.screenshot(path=shot)
        got = previews[n:]
        res.append({"client": name, "doc": doc_id, "responses": got, "iframe": page.locator(".modal iframe").count(), "shot": shot})
        page.click(".modal button:has-text('Închide')")
    b.close()
print(json.dumps({"results": res, "page_errors": errs}, ensure_ascii=False, indent=1))
ok = all(r["iframe"] == 1 and r["responses"] and all(s == 200 and (t or "").startswith("application/pdf") for _, s, t in r["responses"]) for r in res)
sys.exit(0 if ok and not errs else 1)
