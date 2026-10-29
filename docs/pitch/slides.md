Sursă: `docs/pitch/business-case.md`, `demo-script.md`, `qa-juriu.md`, `docs/DECISIONS.md`, `kb/scenariu-demo/maria-ionescu.md`, `kb/scenariu-demo/documente-demo.md`, `kb/bank-procedures/cazuri-reale.md`, rapoartele 039, 048b, 059 · Accesat: 2026-10-28 · Owner: PITCH (065)

# Slide-uri pitch: Agentul de Succesiune (10 slide-uri, 5–7 minute)

Persoane și documente din demo sunt **fictive**. Tot ce nu are sursă în fișierele din KB e marcat **(estimare proprie)**.
Marcatorul **[CIFRA BUCLA]** se înlocuiește după bucla de antrenare (061); până atunci vorbim doar de cifra de pe train: OCR 89,0%.
Bugetul de timp (≈ 6 min fără demo-ul lung): slide-urile 1–5 ≈ 3 min, demo (slide 6) ≈ 5–7 min *dacă* e rulat integral. **Pentru un pitch de 5–7 minute total**, demo-ul live se rulează comprimat (Pașii 1, 4, 6, 7, ≈ 2 min) și restul slide-urilor se spun în ≈ 30 s fiecare; scriptul complet e în `demo-script.md`.

Grila juriului → unde răspundem: originalitate (1, 2, 5), domeniu (1, 8), design agenți (4, 5), completitudine/testabilitate (5, 6), arhitectură (4), business (7, 9).

---

## Slide 1 — Statul știa de deces din prima zi; banca a aflat după 13 luni
- Raiffeisen, Bragadiru (presă, 22.02.2023): cont Premium, **60 lei/lună**.
- Familia: „am depus certificatul pe 4.03.2021”. Banca: „nu există dovezi că banca ar fi fost înștiințată”.
- Decesul era din feb. 2020 ⇒ ≈ 13 luni până la „înștiințare”; **490,66 lei** necontestați + **2.331,45 lei** comisioane și penalități (martie 2021–dec. 2022), transformate în „linie de credit”.
- Nu există recipisă ⇒ nu există adevăr comun.

**Notă de vorbitor (≈ 35 s):** „Un cont Premium costă 60 de lei pe lună. Când un client moare, familia spune că a anunțat banca, banca spune că nu are dovezi. În cazul de la Bragadiru comisioanele au curs aproape doi ani. Nimeni nu minte neapărat: pur și simplu nu există o recipisă și nu există un singur dosar. Iar statul știa de deces din prima zi.”
**Imagine:** axa timpului în 3 puncte (deces feb. 2020 → „înștiințare” 4.03.2021 → decembrie 2022), cu cifrele 490,66 și 2.331,45 lei; sub ea decupajul de presă (titlu, fără nume proprii ale persoanelor private).

---

## Slide 2 — De ce acum: banca primește deja decesele, săptămânal, de la stat
- Contract Raiffeisen–DGEP din iunie 2025: semnal cu data decesului, prin SFTP, **săptămânal** (+ web service la cerere).
- Volum: ≈ 240.000 decese/an (INS) × 7–14% sunt clienți ⇒ **≈ 17–34 mii dosare/an** (central 24.000) **(estimare proprie)**.
- Azi un dosar înseamnă 3–6 interacțiuni manuale (≈ 15–119 FTE, central ≈ 42) **(estimare proprie)**.
- LLM-urile citesc acum documente românești variate (adrese, certificate, scanuri), lucru care înainte cerea reguli rigide.

**Notă de vorbitor (≈ 30 s):** „Piesa care lipsea nu mai lipsește: din 2025 banca are feed-ul DGEP, deci știe de deces în cel mult o săptămână. Ce rămâne manual e restul: citit adresa notarului, certificatul de moștenitor, polița de asigurare. Estimăm 17–34 de mii de dosare pe an, cu 24 de mii ca valoare centrală; e estimarea noastră, un lucru pe care vrem să-l validăm cu voi.”
**Imagine:** pâlnie: 240.000 decese/an → 7–14% clienți → 17–34k dosare; alături, pictograma „feed DGEP, săptămânal”. Etichetă mică: „estimare proprie”.

---

## Slide 3 — Agentul pregătește tot dosarul; omul decide și aprobă plata
- Un singur dosar per client decedat, cu **recipisă pentru fiecare document** primit.
- Agentul: blochează reversibil, extrage din documente, calculează soldurile la data decesului, redactează răspunsul către notar și mesajele către moștenitori.
- Omul: semnează răspunsul către notar, **aprobă sau respinge planul de plată**, rezolvă escaladările.
- Ținta: din 3–6 interacțiuni manuale rămân 1–2 **(estimare proprie)**.

**Notă de vorbitor (≈ 30 s):** „Într-o frază: agentul face ca banca să știe repede și să nu piardă niciun document, iar omul păstrează tot ce cere judecată. Plata nu pleacă niciodată singură. Pentru moștenitori, dosarul e unul singur, cu recipisă; pentru operator, în loc de patru interacțiuni, o aprobare.”
**Imagine:** două coloane „Agentul” / „Omul” cu săgeți; în mijloc dosarul (`FROZEN` → `PAYMENT_PENDING_APPROVAL`).

---

## Slide 4 — Arhitectura: LLM-ul citește și scrie, codul decide banii, omul aprobă plata
- **LLM** (extractor, corespondent, investigator): text → JSON cu scor de încredere; JSON → scrisori în română. Nu calculează sume.
- **Cod determinist** (pipeline, bani în bani întregi): solduri la data decesului, stornări, cote, plan de plată. Cotele se citesc din certificat și se verifică doar că **însumează 1**.
- **Om**: plata rămâne `pending_approval` (Aprobă/Respinge). Pe semnal DGEP doar **măsuri reversibile** (GDPR art. 22).
- Fiecare acțiune are regula citată; auditorul verifică după fiecare rulare (nicio plată fără aprobare, idempotență).

**Notă de vorbitor (≈ 40 s):** „Separăm trei lucruri. Modelul citește și scrie, acolo unde e bun. Banii îi calculează cod, cu teste, nu un model. Iar omul aprobă plata. Pe semnalul DGEP, contractul nostru cu DGEP interzice decizii definitive, deci agentul face doar ce se poate anula: blochează, suspendă. Închiderea definitivă cere certificatul de deces sau un operator.”
**Imagine:** diagrama de arhitectură din `docs/ARCHITECTURE.md` redusă la 3 zone colorate (LLM / cod / om), cu săgeata „semnal DGEP → doar reversibil” și un lacăt pe „plată”.

---

## Slide 5 — Șase agenți care învață din erori, măsurat pe documente nevăzute
- Agenți: orchestrator, extractor, investigator, corespondent, auditor, retro-learner (+ comunicator cu moștenitorii).
- Bucla: eval → retro → eval; **păstrăm schimbarea doar dacă scorul nu scade** (toleranță 1 pct); codul nu e modificat de buclă.
- Train **99,2%** vs. validare nevăzută (holdout, 18 documente) **99,3%** pe câmpuri, Sonnet ⇒ lecțiile generalizează. Haiku: 97,7% pe holdout (**−1,6 pct**, respins; rămâne pe triaj).
- Documente stricate: OCR **89,0%** pe date augmentate (train) ⇒ după bucla de antrenare, pe holdout-ul augmentat nevăzut: **[CIFRA BUCLA]**.

**Notă de vorbitor (≈ 45 s):** „Nu ne mulțumim cu «a mers pe exemple». Învățătorul vede doar setul de antrenare; garda de regresie se măsoară pe documente pe care nu le-a văzut niciodată: 99,2% pe antrenare, 99,3% pe validare. Am testat și un model mai mic, Haiku: cu 1,6 puncte mai prost pe documentele nevăzute, deci l-am respins pentru extracție, deși e mai ieftin. Punctul slab onest: scanurile proaste, 89% pe OCR sintetic. Cifra după antrenare: [CIFRA BUCLA].”
**Imagine:** (a) buclă circulară eval → retro-learner → skill-uri → eval cu poarta „regresie? păstrăm / aruncăm”; (b) bară dublă train 99,2% / holdout 99,3% și o a doua pereche Sonnet / Haiku; (c) mică tabelă pe variante augmentate (fără diacritice 99,2%, formate 100%, OCR 89,0% → [CIFRA BUCLA]). Notă în subsol: holdout-ul e scris de aceeași echipă, deci nu e independent total.

---

## Slide 6 — Demo live: cazul Maria Ionescu, 7 documente, de la semnal la plata în așteptare
- Pas 1 DGEP: `FROZEN`, mandatul lui Andrei suspendat, **stornare 60 lei**.
- Pas 2–3: răspuns către notar cu soldurile la 3.09.2026; termen UNIQA de 30 de zile urmărit automat.
- Pas 4–5: cotele din certificat (soț 1/4, Andrei 3/8, Elena 3/8); **lipsește depozitul** ⇒ cerere de supliment; Elena are 15 ani ⇒ acord scris.
- Pas 6: net **5.273,37 lei**; soț 3.295,85, Andrei 988,76, Elena 988,76 (**blocat**); Pas 7: document ilizibil ⇒ escaladare, nimic definitiv.

**Notă de vorbitor (≈ 40 s + demo):** „Vă arătăm cele șapte documente ale unui dosar fictiv. La semnalul DGEP agentul blochează și storneză comisionul. La certificat vede singur că lipsește depozitul și cere suplimentul. Plata apare în așteptare, iar partea fetiței de 15 ani rămâne blocată până la documentele de reprezentare. La final, un document ilizibil nu deschide niciun dosar: pune un om pe caz.”
**Imagine:** captură ops-ui cu bara „Pas 1..7” și dosarul în `PAYMENT_PENDING_APPROVAL`; rezervă `?mock=1`. Dacă timpul e scurt: Pașii 1, 4, 6, 7. La întrebări: selectorul pe varianta B (testament) și cazurile din `hard/` (ordine inversă, duplicat DGEP, cote ≠ 1, CNP greșit).

---

## Slide 7 — Impactul: ≈ 10 lei cost Claude pe dosar, ≈ 175 lei timp economisit pe dosar
- **Per dosar, alături:** timp economisit ≈ 2 h de operator (3 h manual × 65%) ≈ 175 lei **(estimare proprie)** · cost Claude **2,35 $ ≈ 10,6 lei, măsurat** pe o rulare completă (7 documente, 21 de apeluri de model; interval 1,4–2,4 $) ⇒ **≈ 17×** (prudent ≈ 4×, optimist ≈ 51×). Agentul: ≈ 5 min cap-coadă pe cele 7 documente. Detaliu: `cost-per-dosar.md`.
- Optimizat (auditor doar la închidere, extracție pe Haiku): ≈ 1 $ ≈ 4,7 lei/dosar **(estimare proprie)**.
- Pe an (central, 24.000 dosare): cost Claude ≈ 56k $ ≈ 254k lei față de economie la ore: prudent ≈ 0,76 mil. lei, **central ≈ 4,2 mil. lei**, optimist ≈ 18 mil. lei/an (ore × % automatizat × 60/90/120 lei/oră) **(estimare proprie)**.
- Pentru moștenitori: ≈ 3 drumuri la agenție evitate/moștenitor ≈ 180.000/an (central) **(estimare proprie)**; comisioane: formula (luni − 1) × 60 lei.
- Necunoscut și spus ca atare: nr. real de cazuri cu comisioane, reclamații, pensii returnate.

**Notă de vorbitor (≈ 35 s):** „Am măsurat cât costă un dosar complet: în jur de 10 lei de model, pentru 21 de apeluri. În schimb, economisește cam două ore de operator, adică vreo 175 de lei. Raportul e de 17 la 1, iar costul scade la jumătate dacă auditorul rulează o singură dată, la închidere. Pe an, economia e de câteva milioane de lei, dar spunem clar că ore, procente de automatizare și cost orar sunt ipotezele noastre; vă cerem cifrele reale. Nu am monetizat ce nu știm.”
**Imagine:** sus, două cifre mari una lângă alta per dosar: „≈ 2 h / ≈ 175 lei economisiți” și „≈ 10,6 lei cost Claude (măsurat)”; dedesubt tabelul cu 3 scenarii (prudent/central/optimist) cu coloana „estimare proprie” evidențiată și un „?” vizibil la costul infrastructurii interne (necunoscut, parametru de la bancă).

---

## Slide 8 — Date reale unde am putut, ipoteze spuse deschis
- Documente pe **machete oficiale**: certificat de deces MAI Anexa 3/6, certificat de moștenitor Anexa 17 (Reg. Legii 36/1995), formular UNIQA CD_UAV_V8_04.2024, câmpurile DGEP din nota Raiffeisen–DGEP; date fictive, cu variante scan și foto.
- Cazuri reale din presă și jurisprudență, **anonimizate** (11 cazuri: Bragadiru, CEC, ÎCCJ RIL 9/2024 etc.).
- Ipoteze ale noastre: cont și depozit bun comun; pensia din septembrie ca bun comun; dobândă Act/365; compensarea de 26,63 lei.
- Limite: holdout scris de aceeași echipă; rudă la telefon = politică propusă, de validat cu compliance.

**Notă de vorbitor (≈ 35 s):** „Nu avem date reale ale clienților și nu vrem. Am construit documentele pe machetele oficiale, cu persoane fictive, și am învățat din cazuri reale din presă, anonimizate. Ce am presupus, am scris: bun comun, convenția dobânzii. Iar regula de secret bancar pentru o rudă la telefon e propunerea noastră, nu o regulă confirmată de Raiffeisen.”
**Imagine:** colaj cu 4 machete (MAI Anexa 3, Anexa 17, UNIQA, nota DGEP) și, lângă el, o listă „Presupus / De validat” cu 4 puncte.

---

## Slide 9 — Plan: pilot intern în bancă, apoi hub între bănci și notari
- **Faza 1: serviciu intern.** Agentul pregătește, omul decide. Obligații minime DORA art. 28/30 dacă LLM-ul e furnizor extern („standard pentru orice furnizor cloud”, nu „fără obligații”).
- **Ce cere pilotul:** feed DGEP (deja contractat), acces **read-only** la core, un operator back-office, dosare istorice pentru evaluare, avizul compliance/DPO.
- **Faza 2: hub extern** bănci–notari: probabil funcție critică ⇒ notificare BNR, drepturi de audit, strategie de ieșire.
- Succes pilot: aceleași teste (7 documente + cazurile hard) și scorul de extracție pe dosare istorice.

**Notă de vorbitor (≈ 30 s):** „Pornim mic: un serviciu intern, cu acces numai de citire la core și un operator care aprobă. Pilotul are un criteriu clar de succes: aceleași teste și același scor de extracție, dar pe dosare istorice ale voastre. Hub-ul între bănci și notari vine după, cu alt regim de reglementare, pe care îl știm.”
**Imagine:** foaie de parcurs în 2 trepte (Faza 1 → Faza 2) cu lista „ce cere pilotul” sub prima treaptă.

---

## Slide 10 — Ce vă întrebăm pe voi, ca să trecem de la estimare la cifră
1. Câți clienți decedați/an are portofoliul (validează 17–34k) și care e costul orar încărcat al unui operator back-office?
2. Folosiți deja feed-ul săptămânal DGEP pentru blocări? În cât timp după deces apare înregistrarea?
3. Compliance: ce se spune unei rude fără certificat, după RIL ÎCCJ 9/2024?
4. Un LLM găzduit extern în UE în Faza 1: ce evaluare de criticitate și ce clauze cere politica de externalizare/DORA?
5. Câte stornări de comisioane, reclamații/CSALB și restituiri de pensii legate de deces aveți pe an? (Există un pilot intern similar?)

**Notă de vorbitor (≈ 30 s):** „Încheiem cu întrebări, pentru că business case-ul nostru e atât de bun cât sunt cifrele voastre. Dacă ne dați numărul real de decese și costul orar, înlocuim estimările noastre cu date. Mulțumim.”
**Imagine:** slide curat, cele 5 întrebări; în colț, QR/link către repo și `docs/pitch/qa-juriu.md` (21 de răspunsuri pregătite).

---

## De completat / necunoscut
- **[CIFRA BUCLA]** (slide 5): OCR pe holdout-augmentat după bucla de antrenare (061, Ștefan). Dacă nu apare la timp, spunem doar 89,0% pe train și lecțiile OCR ca „în lucru”.
- Duratele pe slide sunt bugete (≈ 5,5 min de vorbit fără demo); de cronometrat la repetiție. Cu demo complet (≈ 5–7 min) pitch-ul total depășește ținta ⇒ demo comprimat, vezi antet.
- Cifra „6 agenți” numără orchestrator, extractor, investigator, corespondent, auditor, retro-learner; `heir-communicator` e al șaptelea, nedemonstrat live.
- Cifra de 11 cazuri (slide 8) din `cazuri-reale.md`; „22 certificate de deces pe formulare oficiale” (commit 32f5e23) se poate adăuga pe slide 8 dacă vrem scala.
