# registries/portofoliu/documente — documentele celor 14 clienți (sarcina 090)

Fiecare pas-document din `../P*.json` are aici fișierul propriu-zis, pe macheta oficială reală, ca la Maria Ionescu.
În `P*.json` stau doar referința la fișier și valorile de referință; ce primește pipeline-ul e **extracția reală** a
fișierului.

```bash
.venv/bin/python registries/portofoliu/documente/genereaza.py        # documentele, din valorile de referință (~25 s, determinist)
.venv/bin/python scripts/portfolio_extract.py                        # extractorul real (Bedrock, ≤10 deodată) -> *.extras.json + acuratețea
.venv/bin/python scripts/portfolio_extract.py --report               # doar acuratețea extracțiilor salvate (fără LLM)
PORTFOLIO_EXTRACT=1 …                                                # resetul re-extrage live în loc să citească *.extras.json
```
`genereaza.py` are nevoie de formularul MAI din `kb/_downloads/` (în worktree: link spre `kb/_downloads`).

## Ce e în fiecare `<Pxx>/`

| Fișier | Ce e |
|---|---|
| `NN-<tip>.md` | textul documentului (valorile din `expected_fields` + date de prezentare din `genereaza.py::CLIENTS`: adrese, notar, date de emitere) |
| `NN-<tip>.pdf` | documentul curat: text Courier cu strat de text; certificatul de deces = formularul MAI Anexa 3 completat, rasterizat |
| `NN-<tip>-scan.pdf` | cum ajunge la bancă: tipărit, semnat, ștampilat, scanat (`registries/generator/scan_demo.py`), doar imagine |
| `NN-semnal-dgep.json` | semnalul DGEP: linia din lotul SFTP, câmpurile notei Raiffeisen–DGEP lit. b) (`.pdf` e redarea ei pentru operator) |
| `NN-<tip>.extras.json` | ieșirea extractorului pe `-scan.pdf` (`agent/extract.py::extract_file`, Sonnet pe Bedrock): tip, încredere, câmpuri, încredere și citat pe câmp, validări, `guard`, `extractor` (model, `model_id`, `extracted_at`, cost) |

`file` din pas = fișierul primit de bancă, servit de previzualizare (`raw_name` = `portofoliu/<file>`,
`agent/doc_preview.py`, doar din acest director): `-scan.pdf` pentru documentele pe hârtie, `.pdf` pentru semnalul DGEP
(intrare electronică) și pentru atașamentul de e-mail al lui P09.

| Tip | Macheta |
|---|---|
| semnal DGEP | câmpurile notei de informare Raiffeisen Bank–DGEP, „Categoriile de date”, lit. b) |
| certificat de deces | PDF-ul oficial MAI, Anexa 3 (HG 255/2024), completat cu `registries/generator/certificat_deces.fill_new` |
| adresa notarului | formularea reală de pe notari.pro („extras de cont unui netitular de cont”), plus termenul de dezbatere la P02–P12 |
| certificat de asigurare, răspunsul asigurătorului | antetul și secțiunile UNIQA (ca `registries/documents/03`, `05`); refuzul P10 după motivarea refuzului din hotărârea lui P13 |
| certificat de moștenitor / testamentar | Anexa 17 la Regulamentul Legii 36/1995 (Ordin MJ 2333/C/2013) |
| cererea de despăgubire UNIQA (P13, P14, `suport-*`) | formularul original CD_UAV_V8_04.2024, completat de mână (085); document-suport, nu pas |

Imperfecțiuni doar unde dosarul are un document cu probleme:
- **P01-D2**: fotografia cu telefonul a certificatului de deces, cu reflexul blițului peste CNP (de la a 8-a cifră),
  data nașterii, data decesului, actul de deces și seria/numărul. `.pdf` = certificatul complet; `.md` = ce se citește (█).
- **P09-D4**: atașamentul unui e-mail (nu de la notar): un „certificat” care numește un moștenitor unic și cere plata
  într-un IBAN de la altă bancă, cu instrucțiuni pentru agent scrise alb pe alb. Garda (`agent/guard.py`) îl pune în
  carantină, deci, ca în drumul real, **nu ajunge la extractor** (`.extras.json`: `extractor.skipped = "guard"`).

P13 și P14 vin din `../cazuri-reale/` (085): `.md`-urile și scanările de acolo, cu IBAN-urile corectate în
certificatul de moștenitor (`cazuri-reale/portofoliu.py::iban`, ca în P13/P14.json); semnalul DGEP e redat și scanat aici.

## Câte documente

| Client | Documente | Client | Documente |
|---|---|---|---|
| P01 Popescu | 2 | P08 Radu | 3 |
| P02 Dumitrescu | 2 | P09 Ilie | 3 |
| P03 Marinescu | 3 | P10 Stan | 4 |
| P04 Stoica | 3 | P11 Vlad | 2 |
| P05 Georgescu | 3 | P12 Matei | 2 |
| P06 Niculescu | 3 | P13 Petrescu | 6 (+ cererea UNIQA) |
| P07 Petrescu | 5 | P14 Neagu | 6 (+ cererea UNIQA) |

47 de documente; 46 extrase (P09-D4 e în carantină).

## Acuratețea extracției (rularea din 28.10.2026, Sonnet 5.5 pe Bedrock)

257/259 câmpuri corecte (99,2 %), tipul corect la 46/46, pragul de încredere corect la 44/46. Pe tip: semnal DGEP 42/42,
adresa notarului 89/89, certificat de asigurare 25/25, răspunsul asigurătorului 26/26, certificat de moștenitor 55/56,
certificat de deces 20/21. Detaliile: `scripts/portfolio_extract.py --report`.

Erori reale ale extractorului (notate, nu corectate; valoarea de referință nu se copiază peste extracție):
- **P13-D4, P14-D4** (pragul): adresa notarului în formularea reală notari.pro nu are termenul de dezbatere; skill-ul
  extractorului (`.claude/skills/extract-documents`) îl trece obligatoriu, deci încrederea iese 0,5 deși documentul se
  citește perfect. Nedeterminist: P13-D4 a ieșit 0,5 la 3 rulări din 3, P14-D4 la 2 din 3 (la a treia, un reset cu
  `PORTFOLIO_EXTRACT=1`, a trecut pragul și a redeschis `document_deficient_institution`). Adresa ajunge la „documente neidentificate” ca `document_illegible`, nu în
  dosar. Înainte (085, încredere scrisă de mână 0,93) deschidea `document_deficient_institution`; etapa celor doi s-a
  schimbat în consecință (vezi `../README.md`).
- **P14-D2** `mother`: „POPA FLOREA” în loc de „POPA FLOAREA”; pe scanare se citește clar FLOAREA. La a doua rulare a ieșit corect.
- **P14-D6** `ibans`: a omis IBAN-ul cardului de credit, care apare la „Pasiv” (datorie), nu la masa activă. La a doua rulare l-a dat.
- Necontabilizat, dar folosit de pipeline: pentru minori extractorul scrie reprezentantul legal cu numele („PETRESCU
  ILEANA”), nu cu id-ul moștenitorului („H1”) din referință (P07-D5). Etapa nu se schimbă.
- Numele moștenitorilor vin cum scriu în certificat („GEORGESCU MARIA”), nu „Maria Georgescu”: aceeași persoană
  pentru core (`core_mock._person_key`), dar așa apar în planul de plată.
