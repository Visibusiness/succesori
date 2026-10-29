# registries/documents/forms-real — formulare oficiale reale, completate cu date fictive

## certificat-deces/ (22 certificate × 3 variante)
Generat de `registries/generator/certificat_deces.py` (seed 2026, determinist):
```sh
.venv/bin/python -m registries.generator.certificat_deces      # --n-nou 12 --n-vechi 10 --seed 2026
```
- **CD01–CD12, model nou (HG 255/2024):** datele se scriu direct pe PDF-ul oficial MAI, Anexa 3 (fizic) sau Anexa 6
  (electronic, la fiecare al treilea), cu fundalul, stema și ghilloșul originale, plus ștampilă rotundă și semnătură.
- **CD13–CD22, model vechi (HG 64/2011, Anexa 3):** nu există imagine oficială publică, doar macheta text din
  metodologie; formularul e desenat după ea (cotor detașabil, serie/număr, CNP în căsuțe, tabel) și completat de mână
  (fonturile Caveat/Kalam) sau la mașina de scris (Courier Prime).
- Pentru fiecare: `.pdf`, `.png` (scan 300 dpi), `-foto.jpg` (telefon: rotire, perspectivă, umbră, contrast scăzut,
  JPEG) și `-{pdf,scan,foto}.mvp.json` = valorile cu care a fost completat (ground truth, cheile `death_certificate`).
- Persoanele sunt **inventate** (nume, locuri și CNP aleatorii, cu cifră de control validă).
- În git sunt doar `.mvp.json` și `-foto.jpg`; `.pdf` și `.png` se regenerează (54 MB + 100 MB).

Formularele sursă: `kb/_downloads/nicolas/mai-anexa3-certificat-deces-tipizat.pdf`, `mai-anexa6-…` (descărcate de pe
webapp.mai.gov.ro). Fonturi: Google Fonts, licență OFL (`registries/generator/fonts/OFL.txt`).
