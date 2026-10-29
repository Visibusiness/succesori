"""A letter written by the correspondent (Markdown) as a PDF the bank can sign: header, recipient, the letter, a
signature block. PyMuPDF only (fitz.Story renders HTML); DejaVu Sans for the Romanian diacritics (ș, ț), subset to the glyphs used.

Markdown handled: headings (#..###), **bold**, *italic*, `code`, tables (| a | b |), lists (- / 1.), paragraphs.
Everything else is kept as plain, escaped text: the PDF shows exactly the words the operator approved.
"""
from __future__ import annotations

import html
import io
import re
from pathlib import Path

import fitz

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
A4 = fitz.paper_rect("a4")
MARGIN = 56
CSS = """
@font-face { font-family: dv; src: url(DejaVuSans.ttf); }
@font-face { font-family: dv; src: url(DejaVuSans-Bold.ttf); font-weight: bold; }
* { font-family: dv; }
body { font-size: 10pt; line-height: 1.4; color: #1d2330; }
h1 { font-size: 15pt; margin: 0 0 6pt 0; } h2 { font-size: 13pt; margin: 12pt 0 4pt 0; } h3 { font-size: 11pt; margin: 10pt 0 4pt 0; }
p { margin: 0 0 6pt 0; } ul, ol { margin: 0 0 6pt 0; }
table { border-collapse: collapse; margin: 4pt 0 8pt 0; } th, td { border: 0.5pt solid #9aa3ad; padding: 2pt 4pt; font-size: 9pt; }
th { background-color: #eef0f3; }
.head { font-size: 9pt; color: #5f6b7a; border-bottom: 1pt solid #1d2330; padding-bottom: 4pt; margin-bottom: 10pt; }
.sign { margin-top: 24pt; } .sign td { border: none; padding: 2pt 18pt 2pt 0; font-size: 10pt; }
"""


def _inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", s)
    return re.sub(r"`([^`]+)`", r"\1", s)


def md_to_html(md: str) -> str:
    out: list[str] = []
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.startswith("<!--"):
            i += 1
            continue
        if m := re.match(r"^(#{1,3})\s+(.*)$", line):
            out.append(f"<h{len(m[1])}>{_inline(m[2])}</h{len(m[1])}>")
            i += 1
        elif line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                head, *body = rows
                out.append("<table><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr>"
                           + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</table>")
        elif re.match(r"^\s*([-*]|\d+\.)\s+", line):
            tag = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i].rstrip()))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3}\s|\s*\||\s*([-*]|\d+\.)\s)", lines[i]):
                para.append(_inline(lines[i].strip()))
                i += 1
            out.append("<p>" + "<br/>".join(para) + "</p>")
    return "\n".join(out)


def letter_pdf(text: str, *, email: str | None = None, case_id: str | None, date: str, title: str = "",
               to: str | None = None, sign: bool = True) -> bytes:
    """The PDF bytes: header (bank, case, recipient, date), the letter, and a blank signature block.
    Any document the bank generated goes through here (agent/generated_docs.py): `to` names a recipient that is not an
    e-mail address, `sign=False` leaves out the signature block (a message, a report, a proposal for the operator)."""
    whom = f"<br/>Trimis prin e-mail către: {html.escape(email)}" if email else f"<br/>Către: {html.escape(to)}" if to else ""
    head = (f'<div class="head"><b>Raiffeisen Bank S.A. · Succesiuni</b><br/>Dosar {html.escape(case_id or "—")} · {html.escape(date)}'
            + whom + (f"<br/>{html.escape(title)}" if title else "") + "</div>")
    sign = ('<table class="sign"><tr><td>Întocmit și verificat de:</td><td>Semnătura:</td></tr>'
            "<tr><td>Nume: ______________________</td><td>______________________</td></tr>"
            "<tr><td>Data: ______________________</td><td>Ștampila băncii</td></tr></table>") if sign else ""
    story = fitz.Story(html=f"<body>{head}{md_to_html(text)}{sign}</body>", user_css=CSS, archive=fitz.Archive(str(FONT_DIR)))
    out = io.BytesIO()
    writer = fitz.DocumentWriter(out)
    where = A4 + (MARGIN, MARGIN, -MARGIN, -MARGIN)
    more = True
    while more:
        dev = writer.begin_page(A4)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    doc = fitz.open("pdf", out.getvalue())
    doc.subset_fonts()
    return doc.tobytes(garbage=3, deflate=True)
