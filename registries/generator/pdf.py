"""Scriitor PDF minimal, fără dependențe (doar zlib). Determinist: fără date, fără ID-uri aleatoare.

Două tipuri de pagini:
- text: font standard Courier (PDF core 14), WinAnsi + /Differences pentru ă/ș/ț, cu ToUnicode ca extracția
  de text să întoarcă diacriticele corecte;
- imagine: o imagine grayscale (8 biți) pe toată pagina, pentru documentele „scanate”.
"""
import zlib

A4 = (595, 842)

# Caracterele din afara WinAnsi pe care le punem pe coduri nefolosite, prin /Differences.
_EXTRA = {"Ă": (0x81, "Abreve"), "ă": (0x8D, "abreve"), "Ș": (0x8F, "Scommaaccent"),
          "ș": (0x90, "scommaaccent"), "Ț": (0x9D, "Tcommaaccent"), "ț": (0x9E, "tcommaaccent")}
_WINANSI_HIGH = {"„": 0x84, "…": 0x85, "–": 0x96, "—": 0x97, "”": 0x94, "“": 0x93, "’": 0x92, "·": 0xB7,
                 "°": 0xB0}


def _code(ch):
    if ch in _EXTRA:
        return _EXTRA[ch][0]
    if ch in _WINANSI_HIGH:
        return _WINANSI_HIGH[ch]
    o = ord(ch)
    if 0x20 <= o < 0x7F or 0xA0 <= o <= 0xFF:
        return o
    raise ValueError(f"caracter fără glifă în Courier/WinAnsi: {ch!r} (U+{o:04X})")


def _encode(text):
    out = bytearray()
    for ch in text:
        c = _code(ch)
        if c in (0x28, 0x29, 0x5C):  # ( ) \
            out.append(0x5C)
        out.append(c)
    return bytes(out)


def _tounicode():
    pairs = [(c, ord(ch)) for ch, (c, _) in _EXTRA.items()] + [(c, ord(ch)) for ch, c in _WINANSI_HIGH.items()]
    pairs += [(o, o) for o in list(range(0x20, 0x7F)) + list(range(0xA0, 0x100))]
    pairs.sort()
    body = []
    for i in range(0, len(pairs), 100):  # max 100 intrări per bloc bfchar
        chunk = pairs[i:i + 100]
        body.append(f"{len(chunk)} beginbfchar")
        body += [f"<{c:02X}> <{u:04X}>" for c, u in chunk]
        body.append("endbfchar")
    return ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
            "1 begincodespacerange <00> <FF> endcodespacerange\n"
            + "\n".join(body) + "\nendcmap CMapName currentdict /CMap defineresource pop end end\n").encode()


class _Doc:
    def __init__(self):
        self.objs = []

    def add(self, body):
        self.objs.append(body)
        return len(self.objs)

    def stream(self, data, extra=""):
        z = zlib.compress(data, 9)
        return self.add(f"<< /Length {len(z)} /Filter /FlateDecode {extra}>>\nstream\n".encode() + z
                        + b"\nendstream")

    def write(self, path, page_ids, pages_id, title):
        catalog = self.add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())
        info = self.add(b"<< /Title (" + _encode(title) + b") /Producer (registries.generator) >>")
        self.objs[pages_id - 1] = (f"<< /Type /Pages /Count {len(page_ids)} /Kids ["
                                   + " ".join(f"{p} 0 R" for p in page_ids) + "] >>").encode()
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(self.objs, 1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(self.objs) + 1}\n0000000000 65535 f \n".encode()
        out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
        out += (f"trailer\n<< /Size {len(self.objs) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n").encode()
        with open(path, "wb") as f:
            f.write(out)


def _wrap(line, width):
    if len(line) <= width:
        return [line]
    indent = " " * min(len(line) - len(line.lstrip()) + 2, 20)
    out, cur = [], line
    while len(cur) > width:
        cut = cur.rfind(" ", 0, width)
        if cut <= len(indent):
            cut = width
        out.append(cur[:cut].rstrip())
        cur = indent + cur[cut:].lstrip()
    return out + [cur]


def text_pdf(path, text, title, size=8.4, margin=40):
    w, h = A4
    width_chars = int((w - 2 * margin) / (0.6 * size))
    leading = round(size * 1.3, 2)
    per_page = int((h - 2 * margin) / leading)
    lines = [l for raw in text.rstrip("\n").split("\n") for l in _wrap(raw, width_chars)]
    chunks = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]

    d = _Doc()
    pages_id = d.add(b"")  # completat la final
    diffs = " ".join(f"{c} /{name}" for c, name in sorted(_EXTRA.values()))
    tu = d.stream(_tounicode())
    font = d.add(f"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding << /Type /Encoding "
                 f"/BaseEncoding /WinAnsiEncoding /Differences [{diffs}] >> /ToUnicode {tu} 0 R >>".encode())
    page_ids = []
    for chunk in chunks:
        ops = [f"BT /F1 {size} Tf {leading} TL {margin} {h - margin - size} Td".encode()]
        ops += [b"(" + _encode(l) + b") Tj T*" for l in chunk]
        ops.append(b"ET")
        content = d.stream(b"\n".join(ops))
        page_ids.append(d.add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {w} {h}] "
                              f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content} 0 R >>".encode()))
    d.write(path, page_ids, pages_id, title)


def image_pdf(path, pixels, width, height, title):
    """`pixels`: bytes grayscale, rând după rând, `width`×`height`. Pagina A4, imaginea pe toată pagina."""
    w, h = A4
    d = _Doc()
    pages_id = d.add(b"")
    img = d.stream(bytes(pixels), f"/Type /XObject /Subtype /Image /Width {width} /Height {height} "
                                  f"/ColorSpace /DeviceGray /BitsPerComponent 8 ")
    content = d.stream(f"q {w} 0 0 {h} 0 0 cm /Im1 Do Q".encode())
    page = d.add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {w} {h}] "
                 f"/Resources << /XObject << /Im1 {img} 0 R >> >> /Contents {content} 0 R >>".encode())
    d.write(path, [page], pages_id, title)
