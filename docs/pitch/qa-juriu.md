Sursă: `kb/` (fișierele citate pe fiecare rând), `registries/documents/hard/` (cazurile H1–H11), `docs/DECISIONS.md`, `docs/pitch/business-case.md` · Accesat: 2026-10-28 · Owner: DOMAIN

# Întrebări probabile ale juriului: „și dacă…?”

Răspunsuri scurte, cu sursa. **[LIVE]** = demonstrabil live cu un fișier din `registries/documents/hard/` (înlocuiește documentul indicat în secvență, vezi `hard/README.md`). Restul se răspunde din KB, fără demo. Cifrele demo: `kb/scenariu-demo/maria-ionescu.md`.

| # | Întrebare | Răspuns scurt | Sursa |
|---|---|---|---|
| 1 | Și dacă documentele vin în altă ordine? | Adresa notarului deschide dosarul și face întâi freeze; semnalul DGEP de după doar confirmă; aceleași valori. **[LIVE H1]** | `hard/H1-adresa-notar-inainte-dgep`; `maria-ionescu.md` §4 |
| 2 | Și dacă semnalul DGEP vine de două ori? | Idempotent: un singur freeze, o singură stornare de 6.000 bani. **[LIVE H2]** | `hard/H2-dgep-semnal-duplicat` |
| 3 | Și dacă cotele din certificat nu fac 1? | Escaladare `shares_invalid`, niciun plan de plată. **[LIVE H3]** | `hard/H3-cote-suma-diferita-de-1`; `DECISIONS.md` (coduri) |
| 4 | Și dacă CNP-ul din certificat nu e al clientului? | `409`, escaladare `cnp_mismatch`, dosarul neatins. **[LIVE H4]** | `hard/H4-cnp-gresit-in-certificat` |
| 5 | Și dacă certificatul nu are IBAN-uri? | Potrivire unică după tip + sumă; marcaj `matched_without_iban`; dacă e ambiguu, escaladare. **[LIVE H5]** | `hard/H5-certificat-fara-iban`; `maria-ionescu.md` §4 |
| 6 | Și dacă documentul e scris în litere, are CNP cu spații sau antet „ADRESĂ”? | Normalizează datele, CNP-ul, fracțiile din cuvinte și clasifică după conținut, nu după titlu. **[LIVE H6–H9]** | `hard/H6`, `H7-cote-in-cuvinte`, `H8-cnp-cu-spatii`, `H9-antet-derutant` |
| 7 | Și dacă decesul vine dintr-un extras multilingv, fără CNP? | Potrivire unică pe nume + prenume + data nașterii, confirmată de data decesului și de soț; dacă nu e unică (omonim), `identity_unconfirmed` și nimic nu se atașează. **[LIVE H10, H11]** | `hard/H10`, `H11`; `DECISIONS.md` (extras multilingv fără CNP) |
| 8 | Și dacă mama a lăsat testament? | Același drum de cod: cotele vin din certificat. Varianta B: 1/2–1/4–1/4, rezerva copiilor respectată; sumele: 3/4–1/8–1/8 din bunul comun. Se comută selectorul din ops-ui. | C.civ. art. 1.088; `maria-ionescu.md` §2.4; `DECISIONS.md` D1 |
| 9 | Și dacă un moștenitor e minor? | Acceptă singur (14+); încasarea cere acordul scris al părintelui, cont pe numele minorului; partea Elenei **blocată** până la documente; dacă tatăl e și comoștenitor, flag de conflict și aprobare umană. Se vede în Pas 4 și 6. | C.civ. art. 41 alin. 3, 507; `kb/legal/mostenitor-minor.md` |
| 10 | Și dacă un moștenitor e în străinătate? | Încasează prin procură notarială sau consulară: apostilă/supralegalizare + traducere legalizată; obiectul trebuie să includă expres încasarea; revocarea se verifică prin notar/RNNEPR (nu știm dacă banca are acces direct). Nu e în demo. | C.civ. art. 2.016, 2.033; CGB (Mandatar); `kb/document-templates/procura-notariala.md` |
| 11 | Și dacă contul era comun cu soțul? | Comunitatea legală se lichidează întâi: ½ revine soțului ca proprietar, ½ intră în masă; între moștenitori contul devine indiviz (operațiuni doar cu acordul tuturor). Ipoteza demo: cont și depozit sunt bunuri comune. | C.civ. art. 339, 343, 357, 2.186, 2.187; `maria-ionescu.md` §2.4 |
| 12 | Și dacă depozitul nu e scadent? | Se propune așteptarea scadenței (2027-01-03): 1.040,00 lei dobândă brut față de 0 la lichidare anticipată; lichidarea cere acordul tuturor (și reprezentantul Elenei). Vizibil în Pas 6. | `maria-ionescu.md` §2.5; `DECISIONS.md` (Depozit nescadent); C.civ. art. 2.187 |
| 13 | Nu încalcă GDPR dacă blochează conturi doar pe semnal DGEP? | Pe semnal agentul face **doar măsuri reversibile** (blocare debit, suspendări). Închiderea definitivă și revocarea cer certificatul de deces sau un operator. Datele decedatului nu intră în GDPR (considerentul 27), dar secretul bancar rămâne. | GDPR art. 22, considerent 27; contract DGEP; `DECISIONS.md`; `gdpr-decedati-mostenitori.md` |
| 14 | Și dacă sună o rudă la bancă și întreabă de cont? | Nu confirmă nici că există cont. Moștenitorii pot primi informații despre perioada dinainte de deces doar dacă justifică scopul (ÎCCJ RIL 9/2024); ruda fără dovadă primește doar lista documentelor. Regula e **de validat cu compliance Raiffeisen**. | OUG 99/2006 art. 111, 113 alin. 2 lit. a; RIL 9/2024; `secret-bancar.md` |
| 15 | Cine plătește și cine răspunde dacă agentul greșește? | Plata e în `pending_approval`: un om aprobă (Aprobă/Respinge). Fiecare acțiune are regula citată; auditorul verifică după fiecare rulare. | `ops-ui/README.md`; `DECISIONS.md` (coduri de escaladare); agentul `auditor` |
| 16 | Cât costă tokenii per dosar? | Măsurat: 2,35 $ ≈ 10,6 lei pe un dosar complet (7 documente, 21 de apeluri, Sonnet 5.5; interval 1,4–2,4 $), față de ≈ 175 lei timp de operator economisit (≈ 17×); optimizat ≈ 1 $. ≈ 56k $/an la 24k dosare. | `docs/pitch/cost-per-dosar.md` |
| 17 | Intră sub DORA dacă folosiți un LLM? | Da, dacă LLM-ul e furnizor extern TIC: rămân registrul de informații și clauzele minime (art. 28/30). Se evită notificarea BNR prealabilă (Reg. 5/2013 art. 230^11) doar dacă funcția e necritică. Fază 2 (hub) = probabil critică. | DORA art. 28, 30; Reg. BNR 5/2013; `kb/legal/outsourcing-bnr-eba-dora.md`; `DECISIONS.md` |
| 18 | Pensia virată după deces: se returnează? | Pensia lunii decesului **se păstrează** (se cuvine); cea din octombrie e necuvenită ⇒ flag, retur la cererea casei de pensii. Nu e înscrisă în `hard/` (se vede între Pas 3 și 4). | Legea 360/2023 art. 100 alin. 1 lit. a, art. 156 alin. 8; `kb/legal/legea-pensiilor-deces.md` |
| 19 | Și dacă împuternicitul a retras bani după deces? | Flag `post_death_mandate_withdrawal`, suma raportată notarului ca element de recuperat, escaladare. Nu e în `hard/`. | `maria-ionescu.md` §4; C.civ. art. 2.030, 2.036 |
| 20 | Notarul cere un răspuns până când? | Legea nu dă un termen; termenul practic e data dezbaterii din adresă. | Legea 36/1995 art. 81 alin. 2; `DECISIONS.md` |
| 21 | De ce cotele din demo nu sunt 1/2–1/4–1/4? | Nicio variantă legală nu le dă; 1/2–1/4–1/4 vine doar din testament (varianta B). Agentul nu le deduce, le citește. | C.civ. art. 972, 975, 1.088; `DECISIONS.md` D1 |

## Necunoscut
- Dacă rândurile 18 și 19 pot fi demonstrate live: nu au fișier în `hard/`; se pot arăta doar în mock/API dacă scenariul e implementat.
- Răspunsul 14 (rudă la telefon) e politică propusă, nu confirmată de Raiffeisen.
- Cifrele din rândul 16 sunt estimări proprii (ipoteze în `business-case.md`).
