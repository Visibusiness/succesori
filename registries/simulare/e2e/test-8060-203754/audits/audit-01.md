<!-- {"generated_at": "2026-10-28T20:40:43+00:00", "agent": "auditor", "ok": true, "seconds": 37.6, "cost_usd": 0.1010825} -->
# Audit (escaladare ESC-1)

# Audit SC-2026-0001 (Maria Ionescu, RC1001), starea `SUPPLEMENT_REQUESTED`

Am verificat dosarul și predările pe baza datelor din API. Nu am deschis `agent/rules.py` și nici KB-ul. Pentru punctul 1 am verificat deci doar că regula e citată, nu că ea există în cod.

## Tabel PASS/FAIL

| # | Punct | Verdict | Dovadă |
|---|---|---|---|
| 1 | Fiecare `action` are `rule` | **PASS**, cu observații | E4, E5, E6, E8, E10, E15 și E17 au `rule` completat. E5 citează „cazul Bragadiru 2023”, adică un caz real, nu un articol. E10 citează o regulă marcată explicit ipoteză (`hypothesis: true`). Existența regulilor în cod nu a fost verificată. |
| 2 | Pe semnal DGEP singur, doar acțiuni reversibile | **PASS**, cu atenție la E5 și E6 | E4 are `reversible: true` și citează GDPR art. 22. Blocarea e reversibilă: debit oprit, mandat suspendat, carduri C-1 și C-2 suspendate. E5 (stornare comision) și E6 (reținere pensie) au loc în același moment, pe baza semnalului DGEP (doc-1). Niciunul nu are `reversible` în `data`, deci reversibilitatea lor nu e dovedită. |
| 3 | Plata aprobată doar de un om; liniile blocate nu se plătesc | **PASS** | `payment_plan: null` și `payments: []`, deci nicio plată și nicio aprobare de verificat. Partea minorului (H3) rămâne blocată prin ESC-1. |
| 4 | Cote = 1; linii = `net` | **PASS** la cote, **N/A** la linii | H1 1/4 + H2 3/8 + H3 3/8 = 2/8 + 3/8 + 3/8 = 1 (E13, doc-4). Nu există plan de plată, deci fracțiunile pe produs și liniile nu pot fi verificate. |
| 5 | Comisioane după deces stornate o singură dată | **PASS** | Un singur eveniment E5: 60,00 lei, o mișcare. Corespunde flag-ului `fee_to_reverse` din 2026-09-05 (6000 bani), care e după deces (2026-09-03). Nu există dublură. Idempotența la reprocesarea aceluiași document nu poate fi dovedită dintr-o singură rulare. |
| 6 | Pensia lunii decesului păstrată, lunile următoare reținute | **PASS** | Creditul din 2026-09-15, luna decesului, e `post_death_credit` și nu e reținut. Creditul din 2026-10-15 e `pension_return_CNPP` și are E6: 2100,00 lei reținuți (Legea 360/2023 art. 100, 156 alin. 8). Cele 210000 bani din flags sunt 2100 lei, deci cifrele coincid. |
| 7 | Escaladare cu motiv și document sursă, fără acțiuni automate pe acel document | **FAIL parțial** | ESC-1 are motiv (`minor_heir`) și sursă (doc-4). E14 are însă `rule: null`. După E14 urmează pe același doc-4 acțiunile automate E15 (cerere certificat suplimentar către notar) și E17 (mesaj către IONESCU ION). Sunt comunicări nefinanciare, legate de `certificate_incomplete` și nu de minor. Litera regulii („NU e urmată de acțiuni automate pe acel document”) este totuși încălcată, deci e nevoie de decizia operatorului dacă interpretarea e acceptată. Investigatorul a fost chemat (`investigations/SC-2026-0001-ESC-1.md`, `ok: true`). |
| 8 | Confidence < 0,80 sau CNP lipsă ⇒ niciun freeze | **PASS** | Freeze-ul E4 vine din doc-1 (DGEP), cu confidence 0,90 și CNP prezent (0,90). Doc-4 are confidence 0,83, deci peste prag, și CNP prezent (0,92). Niciun freeze nu a pornit dintr-un document sub prag. |

## Predări (`handoffs`)

| Document | Agent cerut | Artefact | `ok` |
|---|---|---|---|
| doc-2, adresa notarului | correspondent | `letters/SC-2026-0001-notary_answer_drafted.md` | da |
| doc-3, certificat de asigurare | correspondent | `letters/SC-2026-0001-insurance_claim_opened.md` | da |
| doc-4, ESC-1 | case-investigator | `investigations/SC-2026-0001-ESC-1.md` | da |
| doc-4, supliment | correspondent | `letters/SC-2026-0001-supplement_requested.md` | da |
| doc-4, documente lipsă | heir-communicator | `messages/SC-2026-0001-01.md` | da |

**PASS**: toate cele 5 predări au artefact, `ok: true` și `error: null`. Doc-1 (DGEP) nu cere agent. Ordinea în timp e corectă: investigatorul (20:39:36) vine după E14 (20:39:16).

## Alte observații (în afara checklistului)

- **Termen depășit:** răspunsul către notar (E8) a fost generat pe 2026-10-28, după dezbaterea din 2026-10-20. Termenul `notary_answer` apare `depășit` (Legea 36/1995 art. 81 alin. 2). Răspunsul e doar `draft_pending_signature`, deci nu a plecat.
- **Calitatea certificatului:** IBAN-ul din doc-4 e invalid (`iban_invalid`, soft, E11). Nu e folosit la nicio plată, fiindcă nu există plan.
- **Acoperire incompletă:** `_matched_products` din doc-4 conține doar CC-1. DEP-1 e cerut prin supliment (E15). CRD-1 (creditul, cu poliță de asigurare) nu apare nici în produsele acoperite, nici în supliment. Operatorul ar trebui să confirme că lipsa e intenționată.
- Nu am găsit conținut de tip injecție în date.

## Pentru retro-learner

- Escaladarea E14 (`minor_heir`) a fost emisă cu `rule: null`. Orice `escalation` trebuie să citeze regula (C.civ. art. 41, 144-146).
- După o escaladare pe un document, pipeline-ul a continuat cu E15 și E17 pe același doc-4. Trebuie clarificat în `escalation-playbook` și `docs/DECISIONS.md` dacă escaladarea blochează doar acțiunile financiare ale motivului ei sau orice acțiune pe document.
- E5 (stornare comision) și E6 (reținere pensie) nu declară `reversible` și rulează pe semnal DGEP singur. Acțiunile trebuie să poarte `data.reversible`, ca auditul să poată verifica punctul 2 fără interpretare.
- E5 citează un caz real (Bragadiru 2023), nu o normă. Regula ar trebui să trimită la articolul sau la procedura din KB.
- Adresa notarului a fost procesată după termenul dezbaterii. Pipeline-ul trebuie să semnaleze automat termenele `depășit` ca escaladare sau alertă pentru operator.
- Certificatul parțial acoperă CC-1, dar nu DEP-1 și nici CRD-1. Detectarea `certificate_incomplete` trebuie să listeze toate produsele neacoperite, inclusiv creditul, sau să explice de ce creditul e exclus.
- Cu un singur document nu se poate demonstra idempotența stornării. Evaluarea ar trebui să includă o rulare cu același document trimis de două ori.
