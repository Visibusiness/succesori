Sursă: generat de noi, pe șabloanele din kb/document-templates/*.md, kb/tech/dgep-integration.md §3.1 și datele din kb/scenariu-demo/maria-ionescu.md (v1.1) · Accesat: 2026-10-28 · Owner: DOCS

# Cele 7 documente ale demo-ului (texte fictive, conținut complet)

Toate persoanele, instituțiile notariale, numerele și CNP-urile sunt **fictive**. CNP-urile sunt mascate cu `X` (13
caractere, invalide intenționat); IBAN-urile au cifra de control `00` (invalide intenționat). Banca (Raiffeisen Bank
S.A.) și asigurătorul (UNIQA Asigurări de viață S.A.) sunt reale, pentru că sunt ale brief-ului; documentele lor sunt
inventate de noi, dar urmează machetele oficiale reale (058): certificatul de deces MAI Anexa 3 (Normele
de stare civilă 2024), certificatul de moștenitor Anexa 17 la Regulamentul Legii 36/1995, adresa notarială publicată
pe notari.pro, formularul UNIQA „Cerere de despăgubire în caz de daună” CD_UAV_V8_04.2024 și câmpurile DGEP din nota
Raiffeisen–DGEP.

Sumele și datele sunt cele din `maria-ionescu.md`. Dacă o cifră de acolo se schimbă, se schimbă întâi acolo, apoi aici
și în `registries/documents/`.

Fișierele reale (text integral + ground truth la extracție) sunt în `registries/documents/`. Acest fișier e specificația
lor: ce scrie în document, ce câmpuri trebuie extrase, ce trebuie să facă agentul.

## 0. Identificatori comuni (folosiți în toate documentele)

| Element | Valoare fictivă | Folosit în doc |
|---|---|---|
| Defunctă | IONESCU MARIA, CNP `2XXXXXXXXXXXX`, născută 1958-05-12, client `RC1001` | 1–6 |
| Ultimul domiciliu | Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu | 2, 4, 6 |
| Data decesului | 2026-09-03 | 1–6 |
| Cont curent | `CC-1`, IBAN `RO00 RZBR 0000 0000 0000 01`, RON | 2 (răspuns), 4 |
| Depozit la termen | `DEP-1`, IBAN `RO00 RZBR 0000 0000 0000 02`, 20.000 lei, 5,20%, 2026-01-03 → 2027-01-03 | 2 (răspuns), 6 |
| Credit nevoi personale | `CRD-1`, contract nr. `NP-2023-001001` din 2023-05-10, valoare inițială 15.000 lei | 3, 4, 5 |
| Certificat de asigurare | UNIQA nr. `UQ-0000000-FICTIV`, început 2023-05-10, primă lunară | 3, 5 |
| Dosar de daună | UNIQA nr. `DV-0451/2026` | 5 |
| Birou notarial | Biroul Individual Notarial „Exemplu Ana”, notar public **Ana EXEMPLU** (fictiv), Municipiul Exemplu, Str. Fictivă nr. 10, `notar.exemplu@example.invalid` | 2, 4, 6 |
| Adresa notarului | nr. de ieșire `412` din 28.09.2026 | 2 |
| Dosar succesoral | `123/2026` | 2, 4, 6 |
| Termen de dezbatere | 2026-10-20 | 2 |
| Certificat de moștenitor | nr. `87` din 22.10.2026 | 4, 6 |
| Certificat suplimentar | nr. `95` din 10.11.2026 | 6 |
| Testament (doar varianta B) | testament autentic nr. `314` din 12.03.2024, BIN „Exemplu Ana” | 4B |
| Soț | IONESCU ION, CNP `1XXXXXXXXXXX1`, născut 1955-02-08 | 4, 6 |
| Fiu (major, fost împuternicit) | IONESCU ANDREI, CNP `1XXXXXXXXXXX2`, născut 1986-07-21 | 4, 6 |
| Fiică (minoră, 15 ani) | IONESCU ELENA, CNP `6XXXXXXXXXXX3`, născută 2011-03-14 | 4, 6 |
| Alt client (doc 7) | POPOVICI GHEORGHE, CNP `1XXXXXXXXXXX9`, client `RC1002` — **valori ascunse**, doar pentru generator | 7 |

Identificatorii de produs (`CC-1`, `DEP-1`, `CRD-1`) sunt cei din core-mock; agentul îi obține potrivind IBAN-ul sau nr.
de contract din document.

## Doc 1 — Semnal DGEP · 2026-09-20 · tip `semnal_dgep`
**Fișier:** `registries/documents/01-dgep-semnal.json` (o linie din lotul săptămânal; nu e un document scanat).
**Format:** cel din `kb/tech/dgep-integration.md` §3.1 (generat de noi; formatul real DGEP nu e public).

```json
{
  "schema": "mosteniri.dgep.death_signal/v0",
  "_generated_by_us": true,
  "_fields_source": "Nota de informare Raiffeisen Bank–DGEP, „Categoriile de date”, lit. b) actualizarea periodică: numele de familie și prenumele, CNP, tipul, seria și numărul actului de identitate, data emiterii și data expirării, adresa de domiciliu, adresa de reședință (după caz), data decesului (după caz). Locul decesului și certificatul de deces nu se transmit pe acest canal.",
  "message_id": "DGEP-MOCK-2026-09-20-000123",
  "channel": "periodic_sftp",
  "batch_week": "2026-W38",
  "bank_code": "RZBR",
  "last_name": "IONESCU",
  "first_name": "MARIA",
  "cnp": "2XXXXXXXXXXXX",
  "id_document": {
    "type": "CI",
    "series": "XX",
    "number": "000000",
    "issue_date": "2020-01-01",
    "expiry_date": "2030-01-01"
  },
  "domicile_address": "Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu",
  "residence_address": null,
  "date_of_death": "2026-09-03",
  "communicated_at": "2026-09-20T06:00:00+03:00",
  "changed_fields": ["date_of_death"]
}
```

**Câmpuri:** structurate, fără extracție LLM: `cnp`, `last_name`, `first_name`, `date_of_death`, `communicated_at`
(= data aflării).
**Ce face agentul:**
1. Potrivește CNP + nume cu `RC1001`.
2. Deschide dosarul de succesiune.
3. Aplică freeze **reversibil** (D-DGEP): blochează debitul, suspendă mandatul lui Andrei, cardurile, debitările directe
   și comisionul de pachet.
4. Stornează comisionul din 2026-09-05: **6.000 bani**.
5. Programează termenul de opțiune succesorală: **2027-09-03**.
6. Cere certificatul de deces: lotul periodic DGEP nu conține seria/numărul actului de deces și nici locul decesului
   (nota Raiffeisen–DGEP, „Categoriile de date” lit. b)).

**Stare după:** `FROZEN`. Un semnal duplicat e idempotent pe `cnp + date_of_death`.

## Doc 2 — Adresa notarului · 2026-09-28 · tip `adresa_notar`
**Fișier:** `02-adresa-notar.md` / `.json`. Câmpuri: schema din `kb/document-templates/adresa-notar-catre-banca.md`.

```
ROMÂNIA
Uniunea Națională a Notarilor Publici
Biroul Individual Notarial „Exemplu Ana”
Notar public Ana EXEMPLU
Licența de funcționare nr. 0000/2010 (fictiv)
Sediul: Municipiul Exemplu, Str. Fictivă nr. 10, Jud. Exemplu
Tel. 0000 000 000 · e-mail: notar.exemplu@example.invalid

Nr. 412 / 28.09.2026
Dosar succesoral nr. 123/2026

CĂTRE,
RAIFFEISEN BANK S.A.
Agenția Exemplu

În vederea dezbaterii succesiunii privind pe defuncta IONESCU MARIA, decedată la data de 03.09.2026,
cu ultimul domiciliu în Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu, CNP 2XXXXXXXXXXXX,
născută la data de 12.05.1958, vă rugăm să eliberați un extras de cont unui netitular de cont (stare
financiară), pentru sumele de bani în lei sau în valută deschise pe numele defunctei la banca
dumneavoastră.

În temeiul art. 81 din Legea nr. 36/1995 a notarilor publici și a activității notariale, republicată,
și al art. 238 lit. d) și e) din Regulamentul de aplicare a acesteia, vă rugăm ca situația să cuprindă:
  1. conturile curente, de economii și depozitele la termen, cu IBAN-ul și valuta fiecăruia;
  2. soldul fiecărui cont și depozit la data decesului, 03.09.2026, inclusiv dobânda acumulată
     până la această dată;
  3. creditele și orice alte datorii ale defunctei față de bancă, cu soldul datorat la data
     decesului și mențiunea eventualelor asigurări atașate;
  4. existența unor cutii de valori închiriate;
  5. persoanele împuternicite pe conturile defunctei.

Termenul de dezbatere a succesiunii este 20.10.2026. Vă solicităm ca extrasul de cont să fie
transmis până la această dată la sediul biroului notarial sau la adresa de e-mail de mai sus.

NOTAR PUBLIC,
Ana EXEMPLU
(semnătură indescifrabilă)                                        L.S.
```

**Câmpuri de extras (ground truth):**
- `nr_inregistrare_adresa="412"`, `data_adresa=2026-09-28`, `nr_dosar_succesoral="123/2026"`.
- Defunctă: `defunct_cnp="2XXXXXXXXXXXX"`, `defunct_data_nasterii=1958-05-12`, `defunct_data_decesului=2026-09-03`.
- `informatii_solicitate=[conturi, depozite, sold_la_deces, dobanda, credite, cutii_valori, imputerniciti]`
  (asigurările intră la `credite`).
- `data_referinta_sold=2026-09-03`, `termen_dezbatere=2026-10-20`.
- `temei_invocat="art. 81 din Legea nr. 36/1995; art. 238 lit. d), e) din Regulament"`, `semnatura_stampila_prezente=true`.

**Ce face agentul:**
1. Validează CNP-ul și data decesului contra dosarului (DGEP).
2. Apelează `get_products_at_date(2026-09-03)` și generează răspunsul după
   `kb/document-templates/raspuns-banca-catre-notar.md`, cu valorile de mai jos.
3. Trimite răspunsul la semnare umană.
4. Setează termenul intern de răspuns la **2026-10-13** (termenul de dezbatere minus 5 zile lucrătoare).

**Valorile din răspuns:**
- **Activ:**
  - CC-1: sold 3.200,00 lei.
  - DEP-1: 20.000,00 lei + dobândă acumulată 692,38 lei = **20.692,38 lei**; scadență 2027-01-03.
- **Pasiv:** CRD-1, contract `NP-2023-001001`: principal 9.000,00 lei + dobândă curentă 26,63 lei = **9.026,63 lei**.
  Asigurare UNIQA `UQ-0000000-FICTIV`, dosar de daună în curs.
- **Cutii de valori:** nu există.
- **Mențiuni:**
  - pensia de 2.100,00 lei din 15.09.2026, încasare după deces;
  - comisionul din 05.09.2026 (60,00 lei) a fost stornat;
  - mandatul lui IONESCU ANDREI a încetat la deces (art. 2030 C.civ.).

**Stare după:** `NOTARY_ANSWERED`. Dacă doc 2 vine înaintea doc 1, doc 2 deschide el dosarul și face freeze; valorile
rămân aceleași.

## Doc 3 — Certificatul de asigurare UNIQA · adus la bancă 2026-09-30 · tip `polita_asigurare`
**Fișier:** `03-certificat-asigurare.md` / `.json`. Câmpuri: schema din
`kb/document-templates/polita-asigurare-viata.md`. Macheta certificatului nu e publică; textul de mai jos e generat de noi, cu etichetele și ordinea secțiunilor A/B din
formularul real UNIQA CD_UAV_V8_04.2024 (`kb/_downloads/nicolas/uniqa-anexa-F1-cerere-despagubire-RAIB-2024.pdf`).

```
UNIQA Asigurări de viață S.A.
Str. Nicolae Caramfil nr. 25, etaj 5, sector 1, București
Înregistrată la Oficiul Registrului Comerțului J/40/23525/1992 · Cod unic de înregistrare 1589754
Înmatriculată în Registrul Asigurătorilor sub nr. RA – 003/2003 · Autorizată de ASF (CSA) prin Decizia nr. 289 din 08.04.2010
Telefon: 0374.400.410 · e-mail: info@uniqa.ro · www.uniqa.ro
prin Raiffeisen Bank S.A., Agent Afiliat (Intermediar secundar)

CERTIFICAT DE ASIGURARE nr. UQ-0000000-FICTIV
Asigurarea pentru Deces din orice cauza atașată creditelor de nevoi personale negarantate

A. Detalii despre contractul de asigurare și despre Asigurat
Nume și Prenume Asigurat                     IONESCU MARIA
C.N.P.                                       2XXXXXXXXXXXX
Număr Certificat de asigurare                UQ-0000000-FICTIV
Adresa de domiciliu/reședință                Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu
Adresa de corespondență                      idem
Data intrării în asigurare                   10.05.2023
Telefon                                      0700 000 000      Adresa de e-mail: —

B. Riscul asigurat (acoperit prin prezentul Certificat de asigurare)
[ ] Deces din accident
[X] Deces din orice cauza
[ ] Șomaj
[ ] Spitalizare din accident
[X] Invaliditate Totală Permanentă din Accident

C. Detalii despre credit și Beneficiar
Contract de credit                           nr. NP-2023-001001 din 10.05.2023, Raiffeisen Bank S.A.
Beneficiar                                   Raiffeisen Bank S.A., în limita datoriei din contractul de credit
Suma asigurată inițială                      15.000,00 lei, descrescătoare conform Graficului de rambursare
Prima                                        lunară, debitată odată cu rata creditului
Indemnizația la deces                        soldul rămas de rambursat (principal, exclusiv dobânzi și comisioane)
                                             la data producerii evenimentului asigurat, plus maximum 3 rate lunare
                                             restante; plafon 260.000 lei.

D. Avizarea daunei
În caz de deces, Beneficiarul sau Moștenitorii Asiguratului completează „Cererea de despăgubire în caz de
daună” (formular CD_UAV_V8_04.2024), în maximum 30 de zile calendaristice de la producerea evenimentului
sau de la data la care au luat cunoștință de acesta, și o transmit, împreună cu documentele, la
asigurari@uniqa.ro:
  - Certificatul de asigurare, Termenii și condițiile Pachetului de asigurare și Declarația cu semnătura
    Asiguratului;
  - Copia Graficului de Rambursare semnat de către BANCA și Asigurat și valabil la data încheierii asigurării;
  - Certificat de deces (copie);
  - Certificat constatator al decesului (copie).

Emis la 10.05.2023.
UNIQA Asigurări de viață S.A.                          Asigurat,
(semnătură, ștampilă)                                  (semnătură)
```

**Câmpuri de extras (ground truth):**
- `insurer="UNIQA Asigurări de viață S.A."`, `certificate_number="UQ-0000000-FICTIV"`.
- Asigurat: `insured_name="IONESCU MARIA"`, `insured_cnp="2XXXXXXXXXXXX"`.
- Credit: `loan_contract_number="NP-2023-001001"`, `beneficiary="Raiffeisen Bank S.A."`.
- Condiții: `start_date=2023-05-10`, `initial_sum_insured=1.500.000 bani`, `premium_type=lunara`, `cap=26.000.000 bani`.
- `covered_risks=[deces, invaliditate_permanenta, spitalizare]`.

**Ce face agentul:**
1. Validează că `insured_cnp` e CNP-ul clientului și că `NP-2023-001001` e creditul `CRD-1`, cu asigurare.
2. Verifică vechimea poliței: start 2023-05-10, peste 24 de luni la data decesului ⇒ fără flaguri de excludere.
3. Verifică în core că prima e plătită la zi.
4. Deschide dosarul de daună cu termenul de avizare **2026-10-20** (data aflării 2026-09-20 + 30 de zile).
5. Generează checklistul F1.
6. Indemnizația așteptată: **900.000 bani**.

**Stare după:** `INSURANCE_CLAIM_OPEN`.

## (eveniment) 2026-10-15 — pensia din octombrie
Nu e document. Încasarea de 2.100 lei din 15.10.2026 primește flagul `pension_return_CNPP` (210.000 bani).

## Doc 4 — Certificatul de moștenitor · 2026-10-22 · tip `certificat_mostenitor` · variantele A și B
**Fișiere:** `04-certificat-mostenitor-A.md` / `.json` și `04-certificat-mostenitor-B.md` / `.json`. Câmpuri: schema
din `kb/document-templates/certificat-mostenitor.md`. Depozitul **lipsește intenționat** din ambele variante.

**4A — moștenire legală** (text integral):
```
ROMÂNIA
Uniunea Națională a Notarilor Publici
Birou notarial: Biroul Individual Notarial „Exemplu Ana”
Licența de funcționare nr. 0000/2010 (fictiv)
Sediul: Municipiul Exemplu, Str. Fictivă nr. 10, Jud. Exemplu
Dosar succesoral nr. 123/2026

CERTIFICAT DE MOȘTENITOR Nr. 87
Data: 22.10.2026

Ana EXEMPLU, notar public, cercetând piesele dosarului de mai sus, precum și încheierea finală
respectivă din data de 22.10.2026, în temeiul art. 12 lit. c) și al art. 115 din Legea notarilor
publici și a activității notariale nr. 36/1995, republicată, cu modificările ulterioare, certific
următoarele:

De pe urma defunctei IONESCU MARIA, CNP 2XXXXXXXXXXXX, decedată la data de 03.09.2026, cu ultimul
domiciliu în Municipiul Exemplu, Str. Fictivă nr. 1, județul Exemplu, au rămas următoarele bunuri și
următorii moștenitori legali:

Defuncta a fost căsătorită cu IONESCU ION sub regimul matrimonial al comunității legale de bunuri,
regim care a fost lichidat prin încheierea finală din data de 22.10.2026 (art. 1.133 alin. (2) Cod
civil), disponibilitățile bănești din contul curent de mai jos fiind bun comun, cu cote de
contribuție de 1/2 pentru fiecare soț. Cota de 1/2 a soțului supraviețuitor îi revine acestuia în
calitate de coproprietar și nu face parte din masa succesorală.

I. Masa succesorală:
a) bunuri mobile:
   1. cota de 1/2 din disponibilitățile bănești existente în contul curent
      IBAN RO00 RZBR 0000 0000 0000 01, deschis la Raiffeisen Bank S.A., compuse din soldul la data
      decesului și pensia aferentă lunii septembrie 2026, încasată la 15.09.2026, plus dobânzile
      aferente;
   Pasiv: dobânda curentă datorată la data decesului din contractul de credit nr. NP-2023-001001 din
      10.05.2023, încheiat cu Raiffeisen Bank S.A., în sumă de 26,63 lei; soldul principalului din
      același contract, de 9.000,00 lei la data decesului, pentru care s-a deschis dosar de daună la
      UNIQA Asigurări de viață S.A., în baza certificatului de asigurare nr. UQ-0000000-FICTIV; acest
      pasiv se stinge în măsura plății indemnizației;
b) bunuri imobile: nu există.
Natura succesiunii: legală, în temeiul art. 963 și urm., art. 972 alin. (1) lit. a) și art. 975 din
Codul civil. Din verificarea Registrului național notarial de evidență a liberalităților (RNNEL) nu
rezultă că defuncta ar fi lăsat testament.

II. Moștenitori/Legatari
1. IONESCU ION, CNP 1XXXXXXXXXXX1, domiciliat în Municipiul Exemplu, Str. Fictivă nr. 1, în calitate
   de soț supraviețuitor, cu o cotă de 1/4 (un sfert) din masa succesorală.
2. IONESCU ANDREI, CNP 1XXXXXXXXXXX2, domiciliat în Municipiul Exemplu, Str. Fictivă nr. 7, în
   calitate de fiu, cu o cotă de 3/8 (trei optimi) din masa succesorală.
3. IONESCU ELENA, CNP 6XXXXXXXXXXX3, domiciliată în Municipiul Exemplu, Str. Fictivă nr. 1, în
   calitate de fiică, minoră în vârstă de 15 ani, care a acceptat moștenirea cu încuviințarea
   tatălui, IONESCU ION, cu o cotă de 3/8 (trei optimi) din masa succesorală.
Atribuirea în mod distinct a bunurilor: nu s-a făcut.

Renunțători:
Au renunțat la succesiune, conform art. 1.120 din Codul civil: nu este cazul.
Sunt prezumați renunțători la succesiune, conform art. 1.112 din Codul civil: nu este cazul.
Sunt străini de succesiune: nu este cazul.
Nedemni:
Sunt nedemni, conform art. 958 sau 959 din Codul civil: nu este cazul.

S-a perceput impozit în sumă de 0,00 lei (succesiune dezbătută în termen de 2 ani de la deces, art. 111
alin. (1) Cod fiscal).
S-a perceput onorariul în sumă de 000,00 lei, cu TVA în sumă de 000,00 lei, și a fost achitat cu
chitanță nr. 0000 (fictiv).
S-a perceput tariful de publicitate imobiliară: nu este cazul.

Notar public,
Ana EXEMPLU
(semnătură indescifrabilă)                                        L.S.
```

**4B — moștenire testamentară** (text integral; diferă de 4A la titlu, natura succesiunii și cote):
```
ROMÂNIA
Uniunea Națională a Notarilor Publici
Birou notarial: Biroul Individual Notarial „Exemplu Ana”
Licența de funcționare nr. 0000/2010 (fictiv)
Sediul: Municipiul Exemplu, Str. Fictivă nr. 10, Jud. Exemplu
Dosar succesoral nr. 123/2026

CERTIFICAT DE MOȘTENITOR TESTAMENTAR Nr. 87
Data: 22.10.2026

Ana EXEMPLU, notar public, cercetând piesele dosarului de mai sus, precum și încheierea finală
respectivă din data de 22.10.2026, în temeiul art. 12 lit. c) și al art. 115 din Legea notarilor
publici și a activității notariale nr. 36/1995, republicată, cu modificările ulterioare, certific
următoarele:

De pe urma defunctei IONESCU MARIA, CNP 2XXXXXXXXXXXX, decedată la data de 03.09.2026, cu ultimul
domiciliu în Municipiul Exemplu, Str. Fictivă nr. 1, județul Exemplu, au rămas următoarele bunuri și
următorii legatari:

Defuncta a fost căsătorită cu IONESCU ION sub regimul matrimonial al comunității legale de bunuri,
regim care a fost lichidat prin încheierea finală din data de 22.10.2026 (art. 1.133 alin. (2) Cod
civil), disponibilitățile bănești din contul curent de mai jos fiind bun comun, cu cote de
contribuție de 1/2 pentru fiecare soț. Cota de 1/2 a soțului supraviețuitor îi revine acestuia în
calitate de coproprietar și nu face parte din masa succesorală.

I. Masa succesorală:
a) bunuri mobile:
   1. cota de 1/2 din disponibilitățile bănești existente în contul curent
      IBAN RO00 RZBR 0000 0000 0000 01, deschis la Raiffeisen Bank S.A., compuse din soldul la data
      decesului și pensia aferentă lunii septembrie 2026, încasată la 15.09.2026, plus dobânzile
      aferente;
   Pasiv: dobânda curentă datorată la data decesului din contractul de credit nr. NP-2023-001001 din
      10.05.2023, încheiat cu Raiffeisen Bank S.A., în sumă de 26,63 lei; soldul principalului din
      același contract, de 9.000,00 lei la data decesului, pentru care s-a deschis dosar de daună la
      UNIQA Asigurări de viață S.A., în baza certificatului de asigurare nr. UQ-0000000-FICTIV; acest
      pasiv se stinge în măsura plății indemnizației;
b) bunuri imobile: nu există.
Natura succesiunii: testamentară, în temeiul art. 1.055 și urm. din Codul civil, precum și în baza
testamentului autentic din data de 12.03.2024, nr. 314, întocmit de Biroul Individual Notarial „Exemplu Ana”,
identificat prin verificarea Registrului național notarial de evidență a liberalităților (RNNEL).
Rezerva succesorală a descendenților este respectată (art. 1.086–1.088 Cod civil).

II. Moștenitori/Legatari
1. IONESCU ION, CNP 1XXXXXXXXXXX1, domiciliat în Municipiul Exemplu, Str. Fictivă nr. 1, în calitate
   de soț supraviețuitor, legatar cu titlu universal, cu o cotă de 1/2 (o doime) din masa succesorală.
2. IONESCU ANDREI, CNP 1XXXXXXXXXXX2, domiciliat în Municipiul Exemplu, Str. Fictivă nr. 7, în
   calitate de fiu, legatar cu titlu universal, cu o cotă de 1/4 (un sfert) din masa succesorală.
3. IONESCU ELENA, CNP 6XXXXXXXXXXX3, domiciliată în Municipiul Exemplu, Str. Fictivă nr. 1, în
   calitate de fiică, legatar cu titlu universal, minoră în vârstă de 15 ani, care a acceptat
   moștenirea cu încuviințarea tatălui, IONESCU ION, cu o cotă de 1/4 (un sfert) din masa succesorală.
Atribuirea în mod distinct a bunurilor: nu s-a făcut.

Renunțători:
Au renunțat la succesiune, conform art. 1.120 din Codul civil: nu este cazul.
Sunt prezumați renunțători la succesiune, conform art. 1.112 din Codul civil: nu este cazul.
Sunt străini de succesiune: nu este cazul.
Nedemni:
Sunt nedemni, conform art. 958 sau 959 din Codul civil: nu este cazul.

S-a perceput impozit în sumă de 0,00 lei (succesiune dezbătută în termen de 2 ani de la deces, art. 111
alin. (1) Cod fiscal).
S-a perceput onorariul în sumă de 000,00 lei, cu TVA în sumă de 000,00 lei, și a fost achitat cu
chitanță nr. 0000 (fictiv).
S-a perceput tariful de publicitate imobiliară: nu este cazul.

Notar public,
Ana EXEMPLU
(semnătură indescifrabilă)                                        L.S.
```

**Câmpuri de extras (ground truth), comune:**
- Certificat: `doc_type=certificat_mostenitor`, `nr_certificat="87"`, `data_certificat=2026-10-22`,
  `nr_dosar_succesoral="123/2026"`, `notar="Ana EXEMPLU"`.
- Defunctă: CNP `2XXXXXXXXXXXX`, decedată la 2026-09-03.
- `regim_matrimonial="comunitate legală; cont curent bun comun, 1/2 soț"`.
- `masa_activ`, un singur element: IBAN `…01`, `cota_defunct="1/2"`, `valoare=530.000 bani` (din core; nu e scrisă în certificat, Anexa 17 nota 4).
- `masa_pasiv`:
  - `NP-2023-001001` dobândă, 2.663 bani;
  - `NP-2023-001001` principal, 900.000 bani, cu asigurare.
- `mostenitori`: 3 persoane, cu CNP, calitate, `minor`.
- Variante:
  - **A:** cote `1/4, 3/8, 3/8`, `temei_devolutiune="legal"`.
  - **B:** cote `1/2, 1/4, 1/4`, `temei_devolutiune="testamentar"`, `testament={nr:"314", data:2024-03-12}`.

**Ce face agentul (A și B, același cod):**
1. Extrage cotele ca fracții exacte și verifică `sum == 1`.
2. Validează CNP-ul defunctei și nr. de dosar `123/2026` (= cel din adresa notarului).
3. Certificatul nu menționează valoarea bunurilor mobile (Anexa 17, nota 4). Valoarea `530.000 bani` (3.200 + 2.100)
   vine din core, nu din document; agentul verifică doar că IBAN-ul din certificat e al contului CC-1.
4. **Completitudine:** `coverage_gaps=[DEP-1]` ⇒ cerere de certificat suplimentar către notar (art. 118 alin. 2,
   L. 36/1995). Nu plătește încă nimic: în cronologia din `maria-ionescu.md` §3, planul de plată se face abia la doc 6.
5. Detectează minorul (Elena, 15 ani):
   - cere încuviințarea scrisă a tatălui și un cont pe numele Elenei;
   - pune eticheta `CONFLICT_INTERESE_PARINTE_MINOR` (tatăl e comoștenitor; `kb/legal/mostenitor-minor.md`).
6. Varianta B nu escaladează: testamentul e doar mențiune. Cotele se citesc din certificat, nu se recalculează din lege.
7. Fracțiunea efectivă din bun = `cota_defunct × cota`:
   - A: Ion 5/8 (½ + ½·¼), Andrei 3/16, Elena 3/16;
   - B: Ion 3/4, Andrei 1/8, Elena 1/8.

   Se aplică pe baza netă `527.337 bani` (§2.3 din `maria-ionescu.md`).

**Stare după:** `SUPPLEMENT_REQUESTED`.

## Doc 5 — Răspunsul asigurătorului · 2026-10-27 · tip `raspuns_asigurator`
**Fișier:** `05-raspuns-asigurator.md` / `.json`. Nu are șablon în `kb/document-templates/`; câmpurile sunt definite
aici.

```
UNIQA Asigurări de viață S.A.
Str. Nicolae Caramfil nr. 25, etaj 5, sector 1, București
Cod unic de înregistrare 1589754 · Registrul Asigurătorilor nr. RA – 003/2003
Telefon: 0374.400.410 · e-mail: asigurari@uniqa.ro
Departamentul Daune Viață

Nr. 7781 / 27.10.2026

Către: RAIFFEISEN BANK S.A., în calitate de Beneficiar
Cc:    moștenitorii Asiguratei

Ref.: Cerere de despăgubire în caz de daună (CD_UAV_V8_04.2024) – Dosar de daună nr. DV-0451/2026

A. Detalii despre contractul de asigurare și despre Asigurat
Nume și Prenume Asigurat                     IONESCU MARIA
C.N.P.                                       2XXXXXXXXXXXX
Număr Certificat de asigurare                UQ-0000000-FICTIV
Data intrării în asigurare                   10.05.2023
Contract de credit                           nr. NP-2023-001001 din 10.05.2023

B. Riscul asigurat pentru care se solicită despăgubire
Riscul asigurat                              Deces din orice cauza
Data producerii evenimentului asigurat       03/09/2026 (zi/lună/anul)

Documente primite: Certificatul de asigurare; Copia Graficului de Rambursare; Certificat de deces
(copie); Certificat constatator al decesului (copie).

Vă comunicăm că, în urma analizării documentelor depuse, cererea de despăgubire a fost APROBATĂ.

Indemnizația de asigurare este de 9.000,00 lei (nouă mii lei), reprezentând soldul principalului
rămas de rambursat la data producerii evenimentului asigurat (03.09.2026), conform Graficului de
rambursare. La data evenimentului nu existau rate restante.

Indemnizația se va plăti Beneficiarului, Raiffeisen Bank S.A., în contul aferent contractului de
credit nr. NP-2023-001001, în termen de 10 zile lucrătoare de la data prezentei.

Dobânzile și comisioanele nu fac obiectul indemnizației.

Cu stimă,
Departamentul Daune Viață
(semnătură, ștampilă)
```

**Câmpuri de extras (ground truth):**
- Referințe: `doc_type=raspuns_asigurator`, `insurer="UNIQA Asigurări de viață S.A."`, `nr_raspuns="7781"`,
  `data_raspuns=2026-10-27`, `nr_dosar_dauna="DV-0451/2026"`.
- Asigurare: `insured_cnp="2XXXXXXXXXXXX"`, `certificate_number="UQ-0000000-FICTIV"`,
  `loan_contract_number="NP-2023-001001"`, `data_eveniment=2026-09-03`.
- Decizie și plată: `decizie=aprobat`, `indemnizatie=900.000 bani`, `rate_restante_incluse=0`, `beneficiar_plata="Raiffeisen Bank S.A."`,
  `termen_plata="10 zile lucrătoare"` (⇒ 2026-11-10), `motiv_refuz=null`.

**Ce face agentul:**
1. Validează CNP-ul, certificatul de asigurare și contractul contra dosarului de daună.
2. Verifică `indemnizatie == principal la D` (900.000).
3. Marchează creditul `CRD-1` ca stins de asigurător la încasare.
4. Înregistrează datoria rămasă a masei: dobânda de **2.663 bani**, folosită de `net_of_debts`.
5. Urmărește încasarea până la 2026-11-10.

**Stare după:** `INSURANCE_SETTLED`.

## Doc 6 — Certificatul de moștenitor suplimentar · 2026-11-10 · tip `certificat_mostenitor_suplimentar`
**Fișier:** `06-certificat-suplimentar.md` / `.json`. Un singur fișier pentru A și B: nu repetă cotele, ci trimite la
certificatul nr. 87, ca în practică (art. 118, același notar, aceiași moștenitori).

```
ROMÂNIA
Uniunea Națională a Notarilor Publici
Birou notarial: Biroul Individual Notarial „Exemplu Ana”
Licența de funcționare nr. 0000/2010 (fictiv)
Sediul: Municipiul Exemplu, Str. Fictivă nr. 10, Jud. Exemplu
Dosar succesoral nr. 123/2026 (procedură reluată)

CERTIFICAT DE MOȘTENITOR SUPLIMENTAR Nr. 95
Data: 10.11.2026

Ana EXEMPLU, notar public, cercetând piesele dosarului de mai sus, precum și încheierea finală
suplimentară din data de 10.11.2026, în temeiul art. 12 lit. c) și al art. 115 din Legea notarilor
publici și a activității notariale nr. 36/1995, republicată, cu modificările ulterioare, și al art. 118
alin. (2) din aceeași lege, la cererea moștenitorilor și cu acordul tuturor acestora, exprimat în scris,
certific următoarele:

Prezentul certificat completează Certificatul de moștenitor nr. 87 din 22.10.2026.

De pe urma defunctei IONESCU MARIA, CNP 2XXXXXXXXXXXX, decedată la data de 03.09.2026, cu ultimul
domiciliu în Municipiul Exemplu, Str. Fictivă nr. 1, județul Exemplu, au mai rămas următoarele bunuri,
omise din masa succesorală stabilită prin certificatul inițial:

Defuncta a fost căsătorită cu IONESCU ION sub regimul matrimonial al comunității legale de bunuri,
regim care a fost lichidat prin încheierea finală din data de 22.10.2026, completată prin încheierea
finală suplimentară din data de 10.11.2026; disponibilitățile din depozitul de mai jos sunt bun comun,
cu cote de 1/2 pentru fiecare soț.

I. Masa succesorală (bunuri omise):
a) bunuri mobile:
   1. cota de 1/2 din disponibilitățile bănești din depozitul la termen
      IBAN RO00 RZBR 0000 0000 0000 02, deschis la Raiffeisen Bank S.A., cu dobânzile aferente,
      depozit cu scadența la 03.01.2027;
b) bunuri imobile: nu există.
Natura succesiunii: cea stabilită prin Certificatul de moștenitor nr. 87 din 22.10.2026.

II. Moștenitori/Legatari
Moștenitorii și cotele ce le revin sunt cei stabiliți prin Certificatul de moștenitor nr. 87 din
22.10.2026, respectiv:
1. IONESCU ION, CNP 1XXXXXXXXXXX1, în calitate de soț supraviețuitor;
2. IONESCU ANDREI, CNP 1XXXXXXXXXXX2, în calitate de fiu;
3. IONESCU ELENA, CNP 6XXXXXXXXXXX3, în calitate de fiică, minoră, cu încuviințarea tatălui,
   IONESCU ION;
în cotele menționate în certificatul inițial.

Renunțători: nu este cazul.

S-a perceput impozit în sumă de 0,00 lei (art. 111 alin. (1) Cod fiscal).
S-a perceput onorariul în sumă de 000,00 lei, cu TVA în sumă de 000,00 lei, și a fost achitat cu
chitanță nr. 0000 (fictiv).

Notar public,
Ana EXEMPLU
(semnătură indescifrabilă)                                        L.S.
```

**Câmpuri de extras (ground truth):**
- Certificat: `doc_type=certificat_mostenitor_suplimentar`, `nr_certificat="95"`, `data_certificat=2026-11-10`,
  `ref_certificat_initial={nr:"87", data:2026-10-22}`, `nr_dosar_succesoral="123/2026"`.
- `masa_activ`, un singur element: IBAN `…02`, `cota_defunct="1/2"`, `valoare=2.000.000 bani` (principal, din core; nu e scrisă în certificat),
  `scadenta=2027-01-03`.
- `mostenitori`: 3 CNP-uri fără cote, `cote_din="ref_certificat_initial"`.
- `acord_mostenitori=exprimat`.

**Ce face agentul:**
1. Validează că certificatul inițial nr. 87 e în dosar, că CNP-urile moștenitorilor sunt identice și că notarul și dosarul
   sunt aceleași.
2. Ia cotele din doc 4 (A sau B). `coverage_gaps=[]`.
3. Rulează `split_by_shares` pe CC-1 (527.337 bani) și pe DEP-1 la scadență (2.104.000 bani brut), conform §2.4:

   | Moștenitor | A: CC-1 | A: DEP-1 | B: CC-1 | B: DEP-1 |
   |---|---|---|---|---|
   | Ion | 329.585 | 1.315.000 | 395.503 | 1.578.000 |
   | Andrei | 98.876 | 394.500 | 65.917 | 263.000 |
   | Elena | 98.876 *(blocat)* | 394.500 *(blocat)* | 65.917 *(blocat)* | 263.000 *(blocat)* |

4. Face planul de plată: CC-1 acum, DEP-1 la 2027-01-03. Recomandă așteptarea scadenței (+1.040,00 lei dobândă). Plata
   intră în `pending_approval`, iar partea Elenei rămâne blocată până la cont pe numele ei + încuviințare.

**Stare după:** `PAYMENT_PENDING_APPROVAL`.

## Doc 7 — Certificat de deces ilizibil, alt client · 2026-11-12 · tip `certificat_deces`
**Fișier:** `07-certificat-deces-ilizibil.md` / `.json`. Câmpuri: schema din
`kb/document-templates/certificat-deces.md` (model HG 255/2024 Anexa 3, fizic). Simulează o scanare degradată:
rotită ~7°, pată de cerneală peste CNP și data decesului, colțul dreapta-jos rupt. Textul de mai jos e ce poate citi
OCR-ul; `█` = indescifrabil.

```
ROMÂNIA
CERTIFICAT DE DECES
CERTIFICAT DE DÉCÈS / DEATH CERTIFICATE

Date privind decedatul
  Données concernant le décédé/Data concerning the deceased
Cod numeric personal   1 █ █ █ █ █ █ █ █ █ █ █ █
  Code numérique personnel/Personal identification number
Numele de familie      POP██████
  Nom/Surname
Prenumele              GHEOR███
  Prénom/First name
Sexul                  M
  Sexe/Sex
Data nașterii          19██ / ██ / ██
  Date de naissance/Date of birth   Anul/Année/Year  Luna/Mois/Month  Ziua/Jour/Day
Locul nașterii         ███████, Jud. ████
  Lieu de naissance/Place of birth   Localitatea/Localité/Locality  Județul/Département/County
Domiciliul             Mun. Ex████, Str. ██████ nr. ██
  Domicile/Domicile   Localitatea/Localité/Locality  Județul/Département/County
Data decesului         2026 / ██ / ██
  Date du décès/Date of death   A/A/Y  L/M/M  Z/J/D
Locul decesului        ████████, Jud. ████
  Lieu du décès/Place of death   Localitatea/Localité/Locality  Județul/Département/County

Date privind părinții
  Données concernant les parents/Data concerning the parents
Tatăl  Numele de familie  POP██████
  Père/Father  Nom/Surname
Tatăl  Prenumele          ██████
  Prénom/First name
Mama   Numele de familie  ████████
  Mère/Mother  Nom/Surname
Mama   Prenumele          ███████
  Prénom/First name

Act de deces nr. ███   din 2026 / ██ / ██
  Acte de décès no/Death entry no.  de/from  Anul/Année/Year  Luna/Mois/Month  Ziua/Jour/Day
Înregistrat la         SPCLEP ████████, Jud. ████
  Enregistré à/Registered at   Localitatea/Ambasada/Consulatul  Județul/Département/County
Mențiuni               -
  Mentions/Mentions

Eliberat de            ████████
  Délivré par/Issued by
Data                   ██.██.2026            Semnătura
  Date/Date   Signature/Signature
Certificat seria XX nr. 0000███
  Certificat Série no./Certificate Series no.
[colț rupt: șirul unic și semnătura lipsesc]
```

**Ground truth la extracție:**
- `doc_type=certificat_deces`, `format=fizic_2024`, `legibility=illegible`.
- Ilizibile: `cnp=null` (necitibil, `confidence ≈ 0`), `data_decesului=null`, `data_nasterii=null`, `sir_unic=null`.
- Parțiale: `nume_familie_partial="POP"`, `prenume_partial="GHEOR"`, `sex="M"`.
- Confidence global sub prag (< 0,5).

**Valori ascunse** (doar pentru testul negativ, în `registries/generator/test_only/07-hidden-truth.json`; agentul **nu** trebuie să le ghicească, iar generatorul nu le folosește):
POPOVICI GHEORGHE, CNP `1XXXXXXXXXXX9`, client `RC1002`, decedat 2026-11-02.

**Ce face agentul:**
1. Clasifică documentul ca certificat de deces. Nu potrivește nimic: fără CNP, numele parțial nu e unic și nu e Maria
   (sex M, CNP începe cu 1).
2. **Escaladează** la operator cu motivul `illegible_cnp`.
3. Nu face niciun freeze, nu deschide niciun dosar automat. Dosarul `RC1001` rămâne neatins: nicio scriere, nicio
   schimbare de stare.
4. Nu face potrivire „fuzzy” pe nume parțial.

**Stare după:** dosarul Mariei neschimbat (`PAYMENT_PENDING_APPROVAL`); un element nou în coada de escaladare.

## Ce înseamnă pentru agent
- Setul de test pentru clasificare și extracție are 8 fișiere: 7 documente, cu 4A/4B. Fiecare are câmpuri cu valori
  exacte în `registries/documents/*.json`. Sumele sunt în bani (întregi), cotele ca fracții `"a/b"` (string), datele
  ISO.
- Documentul 7 calibrează pragul de escaladare. Documentele 4A/4B arată că același cod tratează moștenirea legală și pe
  cea testamentară.
- Toate numerele de corelare (dosar `123/2026`, contract `NP-2023-001001`, certificat `UQ-0000000-FICTIV`, certificat
  nr. 87) apar identic în toate documentele. O nepotrivire într-un test derivat (§4 din `maria-ionescu.md`) trebuie să
  ducă la escaladare.

## Necunoscut
- Formatul real al lotului DGEP (doar câmpurile sunt cunoscute, din nota Raiffeisen), macheta reală a certificatului
  UNIQA și răspunsul real de aprobare a daunei nu sunt publice. Le-am generat noi, pe etichetele formularului
  CD_UAV_V8_04.2024 și pe IPID (`kb/bank-procedures/asigurare-viata-credit.md`).
- Formula exactă prin care notarul trece în certificat încasarea pensiei după deces: am ales „sold la deces + pensia
  lunii decesului”, ca să fie consistentă cu §2.3 (v1 o tratează ca bun comun, în masă). E o întrebare deschisă și în
  `maria-ionescu.md`.
- Dacă notarul scrie pasivul acoperit de asigurare în certificat sau doar dobânda rămasă: am trecut ambele, cu mențiunea
  dosarului de daună.
