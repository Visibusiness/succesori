# BRIEF: Agentul de Succesiune — VibeHack 2026 (Raiffeisen Bank)

> Acest fișier e prompt-ul de pornire pentru sesiunile Claude Code ale echipei. Citește-l integral înainte de orice acțiune.
> Suntem 4 oameni, 4 sesiuni Claude Code, pe mașina `mosteniri-reiff`, în folderul comun al repo-ului (git).
> Protocolul de coordonare e cel din `coordonare/CUM-LUCRAM.md`; acest brief spune CE facem, acela spune CUM ne împărțim.
> Faza curentă: **Faza 0 — KB de documente și planul ierarhic de fișiere. NU se scrie cod încă.**

---

## 1. Contextul hackathonului

- Organizator: Nexxt / VibeHack, sponsor **Raiffeisen Bank România**. Temă oficială (PDF): „Provocare deschisă: agenți AI în servicii bancare”, produs condus de agenți AI construiți de noi, demo live end-to-end.
- Indicația verbală a Raiffeisen: **Operational Efficiency** — „Explore how AI agents can reduce repetitive work involving documents, data, and verification.”
- Grila juriului:

| Pondere | Criteriu | Ce înseamnă pentru noi |
|---|---|---|
| 25% | Agent design & orchestration | tool-uri reale, decizii multi-pas, **situații neașteptate tratate explicit** |
| 20% | Functional completeness & testability | scenariu rulabil de juriu, teste, „și dacă…?” cu răspuns demonstrabil |
| 15% | Originality | temă pe care nicio altă echipă nu o are |
| 15% | Problem research & domain | reguli, legi, termene, excepții citate |
| 15% | Architecture & reproducibility | module, interfețe clare, README cu setup |
| 10% | Business mentoring | volum, cost real, adoptabil de bancă |

Concluzie: 45% din punctaj vine din tratarea excepțiilor + testabilitate, nu din UI.

## 2. Ideea aleasă: „Moștenirea” — agentul de succesiune

### Problema
Când moare un client, banca trece printr-un proces de 6–24 luni, condus de documente pe hârtie care vin din 4 direcții (familie, notar, asigurător, DGEP/Evidența Populației) în ordine imprevizibilă, prin agenții diferite, fără un dosar unic:

1. **Aflarea decesului** → blocare debit, încetare împuterniciți și carduri suplimentare (CGB Raiffeisen PF 3.2 b/d, 5.10.4 c; Cod civil art. 2030), oprire debitări directe și comisioane.
2. **Adresa notarului** → soldurile *la data decesului* (nu azi), cu dobânda acumulată, pe toate produsele; răspuns în scris.
3. **Credite + asigurare de viață** → identificare poliță, dosar de daună, recalcul datorie (Cod civil art. 1114: moștenitorii răspund în limita activului).
4. **Certificatul de moștenitor** → cote (ex. soț 1/2, copii 1/4 fiecare), verificare că acoperă toate produsele (altfel supliment de la notar), calcul pe fiecare produs după reținerea datoriilor, plată.
5. **Cazuri speciale** → minor, moștenitor în străinătate cu procură, cont comun cu soțul, depozit nescadent (acordul tuturor, art. 2187), litigiu, succesiune vacantă.
6. **Închidere.**

### Ce pierde banca azi (dovezi)
- Caz real Raiffeisen (Ziar de Bragadiru, 2023): client decedat feb. 2020, comisioane Premium 60 lei/lună încasate până dec. 2022, 2.331 lei reținuți moștenitorului, adresa notarului „nu există” în evidențe.
- Retrageri de împuterniciți între deces și notificare; bancă care cere prezența simultană a tuturor moștenitorilor (avocatnet); conturi „inactive” trecute la venituri fără reguli (manager.ro).
- Volum: ~20.000 decese/lună în RO (INS) → ~240k/an; la cota Raiffeisen ≈ 25–30k clienți decedați/an, 3–6 interacțiuni manuale de 30–60 min fiecare → estimare 40–90k ore/an.

### Soluția
Agent care, la primul semnal de deces, deschide un **dosar de succesiune unic** per client și îl duce până la plata moștenitorilor, indiferent de ordinea în care vin documentele.

- **Face singur:** blocare debit, revocare împuterniciți, oprire + stornare comisioane de la data decesului, flag pe încasări post-deces (pensie), calcul sold la data decesului, răspuns către notar, dosar de daună la asigurător, extracție cote din certificat, cerere de supliment, plan de plată, urmărire termene (1 an opțiune succesorală).
- **NU face singur:** plata efectivă (aprobare umană), litigii, regim matrimonial fără document, documente cu scor de încredere mic.
- **Calculele sunt deterministe** (funcții pure testate): `balance_at_death`, `split_by_shares`, `net_of_debts`, `fees_to_reverse`. LLM-ul doar clasifică, extrage și orchestrează.

### Scenariul de demo (fix, nu-l schimbăm)
Defunctă: **Maria Ionescu**, deces 3 sept. Cont curent 3.200 lei (pensie 2.100 lei/lună pe 15), depozit la termen 20.000 lei scadent peste 4 luni, credit nevoi personale sold 9.000 lei cu asigurare de viață, împuternicit fiul Andrei, comision Premium 25 lei/lună. Moștenitori: soț 1/2, Andrei 1/4, Elena (15 ani) 1/4.
7 documente intră în ordinea: semnal DGEP (20 sept) → adresă notar → poliță → certificat de moștenitor (fără depozit) → răspuns asigurător → supliment notar → certificat de deces ilizibil pentru alt client (escaladare).

### Model de deploy
- **Faza 1 (ce pitch-uim): serviciu intern** al băncii. Rulează în perimetrul băncii, LLM în regiune UE, nimic nu iese.
- **Faza 2 (un slide): hub extern** multi-bancă pentru moștenitori/notari/DGEP (modelul UK Death Notification Service). Banca expune 6 endpoint-uri; hub-ul vede doar referințe și sume, calculul rămâne în bancă.
- În cod: `DEPLOYMENT_MODE=internal|hub` schimbă doar adaptorul de intake.

## 3. Arhitectura țintă a codului (pentru fazele următoare, NU acum)

```

├── BRIEF.md                 # acest fișier
├── CLAUDE.md                # al mașinii: roluri master/lucrători (nu-l rescriem)
├── coordonare/              # sarcini, rapoarte, scripturi de așteptare (există deja)
├── docs/
│   ├── Brief Raiffeisen Bank.pdf, punctare hackathon.jpeg   # materialele oficiale
│   ├── TASKS.md             # vedere de ansamblu, întreținută de master
│   ├── DECISIONS.md         # decizii luate, cu dată și cine
│   └── pitch/               # slide-uri, script de demo
├── kb/                      # knowledge base de documente (Faza 0)
├── core-mock/               # clienți, produse, tranzacții, comisioane; REST
├── registries/              # DGEP mock, asigurător mock, generator de documente
├── agent/                   # orchestrator, tools, extracție, mașina de stări, rules/
├── ops-ui/                  # coada de dosare, detaliu, aprobare plată
└── tests/                   # reguli + clasificare pe cele 7 documente
```

## 4. Echipa și sesiunile Claude

Lucrăm în rădăcina repo-ului pe mașina `mosteniri-reiff`, cu sistemul de coordonare deja existent acolo (`CLAUDE.md` și `coordonare/CUM-LUCRAM.md`): **master** = Nicolas (reiff1), **lucrători** = Visi (reiff2), Ștefan (reiff3), Marius (reiff4). Sarcinile se dau prin fișiere în `coordonare/coada/<nume>/`, rapoartele vin în `coordonare/rapoarte/`. Acel protocol are prioritate față de orice scrie aici.

Peste acel protocol, fiecare om primește un **rol de conținut** și **directoare pe care le deține** în KB. Un lucrător nu scrie în directoarele altuia; dacă are nevoie, scrie în raport și master-ul redistribuie.

| Om | Rol de conținut | Deține | Faza 0 (acum) |
|---|---|---|---|
| **Nicolas** (master) | LEAD | `BRIEF.md`, `docs/`, `kb/README.md` (ierarhia) | construiește ierarhia KB, scrie sarcinile, consolidează rapoartele |
| **Visi** | DOMAIN (drept + proceduri bancare) | `kb/legal/`, `kb/bank-procedures/` | legi, CGB, proceduri bancare, cazuri reale |
| **Ștefan** | DOCS (documente-tip + date) | `kb/document-templates/`, `kb/data/` | modele de certificate, adrese de notar, polițe; cifre INS/BNR |
| **Marius** | TECH (arhitectură + integrare) | `kb/tech/` | API-uri DGEP/ARB, Claude tool use, extracție din documente, produse similare |

### Reguli în plus față de CUM-LUCRAM.md
1. **Git:** toți pe `main` în rădăcina repo-ului, commit-uri mici cu prefix `[nume]`. Înainte de commit: `git pull --rebase`. Fără `--force`.
2. **Fișiere descărcate:** în `kb/_downloads/<nume>/`, niciodată rulate sau importate; doar citite. Extrasele relevante se copiază ca `.md` în directorul potrivit, cu sursa (URL + dată) în prima linie.
3. **Întrebări pentru master:** în secțiunea „Probleme / întrebări” a raportului, nu în alte fișiere.

## 5. Faza 0: KB de documente (sarcina de ACUM)

**Scop:** înainte de a scrie cod, să știm exact pe ce documente, reguli și date se bazează agentul, și să le avem local, organizate ierarhic.

### 5.1 Ce trebuie să facă master-ul (sesiunea lui Nicolas)
1. Citește acest brief și `coordonare/CUM-LUCRAM.md`. Nu scrie cod.
2. Creează `kb/README.md` cu **ierarhia completă de fișiere de care avem nevoie**, ca arbore, cu o linie per fișier: ce conține, de unde se obține (URL/sursă/„generat de noi”), cine îl deține (nume), prioritate (P0 = fără el nu merge demo-ul, P1, P2). Pornește de la lista din §5.2 și completeaz-o.
3. Din arbore, fă lista de sarcini (P0 întâi), fiecare cu fișierul `.md` din `kb/` care trebuie să existe la final și ce trebuie să conțină (vezi §5.3). Ține lista în `docs/TASKS.md`.
4. **Lucrezi singur, delegi oportunist.** Înainte de fiecare sarcină rulezi `coordonare/bin/cine-e-online`. Dacă apare un nume, scrii sarcina în `coordonare/coada/<nume>/NNN-titlu.md` (formatul din CUM-LUCRAM.md, potrivit rolului omului din §4) și treci la următoarea. Dacă nu e nimeni online, o faci tu. Nu aștepți după nimeni și nu blochezi pe rapoarte.
4b. Pornește în fundal `coordonare/bin/asteapta-rapoarte`. La fiecare raport: citește-l, verifică fișierul livrat (are sursă? are citate exacte?), marchează în TASKS.md și, dacă omul e încă online, dă-i următoarea sarcină din lista lui.
5. Ține `docs/TASKS.md` ca vedere de ansamblu (ce e în coadă / în lucru / gata), regenerat din folderele `coordonare/`.
6. Când toate P0 sunt gata: scrie `docs/DECISIONS.md` cu ce s-a confirmat/infirmat din brief (ex. termenul real de răspuns către notar, ce trimite DGEP exact) și propune trecerea la Faza 1 (schelet de cod).

### 5.1b Ce face un lucrător (Visi / Ștefan / Marius)
1. Citește acest brief, `coordonare/CUM-LUCRAM.md`, află-ți numele cu `coordonare/bin/cine`.
2. Pornește în fundal `coordonare/bin/asteapta-sarcina`. Cât rulează, master-ul te vede „online” și îți poate da de lucru; dacă îl oprești, master-ul face singur. Când vine sarcina, o faci după regulile din §5.3, scrii raportul, repornești așteptarea.
3. Dacă în timpul căutării dai de ceva important în afara sarcinii tale, nu-l face: notează-l în raport, la „Probleme / întrebări”.

### 5.2 Ierarhia minimă a KB (punct de pornire; master-ul o completează)

```
kb/
├── README.md                          # arborele complet + sursă + owner + prioritate
├── legal/                             # DOMAIN
│   ├── cod-civil-succesiuni.md        # art. 1100–1163 (opțiune, 1 an), 1114 (datorii), 2030 (mandat), 2187 (co-titulari)
│   ├── cod-civil-regim-matrimonial.md # comunitate de bunuri, cont comun
│   ├── legea-pensiilor-deces.md       # pensia lunii decesului / returnare
│   ├── secret-bancar.md               # OUG 99/2006, cui poate răspunde banca
│   ├── gdpr-decedati-mostenitori.md   # ce date, ale cui
│   ├── outsourcing-bnr-eba-dora.md    # pentru slide-ul „hub extern”
│   └── procedura-succesorala-notar.md # Legea 36/1995 + regulament, ce cere notarul de la bancă
├── bank-procedures/                   # DOMAIN
│   ├── raiffeisen-cgb-pf-extras.md    # clauze 3.2, 5.10.4, împuterniciți, inactivitate (din PDF-ul CGB feb 2024)
│   ├── raiffeisen-deces-ghid.md       # ce cere Raiffeisen public la deces (dacă există)
│   ├── alte-banci-deces.md            # BT, BCR, ING, BRD: liste de documente, termene (comparativ)
│   ├── dgep-arb-acord.md              # ce date vin de la Evidența Populației, de când, frecvență
│   ├── asigurare-viata-credit.md      # cum se declanșează dosarul de daună, documente, termene, refuzuri
│   └── cazuri-reale.md                # Bragadiru 2023, avocatnet, Trustpilot/conso: cu URL și citat
├── document-templates/                # DOCS
│   ├── certificat-deces.md            # câmpuri, aspect, exemplu (fără date reale)
│   ├── adresa-notar-catre-banca.md    # formulare tipice, ce cer exact
│   ├── certificat-mostenitor.md       # structură, cote, supliment
│   ├── procura-notariala.md           # obiect, limite, revocare (RNNEPR)
│   ├── cerere-eliberare-sume.md       # ce semnează moștenitorii la bancă
│   ├── polita-asigurare-viata.md      # câmpuri relevante pentru credit
│   └── hotarare-judecatoreasca.md     # când înlocuiește certificatul
├── data/                              # DOCS
│   ├── ins-decese.md                  # lunar 2024–2025, sursă
│   ├── raiffeisen-cifre.md            # clienți, cotă de piață, din rapoarte anuale
│   └── estimare-volum-cost.md         # calculul nostru 25–30k dosare/an, ore, bani; ipoteze explicite
├── tech/                              # TECH
│   ├── claude-tool-use-notes.md       # cum facem orchestrarea, schema de extracție cu scor
│   ├── document-extraction-approach.md# PDF text vs scan, OCR local, validare pe schemă
│   ├── api-contract-bank.md           # cele 6 endpoint-uri (freeze, products-at-date, fees/reverse, payment-plan, payments, cases)
│   ├── dgep-integration.md            # ce știm despre interfața reală (RNEP), ce mock-uim
│   └── similar-products.md            # UK Death Notification Service, Lightico bereavement, alte referințe
└── _downloads/                        # PDF-uri originale, pe rol; nu se rulează nimic de aici
```

### 5.3 Reguli pentru căutare (toate rolurile)
- Fiecare `.md` din KB începe cu: `Sursă: <URL> · Accesat: <dată> · Owner: <ROL>`. Fără sursă = nu intră în KB.
- Copiază citatele relevante în română, cu articolul/clauza exactă. Nu parafraza legi.
- Dacă nu găsești ceva, scrie fișierul cu secțiunea `## Necunoscut` și ce ai încercat. E informație utilă.
- Nu inventa cifre. Estimările se marchează `(estimare proprie)` cu ipotezele.
- Documente-tip: fără date personale reale; descriem câmpurile și facem exemple fictive.

## 6. Exemplu de sarcină (formatul din CUM-LUCRAM.md)

```
# 001: CGB Raiffeisen PF — clauzele despre deces
Pentru: visi
Fișiere pe care le poți modifica: kb/bank-procedures/raiffeisen-cgb-pf-extras.md, kb/_downloads/visi/
Ce trebuie făcut: descarcă PDF-ul CGB PF (link în BRIEF §8), extrage cu pdftotext, copiază textual
  clauzele 3.2 (cine dispune de cont), 5.10.4 (încetarea cardului), orice clauză cu „deces”,
  „împuternicit”, „moștenitor”, „inactiv”, cu numărul clauzei. Adaugă o secțiune „Ce lipsește din CGB”.
Gata când: fișierul există, începe cu linia de sursă, fiecare citat are numărul clauzei, e commit-at pe main.
```

Prioritate în coadă: P0 primele (numerele mici), apoi P1, P2. Un lucrător are o singură sarcină în lucru la un moment dat.

## 7. Ce NU facem în Faza 0
- Nu scriem cod, nu instalăm dependențe, nu pornim servere.
- Nu schimbăm scenariul de demo sau ideea fără decizie în `docs/DECISIONS.md`.
- Nu lucrăm în directoarele altui rol.
- Nu ștergem nimic din `kb/_downloads/`.

## 8. Referințe deja găsite (punct de pornire pentru DOMAIN/DOCS)
- CGB Raiffeisen PF, feb 2024: https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/conditii-general-bancare-pf/20240220-Conditii-generale-de-derulare-a-operatiunilor-bancare-pentru-persoane-fizice.pdf.coredownload.inline.pdf (clauza 3.2: împuterniciții „numai pe timpul vieții titularului”; moștenitorii cu certificat sau hotărâre; 5.10.4 c: cardul încetează la deces)
- Caz Raiffeisen comisioane post-deces: https://ziardebragadiru.ro/caz-complicat-la-raiffeisen-bank-cum-s-au-strans-comisioanele-luna-dupa-luna-pentru-o-persoana-decedata/
- BRD–DGEP (date inclusiv „data decesului, după caz”, din feb 2025, acord-cadru ARB–DGEP): https://www.brd.ro/colaborare-brd-evidenta-populatiei ; ING: https://ing.ro/ing-in-romania/informatii-utile/colaborare-evidenta-populatiei
- DC Business, bani din cont după deces (împuterniciți, pensie, salariu): https://www.dcbusiness.ro/banii-din-cont-dupa-moartea-titularului-greseala-care-ii-poate-pune-pe-mostenitori-in-dificultate_697260.html
- Manager.ro, conturi inactive / vid legislativ: https://www.manager.ro/articole/financiar-bancar-94/ce-fac-bancile-cu-banii-clientilor-care-decedeaza-intre-vid-legislativ-si-smecherii-113462.html
- Avocatnet, banca refuză plata pe certificat: https://www.avocatnet.ro/forum/discutie_497210/Banca-refuza-plata-drepturilor-stabilite-prin-certificat-mostenitor.html
- Lexeto, conturi în succesiune: https://www.lexeto.ro/conturi-bancare-succesiune-deblocare/
- Credit după deces: https://playtech.ro/2025/ce-se-intampla-cu-imprumutul-bancar-dupa-decesul-persoanei-ce-trebuie-sa-stie-mostenitorii/ ; https://avocatbiancaverdes.ro/succesiune-credit-bancar/
- INS decese lunare 2025: https://www.digi24.ro/stiri/actualitate/problema-demografica-a-romaniei-decesele-au-fost-de-aproape-doua-ori-mai-multe-decat-nasterile-in-decembrie-2025-3624465
- UK Death Notification Service: https://www.thegazette.co.uk/all-notices/content/102431
- Brief-urile detaliate (Claude Docs): succesiune https://claude.ai/artifact/BQEmDwgeuDfTeHXP3aEZRq ; research inițial Raiffeisen https://claude.ai/artifact/PgdnxbKrNnCxZ853RiVg7z
