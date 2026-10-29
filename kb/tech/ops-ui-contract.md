Sursă: generat de noi (kb/tech/api-contract-bank.md, kb/scenariu-demo/maria-ionescu.md v1.1) · Accesat: 2026-10-28 · Owner: TECH

# Ce consumă ops-ui din API (propunere de formă pentru `GET /cases/{id}`)

`api-contract-bank.md` spune ce conține dosarul, dar nu forma exactă. Aceasta e forma pe care o folosește
`ops-ui/` și pe care o are `ops-ui/mock-data.json`; `core-mock` o poate adopta sau o putem ajusta împreună.
Sume în bani (int), date ISO, cote ca fracții-text exacte („5/8”).

## Endpoint-uri folosite
| Endpoint | Folosit pentru | În contract? |
|---|---|---|
| `GET /cases` | coada; acceptă listă sau `{ "cases": [...] }`, cu cel puțin `case_id`, `state`, `deceased.name`, `updated_at` | da |
| `GET /cases/{id}` | detaliul (forma de mai jos) | da |
| `POST /cases/{id}/documents` | upload multipart: `file` + opțional `document_type` | da |
| `POST /payments/{id}/approve` | aprobare; UI-ul trimite `X-Role: ops_approver` până avem autentificare | da |
| `POST /payments/{id}/reject` `{ "reason": "..." }` | respingere cu motiv; dosarul revine în `PLAN_DRAFTED` | **nu — propunere** |
| `GET /escalations?unmatched=true` | documente fără dosar (ex. documentul 7) | **nu — propunere**; UI-ul încă nu-l apelează |

## Forma dosarului
```json
{ "case_id": "SC-2026-0001", "state": "PAYMENT_PENDING_APPROVAL", "opened_at": "2026-09-20", "updated_at": "2026-11-10",
  "deceased": { "name": "Maria Ionescu", "cnp": "2XXXXXXXXXXXX", "cif": "RC1001", "date_of_death": "2026-09-03" },
  "state_history": [ { "state": "FROZEN", "at": "2026-09-20", "by_document": "doc-001" } ],
  "products_as_of": "2026-09-03",
  "products": [ { "id": "RO..CUR", "type": "current_account", "label": "Cont curent", "iban": "…", "balance": 320000, "accrued_interest": 0 } ],
  "heirs": [ { "heir_id": "H3", "name": "Elena Ionescu", "relation": "fiică", "minor": true, "legal_representative": "H1" } ],
  "documents": [ { "document_id": "doc-004", "document_type": "certificat_mostenitor", "received_at": "2026-10-22",
                   "source": "Notar", "legibility": "ok", "confidence": 0.94, "variant": "A",
                   "fields": [ { "name": "mostenitori_si_cote", "value": "…", "confidence": 0.95 } ] } ],
  "events": [ { "at": "2026-09-20T10:02:13Z", "action": "Stornare comision", "rule": "fees_to_reverse — …",
                "detail": "Premium 2026-09-05", "document_id": "doc-001", "amount": 6000, "audit_id": "A-0002" } ],
  "deadlines": [ { "name": "Termen opțiune succesorală", "date": "2027-09-03", "rule": "C.civ. art. 1103", "status": "deschis" } ],
  "open_tasks": [ "Aprobare plată PAY-1 (ops_approver)" ],
  "escalations": [ { "at": "…", "reason": "…", "document_id": "…", "status": "deschis" } ],
  "payment_plan": { "plan_id": "PP-1", "status": "submitted", "variant": "A", "variant_label": "4A — moștenire legală",
    "lines": [ { "line_id": "L3", "heir_id": "H3", "name": "Elena Ionescu", "share": "3/16", "product_id": "RO..CUR",
                 "amount": 98876, "pay_on": "acum", "blocked": true, "blocked_reason": "minoră: …" } ],
    "withheld": [ { "reason": "pension_return_CNPP", "label": "Pensie octombrie — retur CNPP", "amount": 210000 } ],
    "warnings": [ "minor_requires_authorization" ] },
  "payments": [ { "payment_id": "PAY-1", "plan_id": "PP-1", "status": "pending_approval", "line_ids": ["L1","L2"], "total": 428461 } ] }
```
- `events[].rule` e obligatoriu: UI-ul arată pentru fiecare acțiune a agentului regula aplicată.
- `pay_on`: `"acum"` sau o dată ISO (depozitul se plătește la scadență, 2027-01-03).
- `status` termen: `deschis | în așteptare | îndeplinit | programat | depășit`.
- În mock, `case_id` are sufixul `~N` (pasul demo-ului) și câmpurile `snapshot_of`, `demo_step`, `demo_label`; API-ul real nu le are.

## Necunoscut
- Autentificarea reală pentru `ops_approver` (acum header `X-Role`, doar pentru demo).
- Dacă respingerea duce dosarul în `PLAN_DRAFTED` sau în `ESCALATED`: propunerea noastră e `PLAN_DRAFTED` + eveniment cu motiv.

## Ce înseamnă pentru agent
- Agentul scrie în `events` câte o intrare cu `rule` pentru fiecare acțiune; fără ea, operatorul nu poate audita decizia.
- `approve`/`reject` nu sunt tool-uri ale agentului.
