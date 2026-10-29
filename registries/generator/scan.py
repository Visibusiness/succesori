"""Simulează un document scanat prost: text randat cu fontul bitmap, pete de cerneală, rotire, colț rupt, zgomot.

Totul e determinist: un singur `random.Random(seed)` și aritmetică fixă. Imaginea se randează doar din textul
documentului (care are deja `█` în locul datelor ilizibile); valorile reale ascunse nu sunt folosite, deci nu pot
„scăpa” prin pixeli.
"""
import math
import random

from .bitmap_font import CELL_H, CELL_W, glyph

W, H = 1240, 1754          # A4 la 150 dpi
PAPER, INK, BED = 236, 38, 92
MARGIN_X, MARGIN_Y = 90, 80
BLANK = 10                 # px pentru un rând gol


def _draw_text(img, rng, x0, y0, text, scale):
    for i, ch in enumerate(text):
        ink = INK + rng.randint(-12, 18)
        cell = glyph(ch)
        gx = x0 + i * CELL_W * scale
        for r, row in enumerate(cell):
            for c, on in enumerate(row):
                if not on:
                    continue
                for dy in range(scale):
                    base = (y0 + r * scale + dy) * W + gx + c * scale
                    for dx in range(scale):
                        img[base + dx] = ink


def _blot(img, rng, x0, y0, x1, y1):
    """Pată neregulată: reuniune de discuri în jurul dreptunghiului (x0,y0)-(x1,y1)."""
    for _ in range(18 + (x1 - x0) // 25):
        cx, cy = rng.randint(x0, x1), rng.randint(y0, y1)
        rad = rng.randint(14, 34)
        for y in range(max(0, cy - rad), min(H, cy + rad)):
            span = int(math.sqrt(max(0, rad * rad - (y - cy) ** 2)))
            for x in range(max(0, cx - span), min(W, cx + span)):
                img[y * W + x] = min(img[y * W + x], 24 + (x * 7 + y * 3) % 11)


def _rotate(src, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = W / 2, H / 2
    out = bytearray(W * H)
    for y in range(H):
        dy = y - cy
        sx = ca * (0 - cx) + sa * dy + cx
        sy = -sa * (0 - cx) + ca * dy + cy
        row = y * W
        for x in range(W):
            ix, iy = int(sx), int(sy)
            if 0 <= ix < W - 1 and 0 <= iy < H - 1:
                fx, fy = sx - ix, sy - iy
                p = iy * W + ix
                top = src[p] + (src[p + 1] - src[p]) * fx
                bot = src[p + W] + (src[p + W + 1] - src[p + W]) * fx
                out[row + x] = int(top + (bot - top) * fy)
            else:
                out[row + x] = BED
            sx += ca
            sy -= sa
    return out


def _torn_corner(img, rng, size_x=360, size_y=420):
    edge = 0
    for y in range(H - size_y, H):
        t = (y - (H - size_y)) / size_y
        edge = max(-14, min(14, edge + rng.randint(-3, 3)))
        x_from = int(W - t * size_x) + edge
        for x in range(max(0, x_from), W):
            img[y * W + x] = BED + (x + y) % 5


def _noise(img, rng):
    table = [rng.randint(-7, 7) for _ in range(4093)]
    for i in range(len(img)):
        v = img[i] + table[(i * 31) % 4093]
        img[i] = 0 if v < 0 else 255 if v > 255 else v
    for _ in range(450):  # praf
        x, y = rng.randint(0, W - 3), rng.randint(0, H - 3)
        for dy in range(rng.randint(1, 3)):
            for dx in range(rng.randint(1, 3)):
                img[(y + dy) * W + x + dx] = rng.randint(30, 90)


def render(text, degradation, seed):
    """Întoarce (pixeli grayscale, lățime, înălțime)."""
    rng = random.Random(seed)
    img = bytearray([PAPER]) * (W * H)
    blot_fields = set(degradation.get("ink_blot_over", []))
    prefixes = {"cnp": "Cod numeric personal", "data_decesului": "Data decesului", "data_nasterii": "Data nașterii"}
    y = MARGIN_Y
    for line in text.rstrip("\n").split("\n"):
        if line.startswith("["):     # notă editorială din .md, nu face parte din document
            continue
        if not line.strip():
            y += BLANK
            continue
        title = line.strip().startswith("CERTIFICAT DE DECES")
        sub = line.startswith("  ")  # traducerea etichetei (FR/EN), cu litere mici sub eticheta română, ca pe tipizat
        scale = 5 if title else 2 if sub else 3
        x = (W - len(line.strip()) * CELL_W * scale) // 2 if line.strip() in (
            "ROMÂNIA", "CERTIFICAT DE DECES", "CERTIFICAT DE DÉCÈS / DEATH CERTIFICATE") else MARGIN_X
        content = line.strip() if x != MARGIN_X else line
        _draw_text(img, rng, x, y, content, scale)
        for field, prefix in prefixes.items():
            if field in blot_fields and line.startswith(prefix):
                vx = MARGIN_X + (25 if field == "cnp" else 23) * CELL_W * scale  # prima cifră a CNP rămâne vizibilă
                _blot(img, rng, vx, y, MARGIN_X + len(line) * CELL_W * scale, y + CELL_H * scale)
        if len(content) * CELL_W * scale > W - (x if x != MARGIN_X else MARGIN_X):
            raise ValueError(f"rând prea lung pentru scan: {line!r}")
        y += CELL_H * scale + (24 if title else 2 if sub else 6)
    if y > H:
        raise ValueError(f"textul nu încape pe pagina scanată ({y} > {H} px)")
    img = _rotate(img, degradation.get("rotation_deg", 0))
    if degradation.get("torn_corner") == "bottom_right":
        _torn_corner(img, rng)
    _noise(img, rng)
    return img, W, H
