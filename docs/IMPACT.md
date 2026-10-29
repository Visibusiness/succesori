# Impact măsurat: procesul e automatizat și corect

Sursă: rulările din 2026-10-28 (sarcina 082); fiecare cifră are fișierul ei, regenerabil cu comanda din paranteză ·
Owner: LEAD. Pe ecran: `ops-ui/rezultate.html#impact` (`scripts/build_results.py`).

## 1. Automatizarea pe dosarul demo: măsurată din jurnal
Sursa: rularea cap-coadă `test-8060-203754`, smoke **49/49 PASS** pe instanța izolată :8060 (`coordonare/bin/test-instance`),
copiată în `registries/simulare/e2e/test-8060-203754/`. Analiza e în `automatizare-test-8060-203754.json`
(`scripts/impact_automation.py`).

| Ce | Cifra |
|---|---|
| Operațiuni pe dosar (7 documente, dosarul ajunge la PAID) | **47** |
| …făcute de cod determinist (blocare, stornare, solduri, cote, plan, termene, escaladări) | 25 |
| …făcute de agenți AI: 7 extracții, 4 scrisori, 2 investigații, 2 mesaje către moștenitor, 3 audituri | 18 |
| …decizii umane: aprobarea plății (executată) + semnarea răspunsului către notar și 2 escaladări (deschise prin design) | 4 |
| Operațiuni fără om | **91,5%** |
| Reacția, de la sosirea fișierului în inbox la acțiunea pe dosar (cu citirea LLM) | mediană **9,4 s** (8,6–10,5 s) |
| …până la scrisori și mesaje gata | mediană 24 s, maxim 59,5 s |
| Timpul de lucru al agentului pe tot dosarul (fără pauzele dintre documente) | **190 s** |

**Cele 12 operațiuni manuale din brief.** Sunt cele 11 din BRIEF §2 „Face singur”, plus plata efectivă. Toate 12 au loc în
rulare, fiecare cu evenimentul ei în dosar. **10 se fac fără om**: 7 sunt complet automate (blocarea debitului și a
cardurilor, încetarea împuterniciților, stornarea comisioanelor, pensia de returnat, soldurile la data decesului, planul
de plată, termenele), iar 3 sunt făcute de cod împreună cu un agent AI care scrie textul (avizarea daunei, cererea de
supliment, cotele citite din certificat). La om rămân 2: semnarea răspunsului către notar, pe care agentul îl scrie, și
aprobarea plății. Tabelul complet e pe ecran.

## 2. Simularea la scară: 200 de dosare, comparate la ban
Sursa: `registries/simulare/rezultat-seed82.json` și `RAPORT-seed82.md` (`scripts/impact_simulare.py`, seed 82). Generatorul
determinist (`registries/simulare/generator.py`) produce dosare cu 2–5 moștenitori (61 cu testament), 0–2 minori (110
dosare), bunuri comune sau proprii, depozit scadent sau nu, credit cu sau fără asigurare (aprobată sau refuzată),
comisioane, pensii și retrageri după deces, produse omise, ordini diferite și documente ilizibile sau suspecte. Ground
truth-ul vine din `registries/simulare/referinta.py`, scrisă separat (nu importă `agent/`). Pe dosarul demo, referința
dă exact valorile din `kb/scenariu-demo/maria-ionescu.md` (test `tests/test_impact.py`). Documentele sunt deja extrase,
deci simularea testează logica dosarului, fără LLM.

| Ce | Cifra |
|---|---|
| Timp: 200 de dosare, 877 de documente, prin `Pipeline` în proces | **0,12 s** (0,6 ms/dosar) |
| Plăți executate fără aprobare umană | **0** |
| Dosare cu escaladările exacte (211 escaladări așteptate) | **200/200** |
| Capcane prinse: pensie de returnat 32/32 · produs omis ⇒ supliment 45/45 · minor blocat 110/110 · retragere a împuternicitului 25/25 · asigurare refuzată 10/10 · document ilizibil sau suspect 33/33 | toate |
| Comisioane după deces stornate | 55/84 (cele 29 ratate au alt cod decât PREMIUM) |
| Dosare complet corecte (fiecare linie la ban, fiecare flag, fiecare escaladare) | **125/200 (62,5%)** |
| Linii de plată exacte la ban | 860/1048 |

Toate cele 75 de dosare greșite se explică prin **6 bug-uri** în `agent/`. Codul nu a fost modificat; fiecare bug are în
raport un exemplu minim, rulat:
1. **Soțul e luat după poziție (H1), nu după calitate.** Când certificatul trece întâi un copil, acel copil primește
   jumătatea de proprietar a soțului (13 dosare).
2. **Același cod, cu un minor pe primul rând și bunuri comune:** `AssertionError`, iar dosarul rămâne fără plan (3 dosare).
3. **Când datoria e mai mare decât contul curent, netul și liniile de plată ies negative.** Diferența nu se ia din depozit
   (21 dosare).
4. **Depozitul ajuns la scadență înainte de plan rămâne blocat** (17 dosare).
5. **Se stornează doar comisionul PREMIUM** (29 dosare).
6. **Refuzul asigurătorului, venit după un certificat complet, lasă dosarul fără plan.** Rezultatul depinde de ordinea
   documentelor (4 dosare).

În afara acestor 6 cauze nu a apărut nicio diferență, nici măcar de un ban: nici la dobânzi (float în cod, fracții
exacte în referință), nici la rotunjirea pe moștenitori.

## 3. Studiul de timp om vs. agent: în așteptare
Sursa: `docs/studiu-timp/` (fișa, extrasul din core, regulile, tabelul și cheia) și `docs/studiu-timp/rezultat.json`
(`scripts/impact_studiu.py`). Doi colegi fac de mână dosarul Mariei, în 6 sarcini: soldurile cu dobânda, răspunsul către
notar, comisioanele, pensia, cotele și planul, ce lipsește și mesajul. **Datele lor nu au venit încă.**

Agentul, punctat cu aceeași cheie: **30/33 de câmpuri corecte**. Toate sumele, cotele și datele sunt corecte. Cele 3
greșeli sunt toate în scrisoarea către notar, unde lipsesc trei puncte cerute în adresă: IBAN-ul și valuta (pct. 1),
cutiile de valori (pct. 4) și numele împuternicitului (pct. 5). Timpii agentului pe sarcină sunt între 8,7 și 23,7 s de la
sosirea documentului.

## Ce e măsurat și ce e estimare
- **Măsurat:** tot ce e mai sus, din fișierele citate. Timpii vin din ora jurnalului (la secundă) și din ora la care
  fișierul a ajuns în inbox.
- **Alegerea noastră (de validat cu Raiffeisen):** cele 12 operațiuni (lista din brief); probabilitățile variantelor din
  generator (nu reflectă frecvența reală); regulile referinței acolo unde KB-ul are „Necunoscut”: datoria se scade din cont
  înainte de lichidarea comunității, ca în maria-ionescu.md §2.3, apoi din depozit; un depozit scadent devine plătibil;
  orice comision după deces se stornează.
- **Estimare proprie:** orele manuale pe dosar (1,5 / 3 / 6 h, `docs/pitch/business-case.md`), până când studiul de timp
  le înlocuiește cu o măsurătoare.
- **Nu e acoperit aici:** calitatea extracției pe documente reale (secțiunea „Citire” a ecranului) și costul
  (secțiunea „Cost și timp”).
