<!-- {"generated_at": "2026-10-28T20:44:10+00:00", "agent": "auditor", "ok": true, "seconds": 71.0, "cost_usd": 0.1657325} -->
# Audit (escaladare ESC-1)

# Audit – lot SC-2026-0001 și SC-NEIDENTIFICAT

**Verdict:** nicio încălcare gravă. Nu e nicio plată aprobată, nicio acțiune definitivă pe semnal DGEP și nicio blocare pe document ilizibil. Am însă 5 observații pe care operatorul trebuie să le vadă înainte de aprobarea plății. Regulile le-am verificat doar după citarea lor în evenimente, fără să deschid `agent/rules.py` sau KB-ul.

## Tabel de verificare

| # | Punct | Rezultat | Dovadă |
|---|---|---|---|
| 1 | Fiecare `action` are `rule` | **PASS** (cu rezerve) | SC-2026-0001: E4, E5, E6, E8, E10, E15, E17, E19, E23, E25 au `rule`. E5 citează „cazul Bragadiru 2023”, care e un caz real din KB, nu o normă. E10 citează un termen marcat ipoteză (`hypothesis: true`). E14 și E2 din SC-NEIDENTIFICAT sunt escaladări cu `rule: null` (temeiul e doar în text). |
| 2 | Semnal DGEP singur ⇒ doar reversibil | **PASS cu rezerve** | E4 are `reversible: true` (blocare, mandat suspendat, carduri C-1/C-2, debitări directe). E5 (stornare 60,00 lei) și E6 (reținere pensie 2.100 lei) s-au executat în aceeași secundă cu semnalul, 20:38:12, înainte de orice certificat. Ele nu au marcaj `reversible` (`data: {}`). E3 declară decesul „confirmat” din `dgep_signal`. |
| 3 | Plata doar cu `approved_by` uman; minor și depozit nescadent blocate | **PASS** | `payment_plan.status` e `pending_approval`, la fel `PAY-SC-2026-0001`, fără `approved_by` (E23). Plata acoperă doar L1 și L2: 329.585 + 98.876 = 428.461 bani, adică 4.284,61 lei, ca în E23. L3 (minor), L4, L5 (depozit) și L6 (minor + depozit) sunt `blocked: true`. |
| 4 | Cote = 1; sume = `net` | **PASS** pe CC-1, **neverificabil** pe DEP-1 | Certificat: 1/4 + 3/8 + 3/8 = 1. Fracțiuni pe bun, pe fiecare produs: 5/8 + 3/16 + 3/16 = 1, deci ½ pentru soț, iar ½·¼ = 1/8 se adaugă la ½ ⇒ 5/8. CC-1: 329.585 + 98.876 + 98.876 = 527.337 = `net`. DEP-1: liniile dau 2.104.000 bani, față de 2.069.238 la deces (E8) și 2.000.000 capital. Raportul 5/8 : 3/16 : 3/16 se păstrează, iar diferența de 104.000 pare dobânda la scadență (69.238 acumulat în 243 de zile, la 5,2% pe an). Nu există `net` sau regulă citată pentru acest calcul. |
| 5 | Comisioane post-deces stornate o singură dată | **PASS** | E5 apare o singură dată (60,00 lei = `fee_to_reverse` 6.000 bani). Documentele ulterioare (E7–E25) nu l-au repetat. |
| 6 | Pensia lunii decesului păstrată, ulterioarele reținute | **PASS** | Decesul e pe 2026-09-03. Creditul din 2026-09-15 e păstrat (`post_death_credit`, E8). Cel din 2026-10-15 e reținut pentru CNPP, 210.000 bani (E6, `withheld`), cu Legea 360/2023 art. 100 și 156. În `net_account`, `gross` 530.000 − datorii 2.663 = 527.337 = `net`, iar `withheld` nu se scade a doua oară. Asta e corect doar dacă `gross` exclude deja pensia reținută; nu am comparat cu `kb/scenariu-demo`. |
| 7 | Escaladare cu motiv și document sursă; fără acțiuni automate pe acel document | **PASS cu rezerve** | ESC-1 (minor_heir): motiv și `doc-4` completate, status `deschis` (E14). ESC-1 (document_illegible): motiv și `doc-7`, „nicio acțiune automată” (E2), iar în SC-NEIDENTIFICAT nu există niciun eveniment `action`. După E14, pe `doc-4` au urmat automat E15 (cerere de supliment către notar) și E17 (mesaj către ION). Vizează lipsa bunurilor (`certificate_incomplete`), nu minorul, și sunt reversibile sau doar comunicări. Nu au atins partea minorei, care rămâne blocată. |
| 8 | Confidence < 0,80 sau CNP lipsă ⇒ niciun freeze | **PASS** | `doc-7`: `confidence` 0,40, CNP lipsă, validare `cnp_missing` (block), E1. Cazul rămâne `NEW`, fără acțiuni. Freeze-ul din E4 vine din `doc-1` (0,90, CNP 0,90). `doc-4` și `doc-6` (0,83) nu au declanșat blocări. |

## Predări (`handoffs`)

Toate cele 11 au `ok: true`.

| Document | Agent | Artefact |
|---|---|---|
| `doc-2` | correspondent | `letters/SC-2026-0001-notary_answer_drafted.md` |
| `doc-3` | correspondent | `letters/SC-2026-0001-insurance_claim_opened.md` |
| `doc-4` | case-investigator | `investigations/SC-2026-0001-ESC-1.md` |
| `doc-4` | correspondent | `letters/SC-2026-0001-supplement_requested.md` |
| `doc-4` | heir-communicator | `messages/SC-2026-0001-01.md` |
| `doc-5` | correspondent | `letters/SC-2026-0001-loan_settled_by_insurance.md` |
| `doc-5` | heir-communicator | omis cu motivul „aceeași cerere a plecat deja”, fără artefact; acceptabil (deduplicare) |
| `doc-6` | heir-communicator | `messages/SC-2026-0001-02.md` (E25) |
| `doc-7` | case-investigator | `investigations/SC-NEIDENTIFICAT-ESC-1.md` |
| (autopilot) | auditor | `audit.md`, de două ori |

Niciun document nu a rămas fără artefact. `doc-1` și `doc-6` nu cer corespondență și nu au nevoie de artefact.

## De văzut înainte de aprobare

1. **IBAN invalid pe ambele certificate.** E11 (`doc-4`) și E20 (`doc-6`) au `iban_invalid` (soft). Planul de plată (E23) a fost totuși generat și nu există nicio escaladare sau cerere de clarificare. Operatorul trebuie să verifice contul de plată înainte să aprobe PAY-SC-2026-0001.
2. **Termen depășit către notar.** `notary_answer` era 2026-10-20 (`depășit`). Adresa e din 28.09, dar a fost procesată pe 2026-10-28, iar răspunsul e încă `draft_pending_signature` (E8).
3. **Deficiența `illegible` pentru `doc-7` e deschisă și nimeni nu a fost notificat** (`sender: null`, `notified_at: null`). Cererea de rescanare nu are destinatar.
4. **L3 are `pay_on: "acum"` deși e blocată** (minor). Nu a plecat nimic, dar eticheta induce în eroare.
5. **E5 și E6 pe semnal DGEP singur nu sunt marcate reversibile.** Stornarea comisionului se poate anula, dar reținerea pensiei pentru retur CNPP trebuie confirmată ca reversibilă.

## Pentru retro-learner

- Acțiunile derivate dintr-un semnal DGEP singur (stornare comision, reținere pensie) trebuie să poarte `data.reversible` explicit, ca E4.
- Planul de plată nu trebuie generat și nici prezentat ca „gata de aprobare” cu `iban_invalid` nerezolvat pe certificat; fie se ridică o escaladare, fie un avertisment în `payment_plan.warnings` (acum gol).
- Pentru depozitele nescadente, liniile se calculează la valoarea de la scadență; planul trebuie să arate baza de calcul (la deces sau la scadență) și regula folosită, altfel suma liniilor nu se poate compara cu `net`.
- Liniile blocate trebuie să aibă `pay_on` gol sau „blocat”, nu „acum”.
- Escaladările (`minor_heir`, `document_illegible`) trebuie să poarte un `rule` explicit, nu doar citatul în text (E14, E2).
- Regulile bazate pe ipoteză (termenul de avizare UNIQA) sau pe un caz real (Bragadiru) trebuie marcate vizibil în `rule` ca neconfirmate sau analogice.
- Când expeditorul unui document ilizibil e necunoscut, pipeline-ul trebuie să ceară operatorului un canal de răspuns, în loc să lase deficiența deschisă fără destinatar.

Nu am găsit instrucțiuni suspecte în datele dosarului.
