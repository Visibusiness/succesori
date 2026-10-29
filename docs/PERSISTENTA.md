# Persistență și portofoliul de clienți (sarcina 084)

## Ce se salvează

Tot ce știe API-ul (`agent/api.py`), după **fiecare cerere care poate schimba starea** (POST/PUT/PATCH/DELETE, inclusiv
cele refuzate cu 4xx: un mesaj oprit lasă totuși o escaladare `unsafe_output`), și după fiecare document trimis de
firele demo-ului ghidat (`agent/ai_jobs.py`, în afara unei cereri HTTP):

| Ce | Unde în SQLite | Cum se serializează |
|---|---|---|
| dosarele: etape (milestones), documente, evenimente cu id, escaladări, plan de plată, termene, asigurare, flags, contacte, chei de idempotență | tabelul `cases`, un rând pe dosar | `Case.to_dict` / `Case.from_dict` (`agent/case_state.py`): date ISO, mulțimi ca liste sortate |
| core-ul mock: clienți (cu blocările), produse, mișcări, IBAN-uri, contracte de credit, contacte KYC, stornări, plăți, jurnalul de audit | `state.bank` | `Bank.to_dict` / `Bank.from_dict` (`agent/core_mock.py`): `Fraction` ca șir „1/2”, date ISO |
| datele API-ului: extracțiile, datele evenimentelor, tokenurile de încărcare, scara de contact făcută, persoana care a notificat, documentele cu probleme și ce s-a comunicat, ceasul demo, modul pas-cu-pas, data portofoliului | `state.api` | JSON (mulțimile ca liste) |
| fișierele run-ului: `outbox.jsonl` (mesajele), `handoffs.jsonl`, `letters/`, `messages/`, `investigations/`, `audits/`, `audit.md` | `state.artifacts` | text |
| run-ul (id, epoch) | `state.run` | JSON |

Fără pickle. O cerere = **o tranzacție** (`BEGIN IMMEDIATE … COMMIT`, rollback la eroare); se scriu doar rândurile
al căror JSON s-a schimbat. La pornire (`_boot`), dacă baza are o stare, ea înlocuiește memoria; altfel banca pornește
proaspătă (cu portofoliul). Fișierele run-ului se refac în directorul run-ului nou dacă lipsesc (de exemplu după
`scripts/test-instance.sh start`, care pornește mereu un `RUN_ID` nou); dacă vechiul director există încă pe disc, versiunea de
acolo are prioritate (autopilotul scrie fișierele direct, fără să treacă prin API). `GET /store/status` spune unde e
baza și când s-a scris ultima dată.

## Unde

- `MVP_DB=<cale>`: explicit; `MVP_DB=:memory:` (sau `off`) = fără persistență.
- implicit, dacă `RUNS_DIR` e setat (instanțele de test: `coordonare/bin/test-instance`, pytest): `$RUNS_DIR/<RUN_ID>/mvp.sqlite`,
  deci fiecare instanță de test pornește cu o bancă nouă;
- altfel (MVP-ul viu pe :8001): `data/mvp.sqlite`; `data/` nu e în git (`data/.gitignore`).

## Portofoliul și resetul

- `registries/portofoliu/P*.json` + `README.md`: 14 clienți fictivi (P13, P14 pe cazuri reale, 085), fiecare cu povestea și etapa lui;
  `agent/portfolio.py` îi pune în core și le reia istoria prin pipeline-ul real (documente pre-extrase, fără LLM).
- `POST /demo/reset`: portofoliul din nou în starea inițială + Maria Ionescu la zero (primul ei document deschide tot
  `SC-2026-0001`, ca înainte; dosarele portofoliului au numere proprii). Demo-ul ghidat merge ca înainte.
- `POST /demo/reset?gol=1`: banca goală (doar Maria în core, niciun dosar), pentru `scripts/smoke_e2e.py`.
- `MVP_PORTFOLIO=0` face din banca goală implicitul (pytest, `coordonare/bin/live`); `?portofoliu=1` cere portofoliul oricum.
- Autopilotul nu conduce scara de contact și notificările de documente cu probleme ale clienților din portofoliu
  (`portfolio: true` în `GET /cases`): sunt lista de lucru a operatorului, iar un salt al ceasului demo ar porni un agent
  pentru fiecare client; nici auditorul nu le primește (13 dosare complete într-un prompt). `AUTOPILOT_PORTFOLIO=1` îl lasă
  să le conducă. Documentele noi trimise pentru ei trec normal.

Lista de lucru: `GET /worklist?filtru=toate|de_aprobat|escaladari|documente|termene&q=<nume, CNP, dosar>` (tabul
„Dosare” din ops-ui și contorul „X decizii te așteaptă” din antet).

## Limite

- **SQLite într-un singur proces.** Un singur server uvicorn (un worker) scrie baza; două procese pe aceeași cale și-ar
  suprascrie starea (fiecare ține totul în memorie și scrie instantaneul lui). În producție: Postgres, cu tranzacția pe
  cerere și blocare pe dosar (`SELECT … FOR UPDATE`), fără stare în memoria procesului.
- Instantaneul se ia după cerere: o cerere care rulează în paralel cu alta poate fi prinsă la jumătate, dar următoarea
  cerere care schimbă starea o scrie complet. Firele demo-ului ghidat salvează la fiecare document.
- Starea joburilor AI ale demo-ului ghidat (`/demo/ai/*`) nu se salvează: după o repornire în mijlocul lui, demo-ul
  pas-cu-pas se ia de la capăt (dosarele rămân).
- Fișierele scrise de autopilot după ultima cerere (de exemplu un `audit.md`) ajung în bază la următoarea cerere; până
  atunci rămân doar în directorul run-ului.
- Fișierele primite (inbox, carantină) rămân pe disc, în `registries/inbox/`; baza ține doar ce s-a extras din ele.
