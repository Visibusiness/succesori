<!-- {"generated_at": "2026-10-28T20:42:30+00:00", "agent": "auditor", "ok": true, "seconds": 58.9, "cost_usd": 0.144345} -->
# Audit (plan de plată SC-2026-0001)

# Audit SC-2026-0001 (Maria Ionescu), stare `PAYMENT_PENDING_APPROVAL`

Am verificat dosarul doar pe baza JSON-ului primit din API. Nu am deschis `agent/rules.py` sau KB-ul. La punctul 1 verific deci că regula este citată, nu că există în cod.

## Tabel PASS/FAIL

| # | Verificare | Rezultat | Dovadă |
|---|---|---|---|
| 1 | Acțiuni cu `rule` completat | **PASS** (cu 2 observații) | Toate acțiunile (E4, E5, E6, E8, E10, E15, E17, E19, E23, E25) au `rule`. Existența regulilor în `rules.py`/KB nu a fost verificată aici. Observații: E5 citează „cazul Bragadiru 2023”, un caz real din KB și nu un articol. E10 citează o ipoteză declarată („30 de zile, de confirmat”), marcată `hypothesis: true`. |
| 2 | Semnal DGEP singur ⇒ doar reversibil | **PASS cu rezervă** | E4 are `reversible: true` și citează GDPR art. 22. E5 (stornare 60,00 lei) și E6 (reținere pensie 2100,00 lei) au rulat în același lot, la 20:38:12, tot pe semnalul DGEP singur. Ele nu poartă marcajul `reversible` (`data: {}`). E6 este doar o reținere pentru retur CNPP, fără retur efectiv. E3 scrie „Deces confirmat… (sursă: dgep_signal)” deși există doar semnalul. |
| 3 | Plata doar cu `approved_by` uman; linii blocate neplătite | **PASS** | `payment_plan.status` și `payments[0].status` sunt `pending_approval`, fără `approved_by` și fără trecere în `approved`. `PAY-SC-2026-0001` cuprinde doar L1+L2 = 329585 + 98876 = 428461 bani, adică 4284,61 lei, ca în E23. L3, L4, L5, L6 sunt `blocked: true` (minor, depozit nescadent până la 2027-01-03) și nu sunt în plată. |
| 4a | Cote moștenitori = 1 | **PASS** | 1/4 + 3/8 + 3/8 = 1 (E13 și `heirs`). |
| 4b | Fracțiuni din bun = 1 pe fiecare produs (comunitate de bunuri) | **PASS** | CC-1 și DEP-1 au 5/8 + 3/16 + 3/16 = 16/16, adică soț ½ + ½·¼ și copii ½·3/8. |
| 4c | Sume linii = `net` | **PASS pe CC-1**, **neverificabil pe DEP-1** | CC-1: 329585 + 98876 + 98876 = 527337 = `net_account.net`. DEP-1: liniile dau 1315000 + 394500 + 394500 = 2.104.000 bani. Dosarul nu are `net` pentru DEP-1. Notarului i s-a comunicat 2.069.238 la data decesului (E8). Diferența (+34.762 bani) pare dobândă proiectată până la scadență, dar nu e explicată în dosar. |
| 5 | Comisioane după deces stornate o dată | **PASS** | Un singur eveniment, E5: 60,00 lei, 1 mișcare. Coincide cu `flags[fee_to_reverse]` = 6000 bani. Nu există stornare dublă după documentele 02–06. |
| 6 | Pensia lunii decesului păstrată, lunile următoare reținute | **PASS** | Decesul e din septembrie. Creditul din 2026-09-15 (210000) nu e reținut. Creditul din 2026-10-15 (210000) este în `withheld` și în E6, o singură dată (Legea 360/2023 art. 100, 156). |
| 7 | Escaladare cu motiv, document sursă, fără acțiuni automate pe document | **PASS cu rezervă** | ESC-1 (`minor_heir`, doc-4, E14) are motiv și document sursă și este încă deschisă. Plata minorului e blocată (L3, L6). După E14, pe același doc-4, au rulat E15 (cerere certificat suplimentar), E16 și E17 (mesaj SUPPLEMENT_NEEDED către Ion). Ele privesc `certificate_incomplete`, nu minorul, dar sunt acțiuni automate pe documentul escaladat. E14 are `rule: null` (temeiul C.civ. art. 41, 144-146 apare doar în text). |
| 8 | Extracție: `confidence` < 0,80 sau CNP lipsă ⇒ niciun freeze | **PASS** | Freeze-ul (E4) vine din doc-1 (confidence 0,90, CNP prezent). doc-4 și doc-6 au 0,83, deci peste prag, cu CNP prezent. Câmpurile au confidence ≥ 0,90, cu excepția `ibans` din doc-4 (0,95) și doc-6 (0,93), care sunt la fel peste prag. Niciun document nu e în carantină. |

## Predări (`handoffs`)

| Document | Agent | Artefact | `ok` |
|---|---|---|---|
| doc-2 (adresă notar) | correspondent | `letters/…-notary_answer_drafted.md` | ✔ |
| doc-3 (certificat asigurare) | correspondent | `letters/…-insurance_claim_opened.md` | ✔ |
| doc-4 (escaladare ESC-1) | case-investigator | `investigations/…-ESC-1.md` | ✔ |
| doc-4 (supliment) | correspondent | `letters/…-supplement_requested.md` | ✔ |
| doc-4 | heir-communicator | `messages/…-01.md` | ✔ |
| doc-5 (răspuns asigurător) | correspondent | `letters/…-loan_settled_by_insurance.md` | ✔ |
| doc-5 | heir-communicator | fără artefact | ✔ (`skipped`: „aceeași cerere a plecat deja”, idempotență corectă) |
| doc-6 (certificat suplimentar) | heir-communicator | `messages/…-02.md` | ✔ |
| doc-1 (DGEP) | – | – | Nu cere agent. |
| auditor (autopilot) | auditor | `audit.md` | ✔ (doar pentru ESC-1, la 20:40:43) |

Toate predările au `ok: true` și `error: null`. Nu lipsește niciun artefact.

## Ce e în regulă
- Nicio plată aprobată fără om. Planul și plata așteaptă aprobarea.
- Minorul (L3, L6) și depozitul nescadent (L4, L5) sunt blocate.
- Cotele și fracțiunile din bun însumează 1.
- Comisionul e stornat o dată, iar pensia e tratată corect.
- Datoria rămasă (26,63 lei, E19) este dedusă din `net` (`debts_deducted: 2663`). Indemnizația (900000) acoperă creditul (`outstanding` −900000).

## Neconcordanțe și atenționări (pentru operator)
1. **E5 și E6 pe semnal DGEP singur**, fără marcaj `reversible`. Stornarea comisionului și reținerea pensiei ar trebui marcate explicit ca reversibile sau condiționate de un document care confirmă decesul.
2. **E14 are `rule: null`**. Temeiul legal e doar în `detail`.
3. **E15, E16, E17 vin după E14 pe doc-4.** Trebuie confirmat că regula „fără acțiuni automate pe documentul escaladat” se aplică doar pentru problema escaladată (minorul) și nu și pentru alte probleme ale aceluiași document.
4. **Liniile DEP-1 însumează 2.104.000 bani.** În E8 s-au comunicat notarului 2.069.238 la data decesului. Dosarul nu arată un `net` pentru depozit și nici baza de calcul a diferenței.
5. **`net_account`:** `gross` 530000 − `debts_deducted` 2663 = `net` 527337, iar `withheld` (210000) nu apare scăzut în formulă. Probabil `gross` e deja fără retur CNPP (320000 + 210000 + 210000 − 210000), dar câmpul nu spune asta și poate induce în eroare.
6. **IBAN-uri invalide (soft)** în doc-4 și doc-6 (E11, E20). Planul nu folosește IBAN-urile, dar validarea trebuie rezolvată înainte de aprobarea plății.
7. **Termenul „Răspuns către notar” (2026-10-20) este `depășit`.** Răspunsul din E8 este încă „draft_pending_signature”, deci dezbaterea a trecut deja fără el.
8. **Reprezentantul legal al Elenei (Ion) este și moștenitor.** Acordul lui rămâne document lipsă (`missing`, ESC-1). Operatorul trebuie să aprecieze dacă e nevoie de un curator special.
9. **Auditul automat a rulat doar la ESC-1** (20:40:43). Nu a rulat după generarea planului (E23) și după doc-6.

⚠ injection_suspected: niciuna. Nu am găsit în câmpuri sau citate instrucțiuni adresate agenților.

## Pentru retro-learner
- Acțiunile de stornare comision și reținere pensie declanșate de semnal DGEP singur trebuie să poarte `data.reversible` explicit, ca E4.
- Evenimentele de tip `escalation` trebuie să aibă `rule` completat (ex. C.civ. art. 41, 144-146 pentru `minor_heir`), nu doar în text.
- Regula 7 din checklist trebuie precizată: acțiunile pe un document escaladat sunt interzise doar pe motivul escaladării, sau pe tot documentul?
- `net_account` trebuie să arate explicit dacă `gross` include sau exclude sumele reținute (`withheld`), ca formula să se poată verifica.
- Pentru produsele cu dobândă proiectată (depozit), planul trebuie să afișeze baza (valoare la deces vs. la scadență), ca suma liniilor să se compare cu un `net` explicit.
- Termenul de răspuns către notar a fost depășit (2026-10-20 vs. dosar deschis la 2026-10-28). Pipeline-ul ar trebui să atragă atenția operatorului la `status: depășit` și să nu doar îl înregistreze.
- Auditorul trebuie rulat și după generarea planului de plată (E23) și după fiecare certificat suplimentar, nu doar la escaladare.
- Validarea `iban_invalid` (soft) trebuie să blocheze aprobarea plății până la corectarea IBAN-ului.
