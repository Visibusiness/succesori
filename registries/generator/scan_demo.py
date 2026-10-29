"""Documentele demo 02–06 ca la ghișeu: tipărite, semnate, ștampilate și trecute prin scaner.

  .venv/bin/python -m registries.generator.scan_demo     # scrie registries/documents/scan/*.pdf (~10 s)

Din fiecare `registries/documents/NN-*.md` (sursa de adevăr, la fel ca pentru `pdf/`) desenează pagini A4 la 200 dpi:
font serif (Noto Serif, în `fonts/`), titluri îngroșate, semnătură și ștampilă în locul mențiunilor
„(semnătură…)” / „L.S.”, apoi efectele unui scaner de birou (rotire mică, umbră la margine, contrast, zgomot, blur).
PDF-ul conține DOAR imaginea paginilor, fără strat de text: agentul îl citește vizual (agent/extract.py extract_file),
ca un operator. Documentul 07 e deja o scanare (pdf/07, `scan.py`) și se copiază aici neschimbat; 01 (lotul DGEP)
e o intrare electronică și nu are scanare.

Determinist: un `random.Random` per document (seed din numele fișierului), fără date în PDF.
"""
from __future__ import annotations

import hashlib
import io
import math
import random
import re
import shutil
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

DOCS = Path(__file__).resolve().parent.parent / "documents"
OUT = DOCS / "scan"
FONTS = Path(__file__).resolve().parent / "fonts"
SOURCES = ["02-adresa-notar", "03-certificat-asigurare", "04-certificat-mostenitor-A", "04-certificat-mostenitor-B",
           "05-raspuns-asigurator", "06-certificat-suplimentar"]
COPIED = ["07-certificat-deces-ilizibil"]   # deja scanare (pdf/), doar copiată

DPI = 200
W, H = 1654, 2339                 # A4 la 200 dpi
MX, MY = 150, 150                 # margini
SIZE, LEAD = 25, 37               # corp de literă și distanța dintre rânduri, în px
PAPER = (250, 249, 245)
INK = (28, 28, 30)
# ștampila, după emitent (textul de pe cerc, textul din mijloc)
STAMPS = {"notar": ("NOTAR PUBLIC • ANA EXEMPLU • MUNICIPIUL EXEMPLU • ", ["B.I.N.", "EXEMPLU"]),
          "uniqa": ("UNIQA ASIGURĂRI DE VIAȚĂ S.A. • BUCUREȘTI • ", ["UNIQA", "DAUNE"])}


def _font(style: str = "Regular", size: int = SIZE) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / "NotoSerif.ttf"), size)   # font variabil (OFL): grosimea se alege pe axă
    f.set_variation_by_name(style)
    return f


def _is_heading(line: str) -> bool:
    s = line.strip()
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and len(s) <= 70 and all(c.isupper() for c in letters)


def _wrap(line: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Rupe un rând prea lung la spații; continuările păstrează indentarea rândului + 3 spații."""
    if font.getlength(line) <= width:
        return [line]
    indent = " " * (len(line) - len(line.lstrip()) + 3)
    out, cur = [], ""
    for word in line.split(" "):
        cand = f"{cur} {word}" if cur else word
        if cur and font.getlength(cand) > width:
            out.append(cur)
            cur = indent + word
        else:
            cur = cand
    return out + [cur]


def _signature(rng: random.Random, w: int = 330, h: int = 120) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts, x, y = [], 12.0, h * .62
    for _ in range(rng.randint(5, 8)):
        x2 = x + rng.uniform(24, 52)
        amp, freq = rng.uniform(10, 34), rng.uniform(1, 3)
        pts += [(x + (x2 - x) * t / 11, y + math.sin(t / 11 * math.pi * freq) * amp) for t in range(12)]
        x = x2
    ink = (24, 36, 110, 230)
    d.line(pts, fill=ink, width=3, joint="curve")
    d.line([(pts[0][0] + 6, h * .82), (pts[-1][0], h * .72)], fill=ink, width=3)
    return img.filter(ImageFilter.GaussianBlur(.4))


def _stamp(rng: random.Random, ring: str, center: list[str], px: int = 300) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = rng.choice([(40, 52, 150), (64, 44, 140), (32, 62, 128)])
    c = px // 2
    for r, w in ((c - 5, 5), (c - 36, 2)):
        d.ellipse([c - r, c - r, c + r, c + r], outline=ink + (210,), width=w)
    f = _font("Bold", 21)
    for i, ch in enumerate(ring):
        a = -math.pi / 2 + 2 * math.pi * i / len(ring)
        g = Image.new("RGBA", (30, 32), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((15, 16), ch, font=f, fill=ink + (220,), anchor="mm")
        g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC, expand=True)
        x, y = c + (c - 21) * math.cos(a), c + (c - 21) * math.sin(a)
        img.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    f2 = _font("Bold", 26)
    for k, word in enumerate(center):
        d.text((c, c + (k - (len(center) - 1) / 2) * 32), word, font=f2, fill=ink + (220,), anchor="mm")
    img = img.rotate(rng.uniform(-20, 20), resample=Image.BICUBIC)
    alpha = img.getchannel("A").point(lambda a: int(a * rng.uniform(.7, 1.0)))
    img.putalpha(alpha.filter(ImageFilter.GaussianBlur(.5)))
    return img


def _layout(text: str) -> list[list[tuple[str, str]]]:
    """Textul .md -> pagini de rânduri (stil, text). Stiluri: title, bold, text, blank, sign."""
    rows: list[tuple[str, str]] = []
    regular, title_seen = _font(), False
    for line in text.rstrip("\n").split("\n"):
        if line.startswith("["):                 # notă editorială, nu face parte din document
            continue
        if not line.strip():
            rows.append(("blank", ""))
        elif "(semnătur" in line:
            rows.append(("sign", line))
        elif not title_seen and line.strip().startswith(("CERTIFICAT", "ADRES")) and _is_heading(line.split(" Nr")[0]):
            title_seen = True
            rows.append(("title", line.strip()))
        elif _is_heading(line):
            rows.append(("bold", line))
        else:
            rows += [("text", part) for part in _wrap(line, regular, W - 2 * MX)]
    pages, cur, y = [], [], MY
    for row in rows:
        step = {"blank": LEAD // 2, "title": LEAD * 2, "sign": LEAD * 4}.get(row[0], LEAD)
        if y + step > H - MY and cur:
            pages.append(cur)
            cur, y = [], MY
        cur.append(row)
        y += step
    return pages + [cur] if cur else pages


def _draw_page(rows: list[tuple[str, str]], rng: random.Random, stamp: tuple[str, list[str]] | None) -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    regular, bold, title = _font(), _font("Bold"), _font("Bold", 38)
    y = MY
    for style, line in rows:
        if style == "blank":
            y += LEAD // 2
            continue
        if style == "title":
            d.text((W // 2, y + LEAD), line, font=title, fill=INK, anchor="mm")
            y += LEAD * 2
            continue
        if style == "sign":
            # semnătura (și ștampila, unde documentul are „L.S.” / „ștampilă”) peste mențiunea din text
            # un rând poate avea două coloane: „(semnătură, ștampilă)        (semnătură)”
            for m in re.finditer(r"\(semnătur[^)]*\)", line):
                x_sig = MX + int(regular.getlength(line[:m.start()])) + rng.randint(0, 40)
                sig = _signature(rng)
                img.paste(sig, (x_sig, y - 20), sig)
                if stamp and "ștampil" in m.group(0):
                    st = _stamp(rng, *stamp, px=250)
                    img.paste(st, (x_sig + 210 + rng.randint(-10, 20), y - 40 + rng.randint(-10, 20)), st)
            if stamp and "L.S." in line:
                st = _stamp(rng, *stamp)
                img.paste(st, (W - MX - st.width + rng.randint(-60, 10), y - st.height // 2 + rng.randint(-10, 20)), st)
            y += LEAD * 3 + (LEAD if "ștampil" in line else 0)
            continue
        font = bold if style == "bold" else regular
        d.text((MX, y), line, font=font, fill=(INK[0] + rng.randint(-6, 10),) * 3)
        y += LEAD
    return img


def _scan(img: Image.Image, rng: random.Random) -> Image.Image:
    """Efectele unui scaner de birou: hârtia ușor strâmbă pe geam, umbra marginii, contrast, zgomot, blur."""
    bed = (214, 214, 210)
    img = img.rotate(rng.uniform(-0.8, 0.8), resample=Image.BICUBIC, fillcolor=bed,
                     translate=(rng.randint(-12, 12), rng.randint(-10, 10)))
    shade = Image.linear_gradient("L").rotate(90).resize((60, H))          # umbra marginii din stânga
    img.paste((150, 150, 148), (0, 0), shade.point(lambda v: int(v * .35)))
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(1.05, 1.18))
    noise = Image.frombytes("L", (W, H), rng.randbytes(W * H))           # din rng, ca să rămână determinist
    img = Image.blend(img, noise, rng.uniform(.035, .055))
    for _ in range(140):                                                   # praf pe geam
        x, y = rng.randint(0, W - 4), rng.randint(0, H - 4)
        ImageDraw.Draw(img).point([(x + dx, y + dy) for dx in range(rng.randint(1, 3)) for dy in range(rng.randint(1, 3))],
                                  fill=rng.randint(70, 140))
    return img.filter(ImageFilter.GaussianBlur(rng.uniform(.45, .7)))


def render(stem: str) -> list[Image.Image]:
    rng = random.Random(zlib.crc32(stem.encode()))
    stamp = STAMPS["uniqa"] if stem.startswith(("03", "05")) else STAMPS["notar"]
    text = (DOCS / f"{stem}.md").read_text(encoding="utf-8")
    return [_scan(_draw_page(rows, rng, stamp), rng) for rows in _layout(text)]


def write_pdf(path: Path, pages: list[Image.Image]) -> None:
    """PDF doar cu imaginile paginilor (JPEG), fără text și fără dată, deci determinist."""
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", resolution=DPI, save_all=True, append_images=pages[1:], quality=72,
                  title=f"Scanare {path.stem}", producer="scaner", creator="scaner", creationDate=None, modDate=None)
    path.write_bytes(buf.getvalue())


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for stem in SOURCES:
        target = OUT / f"{stem}.pdf"
        pages = render(stem)
        write_pdf(target, pages)
        print(f"{target.relative_to(DOCS.parent.parent)}  {len(pages)} pag.  {target.stat().st_size // 1024} KB  "
              f"{hashlib.sha256(target.read_bytes()).hexdigest()[:12]}")
    for stem in COPIED:
        shutil.copyfile(DOCS / "pdf" / f"{stem}.pdf", OUT / f"{stem}.pdf")
        print(f"{(OUT / f'{stem}.pdf').relative_to(DOCS.parent.parent)}  (copiat din pdf/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
