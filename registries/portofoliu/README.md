# Portofoliul de clienți (sarcina 084)

Paisprezece persoane decedate, clienți Raiffeisen **fictivi**, alături de Maria Ionescu (scenariul demo, dosarul
`SC-2026-0001`, care pornește de la zero la fiecare reset). Fiecare fișier `P*.json` e un client:

- `customer`, `products`, `movements`, `contacts`: datele din core-ul mock (`agent/core_mock.py`), cu IBAN-uri și
  numere de contract proprii; `contacts` sunt datele KYC ale moștenitorilor (e-mail verificat, adresă);
- `steps`: istoria dosarului, în ordine. Un document (`doc`) sau o acțiune a operatorului (`op`: `sign` = răspunsul
  către notar semnat, `approve` = plată aprobată, `notifier` = persoana care a anunțat decesul). Un `doc` (090) e un
  fișier real din `documente/` (`file`) cu valorile de referință (`expected_type`, `expected_fields`); pipeline-ul
  primește extracția reală a fișierului (`documente/<Pxx>/*.extras.json`, vezi `documente/README.md`), nu valorile
  de aici;
- `expected`: etapa în care trebuie să ajungă (verificat de `tests/test_portfolio.py`).

`agent/portfolio.py::seed` le trece prin drumul real (API `_receive` = gardă + pipeline + verificarea documentelor
cu probleme; endpoint-urile operatorului), deci etapa e rezultatul regulilor, nu o stare scrisă de mână. Data
portofoliului e **28.10.2026** (`AS_OF`): termenele și scara de contact se socotesc față de ea; pașii scării deja
scadenți până atunci sunt trecuți ca făcuți, în ziua lor (istoric), așa că o bancă proaspăt resetată nu are nimic
întârziat pentru autopilot.

Datele sunt inventate: CNP-uri cu cifra de control corectă și data nașterii clientului, IBAN-uri `RO.. RZBR …` cu
cifrele de control corecte, adrese „Str. Fictivă”, e-mailuri `@example.invalid`. Sumele sunt în bani (1 leu = 100).

## Clienții și etapa fiecăruia

| Dosar | Client | Produse | Moștenitori | Etapa (stare) | Ce așteaptă |
|---|---|---|---|---|---|
| SC-2026-0101 | Gheorghe Popescu (Brașov) | cont 4.123,50 lei (comun cu soția), card de credit −1.864,20 | încă necunoscuți | doar semnal DGEP (Blocat, reversibil) | certificatul de moștenitor; fotografia ilizibilă a certificatului de deces stă la „documente neidentificate” (escaladare) |
| SC-2026-0102 | Elisabeta Dumitrescu (Iași) | cont 867,40, depozit 45.000 | încă necunoscuți | răspuns la notar generat, **de semnat** | semnătura; dezbaterea e pe 03.11.2026 (în 6 zile) |
| SC-2026-0103 | Constantin Marinescu (Constanța) | cont 12.345 (comun), credit 68.500 asigurat UNIQA | încă necunoscuți | **dosar de daună deschis** la UNIQA | documentele daunei, răspunsul asigurătorului, certificatul |
| SC-2026-0104 | Ana Stoica (Sibiu) | cont 22.156, depozit 120.000 | 1: fiul, Radu Stoica, **în Germania** | **supliment cerut** (certificatul nu cuprinde depozitul) | certificatul suplimentar; reminderul pe 30.10 |
| SC-2026-0105 | Ioan Georgescu (București) | cont 28.400 (comun cu soția), depozit 30.000 (comun) | 3: soția 1/4, doi copii 3/8 | **plan de plată de aprobat**: 30.850,00 lei plătibili acum, depozitul la scadență | aprobarea; pensia din august (2.450 lei) reținută pentru CNPP |
| SC-2026-0106 | Florica Niculescu (Craiova) | cont 15.600, card de credit −3.420 | 2, **testament**: nepoata 2/3, nepotul 1/3 | **plan de plată de aprobat**: 12.146,27 lei (cardul și dobânda lui, 3.453,73, scăzute din cont) | aprobarea |
| SC-2026-0107 | Vasile Petrescu (Cluj) | cont 34.208 (comun), credit 42.000 asigurat UNIQA (stins de asigurător) | **5**: soția 1/4, patru copii 3/16 (unul **în Canada**, Sofia **minoră**, 16 ani) | **plan de plată de aprobat**: 30.880,35 lei; partea Sofiei (3.194,52) blocată; **escaladare: minor** | aprobarea; acordul reprezentantului legal pentru Sofia |
| SC-2026-0108 | Elena Radu (Timișoara) | **cont comun** cu soțul 19.800 (jumătate e a soțului, ca proprietar) | 2: soțul 1/4, fiica 3/4 | **plătit** pe 12.09.2026: 21.940 lei către 2 moștenitori | nimic; dosarul se poate închide |
| SC-2026-0109 | Doina Ilie (Oradea) | cont 6.453, depozit 25.000 | încă necunoscuți | răspuns la notar semnat; **escaladare: document suspect în carantină** (un „certificat de moștenitor” trimis pe e-mail cu instrucțiuni ascunse și un IBAN străin) | operatorul verifică documentul la sursă |
| SC-2026-0110 | Nicolae Stan (Ploiești) | cont 4.120 (comun), credit 56.000 asigurat UNIQA | încă necunoscuți (soția a anunțat decesul) | dosar de daună; **escaladare: asigurătorul a refuzat** (afecțiune preexistentă nedeclarată) | decizia operatorului; datoria rămâne în masa succesorală |
| SC-2026-0111 | Petre Vlad (Pitești) | cont 9.754, card de credit −589 | încă necunoscuți; fiica a anunțat decesul și **nu mai răspunde** | **scara de contact la 30 de zile**: mesaj (26.09), reminder (10.10), scrisoare recomandată (26.10) | cererea prin notar, pe 25.11.2026 |
| SC-2025-0187 | Aurelia Matei (Bacău) | cont 18.302,50, depozit 60.000 | încă necunoscuți (nepotul a anunțat decesul) | **dosar vechi**: deces 02.11.2025, toți pașii scării făcuți, avertizarea de 10 luni trimisă | **termenul de 1 an se împlinește pe 02.11.2026** (în 5 zile): prezumată renunțarea, operatorul decide |
| SC-2026-0113 | Marin Petrescu (Târgu Jiu) · **caz real** | cont 2.846,30 (comun), Flexicredit 57.175,63 asigurat UNIQA | 4: soția și trei copii, câte 1/4 | dosar de daună; **escaladare: asigurătorul a refuzat** (boală preexistentă, deces la 3 luni de la aderare) | decizia operatorului; nu se face plan (contul nu acoperă creditul) |
| SC-2026-0114 | Cristian Neagu (Sebeș) · **caz real** | cont 18.420 (comun), Flexicredit 24.181,70 asigurat UNIQA (stins), card de credit −3.450 | 3: soția 1/4, doi fii **minori** 3/8 (unul cu curator special, unul reprezentat de mama lui) | **plan de plată de aprobat**: 9.311,78 lei acum; liniile minorilor (2.793,54 și 2.793,53) blocate; **escaladări: minor** ×2 | aprobarea; reprezentanții minorilor, contactați de operator |

Acoperire: cont curent (toți), depozit la termen (5), credit cu asigurare UNIQA (5), card de credit (4), cont comun
cu soțul (8, `estate_fraction` = 1/2); 1–5 moștenitori, trei minori, un testament, doi moștenitori în străinătate.

**P13 și P14 (sarcina 085) sunt construiți pe cazuri reale**: situația vine dintr-o hotărâre judecătorească publicată,
iar documentele sunt pe machetele oficiale (certificatul de deces MAI, cererea de despăgubire UNIQA, Anexa 17).
Datele de identificare sunt inventate. Sursele, ce e real și ce e fictiv, calculele de mână și scanurile sunt în
`cazuri-reale/`; fișierele `P13-*.json`, `P14-*.json` se generează de acolo, cu
`.venv/bin/python registries/portofoliu/cazuri-reale/portofoliu.py`. Ambele adrese de notar folosesc formularea reală
de pe notari.pro, care nu dă data dezbaterii. Cu extracția reală (090) amândouă ies cu încrederea 0,5 (termenul e
obligatoriu pentru extractor), deci așteaptă la „documente neidentificate” (`document_illegible`) și banca nu are
răspuns de semnat; înainte, cu încrederea scrisă de mână, deschideau `document_deficient_institution` (raportul 085).

## Poveștile, pe scurt

- **Gheorghe Popescu** a murit pe 19.10.2026; DGEP l-a semnalat pe 26.10 și conturile sunt blocate reversibil. A doua
  zi fiul lui a lăsat la ghișeu o fotografie a certificatului de deces, făcută cu telefonul: nu se citește nici CNP-ul,
  așa că documentul nu se atașează nimănui și așteaptă un operator.
- **Elisabeta Dumitrescu**, văduvă, fără copii cunoscuți băncii. Notarul din Iași a cerut soldurile pe 23.10; răspunsul
  e generat (cu dobânda depozitului la data decesului) și așteaptă semnătura înainte de dezbaterea din 3 noiembrie.
- **Constantin Marinescu** avea un credit de nevoi personale asigurat la UNIQA. Banca a deschis dosarul de daună pe
  20.10; familia mai are de adus documentele cerute de asigurător.
- **Ana Stoica** are un singur moștenitor, fiul ei, care locuiește la München. Certificatul de moștenitor cuprinde
  doar contul curent; banca a cerut notarului un supliment pentru depozit; mesajul către fiu (e-mail) e în istoricul
  scării de contact, reminderul urmează pe 30.10.
- **Ioan Georgescu**: soția și doi copii, moștenire legală. Contul și depozitul sunt bunuri comune: jumătate e a soției
  ca proprietar, cealaltă jumătate se împarte pe cote. Pensia din iulie (luna decesului) rămâne în masă, cea din august
  se returnează la CNPP. Comisioanele luate după deces sunt stornate.
- **Florica Niculescu** a lăsat testament: nepoata Simona 2/3, nepotul Gabriel 1/3. Datoria de pe cardul de credit, cu
  dobânda până la deces, se plătește din cont înainte de împărțire.
- **Vasile Petrescu**: soția și patru copii; Daniel e în Toronto, Sofia are 16 ani. UNIQA a stins creditul pe 21.10;
  dobânda neacoperită (133,13 lei) se scade din cont. Partea Sofiei rămâne blocată până la acordul mamei ei.
- **Elena Radu** avea un cont comun cu soțul. Planul (soțul: jumătatea lui + 1/4 din cealaltă; fiica: 3/4 din
  jumătatea Elenei) a fost aprobat pe 12.09.2026 și plătit.
- **Doina Ilie**: după adresa notarului, a venit pe e-mail un „certificat de moștenitor” care numește un moștenitor unic
  necunoscut și cere plata urgentă într-un IBAN de la altă bancă; textul ascuns îi cere agentului să aprobe plata.
  Garda l-a pus în carantină: nicio acțiune, un operator îl verifică la notar.
- **Nicolae Stan**: UNIQA a refuzat indemnizația (excludere: afecțiune preexistentă nedeclarată). Creditul rămâne
  datorie a moștenirii; moștenitorii trebuie informați că pot renunța.
- **Petre Vlad**: fiica lui, Mirela, a anunțat decesul și apoi nu a mai răspuns: mesaj inițial, reminder la 14 zile,
  scrisoare recomandată la 30 de zile. Următorul pas e cererea prin notarul din dosar.
- **Aurelia Matei** a murit pe 2 noiembrie 2025. Nepotul ei a anunțat decesul, dar nimeni nu a adus certificatul de
  moștenitor: toți pașii scării au fost făcuți, avertizarea de 10 luni a plecat în septembrie. Pe 2 noiembrie 2026 se
  împlinește termenul de opțiune succesorală: fondurile rămân blocate, fără comisioane, operatorul decide.
- **Marin Petrescu** (Jud. Târgu Jiu, sent. civ. 825/2013): a luat un Flexicredit de 58.700 lei cu asigurare de deces,
  fără chestionar medical, și a murit după trei luni, de pancreatită cronică și ciroză, boli cunoscute dinainte. UNIQA
  refuză indemnizația pe clauza de boală preexistentă. Creditul rămâne datorie a moștenirii și e mult mai mare decât
  contul, deci nu se face plan de plată. Soția și cei trei copii trebuie informați că pot renunța la moștenire.
  În cazul real, instanța a obligat asigurătorul să plătească.
- **Cristian Neagu** (Trib. Alba, dec. civ. 839/A/2015): a murit într-un accident rutier. Soția era separată în fapt;
  fiul lor, Darius, are 16 ani și, pentru că mama lui e comoștenitoare, acceptă moștenirea cu un curator special.
  Andrei, fiul lui din afara căsătoriei, are 9 ani și e reprezentat de mama lui. UNIQA a stins creditul. Dobânda
  neacoperită și cardul de credit se scad din contul comun, iar jumătatea din cont care intră în masă se împarte pe cote.
  Plătibilă acum e doar partea soției.
