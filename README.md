# Agentul de Succesiune

Când moare un client, banca primește documente din patru direcții (DGEP, notar, asigurător, familie), în orice ordine.
Agentul deschide un dosar unic la primul semnal, extrage datele cu un LLM și calculează determinist soldurile la data
decesului, stornările, cotele și planul de plată. Omul aprobă doar plata și rezolvă excepțiile semnalate.

Proiect pentru VibeHack 2026 (Raiffeisen Bank România). Contextul de business e în `BRIEF.md`, arhitectura în
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), securitatea în `docs/SECURITY.md` (dacă există în această versiune),
deciziile în `docs/DECISIONS.md`.

## Pentru juriu: 10 minute

**1. Instalare și teste (fără cheie, fără rețea, ~1 minut).** Python 3.11:

```bash
git clone https://github.com/Visibusiness/succesori.git && cd succesori
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q tests
```

Testele verifică valorile exacte ale scenariului (soldurile la deces, stornările, cotele, planul de plată), ordinea
inversă a documentelor, duplicatele și cazurile grele H1–H11. Calculele sunt cod determinist, nu LLM.

**2. Pornește aplicația și deschide panoul operatorului.**

```bash
DEMO_MODE=1 .venv/bin/uvicorn agent.api:app --port 8001
```

Deschide http://localhost:8001/ui/. Fără cheie LLM merg lista de lucru, dosarele, planul de plată și demo-ul cu
documente pre-extrase:

```bash
curl -s -X POST localhost:8001/demo/run | python3 -m json.tool      # cele 7 documente ale Mariei Ionescu, în ordine
```

Reîncarcă UI-ul: dosarul `SC-2026-0001` are evenimentele, fiecare cu regula aplicată, termenele, ce mai lipsește și
plata care așteaptă aprobarea ta. Nimic nu pleacă din bancă fără un om.

**3. Cu AI (cere o cheie Claude API sau Bedrock, vezi secțiunea de mai jos).** Încarcă `.env` în shell, pornește
serverul ca la pasul 2, apoi în UI → **Demo ghidat** → **Pas cu pas**: fiecare document trece prin extractorul AI,
regulile băncii și agenții (corespondent, investigator, comunicator), iar la fiecare decizie aprobi sau respingi tu.
Un apel AI durează 7–60 s; panoul „Activitate AI” arată fiecare apel, cu durata și costul.

**Ce merită citit:** `BRIEF.md` (problema), `docs/ARCHITECTURE.md` (cum e construit), `docs/IMPACT.md` (timp și cost
economisit), `docs/SECURITY.md` (secret bancar, GDPR, aprobarea umană), `docs/SCALABILITATE.md`, `docs/pitch/`.
Agenții LLM sunt în `.claude/agents/`, cunoștințele învățate de ei în `.claude/skills/`.

Toate persoanele, CNP-urile și IBAN-urile sunt fictive.

## Pornire în 3 comenzi

Ai nevoie de Python 3.11 și, pentru pașii cu LLM, de CLI-ul Claude Code (`npm install -g @anthropic-ai/claude-code`).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q tests                      # deterministe, fără LLM și fără rețea
DEMO_MODE=1 .venv/bin/uvicorn agent.api:app --port 8001 & .venv/bin/python scripts/autopilot.py --watch --api http://localhost:8001
```

UI-ul operatorului e la http://localhost:8001/ui/. `DEMO_MODE=1` acceptă CNP-urile și IBAN-urile mascate ale demo-ului
(sare doar peste cifrele de control). Nu se folosește în producție.

## Claude API sau Amazon Bedrock

Extractorul (`agent/extract.py`) și agenții chemați de autopilot rulează prin `claude -p` și moștenesc mediul procesului.
Copiază `.env.example` în `.env`, completează valorile, apoi încarcă-l în shell înainte de uvicorn și autopilot:
`set -a; . ./.env; set +a`.

- **Claude API:** `ANTHROPIC_API_KEY`.
- **Bedrock:** `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION` și o autentificare AWS: `AWS_BEARER_TOKEN_BEDROCK` sau
  credențialele AWS standard. Aliasurile de model din cod (`sonnet`, `haiku`, `opus`) se mapează pe modelele din regiune
  prin `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`.
- **Opțional:** `EXTRACT_MODEL`, `AUTOPILOT_MODEL` (implicit `sonnet`), `EXTRACT_TIMEOUT`, `RUNS_DIR`, `RUN_ID`,
  `AUTOPILOT_INBOX`, `AUTOPILOT_API`. Lista completă e în `docs/ARCHITECTURE.md` §6.

## Demo

Scenariul fix: Maria Ionescu, decedată pe 3 septembrie, 7 documente. Valorile exacte sunt în
`kb/scenariu-demo/maria-ionescu.md`.

```bash
# determinist, fără LLM: documentele deja extrase
curl -s -X POST localhost:8001/demo/run | python3 -m json.tool             # varianta A (moștenire legală)
curl -s -X POST "localhost:8001/demo/run?variant=B"                         # varianta B (testament)
curl -s -X POST localhost:8001/payments/PAY-SC-2026-0001/approve -H 'content-type: application/json' -d '{"approver":"ops"}'

# cap-coadă, cu LLM: documentele brute trec prin inbox → extractor → pipeline → agenți
.venv/bin/python scripts/autopilot.py --demo --api http://localhost:8001
```

În UI, butonul „Demo ghidat” rulează același scenariu pas cu pas.

## Teste

| Comandă | Ce verifică | LLM |
|---|---|---|
| `pytest -q tests` | regulile (funcții pure), scenariul A/B, ordine inversă, duplicate, cote ≠ 1, cazurile grele H1–H11, API-ul | nu |
| `scripts/smoke_e2e.py --api URL` | serverul viu: cele 7 documente prin inbox și autopilot, valorile exacte, scrisorile, plata | da |
| `scripts/ui_e2e.py` | ops-ui în Chromium: toate taburile, consola curată (cere `playwright install chromium`) | nu |
| `DEMO_MODE=1 scripts/eval_extract.py` | acuratețea extractorului pe ground truth (main, hard, holdout) | da |

`scripts/test-instance.sh smoke [port]` pornește API-ul și autopilotul pe un port separat, cu inbox și `runs/` proprii,
rulează `smoke_e2e.py` pe ele și le oprește. Folosește-l ca să nu resetezi o instanță pe care lucrează altcineva.

## Structura

```
agent/                 API (FastAPI), pipeline, mașina de stări, reguli pure, extractor, poarta de siguranță, core bancar mock
scripts/               autopilot (inbox → agenți), eval extractor, bucla de învățare (retro), smoke e2e, test UI, cost per dosar
tests/                 pytest
ops-ui/                panoul operatorului, static, fără build
.claude/agents/        agenții LLM (extractor, orchestrator, investigator, correspondent, heir-communicator, auditor, retro-learner, qa-tester)
.claude/skills/        cunoștințele învățate, citite de agenți
registries/documents/  corpusul: cele 7 documente demo, hard/ (H1–H11), holdout/, augmented/, adversarial/, real-text/, forms-real/
registries/generator/  generatorul determinist de PDF-uri și scanări
registries/inbox/      directorul urmărit de autopilot
kb/                    legi, proceduri bancare, șabloane de documente, decizii tehnice, cu sursele citate
docs/                  arhitectură, decizii, pitch
```

## Limite cunoscute

- Core-ul bancar, DGEP, notarul și asigurătorul sunt simulate (`agent/core_mock.py`). Contractul pentru integrarea reală
  e în `kb/tech/api-contract-bank.md`.
- Extracția depinde de LLM: scorul se măsoară cu `eval_extract.py`, nu e exact. Sub încrederea de 0,80, documentul
  merge la operator.
- Plata nu pleacă niciodată fără aprobare umană. Mesajele către moștenitori merg doar într-un outbox mock.
- `DEPLOYMENT_MODE=hub` (hub-ul multi-bancă din BRIEF) nu e implementat. Există doar modul intern.
- `docs/` și `README-MVP.md` pomenesc serverul stabil al echipei de pe :8000 (`coordonare/bin/promoveaza`). Scripturile
  echipei nu fac parte din predare. Echivalentul lor aici e `scripts/test-instance.sh`.
- Starea (dosare, core mock, mesaje) se păstrează între reporniri într-un singur fișier SQLite (`data/mvp.sqlite`, un
  singur proces server). Trace-urile rămân în `runs/`. Detalii: `docs/PERSISTENTA.md`.
- PDF-urile și PNG-urile mari din `registries/documents/forms-real/` nu sunt în repo. Se regenerează cu
  `python -m registries.generator.certificat_deces` (cere formularele MAI din `kb/_downloads/`, vezi README-ul de acolo).

## Licență și date

Codul e publicat pentru evaluarea hackathonului. Toate persoanele, CNP-urile, IBAN-urile și dosarele sunt **fictive**.
CNP-urile și IBAN-urile din demo sunt mascate. Legile, procedurile și formularele publice sunt citate în `kb/` cu sursa,
dar nu sunt redistribuite: documentele descărcate (`kb/_downloads/`) nu fac parte din repo. Fonturile din
`registries/generator/fonts/` au licența OFL (`OFL.txt`).
