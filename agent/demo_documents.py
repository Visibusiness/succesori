"""The 7 demo documents (kb/scenariu-demo/maria-ionescu.md §3), already extracted, plus the hard cases.

Loaded from registries/documents/*.mvp.json (Ștefan's ground truth in the shape the pipeline consumes), so the
demo, the tests and the extractor eval all use the same values and identifiers (documente-demo.md §0).
The paper documents (02–07) also exist as the scan the bank would receive (registries/documents/scan/, made by
`python -m registries.generator.scan_demo`): `scan_file` gives it, for the guided demo's "scanned" mode.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).resolve().parent.parent / "registries" / "documents"

# order of the scenario; 04-A is the default heir certificate, 04-B the testament variant
_MAIN = ["01-dgep-semnal", "02-adresa-notar", "03-certificat-asigurare", "04-certificat-mostenitor-A",
         "05-raspuns-asigurator", "06-certificat-suplimentar", "07-certificat-deces-ilizibil"]


def _load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.pop("_deprecated_fields", None)
    return doc


DOCUMENTS: list[dict[str, Any]] = [_load(DOCS_DIR / f"{name}.mvp.json") for name in _MAIN]
VARIANT_B: dict[str, Any] = _load(DOCS_DIR / "04-certificat-mostenitor-B.mvp.json")
VARIANT_B_HEIRS: list[dict[str, Any]] = VARIANT_B["fields"]["heirs"]
CNP: str = DOCUMENTS[0]["fields"]["cnp"]

SCAN_DIR = DOCS_DIR / "scan"


def scan_file(n: int, variant: str = "A") -> Path | None:
    """The scanned original of demo step n (1..7), or None: step 1 is the DGEP batch line (electronic, no paper)."""
    name = "04-certificat-mostenitor-B" if n == 4 and variant.upper() == "B" else _MAIN[n - 1]
    path = SCAN_DIR / f"{name}.pdf"
    return path if n > 1 and path.is_file() else None


# the preview of an already-extracted demo document shows the scan it stands for (what the bank received), not the
# clean PDF the scan was printed from; the .mvp.json files stay as they are (ground truth for the eval)
for _n, _doc in [*enumerate(DOCUMENTS, 1), (4, VARIANT_B)]:
    _scan = scan_file(_n, "B" if _doc is VARIANT_B else "A")
    if _scan is not None:
        _doc["raw_name"] = f"scan/{_scan.name}"


# hard cases (registries/documents/hard/README.md), keyed "H1".."H11"
HARD: dict[str, dict[str, Any]] = {p.name.split("-")[0]: _load(p) for p in sorted((DOCS_DIR / "hard").glob("H*.mvp.json"))}
