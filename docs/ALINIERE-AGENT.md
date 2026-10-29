# Aliniere agent/ (MVP) cu KB, registries și ops-ui — listă pentru owner-ul lui `agent/`

Întreținută de master (nicolas). Sursa adevărului pentru date: `kb/scenariu-demo/maria-ionescu.md`,
`registries/documents/*.mvp.json` (identificatori §0), `docs/DECISIONS.md`.

## Date (agent/core_mock.py, agent/demo_documents.py)
- [x] CNP client RC1001: `2XXXXXXXXXXXX` (mascat), nu `2650903123456`; cu `DEMO_MODE=1` se sare doar peste cifra de control.
- [x] Cont curent: `CC-1` (nu `RO-CUR`); depozit `DEP-1`; credit `CRD-1` cu `loan_contract=NP-2023-001001`.
- [x] Poliță: `insurance_policy_id = UQ-0000000-FICTIV` (nu `POL-55`); dosar daună `DV-0451/2026`.
- [x] Referințe: dosar succesoral `123/2026`, certificat `87/2026`, supliment `95/2026`, notar fictiv „Ana EXEMPLU” (nu `CM 456/2026`, „BNP Popescu”).
- [x] `demo_documents.py` → încarcă `registries/documents/*.mvp.json` în loc de valori hard-codate.
- [x] Testele din `tests/` rulează și pe `registries/documents/hard/` (H1–H5) cu `expected_agent`.

## Cazuri grele (registries/documents/hard/, 021–022)
- [x] H10 (extras multilingv fără CNP): pipeline.py escaladează orice document fără `cnp`; ground truth = potrivire unică pe nume + prenume + data nașterii (core_mock are nevoie de `birth_date` pentru RC1001), confirmată de data decesului (= DGEP) și soț; altfel `identity_unconfirmed`.
- [x] H9: flag `misleading_header` (tipul se stabilește din conținut, nu din antet).
- [x] H6/H7/H8: normalizare dată în litere → ISO, cote în cuvinte → fracție, CNP cu spații/puncte → 13 cifre (în extractor/validări).

## Vocabular (DECISIONS)
- [x] `document_type` EN canonic (vezi `kb/glosar.md`).
- [x] Coduri de escaladare: `shares_invalid` (H3), `cnp_mismatch` (H4), `matched_without_iban` (H5), `illegible` (doc 7).

## API (agent/api.py ↔ kb/tech/ops-ui-contract.md, raport 019b-marius)
- [x] `case_id` în loc de `id`.
- [x] `products` la data decesului în `GET /cases/{id}`.
- [x] încredere per câmp (`fields` ca listă `{name, value, confidence, evidence}`).
- [x] `events.at` = data documentului (nu ora procesării).
- [x] stare pe termene (opțiune 1 an, avizare asigurare 30 zile, dezbatere notar).
- [x] `POST /payments/{id}/approve` pe `payment_id` + `POST /payments/{id}/reject` (cu motiv).
- [x] După aliniere: se șterge `ops-ui/adapter.js`.

## Stare (case_state.py)
- [x] `PLAN_DRAFTED` în `ORDER` (după reject, dosarul revine la PLAN_DRAFTED) — 037.

## Reguli (DECISIONS)
- [x] `.claude/agents/heir-communicator.md` regula 3: consimțământ doar pentru mesaje comerciale; operaționale pe GDPR 6(1)(b)/(c)/(f) (kb/legal/comunicare-canale-consimtamant.md).
- [x] Freeze pe semnal DGEP = doar măsuri reversibile.
- [x] Pensia lunii decesului se păstrează; cea de după → flag retur CNPP.
- [x] Premium 60 lei/lună; stornare de la data decesului.
- [x] Depozit nescadent: recomandare „așteaptă scadența”.
- [x] Partea minorului blocată până la documentele de reprezentare.
