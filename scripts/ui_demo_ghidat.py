#!/usr/bin/env python3
"""„Demo ghidat” (ops-ui/demo.js, demo-manual.js, demo-look.js, live.js) cap-coadă în Chromium, ca la pitch: fiecare pas
cu captură, erori din consolă, cereri eșuate, durată și cifrele afișate față de kb/scenariu-demo/maria-ionescu.md.

Scenarii (--scenarios, în ordinea dată; implicit toate):
  manual-statii   pas cu pas, varianta A, scanate: fiecare apel AI pornit din butonul stației; tastele → ← spațiu;
                  „↺ De la zero” după pasul 3, apoi pașii 1–7; scrisori/mesaje aprobate în fereastra de verificare,
                  plata aprobată cu nume (dialogul de confirmare)
  wow-pauza       momentele „wow” din ghid (A01, fotografia), încărcate cât demo-ul e în modul pas cu pas
  manual-pipe-B   pas cu pas, varianta B (setată din JS: pagina nu mai are comutator), cu „▶ Start pasul n” pe fiecare pas
  auto-extrase    modul automat (setDemoMode('auto') din JS: pagina nu mai are comutator), pre-extrase, varianta A,
                  avans cu → și spațiu, „Aprobă plata”
  auto-scanate-B  modul automat, scanate, varianta B: 3 pași cu spațiu, „↺ De la zero”, apoi „▶ Derulează singur”
  wow             momentele „wow” cu autopilotul pornit: A01 (suspect), fotografia certificatului, scara de contact
                  (avansarea ceasului) în dosarul Mariei
  wow-scara-pas3  scara de contact pe dosarul oprit după pasul 3 (fără certificat de moștenitor: pașii 14/30/60)

Doar pe o instanță izolată (CLAUDE.md: niciodată pe :8001):
  coordonare/bin/test-instance start 8090
  .venv/bin/python scripts/ui_demo_ghidat.py --api http://127.0.0.1:8090 [--scenarios manual-statii,wow] [--out runs/demoqa]
  coordonare/bin/test-instance stop 8090
Ieșire: runs/demoqa/<scenariu>-NN-<pas>.png, runs/demoqa/log.json (fiecare verificare, durată, erori pe pas), cod 0 doar
dacă toate verificările trec. Agenții rulează pe Bedrock: o rulare completă durează ~1 h.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "ops-ui" / "_documente-demo"
CASE = "SC-2026-0001"
APPROVER = "Ana Operator QA"
AI_TIMEOUT = 300          # s: un apel AI (extractor / agent) pe Bedrock; peste asta e o problemă de pitch
SCENARIOS = ["manual-statii", "wow-pauza", "manual-pipe-B", "auto-extrase", "auto-scanate-B", "wow", "wow-scara-pas3"]

# cifrele din kb/scenariu-demo/maria-ionescu.md, formatate ca în ops-ui (fmtMoney: ro-RO, 2 zecimale, „ lei”)
EXPECT = {
    1: {"stare": "Blocat", "text": ["60,00 lei"]},
    2: {"stare": "Răspuns la notar", "text": ["3.200,00 lei", "20.000,00 lei", "692,38 lei"]},
    3: {"stare": "Daună deschisă", "text": []},
    4: {"stare": "Supliment cerut", "text": {"A": ["1/4", "3/8"], "B": ["1/2", "1/4"]}},
    5: {"stare": "Daună închisă", "text": ["9.000,00 lei", "26,63 lei"]},
    6: {"stare": "Plată de aprobat", "text": {"A": ["3.295,85 lei", "988,76 lei", "13.150,00 lei", "3.945,00 lei"],
                                              "B": ["3.955,03 lei", "659,17 lei", "15.780,00 lei", "2.630,00 lei"]}},
    7: {"stare": "Escaladat", "text": []},
}
# planul de plată (bani), din API: §2.4
PLAN = {"A": {"Ion": [329585, 1315000], "Andrei": [98876, 394500], "Elena": [98876, 394500]},
        "B": {"Ion": [395503, 1578000], "Andrei": [65917, 263000], "Elena": [65917, 263000]}}


class QA:
    def __init__(self, api: str, out: Path):
        self.api, self.out = api.rstrip("/"), out
        self.rows: list[dict] = []      # fiecare verificare
        self.steps: list[dict] = []     # fiecare pas: durată, erori, captură
        self.errors: list[str] = []     # erorile de la ultima bornă
        self.scn, self.n = "", 0

    # ---------- jurnal ----------
    def check(self, name: str, ok: bool, detail: str = "", severity: str = "") -> bool:
        self.rows.append({"scenario": self.scn, "check": name, "ok": bool(ok), "detail": detail[:400], "severity": severity})
        print(f"  {'PASS' if ok else 'FAIL'}  [{self.scn}] {name}  {'' if ok else detail[:300]}", flush=True)
        return ok

    def snap(self, page: Page, label: str, t0: float | None = None, extra: dict | None = None) -> str:
        self.n += 1
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower().translate(str.maketrans("ăâîșțşţ", "aaistst"))).strip("-")[:50]
        f = self.out / f"{self.scn}-{self.n:02d}-{slug}.png"
        page.screenshot(path=str(f), full_page=True)
        rec = {"scenario": self.scn, "label": label, "png": f.name, "seconds": round(time.time() - t0, 1) if t0 else None,
               "errors": self.errors, **(extra or {})}
        self.steps.append(rec)
        print(f"    · {label}: {rec['seconds']} s, {len(self.errors)} erori, {f.name}", flush=True)
        self.errors = []
        return f.name

    def hook(self, page: Page) -> None:
        page.on("console", lambda m: m.type == "error" and self.errors.append(f"console: {m.text}"))
        page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: "net::ERR_ABORTED" not in str(r.failure)
                and self.errors.append(f"requestfailed: {r.method} {r.url} {r.failure}"))
        page.on("response", lambda r: r.status >= 400 and self.errors.append(f"http {r.status}: {r.request.method} {r.url}"))

    # ---------- API (doar citire, pentru a compara ce se vede cu ce e în dosar) ----------
    def get(self, path: str):
        with urllib.request.urlopen(self.api + path, timeout=20) as r:
            return json.loads(r.read())

    def post(self, path: str):
        req = urllib.request.Request(self.api + path, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())


# ---------- utilitare de pagină ----------
def view_text(page: Page, sel: str = "#view-demo") -> str:
    return page.eval_on_selector(sel, "e => e.textContent") or ""


def visible_text(page: Page, sel: str = "#view-demo") -> str:
    return page.inner_text(sel)


def js(page: Page, expr: str):
    return page.evaluate(expr)


def wait_until(page: Page, cond, timeout: float, every: float = 1.0):
    end = time.time() + timeout
    while time.time() < end:
        v = cond()
        if v:
            return v
        page.wait_for_timeout(int(every * 1000))
    return None


def nsteps(page: Page) -> int:
    """Câți pași are povestea pe pagină (STORY din demo.js): au fost 7, demo-ul curent are 6 (fără certificatul ilizibil)."""
    return int(js(page, "STORY.length"))


def open_step(page: Page, n: int) -> None:
    page.locator(".rm-node .rm-dot").nth(n - 1).click()
    page.wait_for_timeout(400)


def srv(page: Page, n: int) -> dict:
    return js(page, f"(demo.srv[{n}] && {{next: demo.srv[{n}].next, pipe: demo.srv[{n}].pipeline, "
                    f"gates: Object.values(demo.srv[{n}].gates || {{}})}}) || null") or {}


def handle_send_modal(qa: QA, page: Page) -> bool:
    """Fereastra „Verifică scrisoarea/mesajul înainte să plece”: bifa, numele, Trimite."""
    m = page.locator(".modal .send-card")
    if not m.count():
        return False
    send = m.locator("button.primary")
    qa.check("fereastra de trimitere: „Trimite” inactiv înainte de bifă", send.is_disabled(), "butonul e activ fără bifă")
    m.locator("input[type=checkbox]").check()
    who = m.locator("input[type=text]")
    who.fill(APPROVER)
    send.click()
    page.wait_for_timeout(800)
    return True


def handle_gate(qa: QA, page: Page, n: int, g: dict) -> None:
    """O oprire la om pe pasul n, din butoanele paginii, cu numele operatorului."""
    if handle_send_modal(qa, page):
        return
    st = page.locator(".station.gate.pending").first
    st.scroll_into_view_if_needed()
    who = st.locator("input[aria-label='Numele tău']")
    if who.count():
        who.fill(APPROVER)
    st.locator(".gate-form button.primary").click()
    page.wait_for_timeout(700)
    if g["kind"] in ("letter", "message"):
        handle_send_modal(qa, page)
    elif g["kind"] == "payment":
        dlg = page.locator(".modal [aria-label='Confirmă aprobarea plății']")
        if qa.check("plata: dialogul de confirmare cu sumă și nume", dlg.count() > 0, "dialogul nu s-a deschis"):
            qa.snap(page, f"pas {n} dialog aprobare plata")
            dlg.locator("input").fill(APPROVER)
            dlg.locator("button.primary").click()
            page.wait_for_timeout(1200)


def run_manual_step(qa: QA, page: Page, n: int, how: str, variant: str) -> dict:
    """Un pas în modul pas cu pas. how=statii: fiecare stație din butonul ei; how=pipe: „▶ Start pasul n”."""
    open_step(page, n)
    t0 = time.time()
    qa.snap(page, f"pas {n} inainte")
    timings, started_pipe, last_do, since = [], False, None, time.time()
    while time.time() - t0 < 25 * 60:
        s = srv(page, n)
        nx = (s.get("next") or {}).get("do")
        pipe = (s.get("pipe") or {}).get("status")
        pend = [g for g in s.get("gates") or [] if g.get("status") == "pending"]
        if nx != last_do:
            last_do, since = nx, time.time()
        if pend:
            qa.snap(page, f"pas {n} oprire la om {pend[0]['kind']}")
            handle_gate(qa, page, n, pend[0])
            page.wait_for_timeout(1500)
            continue
        if nx == "done" and (how == "statii" or pipe in ("done", "idle", None)):
            break
        if nx in ("failed", "blocked") or pipe == "failed":
            qa.check(f"pasul {n} ({how}) ajunge la capăt", False, f"next={s.get('next')} pipeline={s.get('pipe')}", "blocant")
            break
        if how == "pipe":
            if not started_pipe:
                b = page.locator(".step-banner button.pipe.run")
                qa.check(f"pasul {n}: butonul „▶ Start pasul {n}”", b.count() > 0 and b.is_enabled(), "lipsește sau e inactiv")
                b.click()
                started_pipe = True
            page.wait_for_timeout(1500)
            continue
        if nx == "extract":
            page.locator(".station.ai button.run", has_text=re.compile("Pornește extractorul|Încearcă din nou")).first.click()
        elif nx == "apply":
            page.locator(".station.code button.run").first.click()
        elif nx == "agent":
            label = s["next"].get("label") or ""
            b = page.locator(".station.ai button.run", has_text=label)
            if not b.count():
                b = page.locator(".station.ai button.run", has_text=re.compile("Pornește|Încearcă din nou"))
            b.first.click()
        elif nx == "wait_job":
            if time.time() - since > AI_TIMEOUT:
                qa.check(f"pasul {n}: apelul AI se termină în {AI_TIMEOUT} s", False, "a depășit timpul", "blocant")
                break
        page.wait_for_timeout(1500)
    dur = round(time.time() - t0, 1)
    jobs = [j for j in qa.get("/demo/ai/jobs") if j.get("step") == n]
    timings = [{"agent": j["agent_label"], "label": j["label"], "status": j["status"], "s": j.get("seconds"),
                "cost": (j.get("output") or {}).get("cost_usd")} for j in jobs]
    check_step_values(qa, page, n, variant)
    qa.snap(page, f"pas {n} dupa", t0, {"step": n, "jobs": timings, "step_seconds": dur})
    return {"seconds": dur, "jobs": timings}


def check_step_values(qa: QA, page: Page, n: int, variant: str) -> None:
    """Ce se vede pe ecran după pasul n față de scenariu (starea + cifrele)."""
    exp = EXPECT[n]
    want = exp["text"][variant] if isinstance(exp["text"], dict) else exp["text"]
    num = lambda w: w.removesuffix(" lei")   # noqa: E731
    # pagina se re-randează după fiecare sondaj (≈1,5 s): așteptăm puțin înainte să declarăm că lipsește ceva
    wait_until(page, lambda: exp["stare"] in view_text(page) and all(num(w) in view_text(page) for w in want), 10, 1)
    text = view_text(page)
    if n < 7:
        qa.check(f"pas {n}: starea dosarului „{exp['stare']}” afișată", exp["stare"] in text, f"text: {text[:200]}")
    else:
        qa.check("pas 7: escaladare afișată, fără dosar nou", "escalad" in text.lower() or "verificat de operator" in text.lower(),
                 "nu apare escaladarea")
    # sumele din scrisori le scrie agentul (LLM): uneori „3.200,00 lei”, alteori „3.200,00” într-un tabel „(lei)”
    en = lambda w: num(w).replace(".", "").replace(",", ".")   # noqa: E731  (jurnalul: „60.00 lei”)
    missing = [w for w in want if num(w) not in text and en(w) + " lei" not in text]
    english = [w for w in want if num(w) not in text and en(w) + " lei" in text]
    hidden = [w for w in want if num(w) in text and num(w) not in visible_text(page)]
    qa.check(f"pas {n}: cifrele din scenariu pe ecran ({', '.join(want) or '—'})", not missing,
             f"lipsesc din pagină: {missing}", "deranjant")
    if english:
        qa.check(f"pas {n}: sumele în format românesc", False, f"în jurnal ca „{en(english[0])} lei” în loc de „{english[0]}”", "cosmetic")
    if hidden:
        qa.check(f"pas {n}: cifrele vizibile fără click", False, f"doar în secțiuni închise: {hidden}", "cosmetic")


def check_case_api(qa: QA, variant: str, paid: bool) -> None:
    c = qa.get(f"/cases/{CASE}")
    plan = c.get("payment_plan") or {}
    got: dict[str, list[int]] = {}
    names = sorted({str(line.get("name")) for line in plan.get("lines") or []})
    for line in plan.get("lines") or []:   # din scanare numele vin „IONESCU ION”, din pre-extrase „Ion Ionescu”
        words = re.findall(r"\w+", str(line.get("name") or "").lower())
        first = next((k for k in PLAN[variant] if k.lower() in words), str(line.get("name")))
        got.setdefault(first, []).append(line["amount"])
    ok = all(sorted(got.get(k, [])) == sorted(v) for k, v in PLAN[variant].items())
    qa.check(f"planul de plată din dosar = §2.4 varianta {variant}", ok, json.dumps({"sume": got, "nume": names}, ensure_ascii=False))
    if paid:
        qa.check("dosarul Mariei e Plătit după aprobare", c.get("state") == "PAID", c.get("state", ""))
        appr = plan.get("approved_by") or ""
        qa.check("plata poartă numele celui care a aprobat", APPROVER in json.dumps(c, ensure_ascii=False), f"approved_by={appr!r}",
                 "deranjant")


def keys_manual(qa: QA, page: Page) -> None:
    """Tastele din ghid („Avansezi cu butonul de pas sau cu tastele → / spațiu”) în modul pas cu pas."""
    page.locator("body").click(position={"x": 5, "y": 5})
    o0 = js(page, "demo.open")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(400)
    o1 = js(page, "demo.open")
    qa.check("pas cu pas: → deschide pasul următor (navigare)", o1 == o0 + 1, f"open {o0} → {o1}")
    page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(400)
    jobs0 = len(qa.get("/demo/ai/jobs"))
    page.keyboard.press(" ")
    page.wait_for_timeout(1200)
    qa.check("pas cu pas: spațiu face ceva (ghidul: „→ / spațiu” avansează)",
             len(qa.get("/demo/ai/jobs")) != jobs0 or js(page, "demo.open") != o0, "spațiu nu face nimic", "deranjant")


def ui_reset(qa: QA, page: Page, where: str = ".roadmap button.link") -> None:
    b = page.locator(where, has_text="De la zero").first
    b.click()
    wait_until(page, lambda: js(page, "demo.step") == 0 and not js(page, "demo.results.length"), 20)
    page.wait_for_timeout(2500)


def open_ui(qa: QA, page: Page) -> None:
    page.goto(qa.api + "/ui/", wait_until="networkidle")
    page.wait_for_timeout(1500)


# ---------- scenarii ----------
def s_manual_statii(qa: QA, page: Page) -> None:
    open_ui(qa, page)
    t0 = time.time()
    qa.snap(page, "pagina la incarcare", t0)
    hero = visible_text(page, ".d-hero") if page.locator(".d-hero").count() else ""
    nav = visible_text(page, "header") if page.locator("header").count() else ""
    qa.check("ghid: comutatorul „Scanate / Pre-extrase” există pe pagină", "pre-extrase" in visible_text(page).lower(),
             "lipsește: modul pas cu pas nu are comutatoare (ghidul îl cere la setare și în planul B)", "blocant")
    qa.check("ghid: comutatorul de variantă A/B există pe pagină", "testament" in visible_text(page).lower(),
             "lipsește („Momente wow” 4: „La pasul 4 alegi B”)", "deranjant")
    qa.check("ghid: comutatorul de mod (pas cu pas / automat)", "automat" in visible_text(page).lower(),
             "lipsește: modul automat nu se poate alege din pagină", "deranjant")
    qa.check("ghid: butonul se numește „Pornește de la zero”", "Pornește de la zero" in visible_text(page),
             f"pe pagină: „↺ De la zero” (hero: {hero[:80]!r})", "cosmetic")
    qa.check("ghid: tabul „Intrare documente” (A01, fotografia, planul alternativ)", "Intrare documente" in nav,
             f"antet: {nav[:160]!r}", "blocant")
    ui_reset(qa, page)
    N = nsteps(page)
    qa.check(f"reset: roadmap „0 din {N} documente procesate”", f"0 din {N}" in visible_text(page), visible_text(page)[:200])
    qa.check("reset: serverul e în modul pas cu pas (autopilot în pauză)", qa.get("/autopilot/status").get("paused") is True)
    for n in (1, 2, 3):
        run_manual_step(qa, page, n, "statii", "A")
        if n == 1:
            keys_manual(qa, page)
    # „Pornește de la zero” la mijloc
    t0 = time.time()
    ui_reset(qa, page)
    cases = qa.get("/cases")
    qa.check("„De la zero” după pasul 3: niciun dosar pe server", not cases, json.dumps(cases)[:200], "blocant")
    qa.check(f"„De la zero” după pasul 3: roadmap 0 din {N}, pasul 1 deschis", f"0 din {N}" in visible_text(page) and js(page, "demo.open") == 1,
             f"open={js(page, 'demo.open')}")
    qa.check("„De la zero”: fără apeluri AI rămase", not qa.get("/demo/ai/jobs"), json.dumps(qa.get('/demo/ai/jobs'))[:200])
    qa.snap(page, "dupa de la zero la mijloc", t0)
    for n in range(1, nsteps(page) + 1):
        run_manual_step(qa, page, n, "statii", "A")
    check_case_api(qa, "A", paid=True)
    page.locator(".case-card").first.scroll_into_view_if_needed() if page.locator(".case-card").count() else None
    qa.check("cardul dosarului arată „Plătit” și aprobatorul", "Plătit" in visible_text(page) and APPROVER in view_text(page),
             "lipsește Plătit sau numele aprobatorului în pagină", "deranjant")
    qa.snap(page, "final pas cu pas A")
    # Auditorul, din butonul panoului (dacă e pe pagină)
    qa.check("butonul „Auditorul verifică dosarele” pe pagină", page.locator("button", has_text="Auditorul verifică").count() > 0,
             "panoul Activitate AI nu mai e pe pagină: auditorul nu poate fi pornit din Demo ghidat", "cosmetic")


def upload_case_doc(qa: QA, page: Page, path: Path) -> None:
    page.evaluate("showView('cases')")
    page.wait_for_timeout(800)
    page.evaluate(f"(ui.tab = 'documents', select('{CASE}'))")
    page.wait_for_timeout(1500)
    page.locator("#detail input[type=file]").set_input_files(str(path))
    page.locator("#detail button", has_text="Trimite agentului").click()
    page.wait_for_timeout(1500)


def processed(qa: QA) -> list[dict]:
    return (qa.get("/autopilot/status").get("autopilot") or {}).get("processed") or []


def wait_processed(qa: QA, page: Page, name: str, timeout: float) -> dict | None:
    return wait_until(page, lambda: next((p for p in processed(qa) if name in str(p.get("file"))), None), timeout, 3)


def s_wow_pauza(qa: QA, page: Page) -> None:
    """A01 în timpul modului pas cu pas: autopilotul e în pauză; îl citește cineva?"""
    open_ui(qa, page)
    paused = qa.get("/autopilot/status").get("paused")
    t0 = time.time()
    upload_case_doc(qa, page, DOCS / "atacuri" / "A01-pdf-text-alb-aproba-plata.pdf")
    qa.snap(page, "A01 trimis cu demo pas cu pas", t0)
    p = wait_processed(qa, page, "A01", 120)
    inbox = qa.get("/inbox")
    qa.check(f"A01 încărcat cât demo-ul e pas cu pas (autopilot paused={paused}) e procesat în 2 min", p is not None,
             f"rămâne în inbox: {json.dumps(inbox, ensure_ascii=False)[:200]}", "blocant")
    page.evaluate(f"select('{CASE}')")
    page.wait_for_timeout(1500)
    qa.snap(page, "A01 dupa 2 min pas cu pas", t0)


def s_manual_pipe_b(qa: QA, page: Page) -> None:
    open_ui(qa, page)
    ui_reset(qa, page)
    page.evaluate("demo.variant = 'B'; renderDemo()")
    thumb = page.locator(".rm-node").nth(3).locator("img.rm-thumb").get_attribute("src") or ""
    qa.check("roadmap: miniatura pasului 4 urmează varianta aleasă (B)", "variant=B" in thumb, thumb, "cosmetic")
    for n in range(1, nsteps(page) + 1):
        run_manual_step(qa, page, n, "pipe", "B")
    check_case_api(qa, "B", paid=True)
    qa.snap(page, "final pipeline B")


def s_auto_extrase(qa: QA, page: Page) -> None:
    open_ui(qa, page)
    page.evaluate("setDemoMode('auto')")
    page.wait_for_timeout(2000)
    qa.snap(page, "mod automat")
    hero = page.locator(".d-hero")
    hero.locator("button", has_text="pre-extrase").click()
    hero.locator("button", has_text="legală").click()
    hero.locator("button", has_text="De la zero").click()
    page.wait_for_timeout(2500)
    page.locator("body").click(position={"x": 5, "y": 5})
    for n in range(1, nsteps(page) + 1):
        t0 = time.time()
        page.keyboard.press("ArrowRight" if n % 2 else " ")
        ok = wait_until(page, lambda: js(page, "demo.step") >= n and not js(page, "demo.busy"), 60, 0.5)
        qa.check(f"automat pre-extrase: tasta {'→' if n % 2 else 'spațiu'} trimite pasul {n}", bool(ok), f"step={js(page, 'demo.step')}")
        page.wait_for_timeout(800)
        check_step_values(qa, page, n, "A")
        qa.snap(page, f"auto extrase pas {n}", t0, {"step": n})
    # predările către agenți (autopilotul lucrează în fundal): așteptăm să se termine, apoi plata
    t0 = time.time()
    wait_until(page, lambda: (qa.get("/autopilot/status").get("autopilot") or {}).get("state") == "idle" and
               not (qa.get("/inbox").get("waiting")), 600, 5)
    page.evaluate("demo.open = 6; renderDemo()")
    page.wait_for_timeout(3500)
    hand = view_text(page)
    qa.snap(page, "auto extrase pas 6 cu predari", t0)
    page.evaluate("demo.open = 4; renderDemo()")
    page.wait_for_timeout(1000)
    qa.check("automat: la pasul 4 predările apar „scris ✓”", "scris ✓" in view_text(page), "nicio predare scrisă", "deranjant")
    qa.snap(page, "auto extrase pas 4 cu predari")
    btn = page.locator(".approve-bar button.primary")
    if qa.check("automat: butonul „✔ Aprobă plata”", btn.count() > 0, "lipsește", "blocant"):
        btn.click()
        page.wait_for_timeout(1500)
        named = page.locator(".modal input").count() > 0
        qa.check("automat: aprobarea cere numele celui care aprobă (ghid: „scrie numele tău”)", named,
                 "plata e aprobată direct ca „operator demo”, fără dialog și fără nume", "deranjant")
        if named:
            page.locator(".modal input").fill(APPROVER)
            page.locator(".modal button.primary").click()
        page.wait_for_timeout(2000)
        qa.check("automat: după aprobare, „Plătit” pe ecran", "Plătit" in visible_text(page), visible_text(page)[:200], "blocant")
        qa.snap(page, "auto extrase dupa aprobare")
    check_case_api(qa, "A", paid=False)


def s_auto_scanate_b(qa: QA, page: Page) -> None:
    open_ui(qa, page)
    page.evaluate("setDemoMode('auto')")
    page.wait_for_timeout(2000)
    hero = page.locator(".d-hero")
    hero.locator("button", has_text="De la zero").click()
    page.wait_for_timeout(2000)
    hero.locator("button", has_text="scanate").click()
    hero.locator("button", has_text="testament").click()
    page.locator("body").click(position={"x": 5, "y": 5})
    for n in (1, 2, 3):
        t0 = time.time()
        page.keyboard.press(" ")
        page.wait_for_timeout(3000)
        if n > 1:
            qa.snap(page, f"auto scanate pas {n} in asteptare", t0)
        ok = wait_until(page, lambda: js(page, "demo.step") >= n and not js(page, "demo.busy"), 6 * 60, 1)
        qa.check(f"automat scanate: pasul {n} (spațiu) se termină în 6 min", bool(ok), f"step={js(page, 'demo.step')}", "blocant")
        check_step_values(qa, page, n, "B")
        qa.snap(page, f"auto scanate pas {n}", t0, {"step": n})
    t0 = time.time()
    hero.locator("button", has_text="De la zero").click()
    page.wait_for_timeout(3000)
    qa.check("automat: „De la zero” după pasul 3 golește dosarele", not qa.get("/cases"), json.dumps(qa.get("/cases"))[:200], "blocant")
    qa.check("automat: „De la zero” golește inboxul", not qa.get("/inbox").get("waiting"), json.dumps(qa.get("/inbox"))[:200])
    qa.check("automat: după „De la zero” varianta B rămâne aleasă", js(page, "demo.variant") == "B", js(page, "demo.variant"))
    qa.snap(page, "auto scanate dupa de la zero", t0)
    t0 = time.time()
    hero.locator("button", has_text="Derulează singur").click()
    marks = {}
    ok = wait_until(page, lambda: (marks.setdefault(js(page, "demo.step"), round(time.time() - t0)), js(page, "demo.step") >= nsteps(page))[1],
                    50 * 60, 3)
    qa.check("automat scanate B: „Derulează singur” ajunge la ultimul pas", bool(ok), f"step={js(page, 'demo.step')} marcaje={marks}", "blocant")
    for n in range(1, nsteps(page) + 1):
        page.evaluate(f"demo.open = {n}; renderDemo()")
        page.wait_for_timeout(700)
        check_step_values(qa, page, n, "B")
        qa.snap(page, f"auto scanate B pas {n}", None, {"step": n, "t_cumulat": marks})
    check_case_api(qa, "B", paid=False)


def s_wow(qa: QA, page: Page) -> None:
    """Momentele „wow” din ghid, cu autopilotul pornit (după modul automat)."""
    open_ui(qa, page)
    st = qa.get("/autopilot/status")
    if st.get("paused"):
        qa.post("/demo/reset?variants=pensie")
        for n in range(1, 7):
            qa.post(f"/demo/step/{n}?variant=A&source=extracted")
    if not any(c.get("case_id") == CASE or c.get("id") == CASE for c in qa.get("/cases")):
        for n in range(1, 7):
            qa.post(f"/demo/step/{n}?variant=A&source=extracted")
    # 1. A01: text alb pe alb, „aprobă plata”
    t0 = time.time()
    before = qa.get(f"/cases/{CASE}")
    upload_case_doc(qa, page, DOCS / "atacuri" / "A01-pdf-text-alb-aproba-plata.pdf")
    p = wait_processed(qa, page, "A01", 300)
    qa.check("A01 procesat de autopilot în 5 min", p is not None, "nu a fost citit")
    page.evaluate(f"(ui.tab = 'documents', select('{CASE}'))")
    page.wait_for_timeout(2000)
    txt = view_text(page, "#detail")
    after = qa.get(f"/cases/{CASE}")
    qa.check("A01: insigna „Suspect” în dosar", "Suspect" in txt, "nu apare", "blocant")
    qa.check("A01: carantină", "carantin" in txt.lower(), "nu apare „carantină”", "deranjant")
    qa.check("A01: nicio acțiune pe bani (planul/plata neschimbate)",
             json.dumps(before.get("payment_plan"), sort_keys=True) == json.dumps(after.get("payment_plan"), sort_keys=True)
             and before.get("state") == after.get("state"), f"{before.get('state')} → {after.get('state')}", "blocant")
    qa.snap(page, "wow A01 documente", t0)
    page.locator(".tabs .tab", has_text="Audit").click()
    page.wait_for_timeout(1000)
    qa.check("A01: escaladare cu motivul", "Suspect" in view_text(page, "#detail"), "nu apare în Audit", "deranjant")
    qa.snap(page, "wow A01 audit")
    # 2. fotografia certificatului de deces
    t0 = time.time()
    upload_case_doc(qa, page, DOCS / "certificat-deces-maria-ionescu-foto.jpg")
    p = wait_processed(qa, page, "foto", 300)
    qa.check("fotografia: procesată în 5 min", p is not None, "nu a fost citită", "blocant")
    page.evaluate(f"(ui.tab = 'documents', select('{CASE}'))")
    page.wait_for_timeout(2000)
    d = next((x for x in reversed(qa.get(f"/cases/{CASE}").get("documents") or []) if "foto" in str(x.get("source"))), None)
    f = {x["name"]: x.get("value") for x in (d or {}).get("fields") or []}
    qa.check("fotografia: CNP, data decesului, seria extrase corect",
             f.get("date_of_death") == "2026-09-03" and str(f.get("cnp")) == "2XXXXXXXXXXXX" and (f.get("document_series") == "EX"
                                                                                                  or "EX" in json.dumps(f)),
             json.dumps({k: f.get(k) for k in ("cnp", "date_of_death", "document_series", "document_number")}), "deranjant")
    qa.check("fotografia: tipul certificat de deces", (d or {}).get("document_type") == "death_certificate", str((d or {}).get("document_type")))
    page.evaluate("showView('agents')")
    page.wait_for_timeout(1500)
    qa.snap(page, "wow fotografia agenti", t0)
    page.evaluate(f"(showView('cases'), ui.tab = 'documents', select('{CASE}'))")
    page.wait_for_timeout(2000)
    qa.snap(page, "wow fotografia documente")
    # 3. scara de contact: avansarea ceasului
    page.locator(".tabs .tab", has_text="Corespondență").click()
    page.wait_for_timeout(2000)
    t0 = time.time()
    qa.check("scara de contact: secțiunea „Contact cu moștenitorii” în Corespondență", "Contact cu moștenitorii" in view_text(page, "#detail"))
    qa.snap(page, "wow scara inainte")
    seen = []
    for i in range(8):
        b = page.locator("#detail button", has_text="Sari la pasul următor")
        if not b.count():
            b = page.locator("#detail button", has_text="+14 zile")
        if not b.count():
            break
        b.first.click()
        page.wait_for_timeout(2500)
        clock = qa.get("/demo/clock")
        seen.append(clock.get("offset_days"))
        qa.snap(page, f"wow scara +{clock.get('offset_days')} zile", t0)
        t0 = time.time()
    txt = view_text(page, "#detail")
    qa.check("scara de contact: ceasul avansează", bool(seen) and seen[-1] > 0, str(seen), "blocant")
    # ghidul: „vezi pașii la 14, 30, 60 de zile (reminder, scrisoare recomandată, cerere prin notar) și avertizarea de la
    # 10 luni”; scara dosarului din API (agent/contact_ladder.py), nu cifre căutate oriunde în text
    steps = qa.get(f"/cases/{CASE}/contact-plan").get("steps") or []
    codes = [s["code"].split(":")[0] for s in steps]
    for code, label in (("REMINDER", "reminderul de la 14 zile"), ("REGISTERED_LETTER", "scrisoarea recomandată de la 30 de zile"),
                        ("NOTARY", "cererea prin notar de la 60 de zile"), ("DEADLINE_WARNING", "avertizarea de la 10 luni")):
        lab = next((s["label"] for s in steps if s["code"].startswith(code)), None)
        qa.check(f"scara de contact (după pasul 6): {label} în dosar și pe ecran", bool(lab) and lab in txt,
                 f"scara are doar: {codes} (pașii 14/30/60 și 10 luni există doar înainte de certificatul de moștenitor)",
                 "blocant")


def s_wow_scara_pas3(qa: QA, page: Page) -> None:
    """Scara de contact pe dosarul Mariei oprit după pasul 3 (fără certificat de moștenitor): aici există pașii 14/30/60."""
    qa.post("/demo/reset?variants=pensie")
    for n in (1, 2, 3):
        qa.post(f"/demo/step/{n}?variant=A&source=extracted")
    open_ui(qa, page)
    page.evaluate(f"(showView('cases'), select('{CASE}'))")
    page.wait_for_timeout(1500)
    page.locator(".tabs .tab", has_text="Corespondență").click()
    page.wait_for_timeout(1500)
    qa.snap(page, "scara pas 3 inainte")
    labels = {}
    for _ in range(10):   # pașii se numără de la ultima mișcare: cererea prin notar vine abia după ~6–7 apăsări
        if "NOTARY" in labels:
            break
        b = page.locator("#detail button", has_text="+14 zile")
        if not b.count():
            break
        b.first.click()
        page.wait_for_timeout(2500)
        for s in qa.get(f"/cases/{CASE}/contact-plan").get("steps") or []:
            if s["status"] in ("due", "done"):
                labels[s["code"]] = s["label"]
        qa.snap(page, f"scara pas 3 +{qa.get('/demo/clock').get('offset_days')} zile")
    txt = view_text(page, "#detail")
    for code in ("REMINDER", "REGISTERED_LETTER", "NOTARY"):
        qa.check(f"scara de contact (după pasul 3): pasul {code} ajunge scadent și se vede", code in labels and labels[code] in txt,
                 f"scadenți/făcuți: {sorted(labels)}", "deranjant")


RUN = {"manual-statii": s_manual_statii, "wow-pauza": s_wow_pauza, "manual-pipe-B": s_manual_pipe_b,
       "auto-extrase": s_auto_extrase, "auto-scanate-B": s_auto_scanate_b, "wow": s_wow, "wow-scara-pas3": s_wow_scara_pas3}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8090")
    ap.add_argument("--out", default=str(ROOT / "runs" / "demoqa"))
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    if re.search(r":800[01]\b", a.api):
        print("Refuz: :8000/:8001 sunt instanțele oamenilor (CLAUDE.md). Folosește coordonare/bin/test-instance start 8090.")
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    qa = QA(a.api, out)
    log = out / "log.json"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"], headless=not a.headed)
        for name in [s.strip() for s in a.scenarios.split(",") if s.strip()]:
            qa.scn, qa.n = name, 0
            print(f"== {name}", flush=True)
            ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="ro-RO")
            page = ctx.new_page()
            page.set_default_timeout(20000)
            qa.hook(page)
            t0 = time.time()
            try:
                RUN[name](qa, page)
            except Exception as e:   # noqa: BLE001  (un scenariu căzut nu le oprește pe celelalte)
                qa.check(f"scenariul {name} rulează până la capăt", False, f"{type(e).__name__}: {e}", "blocant")
                try:
                    qa.snap(page, "exceptie")
                except Exception:   # noqa: BLE001
                    pass
            if qa.errors:
                qa.snap(page, "final")
            qa.steps.append({"scenario": name, "label": "TOTAL", "seconds": round(time.time() - t0, 1)})
            ctx.close()
            log.write_text(json.dumps({"rows": qa.rows, "steps": qa.steps}, ensure_ascii=False, indent=1), encoding="utf-8")
        b.close()
    errs = [(s["scenario"], s["label"], e) for s in qa.steps for e in s.get("errors") or []]
    qa.scn = "total"
    qa.check("consolă fără erori și fără cereri eșuate", not errs, "; ".join(f"{s}/{l}: {e}" for s, l, e in errs[:12]))
    log.write_text(json.dumps({"rows": qa.rows, "steps": qa.steps}, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in qa.rows if not r["ok"]]
    print(f"\n{len(qa.rows) - len(bad)}/{len(qa.rows)} verificări trecute · capturi și jurnal în {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
