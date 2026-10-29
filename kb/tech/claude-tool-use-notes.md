Sursă: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview ; https://platform.claude.com/docs/en/build-with-claude/structured-outputs ; https://platform.claude.com/docs/en/build-with-claude/pdf-support ; https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking · Accesat: 2026-10-28 · Owner: TECH

# Orchestrarea cu Claude: tool use și extracție cu scor de încredere

## Fapte din documentația Claude (relevante pentru noi)
- Tool-urile se definesc cu `name`, `description`, `input_schema` (JSON Schema). Descrierea trebuie să spună
  **când** să fie chemat tool-ul, nu doar ce face.
- `strict: true` pe definiția tool-ului (cu `additionalProperties: false` și `required`) garantează că argumentele
  respectă schema.
- Pe modelul implicit (`claude-opus-5-5`) **`tool_choice` `any`/`tool` (forțat) dă 400**: folosim `auto` +
  instrucțiune în prompt + verificare în cod că s-a chemat tool-ul.
- Mai multe tool-uri pot fi cerute într-un singur răspuns; toate `tool_result`-urile se trimit înapoi într-un singur
  mesaj `user`. Pentru un tool care eșuează: `tool_result` cu `is_error: true` și mesaj informativ.
- Ieșiri structurate: `output_config.format` (JSON Schema) sau `client.messages.parse()` — util pentru extracție.
  Nu se poate combina cu citations.
- PDF-uri: bloc `document` (base64 sau Files API); imaginile (scanări) ca bloc `image`. Limită 32 MB / cerere.
- Thinking: pe Opus 5.5 e adaptiv și nu se poate dezactiva; efortul (`output_config.effort`) are implicit
  `medium` — îl setăm explicit (`low` pentru clasificare, `high` pentru orchestrare).
- SDK-ul are un **Tool Runner** (`client.beta.messages.tool_runner`) care rulează bucla; gate-urile de aprobare
  umană se pun în funcția tool-ului.
- Rezidență date: pentru „LLM în regiune UE” (BRIEF §2) varianta realistă e Claude prin Vertex AI cu regiune `eu`
  sau Amazon Bedrock în regiune UE (de confirmat în Faza 1); nu e nevoie pentru demo.

## Arhitectura propusă (decizie de luat în `docs/DECISIONS.md`)
Recomandare: **workflow controlat de cod + LLM la puncte precise**, nu un agent liber.
1. **Intake** (cod): document nou → `classify_document` (LLM, efort `low`) → tip + scor.
2. **Extracție** (LLM, ieșire structurată pe schema tipului) → câmpuri + scor per câmp.
3. **Validare** (cod, deterministă): CNP din document = CNP client, dată deces ≤ data documentului, cote care
   însumează 1, produse din certificat ⊂ produse client etc.
4. **Orchestrare** (LLM cu tool-uri, efort `high`): primește starea dosarului + documentul validat și decide
   pașii următori chemând tool-urile de mai jos. Mașina de stări din `api-contract-bank.md` respinge pașii invalizi.
5. **Escaladare** (cod): scor sub prag, validare picată, `409`/`422` de la API, stare imposibilă → `ESCALATED`.

Juriul cere „decizii multi-pas” și „situații neașteptate tratate explicit”: pasul 4 dă deciziile, pașii 3 și 5
fac excepțiile vizibile și testabile.

## Tool-urile agentului (orchestrare)
| Tool | Când îl cheamă (în descriere) | Endpoint / funcție |
|---|---|---|
| `open_or_get_case` | la orice document pentru un client fără dosar deschis | `POST /cases` |
| `freeze_customer` | la primul document care atestă decesul cu scor ≥ prag | `POST /customers/{cif}/freeze` |
| `get_products_at_date` | înainte de orice răspuns către notar sau calcul | `GET /customers/{cif}/products?as_of=` |
| `compute_balance_at_death` | pentru răspunsul către notar | `balance_at_death()` |
| `compute_fees_to_reverse` + `reverse_fees` | după freeze, dacă există comisioane după data decesului | `fees_to_reverse()` + `POST …/fees/reverse` |
| `flag_post_death_credits` | dacă există încasări după deces (pensie) | `post_death_credits()` |
| `draft_notary_reply` | la adresa notarului | generează documentul din `document-templates/raspuns-banca-catre-notar.md` |
| `open_insurance_claim` | credit cu poliță de viață + deces confirmat | mock asigurător |
| `check_certificate_coverage` | la certificatul de moștenitor | `coverage_gaps()` |
| `request_supplement` | dacă lipsesc produse din certificat | generează cererea către notar |
| `draft_payment_plan` | certificat complet + datorii stinse/calculate | `split_by_shares()` + `net_of_debts()` + `POST …/payment-plan` |
| `submit_payment_for_approval` | plan validat | `POST /payments` (stare `pending_approval`) |
| `escalate` | orice excepție: scor mic, neconcordanță, minor fără autorizare, litigiu | `PATCH /cases/{id}` → `ESCALATED` |
| `schedule_reminder` | termene (opțiune succesorală 1 an, răspuns asigurător) | tabel termene în dosar |

Nu există tool pentru aprobarea plății.

## Schema de extracție cu scor (comună tuturor tipurilor)
```json
{
  "document_type": "certificat_deces | adresa_notar | certificat_mostenitor | certificat_suplimentar | polita_asigurare | raspuns_asigurator | semnal_dgep | procura | altul",
  "type_confidence": 0.0,
  "subject": { "full_name": "", "cnp": "", "confidence": 0.0 },
  "fields": [ { "name": "date_of_death", "value": "2025-09-03", "confidence": 0.0, "evidence": "citat din document" } ],
  "legibility": "ok | partial | illegible",
  "issues": [ "text liber: ce lipsește/nu se potrivește" ]
}
```
`evidence` (citatul) e obligatoriu pentru câmpurile critice — permite verificarea umană și demonstrația în fața
juriului. Câmpurile specifice fiecărui tip vin din `kb/document-templates/*.md` („Ce înseamnă pentru agent”).

## Praguri propuse (de calibrat pe cele 7 documente din demo)
| Situație | Regulă |
|---|---|
| `type_confidence < 0.80` sau `legibility = illegible` | escaladare, nimic automat (documentul 7 din demo) |
| câmp critic (CNP, dată deces, cote, sume) `< 0.90` | escaladare a câmpului, restul dosarului continuă |
| CNP document ≠ CNP client | escaladare, niciun freeze |
| cote care nu însumează 1 | escaladare |
| moștenitor minor | plata părții lui blocată până la documentul de autorizare/reprezentare (vezi `kb/legal/mostenitor-minor.md`) |

## Necunoscut
- Scorurile de încredere declarate de model nu sunt probabilități calibrate. În Faza 1 le combinăm cu validările
  deterministe (pasul 3); pentru demo, pragurile se fixează pe setul de test.

## Ce înseamnă pentru agent
- Calculele nu se fac niciodată în LLM; LLM-ul alege tool-ul, codul calculează.
- Fiecare tool are descriere cu condiția de declanșare; `strict: true` pe toate.
- Orice document trece clasificare → extracție → validare înainte de orchestrare; escaladarea e un tool ca oricare altul
  și apare în istoria dosarului.
