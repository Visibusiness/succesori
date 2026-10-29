# Cost per dosar: măsurat, nu presupus

Sursă: `runs/*/trace.jsonl` (extractor, `cost_usd` per document) și `runs/*/autopilot-status.json` (agenți, `cost_usd`
per apel), ambele din `total_cost_usd` raportat de `claude -p`. Se reface cu `.venv/bin/python scripts/cost_dosar.py`.
Model: Sonnet 5.5 (`EXTRACT_MODEL` / `AUTOPILOT_MODEL` implicit). Dosarul: scenariul demo Maria Ionescu, 7 documente.
Curs 1 USD = 4,5 lei (estimare proprie, ca în `business-case.md`). Data măsurării: 2026-10-28.

## Ce costă o rulare completă (un dosar, toți agenții)

Rularea de referință `runs/20261028T130938Z` e singura cu toate cele 7 documente și toți cei 4 agenți apelați de autopilot:

| Pas | Apeluri | Cost | Timp model |
|---|---|---|---|
| Extracție (7 documente, câte unul pe tip) | 7 | 0,49 $ | – |
| Auditor (după fiecare etapă) | 7 | 1,06 $ | 377 s |
| Comunicare cu moștenitorii | 3 | 0,37 $ | 49 s |
| Corespondent (notar, asigurător, supliment) | 3 | 0,33 $ | 50 s |
| Investigator (escaladare) | 1 | 0,10 $ | 19 s |
| **Total per dosar** | **21** | **2,35 $ ≈ 10,6 lei** | **≈ 8 min** |

Alte rulări de demo cu agenți: 1,39 $ (`dev-autopilot-121206`) și 1,48 $ (`20261028T123605Z`), cu mai puțini agenți
(fără mesaje către moștenitor). **Interval măsurat: 1,4–2,4 $ per dosar.** Smoke-ul cap-coadă (`runs/e2e/smoke-run*.json`)
procesează cele 7 documente în 289–313 s.

Ce cântărește: **auditorul face 45% din cost**, pentru că rulează după fiecare etapă (7 apeluri). Extracția costă
0,04–0,07 $ per document (eval-urile din 28.10: mediana 0,036–0,058 $; pe PDF/fotografie 0,05–0,06 $).

## Cât poate scădea (estimare proprie, nemăsurată cap-coadă)

| Schimbare | Efect pe dosar | Pe ce se bazează |
|---|---|---|
| Auditor o singură dată, la închiderea dosarului | 1,06 $ → ≈ 0,2 $ | cel mai scump apel de auditor măsurat: 0,21 $ |
| Extracție pe Haiku | 0,49 $ → ≈ 0,03 $ | `eval-haiku-*.json`: 0,004 $/document, câmpuri 97,7% (−1,6 pct) |
| **Total optimizat** | **≈ 1,0 $ ≈ 4,7 lei** | |

`claude -p` adaugă la fiecare apel promptul de sistem al Claude Code (citit din cache). Un apel direct la API, fără
acest prompt, ar costa mai puțin; diferența nu e măsurată.

## Costul alături de timpul economisit (per dosar)

Ore manuale per dosar și % automatizat din `kb/data/estimare-volum-cost.md` și `business-case.md` (estimare proprie):

| Scenariu | Ore manuale/dosar | Ore economisite (× % automat.) | Valoare (× lei/oră) | Cost Claude măsurat | Raport |
|---|---|---|---|---|---|
| Prudent | 1,5 h | 0,75 h (50%) | 45 lei | 10,6 lei | ≈ 4× |
| **Central** | **3 h** | **≈ 2 h (65%)** | **≈ 175 lei** | **10,6 lei** | **≈ 17×** |
| Optimist | 6 h | 4,5 h (75%) | 540 lei | 10,6 lei | ≈ 51× |

Pe an (central, 24.000 dosare): 2,35 $ × 24.000 ≈ 56k $ ≈ 254k lei cost Claude, față de ≈ 4,2 mil. lei economie la ore
(≈ 17×). Cu varianta optimizată (≈ 1 $/dosar): ≈ 24k $ ≈ 108k lei (≈ 39×).

Agentul lucrează ≈ 8 minute de model pe dosar și 5 minute cap-coadă pe cele 7 documente. Rămâne la operator partea
neautomatizată: ≈ 1 h în scenariul central (aprobarea plății, cazurile escaladate).

## Ce nu e inclus
- Infrastructura internă (găzduire, integrare DGEP/core, monitorizare): **necunoscut**, parametru de la bancă.
- Bucla de învățare (`scripts/retro.py`, eval-uri): cost de dezvoltare, nu per dosar.
- Dosarele grele (cote invalide, CNP ambiguu) fac mai multe apeluri de investigator și corespondent: ≈ +0,1 $ per escaladare.
