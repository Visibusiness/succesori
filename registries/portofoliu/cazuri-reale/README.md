# registries/portofoliu/cazuri-reale — doi clienți pe cazuri reale (sarcina 085)

Doi clienți Raiffeisen **fictivi** (nume, CNP-uri, adrese, numere de contract și de document inventate), fiecare construit
pe situația reală dintr-o hotărâre judecătorească anonimizată, cu documentele pe machetele oficiale reale.

| Client | Cazul real din spate | Situația | Etapa din portofoliu |
|---|---|---|---|
| [A-petrescu-marin](A-petrescu-marin/README.md) `RC8501` | Judecătoria Târgu Jiu, Sentința civilă nr. 825/31.01.2013, dosar 14781/318/2012 | credit Raiffeisen cu asigurare de deces încheiată fără chestionar; deces la 3 luni, din boli cunoscute dinainte; asigurătorul refuză („boală preexistentă”); soția + 3 copii majori, câte 1/4 | escaladarea `insurance_refused` deschisă, fără plan |
| [B-neagu-cristian](B-neagu-cristian/README.md) `RC8502` | Tribunalul Alba, Decizia civilă nr. 839/A/08.12.2015 (apel la Sent. civ. 78/2015, Judecătoria S.) | deces în accident rutier; cont, Flexicredit asigurat (aprobat), card de credit; soția separată în fapt 1/4, fiu minor din căsătorie (curator special) 3/8, fiu minor din afara căsătoriei (reprezentat de mama lui) 3/8 | planul de plată `pending_approval`: 9.311,78 lei plătibili, liniile minorilor blocate |

Fiecare director are:
- `README.md`: cazul real (instanță, număr, an, fapte citate), ce am preluat și ce am schimbat, clientul, produsele adaptate
  (CGB 2026, tarife PF 2026, asigurarea UNIQA a creditelor), moștenitorii, cronologia documentelor, **valorile așteptate
  calculate de mână** (solduri la deces, cote, plan de plată) și tabelul real / fictiv;
- `client.json`: datele de core ale clientului, în forma argumentelor lui `Bank.add_customer` de pe ramura `persistenta`
  (084): `customer`, `products`, `movements`, `ibans`, `loan_contracts`, `installments`, `contacts` (sume în bani, date ISO,
  fracții „a/b”), plus `etapa_demo` (ordinea documentelor și starea în care se oprește dosarul);
- `NN-*.md` + `NN-*.mvp.json`: textul fiecărui document și adevărul de referință, în forma din `agent/demo_documents.py`
  (`id, raw_name, document_type, received_on, confidence, fields`), vocabularul câmpurilor din `agent/guard.py`;
- `scan/NN-*.pdf`: documentul cum ajunge la bancă (tipărit, semnat, ștampilat, scanat; doar imagine, fără strat de text);
- `01-dgep-semnal.json`: semnalul DGEP e o linie de lot electronic, nu are PDF;
- `formulare.json`: valorile cu care se completează formularele oficiale.

| Document | Macheta reală |
|---|---|
| semnal DGEP | câmpurile din Nota de informare Raiffeisen Bank–DGEP, „Categoriile de date”, lit. b) (`kb/bank-procedures/dgep-arb-acord.md`) |
| certificat de deces | PDF-ul oficial MAI, Anexa 3 la Normele de stare civilă (HG 255/2024), completat cu `registries/generator/certificat_deces.fill_new`, ca la `registries/documents/forms-real/` |
| certificat de asigurare, răspunsul asigurătorului | antetul și secțiunile formularului UNIQA + textele din IPID-ul UNIQA V4_09.2025 (`kb/bank-procedures/asigurare-viata-credit.md`); refuzul (A) e construit după motivarea refuzului citată în hotărâre |
| cererea de despăgubire | PDF-ul original UNIQA „Cerere de despagubire în caz de daună” CD_UAV_V8_04.2024 (Anexa F1 RAIB), completat de mână (fonturi Caveat/Kalam) |
| adresa notarului | formularea reală a Notariatului Professio de pe notari.pro (07-06-2014), `kb/_downloads/realsurse/forum/notaripro-supliment-mostenire.txt` |
| certificat de moștenitor | Anexa 17 la Regulamentul Legii 36/1995 (Ordin MJ 2333/C/2013) |

În portofoliul lui 084 cei doi sunt `P13` (`SC-2026-0113`) și `P14` (`SC-2026-0114`). `portofoliu.py` scrie
`../P13-marin-petrescu.json` și `../P14-cristian-neagu.json` din `client.json` și `*.mvp.json`: id-urile produselor sunt
`P13-CC`, …, IBAN-urile au cifra de control recalculată, se adaugă semnătura răspunsului către notar, iar
documentele-suport rămân pe dinafară. Testele: `tests/test_portfolio.py` (etapa) și
`tests/test_portfolio_cazuri_reale.py` (sumele de mână și două bug-uri, `xfail`).

```bash
.venv/bin/python registries/portofoliu/cazuri-reale/portofoliu.py    # P13/P14 în registries/portofoliu/
.venv/bin/python registries/portofoliu/cazuri-reale/genereaza.py     # din rădăcina repo-ului; scan/*.pdf + formularele completate (~15 s)
```
Determinist (două rulări dau aceleași sha256). Folosește `registries/generator/scan_demo.py` și `certificat_deces.py`
fără să le modifice. În git stau `scan/*.pdf`; formularele completate în vector (`02-certificat-deces.pdf`, ~4 MB, și
`04-cerere-despagubire-uniqa.pdf`) se regenerează.

Convenții (diferite de demo-ul Maria): CNP-urile au format valid (cifră de control corectă), inventate; IBAN-urile au
cifra de control `00` (invalide intenționat, ca în `registries/documents/`). Cererea de despăgubire UNIQA (`04-*`) e
document-suport: avizarea daunei nu are tip în vocabularul pipeline-ului (`unknown`, `_pipeline: false`), deci nu se
trimite agentului.
