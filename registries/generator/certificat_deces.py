"""Certificate de deces completate cu date FICTIVE, pe formularele oficiale reale.

  .venv/bin/python -m registries.generator.certificat_deces [--n-nou 12] [--n-vechi 10] [--seed 2026]

Model nou (HG 255/2024): textul se scrie direct pe PDF-ul oficial MAI (Anexa 3 fizic, Anexa 6 electronic), cu
fundalul, stema și ghilloșul originale. Model vechi (HG 64/2011, Anexa 3): nu există o imagine oficială publică,
doar macheta text din metodologie; îl desenăm după acea machetă și îl completăm de mână / la mașina de scris.

Pentru fiecare certificat: .pdf, .png (300 dpi, „scanat”), -foto.jpg („fotografiat cu telefonul”) și
.mvp.json (ground truth = datele cu care l-am completat). Persoanele sunt inventate (nume și CNP aleatorii).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = Path(__file__).resolve().parent / "fonts"
FORMS = {"anexa3": ROOT / "kb/_downloads/nicolas/mai-anexa3-certificat-deces-tipizat.pdf",
         "anexa6": ROOT / "kb/_downloads/nicolas/mai-anexa6-certificat-deces-electronic.pdf"}
OUT = ROOT / "registries/documents/forms-real/certificat-deces"

# ---------------------------------------------------------------- date fictive
NUME = ["POPESCU", "IONESCU", "POPA", "RADU", "DUMITRU", "STAN", "STOICA", "GHEORGHE", "MATEI", "CONSTANTIN",
        "MARIN", "TUDOR", "DOBRE", "BARBU", "NISTOR", "FLOREA", "ENACHE", "MOLDOVAN", "ROTARU", "LUPU", "CIOBANU",
        "OPREA", "VOICU", "DRĂGHICI", "ȘERBAN", "MUNTEANU", "ZAHARIA", "PĂUN", "ȚURCANU", "BĂLAN"]
PRENUME_F = ["MARIA", "ELENA", "IOANA", "ANA", "GEORGETA", "VASILICA", "ECATERINA", "FLOAREA", "VIORICA",
             "AURELIA", "DOINA", "RODICA", "ȘTEFANIA", "MIHAELA", "LUCREȚIA"]
PRENUME_M = ["ION", "GHEORGHE", "VASILE", "CONSTANTIN", "NICOLAE", "DUMITRU", "MIHAI", "ȘTEFAN", "PETRU",
             "AUREL", "TUDOR", "IULIAN", "COSTICĂ", "GRIGORE", "TRAIAN"]
# (localitate, județ, cod județ CNP)
LOCURI = [("Mun. Iași", "Iași", "22"), ("Mun. Cluj-Napoca", "Cluj", "12"), ("Mun. Craiova", "Dolj", "16"),
          ("Mun. Brașov", "Brașov", "08"), ("Mun. Constanța", "Constanța", "13"), ("Mun. Ploiești", "Prahova", "29"),
          ("Mun. Bacău", "Bacău", "04"), ("Mun. Oradea", "Bihor", "05"), ("Com. Vulcana-Băi", "Dâmbovița", "15"),
          ("Oraș Bușteni", "Prahova", "29"), ("Com. Șendriceni", "Botoșani", "07"), ("Mun. Suceava", "Suceava", "33"),
          ("Mun. Pitești", "Argeș", "03"), ("Oraș Mizil", "Prahova", "29"), ("Com. Țânțăreni", "Gorj", "18")]
STRAZI = ["Str. Teilor", "Str. Morii", "Bd. Independenței", "Str. Libertății", "Aleea Florilor", "Str. Gării",
          "Str. Mihai Eminescu", "Calea Moldovei", "Str. Zorilor", "Str. Câmpului"]
SPITALE = ["Spitalul Clinic Județean de Urgență", "Spitalul Municipal", "la domiciliu"]


def cnp(sex: str, born: date, county: str, rng: random.Random) -> str:
    """CNP cu cifră de control validă (S AA LL ZZ JJ NNN C). Inventat: nu corespunde intenționat nimănui."""
    s = (1 if sex == "M" else 2) if born.year < 2000 else (5 if sex == "M" else 6)
    base = f"{s}{born:%y%m%d}{county}{rng.randint(1, 999):03d}"
    c = sum(int(a) * int(b) for a, b in zip(base, "279146358279")) % 11
    return base + str(1 if c == 10 else c)


def person(rng: random.Random, idx: int) -> dict:
    sex = rng.choice("MF")
    born = date(1930, 1, 1) + timedelta(days=rng.randint(0, 365 * 62))
    died = date(2024, 5, 1) + timedelta(days=rng.randint(0, 900))
    loc_b, loc_d, loc_dom = rng.choice(LOCURI), rng.choice(LOCURI), rng.choice(LOCURI)
    surname = rng.choice(NUME)
    first = rng.choice(PRENUME_M if sex == "M" else PRENUME_F)
    father_first, mother_first = rng.choice(PRENUME_M), rng.choice(PRENUME_F)
    mother_surname = rng.choice(NUME)
    act_date = died + timedelta(days=rng.randint(1, 4))
    issued = act_date + timedelta(days=rng.choice([0, 0, 1, 3, 30, 200]))
    return {
        "id": idx, "sex": sex, "surname": surname, "first": first, "born": born, "died": died,
        "cnp": cnp(sex, born, loc_b[2], rng),
        "birth_place": loc_b, "death_place": loc_d,
        "domicile": (f"{loc_dom[0]}, {rng.choice(STRAZI)} nr. {rng.randint(1, 120)}", loc_dom[1]),
        "father": (surname, father_first), "mother": (mother_surname, mother_first),
        "act_no": str(rng.randint(12, 2400)), "act_date": act_date,
        "registered": (f"Primăria {loc_d[0]}", loc_d[1]),
        "issued_by": f"SPCLEP {loc_d[0].split(' ', 1)[1]}",
        "issued": issued,
        "series": "".join(rng.choice("ABCDEFGHJKLMNPRSTUVZ") for _ in range(2)) if rng.random() < .8 else "DE",
        "number": f"{rng.randint(100000, 999999)}",
    }


def ground_truth(p: dict, model: str, variant: str) -> dict:
    """Cheile canonice ale extractorului (death_certificate), ca în registries/documents/hard/H10."""
    return {
        "document_type": "death_certificate",
        "confidence": 0.9 if variant != "foto" else 0.85,
        "fields": {
            "cnp": p["cnp"],
            "name": f"{p['first'].title()} {p['surname'].title()}",
            "birth_date": p["born"].isoformat(),
            "date_of_death": p["died"].isoformat(),
            "father": f"{p['father'][0]} {p['father'][1]}",
            "mother": f"{p['mother'][0]} {p['mother'][1]}",
            "document_series": None if model == "anexa6" else p["series"],
            "document_number": p["number"],
            "death_record_number": p["act_no"],
        },
        "_document_variant": {"anexa3": "certificat_fizic_2024", "anexa6": "certificat_electronic_2024",
                              "vechi": "certificat_model_vechi_2011"}[model],
        # CD09–CD12 și CD19–CD22 nu sunt arătate niciodată retro-learner-ului (validare onestă)
        "_split": "holdout" if p["id"] in (9, 10, 11, 12, 19, 20, 21, 22) else "train",
        "_fictiv": True,
        "_model": model,
        "_variant": variant,
    }


# ---------------------------------------------------------------- ștampilă + semnătură (PNG transparent)
def stamp_png(p: dict, rng: random.Random, px: int = 420) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = rng.choice([(40, 50, 150), (70, 40, 140), (30, 60, 120)])
    c = px // 2
    for r, w in ((c - 6, 7), (c - 46, 3)):
        d.ellipse([c - r, c - r, c + r, c + r], outline=ink + (215,), width=w)
    f = ImageFont.truetype(str(FONTS / "NotoSans.ttf"), 34)
    text = f"ROMÂNIA • {p['registered'][1].upper()} • {p['issued_by'].upper()} • "
    for i, ch in enumerate(text):
        a = -math.pi / 2 + 2 * math.pi * i / len(text)
        x, y = c + (c - 27) * math.cos(a), c + (c - 27) * math.sin(a)
        g = Image.new("RGBA", (40, 44), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((20, 22), ch, font=f, fill=ink + (225,), anchor="mm")
        g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    f2 = ImageFont.truetype(str(FONTS / "NotoSans.ttf"), 30)
    d.text((c, c - 18), "STARE", font=f2, fill=ink + (225,), anchor="mm")
    d.text((c, c + 20), "CIVILĂ", font=f2, fill=ink + (225,), anchor="mm")
    img = img.rotate(rng.uniform(-25, 25), resample=Image.BICUBIC)
    # cerneală neuniformă
    alpha = img.getchannel("A").point(lambda a: int(a * rng.uniform(.75, 1.0)))
    img.putalpha(alpha.filter(ImageFilter.GaussianBlur(.6)))
    return img


def signature_png(rng: random.Random, w: int = 520, h: int = 200) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = (20, 30, 90, 235)
    x, y = 20, h * .6
    pts = []
    for i in range(rng.randint(5, 8)):
        x2 = x + rng.uniform(40, 90)
        for t in range(12):
            tt = t / 11
            pts.append((x + (x2 - x) * tt, y + math.sin(tt * math.pi * rng.uniform(1, 3)) * rng.uniform(15, 55)))
        x = x2
    d.line(pts, fill=ink, width=5, joint="curve")
    d.line([(pts[0][0] + 10, h * .78), (pts[-1][0], h * .7)], fill=ink, width=4)
    return img.filter(ImageFilter.GaussianBlur(.5))


def png_bytes(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


# ---------------------------------------------------------------- model nou: scriem pe PDF-ul oficial
def fill_new(p: dict, model: str, rng: random.Random, target: Path) -> None:
    doc = fitz.open(FORMS[model])
    page = doc[0]
    page.insert_font(fontname="noto", fontfile=str(FONTS / "NotoSans.ttf"))
    jit = lambda: rng.uniform(-0.6, 0.6)  # mică variație de imprimare
    # Coordonatele de mai jos sunt ale etichetelor raportate de PyMuPDF (get_text "words"); în randare formularul
    # apare cu 33 pt mai jos (transformare internă a PDF-ului MAI), măsurat pe imaginea la 100 dpi.
    DY = 33

    def put(x, y, text, size=10.5):
        page.insert_text((x + jit(), y + DY + jit()), text, fontname="noto", fontsize=size, color=(0.05, 0.05, 0.08))

    # CNP în căsuțe: 13 căsuțe între x≈360 și x≈528 pt, pe rândul de la y≈236
    pitch = (528 - 360) / 13
    for i, ch in enumerate(p["cnp"]):
        put(360 + pitch * i + pitch / 2 - 3.1, 252 - DY, ch, 10.5)   # căsuțele sunt la y≈240–256 pt
    put(205, 250, p["surname"])
    put(205, 270, p["first"])
    put(205, 291, "M" if p["sex"] == "M" else "F")
    put(180, 301, f"{p['born']:%Y}"); put(282, 301, f"{p['born']:%m}"); put(380, 301, f"{p['born']:%d}")
    put(200, 327, p["birth_place"][0]); put(400, 327, p["birth_place"][1])
    put(155, 360, p["domicile"][0], 9.5); put(397, 360, p["domicile"][1])
    put(172, 392, f"{p['died']:%Y}", 10); put(210, 392, f"{p['died']:%m}", 10); put(240, 392, f"{p['died']:%d}", 10)
    put(198, 422, p["death_place"][0]); put(398, 422, p["death_place"][1])
    put(262, 473, p["father"][0]); put(262, 492, p["father"][1])
    put(262, 512, p["mother"][0]); put(262, 531, p["mother"][1])
    put(122, 553, p["act_no"])
    put(308, 548, f"{p['act_date']:%Y}"); put(372, 548, f"{p['act_date']:%m}"); put(432, 548, f"{p['act_date']:%d}")
    put(215, 589, p["registered"][0]); put(420, 589, p["registered"][1])
    put(125, 640, "—")
    put(128, 712, p["issued_by"])
    put(128, 738, f"{p['issued']:%d.%m.%Y}")
    if model == "anexa3":
        put(366, 764, p["series"]); put(412, 764, p["number"])
    else:
        put(340, 764, p["number"])
    st = stamp_png(p, rng)
    sx, sy = rng.uniform(300, 350), rng.uniform(675, 695) + 10
    page.insert_image(fitz.Rect(sx, sy, sx + 105, sy + 105), stream=png_bytes(st), overlay=True)
    sg = signature_png(rng)
    gx, gy = rng.uniform(470, 490), rng.uniform(738, 748) + 18
    page.insert_image(fitz.Rect(gx, gy, gx + 100, gy + 38), stream=png_bytes(sg), overlay=True)
    while len(doc) > 1:  # versoul (mențiuni) rămâne gol: păstrăm doar fața
        doc.delete_page(1)
    doc.save(target, garbage=3, deflate=True)


# ---------------------------------------------------------------- model vechi: desenat după macheta HG 64/2011
def draw_old(p: dict, rng: random.Random) -> Image.Image:
    W, H = 2480, 3508  # A4 la 300 dpi
    paper = (rng.randint(232, 242), rng.randint(229, 238), rng.randint(214, 226))  # hârtie cenușie-gălbuie
    img = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(img)
    pr = lambda s: ImageFont.truetype(str(FONTS / "NotoSerif.ttf"), s)
    sm = lambda s: ImageFont.truetype(str(FONTS / "NotoSans.ttf"), s)
    hand = ImageFont.truetype(str(FONTS / rng.choice(["Caveat.ttf", "Kalam.ttf"])), rng.randint(58, 66))
    typed = ImageFont.truetype(str(FONTS / "CourierPrime.ttf"), 50)
    fill_font = typed if rng.random() < .35 else hand
    ink = rng.choice([(25, 35, 110), (20, 20, 25), (35, 45, 140)])
    line = (60, 60, 60)
    # fundal tipizat: linii fine ondulate (imită hârtia de siguranță)
    for y in range(0, H, 18):
        d.line([(x, y + 4 * math.sin(x / 90)) for x in range(0, W, 40)], fill=tuple(c - 6 for c in paper), width=1)
    # cotorul detașabil (sus): cine a primit certificatul
    d.text((160, 120), "Numele de familie ..........................  Prenumele ......................", font=sm(34), fill=line)
    d.text((160, 180), "Actul de identitate: seria .......... nr. ...............", font=sm(34), fill=line)
    d.text((160, 240), "Actul de deces: nr. .............. din ...................", font=sm(34), fill=line)
    d.text((160, 300), "Data eliberării ...................   Semnătura de primire ..............", font=sm(34), fill=line)
    d.text((W - 260, 140), "Seria", font=sm(30), fill=line); d.text((W - 260, 260), "Nr.", font=sm(30), fill=line)
    d.text((W - 170, 140), p["series"], font=sm(38), fill=(150, 20, 20)); d.text((W - 200, 260), p["number"], font=sm(34), fill=(150, 20, 20))
    for x in range(120, W - 120, 30):  # linia de perforație
        d.line([(x, 400), (x + 15, 400)], fill=line, width=3)
    # antet
    d.ellipse([W // 2 - 90, 470, W // 2 + 90, 650], outline=line, width=4); d.text((W // 2, 560), "STEMĂ", font=sm(26), fill=line, anchor="mm")
    d.text((W // 2 - 600, 720), "ROUMANIE", font=pr(46), fill=line, anchor="mm")
    d.text((W // 2, 720), "ROMÂNIA", font=pr(60), fill=line, anchor="mm")
    d.text((W // 2 + 600, 720), "ROMANIA", font=pr(46), fill=line, anchor="mm")
    d.text((W // 2, 830), "CERTIFICAT DE DECES", font=pr(84), fill=line, anchor="mm")
    d.text((W // 2, 920), "CERTIFICAT DE DÉCÈS / DEATH CERTIFICATE", font=pr(40), fill=line, anchor="mm")
    d.text((W // 2 - 380, 1010), "Seria ...............   Nr. ....................", font=pr(42), fill=line)
    d.text((W // 2 - 160, 990), p["series"], font=sm(46), fill=(150, 20, 20)); d.text((W // 2 + 140, 990), p["number"], font=sm(44), fill=(150, 20, 20))
    # CNP în căsuțe
    d.text((160, 1120), "DATE PRIVIND DECEDATUL / Données concernant le décédé / Data concerning the deceased", font=sm(34), fill=line)
    d.text((160, 1190), "Cod Numeric Personal", font=sm(38), fill=line)
    bx, by, bw = 900, 1170, 92
    for i in range(13):
        d.rectangle([bx + i * bw, by, bx + (i + 1) * bw, by + 90], outline=line, width=3)
        d.text((bx + i * bw + bw // 2, by + 120), "SAALLZZNNNNNC"[i], font=sm(26), fill=line, anchor="mm")
        d.text((bx + i * bw + bw // 2 + rng.randint(-5, 5), by + 48 + rng.randint(-6, 6)), p["cnp"][i], font=fill_font, fill=ink, anchor="mm")
    # tabelul principal
    x0, x1 = 160, W - 160
    rows = [("Numele de familie\nNom/Surname", p["surname"]), ("Prenumele\nPrénom/First name", p["first"]),
            ("Sexul / Data nașterii\nSexe / Date de naissance", f"{'M' if p['sex'] == 'M' else 'F'}        {p['born']:%Y}  {p['born']:%m}  {p['born']:%d}"),
            ("Locul nașterii\nLieu de naissance", f"{p['birth_place'][0]},  jud. {p['birth_place'][1]}"),
            ("Domiciliul\nDomicile", f"{p['domicile'][0]}, jud. {p['domicile'][1]}"),
            ("Data decesului (A/L/Z)\nDate du décès", f"{p['died']:%Y}  {p['died']:%m}  {p['died']:%d}"),
            ("Locul decesului\nLieu du décès", f"{p['death_place'][0]},  jud. {p['death_place'][1]}")]
    def fit(text, font, width):
        """Scrisul se strânge când nu încape în rubrică (ca la completarea de mână)."""
        size = font.size
        while size > 30 and d.textlength(text, font=font) > width:
            size -= 2
            font = font.font_variant(size=size)
        return font

    y, RH = 1320, 128
    for label, value in rows:
        d.rectangle([x0, y, x1, y + RH], outline=line, width=3)
        d.line([(x0 + 620, y), (x0 + 620, y + RH)], fill=line, width=3)
        d.multiline_text((x0 + 20, y + 16), label, font=sm(32), fill=line, spacing=8)
        d.text((x0 + 660 + rng.randint(-10, 10), y + RH // 2 + rng.randint(-6, 6)), value,
               font=fit(value, fill_font, x1 - x0 - 700), fill=ink, anchor="lm")
        y += RH
    d.text((x0, y + 30), "DATE PRIVIND PĂRINȚII / Données concernant les parents / Data concerning the parents", font=sm(32), fill=line)
    y += 90
    for who, (sn, fn) in (("TATĂL\nPère/Father", p["father"]), ("MAMA\nMère/Mother", p["mother"])):
        d.rectangle([x0, y, x1, y + 190], outline=line, width=3)
        d.line([(x0 + 380, y), (x0 + 380, y + 190)], fill=line, width=3); d.line([(x0 + 380, y + 95), (x1, y + 95)], fill=line, width=3)
        d.multiline_text((x0 + 20, y + 50), who, font=sm(32), fill=line)
        d.text((x0 + 400, y + 30), "Numele de familie", font=sm(28), fill=line); d.text((x0 + 400, y + 125), "Prenumele", font=sm(28), fill=line)
        d.text((x0 + 800, y + 48), sn, font=fill_font, fill=ink, anchor="lm"); d.text((x0 + 800, y + 143), fn, font=fill_font, fill=ink, anchor="lm")
        y += 190
    y += 80
    d.text((x0, y), "Act de deces nr. ...................   din ...........................................", font=sm(38), fill=line)
    d.text((x0 + 330, y - 22), p["act_no"], font=fill_font, fill=ink); d.text((x0 + 860, y - 22), f"{p['act_date']:%d.%m.%Y}", font=fill_font, fill=ink)
    y += 110
    d.text((x0, y), "Înregistrat la ...............................................   ................................", font=sm(38), fill=line)
    d.text((x0 + 380, y - 22), p["registered"][0], font=fit(p["registered"][0], fill_font, 1050), fill=ink); d.text((x0 + 1500, y - 22), f"jud. {p['registered'][1]}", font=fill_font, fill=ink)
    y += 100
    d.text((x0, y), "Mențiuni / Mentions ..............................................................................", font=sm(38), fill=line)
    y += 200
    d.text((x0, y), "Eliberat de .....................................      Data", font=sm(38), fill=line)
    d.text((x0 + 250, y - 22), p["issued_by"], font=fit(p["issued_by"], fill_font, 560), fill=ink)
    for i, ch in enumerate(f"{p['issued']:%Y%m%d}"):
        d.rectangle([x0 + 1330 + i * 70, y - 10, x0 + 1400 + i * 70, y + 60], outline=line, width=3)
        d.text((x0 + 1365 + i * 70, y + 25), ch, font=fill_font, fill=ink, anchor="mm")
    d.text((W - 640, y - 230), "Semnătura", font=sm(34), fill=line); d.text((W - 1120, y - 230), "L.S.", font=sm(34), fill=line)
    st = stamp_png(p, rng, 520)
    img.paste(st, (W - 1230 + rng.randint(-40, 40), y - 420 + rng.randint(-30, 30)), st)
    sg = signature_png(rng, 600, 230)
    img.paste(sg, (W - 760 + rng.randint(-20, 20), y - 200), sg)
    return img


# ---------------------------------------------------------------- variante: scanat (300 dpi) și „foto”
def as_photo(img: Image.Image, rng: random.Random) -> Image.Image:
    img = img.convert("RGB")
    W, H = img.size
    bg = Image.new("RGB", (int(W * 1.12), int(H * 1.08)), rng.choice([(92, 74, 58), (140, 130, 120), (60, 64, 70)]))
    doc = img.rotate(rng.uniform(-6, 6), resample=Image.BICUBIC, expand=True, fillcolor=bg.getpixel((0, 0)))
    bg.paste(doc, ((bg.width - doc.width) // 2 + rng.randint(-40, 40), (bg.height - doc.height) // 2 + rng.randint(-40, 40)))
    # perspectivă ușoară (telefon ținut oblic)
    dx = rng.uniform(.01, .04) * bg.width
    quad = (dx, 0, 0, bg.height, bg.width, bg.height, bg.width - dx * rng.uniform(.3, 1.2), 0)
    ph = bg.transform(bg.size, Image.QUAD, quad, resample=Image.BICUBIC)
    # umbră/iluminare neuniformă + contrast scăzut + puțin blur
    grad = Image.linear_gradient("L").resize(ph.size).rotate(rng.uniform(0, 360), fillcolor=255)
    ph = Image.composite(ph, ImageEnhance.Brightness(ph).enhance(rng.uniform(.55, .7)), grad)
    ph = ImageEnhance.Contrast(ph).enhance(rng.uniform(.62, .82))
    ph = ImageEnhance.Brightness(ph).enhance(rng.uniform(.88, 1.05))
    ph = ph.filter(ImageFilter.GaussianBlur(rng.uniform(.6, 1.4)))
    return ph.resize((ph.width * 2 // 3, ph.height * 2 // 3), Image.LANCZOS)


def raster(pdf: Path) -> Image.Image:
    pix = fitz.open(pdf)[0].get_pixmap(dpi=300)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-nou", type=int, default=12)
    ap.add_argument("--n-vechi", type=int, default=10)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for i in range(1, a.n_nou + a.n_vechi + 1):
        p = person(rng, i)
        model = ("anexa3" if i % 3 else "anexa6") if i <= a.n_nou else "vechi"
        stem = f"CD{i:02d}-{model}"
        pdf, png, jpg = OUT / f"{stem}.pdf", OUT / f"{stem}.png", OUT / f"{stem}-foto.jpg"
        if model == "vechi":
            img = draw_old(p, rng)
            img.save(pdf, "PDF", resolution=300)
        else:
            fill_new(p, model, rng, pdf)
            img = raster(pdf)
        img.convert("L" if model == "vechi" and rng.random() < .5 else "RGB").save(png, optimize=True)
        as_photo(img, rng).save(jpg, quality=rng.randint(50, 68))
        for variant, f in (("pdf", pdf), ("scan", png), ("foto", jpg)):
            gt = ground_truth(p, model, variant)
            gt.update({"id": f"{stem}-{variant}", "raw_name": f"forms-real/certificat-deces/{f.name}",
                       "received_on": p["issued"].isoformat()})
            (OUT / f"{stem}-{variant}.mvp.json").write_text(json.dumps(gt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        made.append(stem)
        print(stem, p["first"], p["surname"], p["cnp"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
