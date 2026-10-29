Sursă: generat de noi pe baza practicii; temei: https://notari.pro/legea-36-1995/art-81, https://notari.pro/legea-36-1995/art-112, https://notari.pro/legea-36-1995/art-115, https://notari.pro/regulament-aplicare-legea-36-1995/art-238, https://www.avocatnet.ro/forum/discutie_735783/Ce-informa%C8%9Bii-trebuie-s%C4%83-con%C8%9Bin%C4%83-extrasul-de-cont-pentru-succesiune.html, https://legislatie.just.ro/Public/DetaliiDocument/175630 (Cod civil, art. 1114) · Accesat: 2026-10-28 · Owner: DOCS

# Răspunsul băncii către notar (document GENERAT de agent)

Prioritate P0. **Generat de noi pe baza practicii**: nu am găsit niciun model public (UNNPR, ARB sau bancă) al răspunsului unei bănci către notar. Structura de mai jos derivă din (a) ce trebuie să intre în încheierea finală și certificat (Legea 36/1995 art. 112, 115), (b) ce cere adresa notarului (`adresa-notar-catre-banca.md`) și (c) problemele raportate în practică.

## De ce așa (temeiuri)

- Obligația de a răspunde: Legea 36/1995, art. 81 alin. (2): „Instituţiile publice şi private au obligaţia să furnizeze, în condiţiile legii, informaţiile pe care le solicită notarii publici în cadrul procedurilor succesorale notariale.”
- Ce face notarul cu răspunsul — încheierea finală conține (art. 112 alin. 2): „m) masa succesorală declarată: bunuri mobile, bunuri imobile şi pasivul succesiunii; [...] o) [...] notarul public va constata compunerea masei succesorale, valoarea activului sau, după caz, valoarea masei de calcul, valoarea pasivului şi a activului net”. Deci răspunsul trebuie să separe clar **activ** (conturi, depozite) de **pasiv** (credite).
- Certificatul preia constatările din încheiere (art. 115 alin. 1) → fiecare produs trebuie identificat nominal (IBAN), altfel banca însăși nu va putea plăti pe certificat. Caz real (avocatnet, 2020): banca a refuzat plata pentru că „în actul de succesiune sunt menționate doar sumele”, cerând act „care să specifice și conturile efectiv”.
- Pasivul: Cod civil art. 1114 (moștenitorii răspund pentru datorii în limita activului) — detaliat în `legal/cod-civil-succesiuni.md`.

## Structura recomandată

1. **Antet bancă** (denumire, CUI, nr. registru, sediu, unitate emitentă, contact pentru notar).
2. **Nr. de ieșire și dată**; „Către: Biroul notarial [X], notar public [Y]”.
3. **Referință:** „Răspuns la adresa dvs. nr. ___ din ___, dosar succesoral nr. ___”.
4. **Identificarea defunctului:** nume, prenume, CNP, data decesului (cum apare în certificatul de deces/adresă).
5. **Tabel A – Activ (produse de economisire/curente) la data decesului:**
   coloane: Nr. · Tip produs · IBAN · Valută · Titulari (unic/co-titular) · Data deschiderii · Sold la data decesului (inclusiv) · Dobândă acumulată neîncasată până la data decesului · Total · Observații (scadență, rată dobândă, regim lichidare anticipată, împuterniciți încetați).
6. **Tabel B – Pasiv (credite, carduri de credit, descoperit) la data decesului:**
   coloane: Nr. · Tip · Nr. contract · Data contractului · Sold principal · Dobândă/comisioane restante · Total datorat · Asigurare de viață atașată (asigurător, nr. poliță, stare: „dosar de daună deschis la data ___” / „neacoperit”) · Garanții.
7. **Cutii de valori:** „Defuncta nu a avut închiriate cutii de valori” sau nr. contract + mențiunea că inventarul se face în prezența notarului.
8. **Mențiuni:**
   - sumele încasate în cont **după** data decesului (ex. pensie) nu fac parte din soldul la deces și pot face obiectul restituirii către plătitor (`legal/legea-pensiilor-deces.md`);
   - comisioanele percepute după data decesului au fost/vor fi stornate și nu afectează soldul la deces;
   - conturile au fost blocate pentru debit la data de ___; împuternicirile au încetat la data decesului (C.civ. art. 2030);
   - eventuale sume datorate băncii vor fi reținute din activ doar în condițiile legii / acordului moștenitorilor (de stabilit cu DOMAIN).
9. **Clauză de confidențialitate / secret bancar:** „Informațiile sunt furnizate exclusiv în scopul procedurii succesorale nr. ___, în temeiul art. 81 alin. (2) din Legea nr. 36/1995 și cu respectarea regimului secretului bancar (OUG nr. 99/2006). Nu pot fi folosite în alt scop.”
10. **Semnături:** două persoane autorizate ale băncii (regula „patru ochi”; practică bancară, nu cerință legală găsită) + ștampilă / semnătură electronică calificată. **Agentul NU semnează**: generează draftul, omul aprobă.

## Schema documentului generat

| Câmp | Tip | Obligatoriu | Sursa datelor |
|---|---|---|---|
| `nr_iesire`, `data` | string, date | da | registratura băncii |
| `ref_adresa_notar_nr`, `ref_adresa_notar_data` | string, date | da | extras din adresă |
| `nr_dosar_succesoral` | string | da | extras din adresă |
| `notar`, `birou_notarial`, `adresa_livrare` | string | da | extras din adresă |
| `defunct` {nume, prenume, cnp, data_decesului} | obiect | da | core banking + certificat |
| `activ[]` {tip, iban, valuta, titulari, data_deschidere, sold_la_deces, dobanda_acumulata, total, observatii} | listă | da (poate fi goală cu mențiune) | API `products-at-date` + funcția `balance_at_death` |
| `pasiv[]` {tip, nr_contract, sold_principal, dobanzi_comisioane, total, asigurare {asigurator, nr_polita, stare}, garantii} | listă | da | API `products-at-date` |
| `cutii_valori` | listă / „nu există” | da | |
| `mentiuni[]` | listă text | da | reguli fixe + dosar |
| `clauza_secret_bancar` | text fix | da | |
| `semnatari[]` | listă (2) | da | aprobare umană |
| `generated_by_agent`, `approved_by`, `approved_at` | meta | da | audit |

## Exemplu fictiv (scenariul demo; sumele exacte vin din `scenariu-demo/maria-ionescu.md`)

```
RAIFFEISEN BANK S.A. – [unitate]                     Nr. ______ / __.__.2026
Către: Biroul Individual Notarial „Notar Exemplu”, notar public [nume fictiv]
Ref.: adresa dvs. nr. 0000 din 22.09.2026 – dosar succesoral nr. 000/2026

Defuncta: IONESCU MARIA, CNP 2XXXXXXXXXXXX, decedată la 03.09.2026.

A. Produse de economisire și curente – situația la data decesului (03.09.2026)
| Nr | Produs              | IBAN                       | Val. | Sold la deces | Dobândă acumulată | Total     | Observații                         |
| 1  | Cont curent         | RO00 RZBR 0000 0000 0000 01 | RON  | 3.200,00      | [calc]            | [calc]    | blocat debit 20.09.2026            |
| 2  | Depozit la termen   | RO00 RZBR 0000 0000 0000 02 | RON  | 20.000,00     | [calc] (pro-rata) | [calc]    | scadență 03.01.2027 (≈4 luni)      |

B. Obligații – situația la data decesului
| Nr | Produs                  | Contract | Sold datorat | Asigurare de viață                       |
| 1  | Credit nevoi personale  | 000/2024 | 9.000,00     | DA – [asigurător], poliță nr. 000; dosar de daună în curs |

C. Cutii de valori: nu există.
D. Mențiuni: pensia creditată la 15.09.2026 (după deces) nu face parte din soldul la deces;
   comisionul de pachet perceput după 03.09.2026 a fost stornat; împuternicirea dlui Andrei Ionescu
   a încetat la data decesului.
E. Informațiile sunt furnizate exclusiv pentru dosarul succesoral nr. 000/2026, art. 81 alin. (2)
   Legea 36/1995; secret bancar – OUG 99/2006.

Semnături autorizate: [1] __________  [2] __________   L.S.
```

`[calc]` = rezultat din `balance_at_death` (funcție deterministă); nu inventăm cifre aici. Datele (blocare 20.09, scadență) sunt fictive, aliniate la BRIEF §2.

## Necunoscut

- Model public de răspuns bancă → notar: negăsit (căutat: uniuneanotarilor.ro, forumuri notariale, site-uri bănci). Tot documentul este **generat de noi pe baza practicii**.
- Dacă notarul cere dobânda „acumulată până la data decesului” sau „capitalizată” — formularea diferă de la notar la notar; regula de calcul (pro-rata zilnic pe baza ratei contractuale vs. dobândă la vedere la lichidare anticipată) trebuie fixată cu DOMAIN în `bank-procedures/raiffeisen-tarife-produse.md`.
- Cine semnează la Raiffeisen (funcții, regula 2 semnături) — procedură internă nepublică.

## Ce înseamnă pentru agent

1. Răspunsul se generează **doar** după ce: adresa notarului e validată (CNP, nr. dosar, data decesului), data decesului e confirmată de certificat sau DGEP, iar `balance_at_death` a rulat pentru **toate** produsele clientului (activ + pasiv), inclusiv cele cu co-titular.
2. Sumele din tabel provin numai din funcții deterministe; LLM-ul doar compune textul. Test: suma rândurilor A == total activ calculat; fiecare produs activ din core banking apare exact o dată (completitudine — altfel ajungem la certificat fără depozit și supliment, ca în demo).
3. Fiecare produs are IBAN/nr. contract (evită refuzul „doar sume” la plată).
4. Mențiuni obligatorii automate: încasări post-deces, comisioane stornate, împuterniciri încetate, asigurare atașată creditului.
5. **Escaladare / aprobare umană obligatorie:** întotdeauna pentru trimitere (semnătură); în plus marcaj de risc dacă: co-titulari, produse în valută, depozit cu regim special, credit fără asigurare sau cu daună respinsă, cerere de informații în afara listei standard, discrepanță între data decesului din adresă și din dosar.
6. Termen: răspunsul trebuie trimis înainte de termenul de dezbatere din adresă (Regulament art. 238); agentul urmărește termenul și alertează.
