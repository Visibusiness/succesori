# Agentul de Succesiune — MVP

Agent care preia dosarul de succesiune al unui client decedat: primește documente în orice ordine
(semnal DGEP, adresă de notar, certificat de asigurare, certificat de moștenitor, răspuns asigurător,
supliment, certificat de deces), aplică regulile deterministe din `agent/rules.py` și lasă omului
doar aprobarea plății și excepțiile. Context complet: `BRIEF.md`, `kb/`.

## Rulare (pe mașina `mosteniri-reiff`, în rădăcina repo-ului)

Datele demo au CNP mascat (`2XXXXXXXXXXXX`) și IBAN-uri cu control `00`: **serverul, eval-ul și retro rulează cu
`DEMO_MODE=1`** (sare DOAR peste cifrele de control CNP/IBAN, DECISIONS 2026-10-28). Fără el, extractorul oprește
documentele demo la gate.

```bash
.venv/bin/python -m pytest -q tests                              # 27 de teste: reguli, scenariul end-to-end, cazuri grele H4/H5/H10/H11, variante
DEMO_MODE=1 .venv/bin/uvicorn agent.api:app --port 8000          # API + UI la http://localhost:8000/ui/
DEMO_MODE=1 .venv/bin/python scripts/eval_extract.py             # eval extractor (--set main|hard, --only 04)
DEMO_MODE=1 .venv/bin/python scripts/retro.py --cycles 2         # bucla de învățare
```

Starea (dosare, core mock, mesaje, tokenuri, ceasul demo) se păstrează între reporniri în SQLite: `data/mvp.sqlite`
(sau `MVP_DB`); resetul readuce portofoliul de clienți din `registries/portofoliu/`. Detalii: `docs/PERSISTENTA.md`.

Dacă nu există `.venv`: `python3 -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" pydantic pytest httpx python-multipart claude-agent-sdk`.

## Demo în 7 pași (fără UI)

```bash
curl -s -X POST localhost:8000/demo/run | python3 -m json.tool          # toate cele 7 documente, varianta A (moștenire legală)
curl -s -X POST "localhost:8000/demo/run?variant=B"                      # varianta B (testament 1/2-1/4-1/4)
curl -s -X POST localhost:8000/demo/reset; curl -s -X POST localhost:8000/demo/step/1   # pas cu pas
curl -s -X POST "localhost:8000/demo/reset?variants=pensie,retragere"   # + Andrei retrage 1.000 lei după deces (flag + escaladare)
curl -s -X POST "localhost:8000/demo/reset?variants="                   # fără pensia din octombrie (fără retur CNPP)
curl -s -X POST "localhost:8000/demo/reset?gol=1"                       # bancă goală, fără portofoliul de 14 clienți (084, 085)
curl -s "localhost:8000/worklist?filtru=de_aprobat" | python3 -m json.tool   # lista de lucru: toate|de_aprobat|escaladari|documente|termene, &q=
curl -s localhost:8000/cases | python3 -m json.tool
curl -s localhost:8000/cases/SC-2026-0001 | python3 -m json.tool        # dosarul: stare, evenimente cu regula, termene, plan de plată, ce lipsește
curl -s -X POST localhost:8000/payments/PAY-SC-2026-0001/approve -H 'content-type: application/json' -d '{"approver":"ops"}'
curl -s -X POST localhost:8000/payments/PAY-SC-2026-0001/reject -H 'content-type: application/json' -d '{"reason":"IBAN lipsă"}'   # → PLAN_DRAFTED
```

**Demo ghidat** (`/ui/` → Demo ghidat) are două moduri:
- **Pas cu pas** (implicit): tu pornești AI-ul. Fiecare document are stațiile Documentul (scanarea) → AI Extractorul →
  Regulile băncii (cod, fără AI) → câte un agent AI pe fiecare predare (corespondent, investigator, comunicator) → **Rândul
  tău (OM)**: nimic nu pleacă din bancă înainte să aprobi (scrisoarea către notar/asigurător, aprobată = și semnată;
  mesajul către moștenitor; propunerea investigatorului, acceptată = escaladarea închisă; plata; extracția sub 80%).
  „Nu” cere un motiv și nu trimite nimic; fiecare decizie, cu numele tău, ajunge în `runs/<run>/operator.jsonl`.
  Fiecare pas are **▶ Rulează pipeline-ul** (pe server, stație după stație, se oprește la fiecare decizie a ta) care devine
  **■ Oprește pipeline-ul** (apelurile AI din coadă se anulează; cel în curs se termină; „Reia” continuă de unde a rămas).
  Panoul „Activitate AI” arată fiecare apel (în coadă, lucrează cu secunde, gata cu durată și cost, eșuat, anulat) și ce
  așteaptă decizia ta. Autopilotul stă în pauză cât e pornit modul.
  API (`agent/ai_jobs.py`): `POST /demo/reset?manual=true`, `POST /demo/ai/extract|apply/{n}`, `POST /demo/ai/agent/{n}/{key}`,
  `POST /demo/ai/gate/{n}/{key}/approve|reject` (`{by, note}`), `POST /demo/ai/pipeline/{n}/run|stop`, `POST /demo/ai/audit`,
  `GET /demo/ai/jobs`, `GET /demo/ai/steps`.
- **Automat**: autopilotul face totul. „Documente: scanate”: scanările PDF (`registries/documents/scan/`, fără strat de text)
  intră în inbox și extractorul le citește vizual (`POST /demo/step/{n}?source=scan`, apoi `GET /demo/received/{fișier}`);
  „pre-extrase”: câmpurile din `*.mvp.json`, instant, fără LLM.

Ambele cer serverul pornit cu acces la Claude (Bedrock: `scripts/test-instance.sh start` sau `coordonare/bin/test-instance start`).
Un apel AI durează 7–20 s (extractorul) și 10–60 s (agenții).

Mesaje către moștenitori (mock, `runs/latest/outbox.jsonl`) și link de încărcare cu token de 7 zile:
`POST /messages`, `GET /messages?case_id=`, `POST /cases/{id}/upload-token`, pagina publică `GET /upload?token=`.

Document propriu: `curl -F file=@registries/documents/02-adresa-notar.json localhost:8000/cases/x/documents`
(JSON = deja extras; `.md`/`.txt` trec prin `agent/extract.py` dacă există, altfel se escaladează).

## Module

| Modul | Rol |
|---|---|
| `agent/rules.py` | funcții pure: sold la deces, comisioane de stornat, pensie post-deces, net de datorii, cote (largest remainder), acoperire, termene |
| `agent/case_state.py` | dosarul: milestone-uri, evenimente cu regula aplicată, escaladări, „ce lipsește” |
| `agent/pipeline.py` | orchestrarea: document → verificări → acțiuni pe core → escaladări; idempotent, orice ordine |
| `agent/core_mock.py` | core banking mock (clientul demo), aceleași metode ca `kb/tech/api-contract-bank.md` |
| `agent/api.py` | FastAPI: `/cases`, `/documents`, `/cases/{id}/documents`, `/payments/{id}/approve`, `/demo/*` |
| `agent/demo_documents.py` | încarcă `registries/documents/*.mvp.json` (cele 7 documente + 04-B + `hard/` H1–H11) |
| `agent/extract.py` | extractorul LLM + pasul determinist după el (normalizare, validări V1–V11, flaguri) |
| `tests/` | valorile exacte din scenariu + „și dacă…?” (ordine inversă, duplicat, cote greșite, CNP necunoscut) |
| `ops-ui/` | panoul operatorului (Marius) |
| `registries/documents/` | documentele demo ca text + ground truth (Ștefan) |

## Stabil vs. dezvoltare
- **:8000 = demo stabil**, rulează din `<checkout stabil>` (checkout al ultimului commit cu teste verzi). Se actualizează doar cu
  `coordonare/bin/promoveaza [commit]`, care refuză commit-uri cu teste roșii.
- **:8001 = dezvoltare**, din rădăcina repo-ului: `.venv/bin/uvicorn agent.api:app --port 8001 --reload`.
- Regula: niciun commit cu `pytest` roșu.
