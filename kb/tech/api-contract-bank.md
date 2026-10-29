Sursă: generat de noi (BRIEF.md §2 „Model de deploy”, §3) · Accesat: 2026-10-28 · Owner: TECH

# Contractul API al băncii (core-mock) pentru agentul de succesiune

Propunere de lucru pentru Faza 1. Este contractul pe care `core-mock/` îl implementează și pe care `agent/` îl
apelează prin tool-uri. Aceleași 6 endpoint-uri sunt cele pe care banca le-ar expune unui hub extern (Faza 2,
`DEPLOYMENT_MODE=hub`). Sumele sunt în **bani (integer, RON × 100)**, datele în ISO `YYYY-MM-DD`, ca să nu avem
erori de rotunjire în calculele deterministe.

## Principii
- **Idempotent**: orice operație care schimbă starea primește `Idempotency-Key` (documentul sursă + acțiunea). Același
  document procesat de două ori nu blochează/stornează de două ori — scenariu „și dacă…?” demonstrabil.
- **La data decesului**: interogările de sold acceptă `as_of`; nu există sold „de azi” în dosarul succesoral.
- **Plata nu se execută de agent**: `POST /payments` creează o instrucțiune în stare `pending_approval`; doar un
  utilizator uman (rol `ops_approver`) o trece în `approved`.
- **Audit**: fiecare răspuns care schimbă starea întoarce `audit_id`; agentul îl atașează la evenimentul din dosar.

## 1. `POST /customers/{cif}/freeze` — blocare la semnal de deces
Cerere:
```json
{ "date_of_death": "2025-09-03", "source": "DGEP|notar|familie|certificat_deces",
  "source_document_id": "doc-001", "evidence_confidence": 0.97 }
```
Efect (toate atomic): blocare debit pe toate conturile; revocare împuterniciri (C.civ. art. 2030, CGB 3.2);
închidere carduri principale și suplimentare (CGB 5.10.4 c); suspendare debitări directe/ordine programate;
suspendare comisioane de administrare. Încasările rămân permise, dar marcate (`post_death_credit=true`).
Răspuns `200`:
```json
{ "cif": "RC1001", "frozen_at": "2025-09-20T10:02:11Z", "already_frozen": false,
  "revoked_mandates": [{"mandate_id": "M-7", "holder": "Andrei Ionescu"}],
  "cancelled_cards": ["C-1", "C-2"], "suspended_direct_debits": [], "audit_id": "A-…" }
```
Erori: `404` client inexistent · `409` CNP din document ≠ CNP client (agentul escaladează) ·
`422` `evidence_confidence` sub prag (nu se blochează pe un document nesigur).

## 2. `GET /customers/{cif}/products?as_of=2025-09-03` — produse la data decesului
Răspuns:
```json
{ "cif": "RC1001", "as_of": "2025-09-03", "products": [
  { "id": "RO..CUR", "type": "current_account", "currency": "RON", "balance": 320000, "accrued_interest": 0, "holders": ["RC1001"] },
  { "id": "DEP-1", "type": "term_deposit", "currency": "RON", "principal": 2000000, "rate_pct": 5.5,
    "start": "2025-07-03", "maturity": "2026-01-03", "accrued_interest": 18740, "early_termination": "interest_lost|reduced_rate" },
  { "id": "CRD-1", "type": "personal_loan", "currency": "RON", "outstanding": -900000, "accrued_interest": -4100,
    "insurance_policy_id": "POL-55" } ],
  "post_death_movements": [
    { "date": "2025-09-15", "amount": 210000, "kind": "pension_credit", "counterparty": "CNPP" },
    { "date": "2025-10-01", "amount": -2500, "kind": "fee", "fee_code": "PREMIUM" } ] }
```
Notă: `accrued_interest` este calculat de core la `as_of` (sau de funcția deterministă `balance_at_death`, dacă
core-ul dă doar mișcările). Valorile de mai sus sunt doar ilustrative; cele oficiale sunt în
`kb/scenariu-demo/maria-ionescu.md`.

## 3. `POST /customers/{cif}/fees/reverse` — stornare comisioane după deces
Cerere: `{ "from_date": "2025-09-03", "fee_codes": ["PREMIUM"], "reason": "decease" }`
Răspuns: `{ "reversed": [{"date":"2025-10-01","amount":2500}], "total_reversed": 2500, "audit_id": "A-…" }`
Calculul listei e făcut de `fees_to_reverse()` (funcție pură); endpoint-ul doar execută ce i se dă și refuză
(`409`) comisioanele deja stornate.

## 4. `POST /cases/{case_id}/payment-plan` — plan de plată pe moștenitori
Cerere (produsă de `split_by_shares()` + `net_of_debts()`):
```json
{ "basis_documents": ["cert-mostenitor-001", "cert-suplimentar-001"],
  "lines": [ { "heir_id": "H1", "name": "Ion Ionescu", "share": "1/2", "product_id": "RO..CUR", "amount": 0, "iban": null },
             { "heir_id": "H3", "name": "Elena Ionescu", "share": "1/4", "minor": true, "legal_representative": "H1",
               "requires_court_authorization": true } ],
  "withheld": [ { "reason": "pension_return_CNPP", "amount": 210000 } ] }
```
Răspuns: `{ "plan_id": "PP-1", "status": "draft", "warnings": ["minor_requires_authorization"] }`

## 5. `POST /payments` și `POST /payments/{id}/approve` — plata efectivă (cu om în buclă)
- `POST /payments` `{ "plan_id": "PP-1", "line_ids": [...] }` → `{ "payment_id": "PAY-1", "status": "pending_approval" }`
- `POST /payments/{id}/approve` — **doar rolul `ops_approver`**; tokenul agentului primește `403`.

## 6. `GET|POST|PATCH /cases` — dosarul de succesiune
- `POST /cases` `{ "cif": "RC1001", "opened_by_document": "doc-001" }` → `{ "case_id": "SC-2025-0001", "state": "DEATH_SIGNALLED" }`
  (dacă există deja un dosar deschis pentru CIF → `200` cu dosarul existent, nu dublură).
- `GET /cases/{id}` → stare, documente primite, evenimente, termene (ex. `option_deadline = date_of_death + 1 an`),
  sarcini deschise, escaladări.
- `PATCH /cases/{id}` → tranziții de stare validate de mașina de stări (vezi mai jos); o tranziție invalidă dă `409`.
- `POST /cases/{id}/documents` → atașează documentul + rezultatul extracției (`document_type`, `fields`, `confidence`).

## Mașina de stări a dosarului (propunere)
```
DEATH_SIGNALLED → FROZEN → NOTARY_REQUESTED → NOTARY_ANSWERED → [INSURANCE_CLAIM_OPEN → INSURANCE_SETTLED]
   → HEIR_CERT_RECEIVED → (COVERAGE_GAP → SUPPLEMENT_REQUESTED → SUPPLEMENT_RECEIVED) → PLAN_DRAFTED
   → PAYMENT_PENDING_APPROVAL → PAID → CLOSED
Oricând: → ESCALATED (cu motiv) → înapoi în starea anterioară după decizia umană
```
Documentele pot veni în orice ordine: o tranziție care „sare” o stare (ex. certificatul de moștenitor înainte de
semnalul DGEP) deschide automat dosarul și execută întâi pașii obligatorii (freeze), apoi procesează documentul.

## Funcții deterministe (în `agent/rules/`, testate; LLM-ul nu calculează)
| Funcție | Intrare | Ieșire |
|---|---|---|
| `balance_at_death(products, movements, date_of_death)` | produse + mișcări | sold + dobândă acumulată la data decesului |
| `fees_to_reverse(movements, date_of_death)` | mișcări | lista comisioanelor de stornat |
| `post_death_credits(movements, date_of_death, rules)` | mișcări | încasări de returnat (pensie) vs. de păstrat |
| `net_of_debts(assets, debts, insurance_payout)` | sume | masa netă (C.civ. art. 1114, limita activului) |
| `split_by_shares(net_by_product, heirs)` | sume + cote (fracții exacte) | sumă per moștenitor per produs, rest de rotunjire alocat determinist |
| `coverage_gaps(products, heir_certificate)` | produse + produse menționate în certificat | produse omise → cerere de supliment |

## Necunoscut
- Formatul real al interfețelor core-banking Raiffeisen (nepublic). Contractul de mai sus e al nostru, inspirat de
  practica REST; în pitch îl prezentăm ca „adaptor” către core.
- Regula exactă de dobândă la depozitul nescadent la decesul titularului → depinde de sarcina 003.

## Ce înseamnă pentru agent
- Agentul are câte un tool pentru fiecare endpoint (vezi `claude-tool-use-notes.md`); `approve` NU e tool al agentului.
- Toate sumele trec prin funcțiile deterministe; agentul doar decide ce funcție să cheme și cu ce documente.
- `409`/`422` sunt semnale de escaladare, nu erori de ignorat.
