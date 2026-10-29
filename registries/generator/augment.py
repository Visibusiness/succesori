"""python -m registries.generator.augment — variante augmentate ale documentelor de train, în registries/documents/augmented/.

Pentru fiecare document din train (main, hard, train2/ dacă există) care are text .md, scrie 3 variante:
- `ocr`: zgomot OCR (l↔1, O↔0, rn↔m, rânduri rupte, spații dublate);
- `fara-diacritice`: ă/â/î/ș/ț/é… fără semne (ghilimelele „” rămân, nu sunt diacritice);
- `formate`: date și sume scrise altfel („3 septembrie 2026”, „3 sept. 2026”, „9 000 lei”, „9.000 RON”).

Ground truth-ul (`.mvp.json`) se copiază neschimbat, cu `_augmented_from` și `_variant`: valorile din document sunt
aceleași, doar scrise altfel, deci extractorul trebuie să ajungă la aceleași câmpuri. Intrările structurate fără .md
(01 și H2, linia DGEP) nu se augmentează: se parsează determinist, nu cu LLM. Holdout-ul (`holdout/`, `holdout-real/`)
nu se augmentează niciodată.

Determinist: un `random.Random` per document și variantă, cu seed din numele fișierului (crc32), deci aceleași
fișiere la fiecare rulare.
"""
import json
import random
import re
import sys
import unicodedata
import zlib
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "documents"
OUT = DOCS / "augmented"
SOURCES = [(DOCS, "[0-9][0-9]-*.mvp.json"), (DOCS / "hard", "H[0-9]*-*.mvp.json"), (DOCS / "train2", "*.mvp.json")]
HOLDOUT = {"holdout", "holdout-real"}

LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
        "noiembrie", "decembrie"]
LUNI_SCURT = ["ian.", "feb.", "mar.", "apr.", "mai", "iun.", "iul.", "aug.", "sept.", "oct.", "nov.", "dec."]


def _rng(name, variant):
    return random.Random(zlib.crc32(f"{name}|{variant}".encode()))


def ocr(text, rng):
    """Confuziile tipice ale unui OCR prost, pe ~15% din aparițiile fiecărui caracter confundabil."""
    swaps = {"l": "1", "1": "l", "O": "0", "0": "O"}

    def conf(m):
        s = m.group(0)
        if rng.random() >= 0.15:
            return s
        return "m" if s == "rn" else "rn" if s == "m" else swaps[s]

    out = []
    for line in text.split("\n"):
        if "█" not in line:  # liniile mascate ale documentului 07 rămân cum sunt
            line = re.sub(r"rn|m|l|1|O|0", conf, line)
            line = re.sub(r"(?<=\S) (?=\S)", lambda m: "  " if rng.random() < 0.08 else " ", line)
        spaces = [i for i, c in enumerate(line) if c == " " and 15 < i < len(line) - 10]
        if spaces and rng.random() < 0.12:  # rând rupt: OCR-ul sparge rândul la un spațiu
            cut = rng.choice(spaces)
            out += [line[:cut], line[cut + 1:]]
        else:
            out.append(line)
    return "\n".join(out)


def fara_diacritice(text, rng=None):
    keep = {"„", "”", "–", "·", "█"}
    return "".join(ch if ch in keep else unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode() or ch
                   for ch in text)


def formate(text, rng):
    """Date dd.mm.yyyy / dd/mm/yyyy → în litere; sume „9.000,00 lei” → „9 000 lei” / „9.000 RON”."""
    def data(m):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        return f"{d} {LUNI[mo - 1]} {y}" if rng.random() < 0.5 else f"{d} {LUNI_SCURT[mo - 1]} {y}"

    def suma(m):
        lei, bani = m.group(1), m.group(2)
        if bani == "00":
            return f"{lei.replace('.', ' ')} lei" if rng.random() < 0.5 else f"{lei} RON"
        return f"{lei.replace('.', ' ')},{bani} lei" if rng.random() < 0.5 else f"{lei},{bani} RON"

    text = re.sub(r"\b(\d{2})[./](\d{2})[./](\d{4})\b", data, text)
    return re.sub(r"\b(\d{1,3}(?:\.\d{3})*),(\d{2}) lei\b", suma, text)


VARIANTS = {"ocr": ocr, "fara-diacritice": fara_diacritice, "formate": formate}


def main():
    OUT.mkdir(exist_ok=True)
    n = 0
    for src, pattern in SOURCES:
        if not src.is_dir() or src.name in HOLDOUT:
            continue
        for js in sorted(src.glob(pattern)):
            stem = js.name.removesuffix(".mvp.json")
            md = src / f"{stem}.md"
            if not md.exists():
                continue
            text = md.read_text(encoding="utf-8")
            truth = json.loads(js.read_text(encoding="utf-8"))
            for variant, fn in VARIANTS.items():
                name = f"{stem}__{variant}"
                (OUT / f"{name}.md").write_text(fn(text, _rng(stem, variant)), encoding="utf-8")
                t = dict(truth, id=f"{truth.get('id', stem)}-{variant}", raw_name=f"{name}.md",
                         _augmented_from=str(md.relative_to(DOCS)), _variant=variant)
                (OUT / f"{name}.mvp.json").write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
                n += 1
    print(f"{n} variante în {OUT.relative_to(DOCS.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
