Sursă: CGB Raiffeisen PF 2026 clauza 3.2.5 (`kb/bank-procedures/raiffeisen-cgb-pf-extras.md`) ; `kb/legal/aml-kyc-mostenitori.md` (Legea 129/2019 art. 11, 13, 21; Reg. BNR 2/2019 art. 8) ; `kb/legal/mostenitor-minor.md` ; `kb/legal/secret-bancar.md` · Accesat: 2026-10-28 · Owner: DOMAIN

# Cererea de eliberare a sumelor (semnată de moștenitor la bancă)

Prioritate P1. **Nu am găsit un formular public Raiffeisen pentru plata către moștenitori** (nici pagină, nici model; vezi `raiffeisen-deces-ghid.md`). Schema de mai jos este **propunerea noastră**, derivată din CGB, AML/KYC și regulile pentru minori; nu un document oficial al băncii.

## Ce pune legea / CGB ca bază
- **CGB 3.2.5 c):** moștenitorii pot dispune de sume dacă „dovedesc cu certificat de mostenitor sau cu hotarare judecatoreasca aceasta calitate”.
- **Legea 129/2019 art. 11 alin. (1) lit. a)** identificarea și verificarea identității din surse sigure; **art. 15 alin. (1) lit. a)** „toate datele de stare civilă prevăzute în documentele de identitate”; **Reg. BNR 2/2019 art. 8** nume, prenume, data și locul nașterii, CNP. Detalii și praguri în `aml-kyc-mostenitori.md`.
- **Legea 129/2019 art. 11 alin. (9):** dacă măsurile nu pot fi aplicate, nu se efectuează tranzacția.
- **Legea 129/2019 art. 21 alin. (1):** copiile documentelor de identificare se păstrează 5 ani.

## Ce semnează moștenitorul (câmpuri propuse)
| Câmp | Tip | Obligatoriu | Note |
|---|---|---|---|
| `doc_type` | `cerere_eliberare_sume` | da | |
| `solicitant` {nume, prenume, cnp, data_nasterii, loc_nasterii, domiciliu, act_identitate{tip, serie, nr, emitent, valabil_pana}} | obiect | da | Reg. 2/2019 art. 8 |
| `calitate` | enum `mostenitor_legal` \| `mostenitor_testamentar` \| `legatar` \| `reprezentant_legal` \| `mandatar` | da | |
| `defunct` {nume, cnp, data_decesului} | obiect | da | din certificatul de deces |
| `act_calitate` {tip (certificat_mostenitor \| hotarare), nr, data, emitent} | obiect | da | |
| `cota` | fracție | da | din act, nu calculată |
| `produse_vizate[]` | listă | da | conturi/depozite din act |
| `iban_destinatar` {iban, titular, banca} | obiect | da | titular = moștenitorul (sau minorul) |
| `deja_client_raiffeisen` | bool | da | determină KYC existent vs. nou |
| `scop` | text | da | justificarea scopului pentru informații (RIL 9/2024, `secret-bancar.md`) |
| `pep` | bool + descriere | da | declarație PEP (Legea 129/2019 art. 11 alin. 3, 17) |
| `beneficiar_real` | enum `eu_insumi` \| `alta_persoana` + date | da | art. 11 alin. 1 lit. b) |
| `declaratii` | listă bool | da | (a) cunosc existența altor moștenitori conform actului; (b) nu există alte acte ulterioare (hotărâri/ certificat suplimentar) cunoscute; (c) datele sunt reale — formulări propuse, de validat juridic |
| `consimtamant_gdpr_info` | bool | da | informare art. 13–14 GDPR (prelucrare pe art. 6 alin. 1 lit. c, vezi `gdpr-decedati-mostenitori.md`) |
| `data`, `semnatura` | date, bool | da | |
| `confidence` | float per câmp | da | |

## Particularități minor (`mostenitor-minor.md`)
- **Minor 14–17 ani:** cerere semnată de minor **și** încuviințarea scrisă a părintelui care exercită autoritatea părintească; **IBAN pe numele minorului**; actele de identitate ale ambilor.
- **Minor sub 14 ani:** semnează părintele/tutorele ca reprezentant legal (art. 43 alin. 2 Cod civil, cum e citat în fișierul minorului), tot cu cont pe numele minorului.
- Dacă părintele e și comoștenitor: flag `CONFLICT_INTERESE_PARINTE_MINOR` + aprobare umană.
- Retragere din contul minorului sau altă destinație: autorizarea instanței de tutelă (escaladare).

## Exemplu fictiv
```
solicitant: Ionescu Andrei, CNP 1900101000000 (fictiv), născut 01.01.1990 București; CI RX 000000 (fictiv)
calitate: mostenitor_legal ; defunct: Ionescu Maria, dec. 05.06.2026
act_calitate: certificat de moștenitor nr. 77/15.08.2026, notar Popescu (fictiv) ; cota: 3/8
produse_vizate: cont curent RO00XXXX000000000000 (fictiv)
iban_destinatar: RO00YYYY000000000001, titular Ionescu Andrei
deja_client_raiffeisen: false ; pep: false ; beneficiar_real: eu_insumi
scop: „încasarea cotei din succesiune” ; declaratii: [true, true, true]
```

## Necunoscut
- Formularul real al Raiffeisen (dacă există) și lista oficială de documente: nepublice.
- Dacă banca cere declarațiile (a)–(c) sau alt text: propunere proprie.
- Dacă moștenitorul fără cont primește plata ca „tranzacție ocazională” sau trebuie să deschidă cont: practică internă (vezi `aml-kyc-mostenitori.md`).
- Cursul de echivalare lei–EUR pentru pragul de 15.000 EUR: nesigur.
- Textul art. 43 alin. 2 etc. citat prin `mostenitor-minor.md`, nu reverificat aici.

## Ce înseamnă pentru agent
1. **Agentul pregătește cererea pre-completată** din certificat (nume, cote, conturi, IBAN din formular) și o trimite spre semnare; **nu o semnează, nu o consideră valabilă fără semnătura moștenitorului**.
2. **Validări automate:** IBAN valid ca format și **titular = solicitant** (sau minor, la minor); CI valabilă; `cota` din act, fără recalculare; produsele vizate ⊂ cele din act.
3. **KYC (`aml-kyc-mostenitori.md`):** colectează date; verificarea identității și decizia de risc rămân la om/proces KYC. KYC neterminat ⇒ oprire plată (art. 11 alin. 9), mesaj către moștenitor doar „lipsesc documente de identificare”.
4. **Mandatar:** vezi `procura-notariala.md` (obiect expres, autentic, RNNEPR).
5. **Hotărâre judecătorească în loc de certificat:** vezi `hotarare-judecatoreasca.md`.
6. **Minor:** aplică regulile de mai sus; conflict de interese ⇒ aprobare umană.
7. **Secret bancar:** cererea cu `scop` justifică informarea moștenitorului pentru perioada dinainte de deces (RIL 9/2024); răspunsul se face doar moștenitorului/mandatarului verificat.
8. **Păstrare:** copiile KYC 5 ani; restul conform `gdpr-decedati-mostenitori.md`.
