Sursă: CGB Raiffeisen PF 2026 clauza 3.2.5 (vezi `kb/bank-procedures/raiffeisen-cgb-pf-extras.md`) ; Cod civil art. 1.133–1.134, 1.143–1.144 (`kb/_downloads/nicolas/codcivil-175630.html`, vezi și `kb/document-templates/certificat-mostenitor.md`) ; https://legeaz.net/noul-cod-de-procedura-civila/art-634 (CPC art. 634, copie neoficială; text oficial: Legea 134/2010 pe legislatie.just.ro) · Accesat: 2026-10-28 · Owner: DOMAIN

Copii locale: `kb/_downloads/visi/legeaz-cpc-art633.html`, `legeaz-cpc-art634.html`, `legeaz-cpc-art635.html`.

# Hotărârea judecătorească în succesiune (partaj, calitate de moștenitor)

Prioritate P2 (nu apare în scenariul demo, dar CGB o prevede ca alternativă la certificat).

**Corecție de referință:** Nicolas a citat „CGB 3.2.5 d)”. În textul CGB 2026 hotărârea apare la **3.2.5 lit. c)**; lit. d) privește utilizatorii de carduri suplimentare.

## Texte relevante
**CGB 3.2.5 c):** pot dispune liber de sumele din conturi „mostenitorii titularului, care dovedesc cu certificat de mostenitor sau cu hotarare judecatoreasca aceasta calitate.”

**Cod civil art. 1.133 alin. (1):** „Certificatul de moștenitor face dovada calității de moștenitor, legal sau testamentar, precum și dovada dreptului de proprietate al moștenitorilor acceptanți asupra bunurilor din masa succesorală, în cota care se cuvine fiecăruia.”

**Cod civil art. 1.134:** „Cei care se consideră vătămați în drepturile lor prin eliberarea certificatului de moștenitor pot cere instanței judecătorești constatarea sau, după caz, declararea nulității acestuia și stabilirea drepturilor lor, conform legii.”

**Cod civil art. 1.143 alin. (1):** „Nimeni nu poate fi obligat a rămâne în indiviziune. Moștenitorul poate cere oricând ieșirea din indiviziune […]”. **Art. 1.144 alin. (1)–(2):** partaj voluntar cu toți moștenitorii prezenți și capabili; dacă „printre ei se află minori […]” se respectă regulile de protecție (vezi `mostenitor-minor.md` §6). Partajul judiciar urmează art. 669–686 din Cod civil, aplicabile prin trimitere (art. 1.143 alin. 2).

**CPC art. 634 alin. (1) – hotărâri definitive:** „1. hotărârile care nu sunt supuse apelului şi nici recursului; 2. hotărârile date în primă instanţă, fără drept de apel, neatacate cu recurs; 3. hotărârile date în primă instanţă, care nu au fost atacate cu apel; 4. hotărârile date în apel, fără drept de recurs, precum şi cele neatacate cu recurs; 5. hotărârile date în recurs […]”.

## Când înlocuiește certificatul
Din CGB 3.2.5 c) (literal) și art. 1.133–1.134 (interpretare): hotărârea e folosită când calitatea de moștenitor sau cotele **nu rezultă dintr-un certificat** sau rezultă dintr-un certificat contestat și modificat: (a) hotărâre care constată/declară calitatea de moștenitor ori nulitatea certificatului (art. 1.134); (b) hotărâre de **partaj** care atribuie sumele din cont unui moștenitor; (c) altă hotărâre cu efect asupra cotelor. Hotărârea nu înlocuiește de regulă identificarea contului și a sumei: banca are nevoie să afle ce cont/sume vizează (vezi Necunoscut).

## Ce se verifică
- **Definitivă** (CPC art. 634): mențiune „definitivă” pe hotărâre și/sau dovada neatacării (certificat de definitivitate/ necomunicare apel-recurs). Proiect de agent: cere ambele (propunere proprie).
- **Copie certificată/legalizată** conform cu originalul de instanță (practică; nu am găsit text care o cere pentru bancă).
- Părțile din hotărâre includ **toți** moștenitorii care pretind sume; lipsa unuia = partaj parțial → om.
- Identifică defunctul (nume, CNP/data decesului) și ultimul domiciliu.

## Schema de extracție
| Câmp | Tip | Obligatoriu | Note |
|---|---|---|---|
| `doc_type` | `hotarare_judecatoreasca` | da | |
| `instanta`, `nr_dosar`, `nr_hotarare`, `data_pronuntarii` | string/date | da | |
| `tip` | enum `partaj` \| `constatare_calitate_mostenitor` \| `nulitate_certificat` \| `altele` | da | |
| `definitiva` | bool + `data_ramanerii_definitive` | da | |
| `copie_certificata` | bool | da | |
| `defunct` {nume, cnp, data_decesului} | obiect | da | |
| `parti[]` {nume, calitate, cota_sau_atribuire} | listă | da | |
| `dispozitiv` | text | da | citat literal |
| `conturi_vizate[]` | listă {iban, valoare} | nu | |
| `confidence` | float per câmp | da | |

## Exemplu fictiv
```
instanta: Judecătoria Sectorului 1 București (fictiv); dosar 9999/299/2026; hotărâre 1500/12.09.2026
tip: partaj ; definitiva: true (rămasă definitivă la 20.10.2026, neapelată)
defunct: Ionescu Maria, CNP 2700101000000 (fictiv), dec. 05.06.2026
parti: Ionescu Andrei 3/8 ; Ionescu Elena 3/8 (reprezentată) ; Ionescu Ion 1/4
dispozitiv (citat): „Atribuie reclamantului Ionescu Andrei suma din contul RO00XXXX000000000000 […]”
```

## Necunoscut
- **Tipurile de hotărâre pe care Raiffeisen le acceptă** și condițiile (definitivă, legalizată, cu formulă executorie): CGB spune doar „hotarare judecatoreasca”; nu am găsit ghid public.
- Dacă hotărârea trebuie să identifice **contul** sau poate fi generală: neclar.
- Procedura în care instanța stabilește calitatea de moștenitor în loc de notar (text de CPC/Legea 36): nu l-am extras.
- CPC art. 634 are și alin. (2)+; am citat doar alin. (1) pct. 1–5.
- Formula executorie nu apare în sursele citite.

## Ce înseamnă pentru agent
1. Un document tip hotărâre **nu declanșează plata** automat: agentul extrage câmpurile, verifică `definitiva` și `copie_certificata`, apoi trimite la **operator** (aprobare umană obligatorie în prima versiune).
2. Dacă `definitiva = false` sau lipsește dovada definitivității: dosarul rămâne `INCOMPLET`; mesaj către solicitant: lipsește mențiunea/dovada că hotărârea e definitivă.
3. Cotele vin din hotărâre, nu din cotele legale; agentul nu le recalculează.
4. Dacă un minor e parte, rămân valabile regulile din `mostenitor-minor.md` (încuviințare, cont pe numele minorului, flag conflict de interese).
5. Hotărârea schimbă ce se spune cui: după ea, titularul dreptului la informații este moștenitorul din dispozitiv (`secret-bancar.md`, RIL 9/2024).
6. KYC al beneficiarului rămâne obligatoriu (`aml-kyc-mostenitori.md`).
