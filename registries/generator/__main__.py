"""python -m registries.generator — regenerează determinist PDF-urile din registries/documents/{,hard/}pdf/."""
import hashlib
import json
import sys
from pathlib import Path

from . import pdf, scan

DOCS = Path(__file__).resolve().parent.parent / "documents"


SETS = [(DOCS, "[0-9][0-9]-*.md"), (DOCS / "hard", "H[0-9]*-*.md")]


def main():
    for src, pattern in SETS:
        (src / "pdf").mkdir(exist_ok=True)
    for md in sorted(md for src, pattern in SETS for md in src.glob(pattern)):
        meta = json.loads(md.with_suffix(".json").read_text())
        target = md.parent / "pdf" / (md.stem + ".pdf")
        text = md.read_text()
        if "degradation" in meta:
            pixels, w, h = scan.render(text, meta["degradation"], seed=int(meta["doc_id"]) * 1000 + 7)
            pdf.image_pdf(target, pixels, w, h, title=f"Scan {md.stem}")
        else:
            pdf.text_pdf(target, text, title=md.stem)
        print(f"{target.relative_to(DOCS.parent.parent)}  {hashlib.sha256(target.read_bytes()).hexdigest()[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
