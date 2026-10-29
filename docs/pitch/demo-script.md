Sursă: `kb/scenariu-demo/maria-ionescu.md` v1.1 (cifre), `registries/documents/` (cele 7 documente), `ops-ui/` (bara „Pas 1..7”), `docs/DECISIONS.md`, `kb/bank-procedures/cazuri-reale.md` · Accesat: 2026-10-28 · Owner: DOMAIN

# Script demo: 5–7 minute, 7 pași

Persoane și documente **fictive**. Cifre în lei (în cod: bani). Pe ecran: ops-ui (`/ui/`, `?api=1` sau `?mock=1`), selectorul de variantă pe **A** (moștenire legală); pe B doar dacă juriul întreabă de testament. Data decesului D = **2026-09-03**.

## Deschidere (≈ 40 s): cazul Bragadiru
**Ecran:** titlul „Raiffeisen, Bragadiru, 2023” (slide), cifrele 60 lei/lună, 490,66 lei + 2.331,45 lei.
**Spunem:** „Un cont Premium costă 60 de lei pe lună. După un deces, familia spune că a anunțat banca, banca spune că nu există dovezi; comisioanele au curs aproape doi ani și au devenit o ‘linie de credit’. Statul știa de deces din prima zi. Agentul face ca banca să știe în câteva zile și să nu poată pierde un document.”
**Rațiune:** `kb/bank-procedures/cazuri-reale.md` §1; feed DGEP săptămânal (`dgep-arb-acord.md`).

## Pas 1 — Semnalul DGEP (≈ 45 s)
**Ecran:** dosarul se deschide în `FROZEN`; acțiunile agentului: blocare debit, mandatul lui Andrei suspendat, cardurile, comisionul; **stornare 60 lei (6.000 bani)** a comisionului din 5.09; termen de opțiune 2027-09-03.
**Spunem:** „La semnalul DGEP agentul face doar ce se poate anula: blochează și suspendă; nu închide nimic definitiv.”
**Regula:** contractul DGEP + GDPR art. 22 (decizii doar pe date DGEP interzise ⇒ măsuri reversibile, `DECISIONS.md`); CGB 3.2.5 lit. b (împuternicit „numai pe timpul vieții titularului”), 3.8.3 (blocarea parțială nu oprește comisionul, deci se cere explicit); C.civ. art. 2.030 alin. 1 lit. c (mandatul încetează la deces); termen opțiune 1 an, art. 1.103.

## Pas 2 — Adresa notarului (≈ 60 s)
**Ecran:** răspunsul generat, în așteptare de semnătură umană: sold la D: cont curent **3.200,00**, depozit **20.000,00 + 692,38** dobândă, credit **−9.000,00 și −26,63**; pensia din septembrie ca „încasare după deces”.
**Spunem:** „Notarul cere soldurile la data decesului. Agentul le calculează, nu le ‘ghicește’, și le scrie din date. Omul semnează.”
**Regula:** Legea 36/1995 art. 81 alin. 2 (răspuns, **fără termen legal**; termenul practic e data dezbaterii, 20.10); secret bancar: răspunsul merge notarului (`secret-bancar.md`).

## Pas 3 — Certificatul de asigurare UNIQA (≈ 30 s)
**Ecran:** dosar de daună deschis; **termen de avizare 2026-10-20** (30 de zile de la aflare); lista de documente.
**Spunem:** „Termenul de 30 de zile al asigurătorului e urmărit automat, nu într-un caiet.”
**Regula:** `kb/bank-procedures/asigurare-viata-credit.md` (CGA UNIQA: avizare în 30 de zile).
*Între pașii 3 și 4 (15.10):* pensia din octombrie: **flag `pension_return_CNPP` 210.000 bani**, retur la cererea casei de pensii; **pensia din septembrie rămâne** (Legea 360/2023 art. 100 alin. 1 lit. a și art. 156 alin. 8).

## Pas 4 — Certificatul de moștenitor (≈ 60 s)
**Ecran:** cote extrase din document (varianta A: soț 1/4, Andrei 3/8, Elena 3/8, suma = 1); **lipsește depozitul** (`coverage_gaps` = DEP-1) ⇒ cerere de supliment; **Elena, 15 ani, detectată** ⇒ cere acordul scris al reprezentantului + cont pe numele ei.
**Spunem:** „Agentul nu calculează cotele din lege: le citește din certificat și verifică doar că însumează 1. Vede singur că certificatul nu cuprinde depozitul și cere suplimentul.”
**Regula:** C.civ. art. 972, 975 (cote legale); Legea 36/1995 art. 115 și 118 (certificat, supliment); minor 14–18 ani: art. 41 alin. 3 și art. 507 (`mostenitor-minor.md`).
**Dacă întreabă de testament:** comută selectorul pe B (1/2–1/4–1/4, rezerva copiilor 3/16, art. 1.088); același drum de cod.

## Pas 5 — Răspunsul asigurătorului (≈ 30 s)
**Ecran:** creditul stins (9.000 lei); datoria rămasă **26,63 lei** înregistrată pentru calculul net.
**Spunem:** „Asigurarea acoperă principalul; dobânda curentă rămâne datorie a moștenirii.”
**Regula:** `asigurare-viata-credit.md` (acoperă principal + max. 3 rate, nu dobânzi/comisioane); C.civ. art. 1.155 (datorii ale moștenirii).

## Pas 6 — Certificatul suplimentar, plata (≈ 90 s)
**Ecran:** plan de plată în `pending_approval`; **net de împărțit: 527.337 bani = 5.273,37 lei** (3.200,00 + 2.100,00 pensia din sept. − 26,63; pensia din octombrie exclusă).

| Moștenitor | Variantă A (5/8 · 3/16 · 3/16) | Variantă B (3/4 · 1/8 · 1/8) |
|---|---|---|
| Ion (soț) | 329.585 bani = 3.295,85 lei | 395.503 bani = 3.955,03 lei |
| Andrei | 98.876 bani = 988,76 lei | 65.917 bani = 659,17 lei |
| Elena (minoră) | 98.876 bani — **blocat** | 65.917 bani — **blocat** |

Depozitul (A): 1.315.000 / 394.500 / 394.500 bani la scadență; recomandare: **așteptarea scadenței 2027-01-03** (dobândă 1.040,00 lei brut, față de 0 la lichidare anticipată).
**Spunem:** „Plata nu pleacă singură: un om aprobă (Aprobă / Respinge). Partea Elenei rămâne blocată până sosesc documentele de reprezentare.”
**Regula:** C.civ. art. 2.187 (cont indiviz între moștenitori; lichidare anticipată cu acordul tuturor); CGB 3.2.5 c; `mostenitor-minor.md` (aprobare umană + flag `CONFLICT_INTERESE_PARINTE_MINOR` când tatăl e comoștenitor).

## Pas 7 — Certificat de deces ilizibil, alt client (≈ 30 s)
**Ecran:** documentul apare la „Escaladări fără dosar”; **niciun freeze, niciun dosar deschis**; dosarul Mariei neatins.
**Spunem:** „Când agentul nu e sigur, nu ghicește: pune un om pe caz.”
**Regula:** vocabularul de escaladare `illegible` (`DECISIONS.md`); GDPR art. 22 (nimic definitiv fără om).

## Închidere (≈ 30 s)
„Un dosar de succesiune ia azi 3–6 interacțiuni manuale; estimăm 17–34 mii de dosare pe an la Raiffeisen (estimare proprie, `docs/pitch/business-case.md`). Agentul le face pe cele de rutină și lasă omului ce are nevoie de judecată.”
**Dacă întreabă de „antrenare”:** „Agentul învață din erori: după un ciclu de învățare acuratețea extractorului a urcat de la 95,6% la 100% pe cele 19 documente de test (±1 punct de zgomot între rulări), fără să schimbăm codul; se păstrează doar schimbările care nu scad scorul.” (`runs/retro-*.md`, raportul 039/042b)

## Rezervă (dacă ceva nu merge live)
- Pasul eșuează pe API: comută pe `?mock=1` (instantanee după fiecare document, `ops-ui/mock-data.json`).
- Un număr diferă: sursa unică e `kb/scenariu-demo/maria-ionescu.md` (§2); pe ecran trebuie să fie 527.337 / 329.585 / 98.876 (A) sau 395.503 / 65.917 (B).
- „Reset” din bara demo resetează totul (cere Pas 1).

## Verificare pe server (2026-10-28, `DEMO_MODE=1`, port 8001)
- Rulat de 3 ori: varianta A (`POST /demo/run`), varianta B (`?variant=B`), pas cu pas în ordine inversă (2, 1, 3, 4, 5, 6, 7). **0 erori** față de `maria-ionescu.md`: net 527.337 bani; A: 329.585 / 98.876 / 98.876 (cont) și 1.315.000 / 394.500 / 394.500 (depozit); B: 395.503 / 65.917 / 65.917 și 1.578.000 / 263.000 / 263.000; Elena blocată; stornare 6.000 bani; retur CNPP 210.000 bani; 6 linii de plată, 4.284,61 lei plătibili acum (A).
- **Timp de mașină (măsurat pe :8000 stabil și :8001):** fiecare pas 1–7 durează 1,4–2,6 ms, `GET /cases` ≈ 1 ms, `/ui/` ≈ 5 ms; tot demo-ul ≈ 8 ms. Mașina nu e limita.
- **Timp pe scenă:** frazele „Spunem” au în total **175 de cuvinte** (deschidere 60 + pașii 9–26 fiecare) ⇒ ≈ **70–80 s** vorbit la 130–150 cuvinte/min (calcul, nu cronometrare cu voce). Restul timpului e arătat pe ecran (cifre, regula din spate, click pe Pas n), estimat la 20–45 s per pas. Cu cele 9 segmente din script: **≈ 5–7 min**, în ținta cerută. Duratele „≈ X s” de mai sus rămân bugete pe segment (se ajustează la repetiția cu voce).
- **Idempotență în ordinea inversă:** fiecare acțiune apare o singură dată (blocare, stornare, răspuns notar, supliment, plan).
- **Blocarea e reversibilă și când adresa notarului vine prima** (D-DGEP, `pipeline.py` `REVERSIBLE_ONLY_SOURCES`): definitivă doar la certificatul de deces sau prin operator. Textul din Pas 1 rămâne valabil în ambele ordini. *(Verificarea de mai sus, cu „Blocare definitivă” în ordinea inversă, e dinainte de schimbare; de re-rulat.)*

## Necunoscut
- Durata exactă pe scenă (estimări de mai sus, de cronometrat într-o repetiție).
- Pensia din septembrie: bun comun sau propriu? v1 o tratează ca bun comun (`maria-ionescu.md` Necunoscut); dacă juriul întreabă, spunem asta explicit.
- Convenția dobânzii (Act/365) și compensarea de 26,63 lei: ipoteze ale noastre, întrebare pentru mentori.
