#!/usr/bin/env python3
"""Fluxul Mariei din lista de dosare, pasul 2 (adresa notarului): fereastra de semnare și trimitere se deschide singură,
cu PDF-ul inline, și pe drumurile navigării noi (Dosare = ecranul principal), nu doar când stai pe pas.

Regresia prinsă: fluxul deschis din listă (rândul Mariei, „← Înapoi la dosare” / Esc și înapoi, reîncărcarea, #demo/<id>)
se deschidea pe pasul de DUPĂ cel care așteaptă (demo.open = demo.step + 1), iar fereastra se caută doar pe pasul deschis:
nu apăreau nici fereastra, nici „Previzualizează”, nici butoanele opririi „Rândul tău”.

Scenariul (agenți reali pe Bedrock, ~3-6 min):
  1. reset pas cu pas; /ui/ → rândul Mariei → „▶ Procesează” pasul 1 → gata
  2. nodul 2 din roadmap → „▶ Procesează” → imediat „← Înapoi la dosare”; când regulile pasului 2 sunt aplicate (scrisoarea
     încă se scrie) → rândul Mariei din nou: fluxul trebuie să fie pe pasul 2, iar fereastra să se deschidă singură
  3. „Înapoi (nu trimit acum)” → reîncărcare pe #demo/SC-2026-0001: fereastra se redeschide pe pasul 2
  4. „Înapoi” → „Previzualizează” (PDF-ul în fereastra mare) → „✔ Verifică și trimite…” → „Trimite” inactiv fără bifă →
     bifa + nume → „Trimite”: API-ul arată răspunsul semnat, outbox-ul (GET /messages) scrisoarea cu PDF
  5. pasul 3 se poate porni (butonul „▶ Procesează” activ); zero erori JS; capturi în ambele teme

Doar pe o instanță izolată (CLAUDE.md: niciodată pe :8001):
  coordonare/bin/test-instance start 8042
  .venv/bin/python scripts/ui_notar_trimitere.py --api http://127.0.0.1:8042 [--out /tmp/repara-notar]
  coordonare/bin/test-instance stop 8042
Cod 0 doar dacă toate verificările trec.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

CASE = "SC-2026-0001"
APPROVER = "Ana Operator QA"
AI_TIMEOUT = 360


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--out", default="/tmp/repara-notar")
    ap.add_argument("--chromium", default="/usr/bin/chromium")
    a = ap.parse_args()
    api = a.api.rstrip("/")
    if api.endswith(":8001") or api.endswith(":8000"):
        print("refuz: :8000/:8001 sunt serverele oamenilor; pornește coordonare/bin/test-instance")
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fails: list[str] = []
    errors: list[str] = []

    def http(path: str, method: str = "GET"):
        req = urllib.request.Request(api + path, method=method, data=b"" if method == "POST" else None)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"null")

    def check(name: str, ok: bool, detail: str = "") -> bool:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": {detail}"))
        if not ok:
            fails.append(name)
        return ok

    def step(n: int) -> dict:
        return http("/demo/ai/steps").get(str(n), {})

    def wait(pred, what: str, timeout: float = AI_TIMEOUT) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if pred():
                return True
            time.sleep(2)
        return check(what, False, f"nimic după {timeout:.0f} s")

    def snap(page: Page, name: str) -> None:
        page.screenshot(path=str(out / f"{name}.png"))

    def pdf_shown(page: Page, sel: str) -> bool:
        """Iframe-ul a încărcat chiar un PDF (același origin: contentType-ul documentului din el), apoi lasă vizualizatorul
        să deseneze pagina și animația ferestrei să se termine, ca să se vadă scrisoarea în captură."""
        try:
            page.wait_for_function(f"() => document.querySelector({json.dumps(sel)})?.contentDocument?.contentType === 'application/pdf'",
                                   timeout=15000)
        except Exception:  # noqa: BLE001
            return False
        page.wait_for_timeout(2500)
        return True

    def open_maria(page: Page) -> None:
        page.locator(f".wl-rows li[data-case='{CASE}']").first.click()
        page.wait_for_selector(".d-hero", timeout=10000)

    http("/demo/reset?variants=pensie&manual=true", "POST")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=a.chromium, args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 1400, "height": 1000})
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
        page.add_init_script("try { if (window.top === window) localStorage.setItem('theme', 'light'); } catch (e) {}")
        page.goto(api + "/ui/")
        page.wait_for_selector(f".wl-rows li[data-case='{CASE}']", timeout=15000)
        snap(page, "01-lista")
        open_maria(page)

        # 1. pasul 1 (semnalul DGEP): fără opriri la om
        page.locator(".d-hero button.pipe.run").click()
        wait(lambda: step(1).get("next", {}).get("do") == "done" and step(1).get("pipeline", {}).get("status") not in
             ("running", "stopping"), "pasul 1 procesat")
        page.wait_for_timeout(1500)
        snap(page, "02-pas1-gata")

        # 2. pasul 2 pornit, ieșit din flux cât lucrează agenții, revenit din listă
        page.locator(".rm-node .rm-dot").nth(1).click()
        page.locator(".d-hero button.pipe.run").click()
        page.wait_for_timeout(800)
        page.locator(".flow-back-btn").click()
        wait(lambda: bool(step(2).get("result")), "pasul 2: regulile aplicate")
        open_maria(page)
        page.wait_for_timeout(1500)
        check("re-intrat din listă cât pasul 2 lucrează: fluxul e pe pasul 2", page.evaluate("demo.open") == 2,
              f"demo.open = {page.evaluate('demo.open')}")
        wait(lambda: any(g["status"] == "pending" and g["kind"] == "letter" for g in (step(2).get("gates") or {}).values()),
             "pasul 2: scrisoarea către notar așteaptă semnarea")
        modal = page.locator(".modal .send-card")
        try:
            modal.wait_for(timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        shown = modal.count() > 0 and pdf_shown(page, ".modal .send-card iframe.send-pdf")
        snap(page, "03-pas2-fereastra")
        if check("pasul 2: fereastra de semnare și trimitere se deschide singură", modal.count() > 0,
                 f"fără fereastră; demo.open = {page.evaluate('demo.open')}, opriri pe ecran = "
                 f"{page.locator('.station.gate.pending').count()}"):
            check("fereastra: PDF-ul inline, încărcat ca PDF", shown, "iframe-ul nu are un PDF")
            src = modal.locator("iframe.send-pdf").get_attribute("src") or ""
            with urllib.request.urlopen(src, timeout=30) as r:
                check("fereastra: PDF-ul răspunde ca application/pdf", "pdf" in r.headers.get("content-type", ""),
                      r.headers.get("content-type", ""))
            check("fereastra: destinatarul afișat", "@" in modal.locator(".send-meta").inner_text(), "fără adresă")
            modal.get_by_role("button", name="Înapoi (nu trimit acum)").click()

        # 3. reîncărcare pe deep-link-ul fluxului: fereastra revine pe pasul 2
        page.goto(api + f"/ui/#demo/{CASE}")
        page.reload()
        try:
            modal.wait_for(timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        check("reîncărcat pe #demo/SC-2026-0001: fluxul pe pasul 2", page.evaluate("demo.open") == 2,
              f"demo.open = {page.evaluate('demo.open')}")
        check("reîncărcat: fereastra de trimitere se redeschide", modal.count() > 0, "fără fereastră")
        if modal.count():
            page.evaluate("document.documentElement.dataset.theme = 'dark'")
            pdf_shown(page, ".modal .send-card iframe.send-pdf")
            snap(page, "03b-reincarcat-fereastra-dark")
            page.evaluate("document.documentElement.dataset.theme = 'light'")
            modal.get_by_role("button", name="Înapoi (nu trimit acum)").click()

        # 4. poarta „Rândul tău”: Previzualizează, apoi Verifică și trimite
        gate = page.locator(".station.gate.pending")
        if check("pasul 2: oprirea „Rândul tău” pe ecran", gate.count() == 1, f"{gate.count()} opriri"):
            gate.get_by_role("button", name="Previzualizează").click()
            ok = pdf_shown(page, ".modal.mdv iframe")
            snap(page, "04-previzualizeaza")
            check("„Previzualizează” deschide PDF-ul", ok, "fără PDF în fereastra mare")
            page.locator(".modal.mdv button.mdv-close").click()
            gate.get_by_role("button", name="✔ Verifică și trimite…").click()
            modal.wait_for(timeout=8000)
            send = modal.locator("button.primary")
            check("„Trimite” inactiv fără bifă", send.is_disabled(), "activ fără bifă")
            modal.locator("input[type=checkbox]").check()
            modal.locator("input[type=text]").fill(APPROVER)
            pdf_shown(page, ".modal .send-card iframe.send-pdf")
            snap(page, "05-gata-de-trimis")
            send.click()
            wait(lambda: any(g["status"] == "approved" for g in (step(2).get("gates") or {}).values()), "scrisoarea aprobată", 30)
            case = http(f"/cases/{CASE}")
            check("API: răspunsul către notar semnat de operator",
                  any("Răspunsul către notar semnat de " + APPROVER in (e.get("text") or e.get("message") or json.dumps(e, ensure_ascii=False))
                      for e in case.get("events", [])), "fără evenimentul de semnare")
            msgs = [m for m in http(f"/messages?case_id={CASE}") if m.get("kind") == "letter"]
            check("outbox: scrisoarea către notar, cu PDF, aprobată de operator",
                  any(m.get("approved_by") == APPROVER and str(m.get("attachment_path", "")).endswith(".pdf") for m in msgs),
                  json.dumps(msgs, ensure_ascii=False)[:300])
            page.wait_for_timeout(5000)
            snap(page, "06-trimisa")

        # 5. pasul 3 se poate porni
        wait(lambda: step(2).get("pipeline", {}).get("status") not in ("running", "awaiting", "stopping"), "pipeline-ul pasului 2 s-a încheiat", 120)
        page.locator(".rm-node .rm-dot").nth(2).click()
        page.wait_for_timeout(800)
        run3 = page.locator(".d-hero button.pipe.run")
        check("pasul 3 se poate porni", run3.count() == 1 and run3.is_enabled(), "fără „▶ Procesează” activ")
        snap(page, "07-pas3-light")
        page.evaluate("document.documentElement.dataset.theme = 'dark'")
        page.wait_for_timeout(500)
        snap(page, "08-pas3-dark")
        b.close()

    check("zero erori JS", not errors, "; ".join(errors[:5]))
    print(f"\n{'OK' if not fails else 'EȘUAT'}: {len(fails)} verificări picate; capturi în {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
