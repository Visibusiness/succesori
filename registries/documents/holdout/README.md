# registries/documents/holdout — set de validare NEVĂZUT (048)

**Scop:** să dovedim că lecțiile din `.claude/skills/extract-documents` generalizează, nu că am memorat cele 19 documente
din `registries/documents/` (train: `main` + `hard`). **Regulă:** `retro-learner` nu citește acest director și nici
`runs/eval-holdout-*.json`; doar `scripts/eval_extract.py --set holdout` îl folosește. Dacă pui un exemplu de aici într-un
skill, setul nu mai e ne-văzut: nu o face (copiază lecția, nu documentul).

18 documente, câte un `.md` (sau `.json` pentru semnalul DGEP) + `.mvp.json` (ground truth, aceeași formă ca în train;
scorate doar câmpurile canonice din `eval_extract.py`). Datele sunt fictive: Maria Ionescu (RC1001, decedată 03.09.2026) și
Vasile Pop (RC2002, CNP `1XXXXXXXXXXX7`, decedat 14.08.2026). CNP-uri mascate `X`, IBAN-uri cu cifra de control `00`.

## Ce e luat din sursă și ce e reconstruit (spun deschis)
| Fișier | Format | Sursa formatului | Ce e verificat |
|---|---|---|---|
| V01 | certificat de deces fizic, Anexa 3 | HG 255/2024, Anexa 3 (`kb/_downloads/nicolas/mai-anexa3-certificat-deces-tipizat.pdf`, `norme2024-img-A1506.jpg`), rubricile din `kb/document-templates/certificat-deces.md` | rubricile 1–12 și „seria/nr. + șir unic” transcrise din model |
| V02 | certificat de deces electronic, Anexa 6 | idem, `mai-anexa6-certificat-deces-electronic.pdf` (`A1518.jpg`) | „Certificat nr.” fără serie + cod de verificare, ca în model |
| V03 | model vechi HG 64/2011, completat de mână | descris în `certificat-deces.md` (modelul nu e în KB) | **reconstruit** după descriere; zgomot OCR adăugat de noi |
| V04 | extras multilingv, Anexa 9, fără CNP | `mai-anexa9-extras-multilingv-deces.pdf` (`A1530.jpg`), Convenția CIEC 16 | rubricile 1–12 din model |
| V05, V06, V07 | certificat de moștenitor (legal / testament / reprezentare succesorală) | `kb/document-templates/certificat-mostenitor.md`: Legea 36/1995 art. 112 alin. 2, art. 115; Cod civil art. 964, 972, 975, 1.133 | structura legală e reală; **antetul și textul sunt reconstruite**: nu am găsit public un model integral de certificat |
| V08 | certificat suplimentar | idem, Legea 36/1995 art. 118, Reg. art. 257 | idem |
| V09, V10, V18 | adresă notar către bancă (art. 81 alin. 2) | `kb/document-templates/adresa-notar-catre-banca.md` | elementele cerute sunt cele din lege; formularea e a noastră |
| V11 | poliță asigurare viață legată de credit, alt asigurător (fictiv) | structura IPID/certificat din `polita-asigurare-viata.md` | **reconstruit**; asigurător inventat |
| V12 | certificat UNIQA în tabel | IPID UNIQA V4_09.2025 și formularul F1 (în `polita-asigurare-viata.md`) | câmpurile reale, aspectul în tabel e al nostru |
| V13, V14 | răspuns asigurător: refuz / e-mail cu sumă cu zecimale | pornind de la doc 05 din train, formulări noi | **reconstruit** |
| V15 | certificat de deces străin (DE + traducere RO) | structura Sterbeurkunde (cunoaștere generală; model neverificat în KB) | **reconstruit**, neverificat |
| V16 | semnal DGEP, alt lot | `kb/tech/dgep-integration.md` (format mock al nostru) | mock |
| V17 | scan ilizibil (poarta de încredere) | analog doc 07, alt client | sintetic |

**Lipsesc (necunoscut):** hotărâri judecătorești de pe rolii.ro / portal.just.ro: schema extractorului nu are tip
`court_decision` (ar ieși `unknown`), iar fără fișiere descărcate nu le-am inventat; propunere în raportul 048b.
Formatele de certificat de moștenitor „din site-uri notariale” nu au putut fi descărcate din acest mediu: sunt reconstruite.

## Ce testează (capcane noi față de train)
CNP în căsuțe (V01) · fără serie (V02) · cifre în litere, text mâna (V03) · extras fără CNP (V04, V15) · cote în cuvinte,
nume cu cratimă/diacritice (V06) · doi minori prin reprezentare, IBAN-uri lipite (V07) · CNP-urile moștenitorilor lângă al
defunctului (V10) · număr de poliță repetat, mai multe numere (V11, V12) · refuz (V13) · sumă 12.345,67 în e-mail (V14) ·
nr. de ieșire vs nr. de dosar vs nr. certificat (V18) · poarta de încredere (V17).
