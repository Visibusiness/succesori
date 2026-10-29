# registries/documents/augmented — variante augmentate ale documentelor de train (059)

Generate de `python -m registries.generator.augment` (determinist; nu se editează de mână). Pentru fiecare document
din `../` (01–07), `../hard/` și `../train2/` (când există) care are text `.md`, sunt 3 variante:

| Sufix | Ce simulează |
|---|---|
| `__ocr` | zgomot OCR: l↔1, O↔0, rn↔m (~15% din apariții), rânduri rupte, spații dublate |
| `__fara-diacritice` | text fără ă/â/î/ș/ț/é (ghilimelele „” rămân) |
| `__formate` | date în litere („3 septembrie 2026”, „3 sept. 2026”), sume „9 000 lei” / „9.000 RON” |

Ground truth-ul `.mvp.json` e copiat neschimbat (aceleași valori), cu `_augmented_from` și `_variant`. Intrările
structurate fără `.md` (01, H2: linia DGEP) nu se augmentează. Holdout-ul nu se augmentează niciodată.

Evaluare: `scripts/eval_extract.py --set augmented` (raportează și pe variantă); setul face parte din `train`.
