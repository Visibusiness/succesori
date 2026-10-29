#!/usr/bin/env python3
"""Documentele generate de bancă (agent/generated_docs.py + ops-ui/doc-actions.js), verificate în Chromium: la Maria Ionescu
după pașii 1–2 și la clienții din portofoliu, fiecare document din GET /cases/{id}/generated are „Previzualizează” și
„Descarcă” în dosarul complet (#dosare/<id>); previzualizarea se deschide (iframe 200 application/pdf, apoi textul), Esc o
închide; descărcarea dă un fișier valid (%PDF-, numele din listă); fără erori JS; temele deschisă și întunecată; 390×844
fără scroll orizontal. În flux (demo-manual.js), previzualizarea scrisorii de la poarta notarului e aceeași fereastră.

  .venv/bin/python scripts/ui_documente_generate.py http://127.0.0.1:8044 /tmp/documente-generate [--prepare]

--prepare (doar pe o instanță izolată, coordonare/bin/test-instance start 8044): reset în modul pas cu pas, pașii 1 și 2 ai
Mariei (extractorul și corespondentul pe Bedrock), verificarea fluxului cu poarta scrisorii deschisă, apoi scrisoarea
aprobată (pleacă PDF-ul semnat) și auditorul. Fără --prepare se verifică starea existentă.
Playwright din .venv, /usr/bin/chromium --no-sandbox. Ieșire: JSON cu rezultatele + cod 0 (PASS) / 1 (FAIL).
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

API, OUT = sys.argv[1].rstrip("/"), Path(sys.argv[2])
PREPARE = "--prepare" in sys.argv
CASES = ["SC-2026-0001", "SC-2026-0102", "SC-2026-0104", "SC-2026-0107", "SC-2026-0110"]
MARIA = CASES[0]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "descarcari").mkdir(exist_ok=True)
fails: list[str] = []
report: dict = {"cases": {}, "flow": None, "page_errors": []}


def api(method, path, body=None, timeout=30):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def check(ok, what):
    if not ok:
        fails.append(what)
    return ok


def run_step(n, until=("done", "awaiting"), timeout=420):
    api("POST", f"/demo/ai/pipeline/{n}/run")
    t = time.time()
    while time.time() - t < timeout:
        st = api("GET", "/demo/ai/steps")[str(n)]
        if st["pipeline"]["status"] in until or st["pipeline"]["status"] == "failed":
            return st
        time.sleep(2)
    raise SystemExit(f"pasul {n} nu s-a terminat în {timeout} s")


def wait_jobs(timeout=420):
    t = time.time()
    while time.time() - t < timeout and any(j["status"] in ("queued", "running") for j in api("GET", "/demo/ai/jobs")):
        time.sleep(2)


def open_section(page, key):
    sec = page.locator(f"#dsec-{key}")
    if sec.count() and sec.get_attribute("open") is None:
        sec.locator("> summary").click()
    return sec


def no_hscroll(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


def check_preview(page, d, pdf_responses, shot=None):
    """Opens the preview of one document, checks the PDF response and the text view, closes with Esc."""
    n = len(pdf_responses)
    page.locator(f".gdocs[data-gdocs=toate] .doc-actions[data-doc='{d['id']}'] button.doc-preview").click()
    page.wait_for_selector(".modal.mdv", timeout=10000)
    ok_pdf = True
    if page.locator(".modal.mdv iframe").count():
        t = time.time()
        while len(pdf_responses) == n and time.time() - t < 10:
            page.wait_for_timeout(200)
        got = pdf_responses[n:]
        ok_pdf = check(bool(got) and all(s == 200 and (ct or "").startswith("application/pdf") for _, s, ct in got),
                       f"{d['case_id']} {d['title']}: iframe PDF {got}")
        if shot:
            page.wait_for_timeout(1200)   # the window fades in (demo.css), the PDF viewer draws
            page.screenshot(path=str(shot).replace(".png", "-pdf.png"))
    if page.locator(".mdv-seg button[data-view=text]").count():
        page.click(".mdv-seg button[data-view=text]")
    page.wait_for_selector(".modal.mdv .mdv-text .md", timeout=10000)
    ok_text = check(page.locator(".modal.mdv .mdv-text .md").inner_text().strip() != "", f"{d['case_id']} {d['title']}: textul gol")
    dl = page.locator(".modal.mdv a.mdv-download")
    ok_dl = check(dl.get_attribute("download") == d["filename"], f"{d['case_id']} {d['title']}: numele descărcării în fereastră")
    ok_scroll = check(no_hscroll(page), f"{d['case_id']}: scroll orizontal cu fereastra deschisă")
    if shot:
        page.wait_for_timeout(450)
        page.screenshot(path=str(shot))
    page.keyboard.press("Escape")
    page.wait_for_selector(".modal.mdv", state="detached", timeout=5000)
    return ok_pdf and ok_text and ok_dl and ok_scroll


def check_download(page, d):
    with page.expect_download() as info:
        page.locator(f".gdocs[data-gdocs=toate] .doc-actions[data-doc='{d['id']}'] a.doc-download").click()
    dl = info.value
    path = OUT / "descarcari" / dl.suggested_filename
    dl.save_as(str(path))
    data = path.read_bytes()
    return check(dl.suggested_filename == d["filename"] and data.startswith(b"%PDF-") and len(data) > 800,
                 f"{d['case_id']} {d['title']}: descărcarea {dl.suggested_filename} ({len(data)} B)")


def check_case(page, cid, theme, mobile, full, pdf_responses):
    docs = api("GET", f"/cases/{cid}/generated")
    tag = f"{cid}-{theme}-{'mobil' if mobile else 'desktop'}"
    page.goto(f"{API}/ui/#dosare/{cid}", wait_until="networkidle")
    page.wait_for_selector("#dsec-gen", timeout=15000)
    sec = open_section(page, "gen")
    sec.locator(".gdocs").first.wait_for(timeout=10000)
    page.wait_for_function("() => !document.querySelector('#dsec-gen .gdocs p.muted.small')", timeout=10000)
    rows = sec.locator(".gdoc")
    res = {"documents": len(docs), "rows": rows.count(), "kinds": sorted({d["kind"] for d in docs})}
    check(rows.count() == len(docs), f"{tag}: {rows.count()} rânduri pentru {len(docs)} documente")
    both = sum(1 for d in docs if sec.locator(f".doc-actions[data-doc='{d['id']}'] button.doc-preview").count() == 1
               and sec.locator(f".doc-actions[data-doc='{d['id']}'] a.doc-download").count() == 1)
    res["with_both_buttons"] = both
    check(both == len(docs), f"{tag}: doar {both}/{len(docs)} documente au ambele butoane")
    # the same documents in their own sections: letters and messages, agents, payment, escalations, journal
    for key, group in (("letters", "corr"), ("agents", "ai"), ("plan", "pay")):
        want = [d for d in docs if d["group"] == group]
        if not want or not page.locator(f"#dsec-{key}").count():
            continue
        s = open_section(page, key)
        page.wait_for_timeout(300)
        got = sum(1 for d in want if s.locator(f".doc-actions[data-doc='{d['id']}'] button.doc-preview").count() >= 1)
        res[f"in_{key}"] = f"{got}/{len(want)}"
        check(got == len(want), f"{tag}: secțiunea {key} are {got}/{len(want)} documente cu butoane")
    esc_docs = [d for d in docs if d.get("escalation_id")]
    if esc_docs:
        s = open_section(page, "esc")
        page.wait_for_timeout(300)
        got = sum(1 for d in esc_docs if s.locator(f".doc-actions[data-doc='{d['id']}']").count() >= 1)
        res["in_esc"] = f"{got}/{len(esc_docs)}"
        check(got == len(esc_docs), f"{tag}: escaladările au {got}/{len(esc_docs)} propuneri cu butoane")
    ev_docs = [d for d in docs if d.get("event_id")]
    if ev_docs:
        s = open_section(page, "journal")
        page.wait_for_timeout(400)
        got = sum(1 for d in ev_docs if s.locator(f".doc-actions[data-doc='{d['id']}']").count() >= 1)
        res["in_journal"] = f"{got}/{len(ev_docs)}"
        check(got == len(ev_docs), f"{tag}: jurnalul are {got}/{len(ev_docs)} documente cu butoane")
    res["no_hscroll"] = check(no_hscroll(page), f"{tag}: scroll orizontal")
    sec.scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / f"{tag}-lista.png"), full_page=not mobile)
    if full:   # every document: preview + download
        res["previews_ok"] = sum(check_preview(page, d, pdf_responses, OUT / f"{tag}-{d['filename'][:-4]}.png" if i == 0 else None)
                                 for i, d in enumerate(docs))
        res["downloads_ok"] = sum(check_download(page, d) for d in docs)
    elif docs:   # the first one, in this theme / size
        res["previews_ok"] = int(check_preview(page, docs[0], pdf_responses, OUT / f"{tag}-previzualizare.png"))
    return res


def check_flow(page, pdf_responses):
    """The guided demo's flow (demo-manual.js): the letter at the notary gate opens in the same window (openDocPreview)."""
    page.goto(f"{API}/ui/#demo/{MARIA}", wait_until="networkidle")
    page.wait_for_timeout(1500)
    if not page.locator(".modal").count():   # fereastra de trimitere a scrisorii se deschide singură (repara-notar)
        page.locator('#view-demo [aria-label^="Pasul 2:"]').first.click()   # pasul 2: adresa notarului -> scrisoarea
    page.wait_for_timeout(1000)
    btn = page.locator("#view-demo button.doc-preview")
    if not check(btn.count() >= 1, "fluxul Mariei: niciun buton Previzualizează la poarta scrisorii"):
        page.screenshot(path=str(OUT / "flux-fara-buton.png"))
        return {"ok": False}
    dialog = page.locator(".modal:not(.mdv)")   # a pending letter opens its send dialog (mConfirmSend), with its own preview
    in_dialog = dialog.count() > 0 and dialog.locator("button.doc-preview").count() > 0
    n = len(pdf_responses)
    (dialog.locator("button.doc-preview") if in_dialog else btn).first.click()
    page.wait_for_selector(".modal.mdv", timeout=10000)
    t = time.time()
    while len(pdf_responses) == n and time.time() - t < 10:
        page.wait_for_timeout(200)
    got = pdf_responses[n:]
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "flux-maria-poarta-notar.png"))
    ok = check(page.locator(".modal.mdv iframe").count() == 1 and bool(got) and all(s == 200 for _, s, _ in got),
               f"fluxul Mariei: previzualizarea scrisorii {got}")
    page.keyboard.press("Escape")
    page.wait_for_selector(".modal.mdv", state="detached", timeout=5000)
    if in_dialog:   # Esc closed only the preview: the send dialog is still there
        ok = check(page.locator(".modal:not(.mdv)").count() > 0, "fluxul Mariei: Esc a închis și dialogul de trimitere") and ok
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    return {"ok": ok, "responses": got, "in_send_dialog": in_dialog}


with sync_playwright() as p:
    if PREPARE:
        api("POST", "/demo/reset?variants=pensie&manual=true")
        report["step1"] = run_step(1)["pipeline"]
        report["step2"] = run_step(2)["pipeline"]
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    for theme in ("light", "dark"):
        for mobile in (False, True):
            ctx = b.new_context(viewport={"width": 390, "height": 844} if mobile else {"width": 1440, "height": 1000},
                                device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile, accept_downloads=True)
            ctx.add_init_script(f"try {{ if (location.protocol.startsWith('http')) {{ localStorage.setItem('theme', '{theme}'); "
                                "localStorage.setItem('demoMode', 'manual'); } } catch (e) {}")
            page = ctx.new_page()
            pdfs: list = []
            page.on("pageerror", lambda e, t=f"{theme}/{mobile}": report["page_errors"].append(f"{t}: {e}"))
            page.on("console", lambda m, t=f"{theme}/{mobile}": report["page_errors"].append(f"{t} console: {m.text}") if m.type == "error" else None)
            page.on("response", lambda r, pdfs=pdfs: pdfs.append((r.url, r.status, r.headers.get("content-type")))
                    if "format=pdf" in r.url or r.url.endswith("/pdf") else None)
            if theme == "light" and not mobile:
                report["flow"] = check_flow(page, pdfs)
            if PREPARE and theme == "light" and not mobile:
                gate = next((g for g in api("GET", "/demo/ai/steps")["2"]["gates"].values() if g["kind"] == "letter"), None)
                if gate and gate["status"] == "pending":
                    api("POST", f"/demo/ai/gate/2/{gate['key']}/approve", {"by": "Ioana Marin (test UI)"})
                api("POST", "/demo/ai/audit")
                wait_jobs()
            for cid in CASES:
                key = f"{cid} {theme} {'390x844' if mobile else '1440x1000'}"
                report["cases"][key] = check_case(page, cid, theme, mobile, full=theme == "light" and not mobile, pdf_responses=pdfs)
            ctx.close()
    b.close()

check(not report["page_errors"], f"erori JS: {report['page_errors'][:5]}")
report["fails"] = fails
report["result"] = "PASS" if not fails else "FAIL"
print(json.dumps(report, ensure_ascii=False, indent=1))
sys.exit(0 if not fails else 1)
