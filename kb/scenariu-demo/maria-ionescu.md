Sursă: generat de noi (BRIEF §2 + KB: kb/legal/*, kb/bank-procedures/*, docs/DECISIONS.md) · Accesat: 2026-10-28 · Owner: LEAD

# Scenariul demo: Maria Ionescu — date fixe și valori așteptate

Persoane și documente **fictive**. Toate sumele sunt în **bani** (RON × 100) în cod; aici le scriem și în lei.
Valorile din acest fișier devin testele din Faza 1 (`tests/`). Orice schimbare de cifră se face aici întâi, cu
mențiune în `docs/DECISIONS.md`.

> Stare: **v1.1**. Variantele A/B confirmate de sarcina 012 (`kb/legal/procedura-succesorala-notar.md` § Cele două variante):
> certificatul conține (1) fracțiunea din fiecare produs care intră în masă (ex. „1/2 din cont”, după lichidarea comunității)
> și (2) cotele moștenitorilor din masă. Agentul înmulțește cele două — un singur drum de cod pentru A și B.

## 1. Datele fixe
| Element | Valoare | Sursa regulii |
|---|---|---|
| Defunctă | Maria Ionescu, CNP fictiv `2XXXXXXXXXXXX`, client `RC1001` | — |
| Data decesului (D) | **2026-09-03** | BRIEF („3 sept”), an ales de noi |
| Soț | Ion Ionescu (căsătoriți, comunitate legală de bunuri, fără convenție matrimonială) | C.civ. art. 339, 343 |
| Copii | Andrei (major), Elena (15 ani) | — |
| Împuternicit pe cont | Andrei | mandatul încetează la deces: C.civ. art. 2030; CGB 3.2.5 b |
| Cont curent | sold la D: **3.200,00 lei** | — |
| Pensie | 2.100 lei/lună, virată pe 15 | Legea 360/2023 |
| Pachet de cont | **Premium, 60 lei/lună**, debitat pe 5 ale lunii | lista de tarife PF 2026 (D-Premium în DECISIONS) |
| Depozit la termen | 20.000 lei, 12 luni, 5,20%/an, constituit 2026-01-03, scadent **2027-01-03** (la 4 luni după D) | tarife depozite; lichidare anticipată ⇒ dobânda pierdută |
| Credit nevoi personale | sold principal la D: **9.000 lei**, dobândă 12%/an (fictiv), ultima rată plătită 2026-08-25 | — |
| Asigurare credit | UNIQA, primă lunară plătită la zi, începută 2023-05-10 (> 24 luni ⇒ fără flaguri de excludere) | `kb/bank-procedures/asigurare-viata-credit.md` |

## 2. Valori așteptate (calcule deterministe)

### 2.1 `balance_at_death` — la 2026-09-03
| Produs | Valoare la D | Calcul |
|---|---|---|
| Cont curent | 320.000 bani = **3.200,00 lei** | dat |
| Depozit — principal | 2.000.000 bani = 20.000,00 lei | dat |
| Depozit — dobândă acumulată (brut) | **69.238 bani = 692,38 lei** | 20.000 × 5,20% × 243 zile / 365 (convenție Act/365, ipoteză) |
| Credit — principal | −900.000 bani = −9.000,00 lei | dat |
| Credit — dobândă curentă neacoperită | **−2.663 bani = −26,63 lei** | 9.000 × 12% × 9 zile (25.08→03.09) / 365 |

### 2.2 Mișcări după deces și ce face agentul
| Data | Mișcare | Regula | Acțiune / valoare așteptată |
|---|---|---|---|
| 2026-09-05 | comision Premium −60 lei | comision după D | **stornare 6.000 bani** (`fees_to_reverse`) |
| 2026-09-15 | pensie +2.100 lei (septembrie) | pensia lunii decesului se cuvine (Legea 360/2023 art. 100 alin. 1 lit. a) | **se păstrează**; raportată notarului separat, ca încasare după deces; intră în masă |
| 2026-10-05 | comision Premium | după freeze (20.09) comisionul e suspendat | **nu se mai percepe** (dacă apare: stornare) |
| 2026-10-15 | pensie +2.100 lei (octombrie) | necuvenită | **flag `pension_return_CNPP` 210.000 bani**; retur la cererea casei de pensii (art. 156 alin. 8, fără acordul moștenitorilor) |

### 2.3 `net_of_debts`
- Creditul: indemnizația UNIQA acoperă principalul la D (9.000 lei) ⇒ credit stins de asigurător.
- Rămâne datorie a masei: dobânda curentă 26,63 lei (neacoperită de asigurare).
- **Cont curent net de împărțit** = 3.200,00 + 2.100,00 (pensia sept.) − 26,63 = **5.273,37 lei = 527.337 bani**.
  (Pensia din octombrie e reținută pentru retur și nu intră în calcul.)

### 2.4 `split_by_shares` — două variante (D1 în DECISIONS)
Ipoteză comună: contul și depozitul sunt **bunuri comune** (C.civ. art. 341, 343 — pensia și veniturile din timpul
căsătoriei). Lichidarea comunității: ½ revine soțului **ca proprietar**, ½ intră în masa succesorală.
Rotunjire: cea mai mare rămășiță, egalitățile în ordinea moștenitorilor din certificat (determinist).

**Varianta A — moștenire legală** (art. 972: soț ¼; art. 975: copiii ¾ împărțit egal)
| Moștenitor | Fracție din bun | Cont curent (527.337) | Depozit la scadență brut (2.104.000) |
|---|---|---|---|
| Ion (soț) | ½ + ½·¼ = **5/8** | 329.585 = 3.295,85 lei | 1.315.000 = 13.150,00 lei |
| Andrei | ½·3/8 = **3/16** | 98.876 = 988,76 lei | 394.500 = 3.945,00 lei |
| Elena (minoră) | **3/16** | 98.876 = 988,76 lei — **blocat** până la reprezentare | 394.500 — **blocat** |

**Varianta B — testament** (Maria lasă: soțului ½, fiecărui copil ¼ din moștenire; rezerva copiilor 3/16 din
moștenire e respectată, art. 1088)
| Moștenitor | Fracție din bun | Cont curent (527.337) | Depozit la scadență brut (2.104.000) |
|---|---|---|---|
| Ion (soț) | ½ + ½·½ = **3/4** | 395.503 = 3.955,03 lei | 1.578.000 = 15.780,00 lei |
| Andrei | ½·¼ = **1/8** | 65.917 = 659,17 lei | 263.000 = 2.630,00 lei |
| Elena (minoră) | **1/8** | 65.917 = 659,17 lei — **blocat** | 263.000 — **blocat** |

Notă: în ambele variante agentul **nu deduce cotele din lege**. Le citește din certificatul de moștenitor, verifică
`sum == 1` și le aplică. Varianta se alege prin documentul 4 (certificat cu sau fără mențiunea testamentului).

### 2.5 Depozitul
- Nescadent la D; omis din certificatul inițial ⇒ `coverage_gaps` = [`DEP-1`] ⇒ cerere de supliment.
- Recomandarea agentului: **așteptarea scadenței** (2027-01-03): dobânda integrală 1.040,00 lei brut, față de 0 la
  lichidare anticipată. Lichidarea anticipată cere acordul tuturor moștenitorilor (C.civ. art. 2187) și, pentru Elena,
  reprezentantul legal.
- Impozitul pe dobândă (reținere la sursă) nu e modelat în v1 — sumele de depozit sunt brute.

## 3. Cronologia celor 7 documente (ordinea fixă din BRIEF)
| # | Data | Document | Ce face agentul | Stare dosar după |
|---|---|---|---|---|
| 1 | 2026-09-20 | **Semnal DGEP** (CNP, data decesului 2026-09-03) | deschide dosar; freeze **reversibil** (D-DGEP: blocare debit, suspendă mandatul lui Andrei, cardurile, debitările directe și comisionul — definitiv doar după certificatul de deces/operator); stornează 60 lei; programează termen opțiune 2027-09-03 | `FROZEN` |
| 2 | 2026-09-28 | **Adresa notarului** (dosar succesoral nr. 123/2026, dezbatere 2026-10-20) | `get_products_at_date(D)`; generează răspunsul (tabelul §2.1 + pensia de septembrie ca încasare după D + credit cu asigurare); trimite la semnare umană | `NOTARY_ANSWERED` |
| 3 | 2026-09-30 | **Certificatul de asigurare** UNIQA | validează CNP + nr. credit; deschide dosar de daună; termen avizare = 30 zile de la aflare (2026-10-20); checklist F1 | `INSURANCE_CLAIM_OPEN` |
| — | 2026-10-15 | (eveniment) pensia din octombrie | flag retur CNPP 2.100 lei | — |
| 4 | 2026-10-22 | **Certificatul de moștenitor** (fără depozit; varianta A sau B) | extrage cote; verifică suma = 1; `coverage_gaps` ⇒ depozit lipsă ⇒ cere supliment notarului; minor detectat ⇒ cere acordul scris al reprezentantului + cont pe numele Elenei | `SUPPLEMENT_REQUESTED` |
| 5 | 2026-10-27 | **Răspunsul asigurătorului** (aprobat, 9.000 lei) | stinge creditul; înregistrează datoria restantă 26,63 lei pentru `net_of_debts` | `INSURANCE_SETTLED` |
| 6 | 2026-11-10 | **Certificatul suplimentar** (adaugă depozitul) | acoperire completă; `split_by_shares` (§2.4); plan de plată cont curent acum, depozit la scadență; plata în `pending_approval`; partea Elenei blocată | `PAYMENT_PENDING_APPROVAL` |
| 7 | 2026-11-12 | **Certificat de deces ilizibil, alt client** | clasificare cu `legibility=illegible` / CNP necitibil ⇒ **escaladare**, niciun freeze, niciun dosar deschis automat | (dosarul Mariei neatins) |

## 4. Teste „și dacă…?” derivate (pentru juriu)
| Variantă | Rezultat așteptat |
|---|---|
| Documentele 1 și 2 vin în ordine inversă | adresa notarului deschide dosarul și face întâi freeze; aceleași valori |
| Semnalul DGEP vine de două ori | idempotent: un singur freeze, o singură stornare |
| Andrei retrage 1.000 lei pe 2026-09-10 (după deces, înainte de semnal) | flag `post_death_mandate_withdrawal`; suma raportată notarului ca element de recuperat; escaladare |
| Cotele din certificat însumează ≠ 1 | escaladare, niciun plan de plată |
| CNP din certificatul de moștenitor ≠ CNP client | `409`, escaladare |
| Certificatul conține produsele, dar nu și IBAN-urile | potrivire după tip + sumă; dacă e ambiguu, escaladare |

## Necunoscut
- Pensia din septembrie (încasată după deces): bun comun sau propriu al Mariei? C.civ. art. 341 + Legea 360/2023 art. 107 nu tranșează. v1 o tratează ca bun comun, împreună cu soldul; dacă e bun propriu, intră integral în masă și cifrele din §2.4 se schimbă.
- Convenția de calcul a dobânzii la depozit (Act/365 vs Act/360) și dobânda creditului după deces până la plata
  indemnizației — ipoteze ale noastre; de întrebat mentorii Raiffeisen.
- Dacă banca aplică compensarea (CGB 3.5.1) pentru dobânda de 26,63 lei sau o recuperează din masa succesorală — întrebare juridică deschisă.
- Confirmarea din 012: cum apare exact lichidarea comunității în certificat (cote pe bun vs. pe masă).

## Ce înseamnă pentru agent
- Fiecare rând din §2 și §3 este un test cu valoare exactă în bani.
- Agentul trebuie să producă aceleași rezultate indiferent de ordinea documentelor (§4).
