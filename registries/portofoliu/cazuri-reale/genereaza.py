"""PDF-urile celor doi clienți construiți pe cazuri reale (sarcina 085), din fișierele de date din A-*/ și B-*/.

  .venv/bin/python registries/portofoliu/cazuri-reale/genereaza.py      # din rădăcina repo-ului, ~20 s

Pentru fiecare client:
- NN-*.md (scrisori, certificate)  -> scan/NN-*.pdf: tipărit, semnat, ștampilat, scanat (registries/generator/scan_demo);
- 02-certificat-deces: formulare.json -> 02-certificat-deces.pdf scris pe PDF-ul oficial MAI, Anexa 3
  (registries/generator/certificat_deces.fill_new, ca la forms-real/) -> scan/02-certificat-deces.pdf;
- 04-cerere-despagubire-uniqa: formulare.json -> 04-cerere-despagubire-uniqa.pdf completat de mână pe formularul
  original UNIQA CD_UAV_V8_04.2024 (kb/_downloads/nicolas/uniqa-anexa-F1-cerere-despagubire-RAIB-2024.pdf)
  -> scan/04-cerere-despagubire-uniqa.pdf.
01 (semnalul DGEP) e o linie de lot electronic: nu are PDF.

Determinist: un random.Random per document (seed din numele lui), PDF-uri fără dată. Nu modifică registries/generator.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import zlib
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

import fitz  # noqa: E402  PyMuPDF
from PIL import Image  # noqa: E402

from registries.generator import certificat_deces as cd  # noqa: E402
from registries.generator import scan_demo as sd  # noqa: E402

UNIQA_FORM = ROOT / "kb/_downloads/nicolas/uniqa-anexa-F1-cerere-despagubire-RAIB-2024.pdf"
FONTS = ROOT / "registries/generator/fonts"
CASES = {
    "A-petrescu-marin": {"notar": ("NOTAR PUBLIC • ADRIAN FICTIV • MUN. TÂRGU JIU • ", ["B.I.N.", "FICTIV"]),
                         "text": ["03-certificat-asigurare", "05-adresa-notar", "06-certificat-mostenitor",
                                  "07-raspuns-asigurator-refuz"]},
    "B-neagu-cristian": {"notar": ("NOTAR PUBLIC • CARMEN MODEL • MUN. SEBEȘ • ", ["B.I.N.", "MODEL"]),
                         "text": ["03-certificat-asigurare", "05-adresa-notar", "06-raspuns-asigurator-aprobat",
                                  "07-certificat-mostenitor"]},
}


def _rng(case: str, stem: str) -> random.Random:
    return random.Random(zlib.crc32(f"{case}/{stem}".encode()))


def _scan_image(img: Image.Image, rng: random.Random) -> Image.Image:
    """O pagină deja desenată (formular oficial completat) trecută prin același scaner ca documentele demo."""
    return sd._scan(img.convert("RGB").resize((sd.W, sd.H), Image.LANCZOS), rng)


def _raster(pdf: Path) -> list[Image.Image]:
    out = []
    for page in fitz.open(pdf):
        pix = page.get_pixmap(dpi=sd.DPI)
        out.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return out


# ------------------------------------------------------------------ scrisori și certificate (.md)
def text_doc(case: str, stem: str, stamps: dict) -> Path:
    rng = _rng(case, stem)
    stamp = sd.STAMPS["uniqa"] if "asigur" in stem else stamps["notar"]
    text = (HERE / case / f"{stem}.md").read_text(encoding="utf-8")
    pages = [sd._scan(sd._draw_page(rows, rng, stamp), rng) for rows in sd._layout(text)]
    target = HERE / case / "scan" / f"{stem}.pdf"
    sd.write_pdf(target, pages)
    return target


# ------------------------------------------------------------------ certificatul de deces pe formularul MAI
def death_certificate(case: str, data: dict) -> Path:
    stem = "02-certificat-deces"
    rng = _rng(case, stem)
    p = dict(data)
    for k in ("born", "died", "act_date", "issued"):
        p[k] = date.fromisoformat(p[k])
    for k in ("birth_place", "death_place", "domicile", "father", "mother", "registered"):
        p[k] = tuple(p[k])
    pdf = HERE / case / f"{stem}.pdf"
    cd.fill_new(p, "anexa3", rng, pdf)
    target = HERE / case / "scan" / f"{stem}.pdf"
    sd.write_pdf(target, [_scan_image(img, rng) for img in _raster(pdf)])
    return target


# ------------------------------------------------------------------ cererea de despăgubire UNIQA, de mână
def uniqa_claim(case: str, v: dict) -> Path:
    stem = "04-cerere-despagubire-uniqa"
    rng = _rng(case, stem)
    doc = fitz.open(UNIQA_FORM)
    hand = FONTS / rng.choice(["Caveat.ttf", "Kalam.ttf"])
    ink = rng.choice([(0.10, 0.14, 0.45), (0.08, 0.08, 0.12)])
    for page in doc:
        page.insert_font(fontname="hand", fontfile=str(hand))

    def put(pg: int, x: float, y: float, text: str, size: float = 10.5) -> None:
        # coordonatele sunt ale etichetelor din formular (get_text "words"); y = linia de bază
        doc[pg].insert_text((x + rng.uniform(-.8, .8), y + rng.uniform(-.6, .6)), text, fontname="hand",
                            fontsize=size, color=ink)

    def tick(pg: int, x0: float, y0: float) -> None:   # „X” în căsuța de 10 pt cu colțul (x0, y0)
        put(pg, x0 + 1.5, y0 + 8.8, "X", 11)

    # A. contractul și Asiguratul (coloana valorilor începe la x≈258)
    put(0, 262, 185, v["nume_asigurat"])
    cells = [255.6, 269.1, 282.5, 296.0, 309.4, 322.9, 336.3, 349.9, 363.3, 376.8, 390.2, 403.6, 417.1, 430.5]
    for ch, a, b in zip(v["cnp"], cells, cells[1:]):
        put(0, (a + b) / 2 - 2.6, 197, ch, 10)
    put(0, 262, 210, v["certificat"])
    put(0, 262, 222.5, v["adresa_domiciliu"])
    put(0, 262, 235.5, v["adresa_corespondenta"])
    put(0, 262, 248, v["data_intrarii"])
    put(0, 120, 260.5, v["telefon"])
    put(0, 412, 260.5, v["email"], 9.5)
    # B. riscul (căsuțele de la x=241.1) și data evenimentului (8 căsuțe zz ll aaaa)
    boxes = {"Deces din accident": 291.8, "Deces din orice cauza": 304.0, "Șomaj": 316.1,
             "Spitalizare din accident": 328.4, "Invaliditate Totală Permanentă din Accident": 340.6}
    tick(0, 241.1, boxes[v["risc"]])
    dcells = [234.1, 254.2, 274.2, 294.4, 314.5, 334.6, 354.7, 374.8, 394.9]
    for ch, a, b in zip(v["data_eveniment"], dcells, dcells[1:]):
        put(0, (a + b) / 2 - 2.6, 363, ch, 10)
    # C. cauza, accidentul, medicul de familie
    for i, line in enumerate(v["cauza"]):
        put(0, 246, 401 + i * 11, line, 9.5)
    tick(0, 241.2 if v["accident"] else 276.6, 428.0)
    if v["accident"]:
        put(0, 324, 449, v["data_accident"])
        put(0, 324, 461.5, v["loc_accident"])
        put(0, 244, 497, v["politie"], 9.5)
    for i, line in enumerate(v["medic_familie"]):
        put(0, 276, 576 + i * 11, line, 9.5)
    # F. declarația (pagina 3)
    put(2, 54, 102, v["declarant"])
    put(2, 54, 115, v["calitate"])
    put(2, 251, 115, v["adresa_contact"])
    put(2, 128, 127, v["telefon_declarant"])
    put(2, 304, 127, v["email_declarant"], 9.5)
    tick(2, 53.0, 289.4)
    put(2, 54, 580, v["data_completarii"])
    put(2, 320, 580, v["declarant"])
    sig = cd.signature_png(rng)
    doc[2].insert_image(fitz.Rect(440, 562, 530, 596), stream=cd.png_bytes(sig), overlay=True)
    pdf = HERE / case / f"{stem}.pdf"
    doc.save(pdf, garbage=3, deflate=True)
    target = HERE / case / "scan" / f"{stem}.pdf"
    sd.write_pdf(target, [_scan_image(img, rng) for img in _raster(pdf)])
    return target


def main() -> int:
    for case, cfg in CASES.items():
        (HERE / case / "scan").mkdir(exist_ok=True)
        forms = json.loads((HERE / case / "formulare.json").read_text(encoding="utf-8"))
        made = [death_certificate(case, forms["certificat_deces"]), uniqa_claim(case, forms["cerere_uniqa"])]
        made += [text_doc(case, stem, cfg) for stem in cfg["text"]]
        for t in sorted(made):
            print(f"{t.relative_to(ROOT)}  {len(fitz.open(t))} pag.  {t.stat().st_size // 1024} KB  "
                  f"{hashlib.sha256(t.read_bytes()).hexdigest()[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
