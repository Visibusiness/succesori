# registries/generator — PDF-urile documentelor demo

```bash
.venv/bin/python -m registries.generator      # din rădăcina repo-ului; scrie registries/documents/pdf/*.pdf (~2 s)
```

- **Fără dependențe:** doar biblioteca standard Python (`zlib`, `random`, `math`). Nu trebuie instalat nimic în `.venv`.
- **Determinist:** aceleași fișiere, byte cu byte, la fiecare rulare. Nu se scriu date sau ID-uri aleatoare, iar
  zgomotul vine dintr-un `random.Random(seed)` fix. Scriptul afișează primele caractere din sha256 pentru fiecare fișier.
- **02–06** (`pdf.text_pdf`): PDF cu text, font standard Courier, codificare WinAnsi + `/Differences` pentru ă/ș/ț și
  `/ToUnicode`, deci extracția de text întoarce diacriticele corecte. Rândurile lungi se rup cu indentare.
- **07** (`scan.render` + `pdf.image_pdf`): imagine grayscale 1240×1754 (A4 la 150 dpi), pe toată pagina, fără strat
  de text. Textul e randat cu un font bitmap 5×7 desenat în `bitmap_font.py` (pe mașină nu există fonturi). Apoi
  `degradation` din `.json` aplică pete peste câmpuri, rotire, colț rupt și zgomot. Imaginea vine **doar** din `.md`
  (care are deja `█`); valorile ascunse din `test_only/` nu sunt citite de generator. Rândurile care încep cu
  două spații sunt traducerile FR/EN ale etichetelor (ca pe tipizatul MAI, Anexa 3 la Normele de stare civilă 2024)
  și ies cu litere mai mici; un rând prea lung sau un text care nu încape pe pagină oprește generarea cu eroare.
- Documentul 01 (semnalul DGEP) e JSON structurat și nu are PDF.

Sursa de adevăr pentru texte: `kb/scenariu-demo/documente-demo.md` → `registries/documents/*.md` → `pdf/`.

## Augmentare (059)

```bash
.venv/bin/python -m registries.generator.augment   # scrie registries/documents/augmented/ (3 variante × document de train)
```

Variante `ocr`, `fara-diacritice`, `formate` pentru main + hard (+ `train2/` când există), cu ground truth-ul copiat
neschimbat. Determinist (seed din numele fișierului). Holdout-ul nu se atinge. Detalii în
`registries/documents/augmented/README.md`.
