"""Preview of the source file of a received document (read-only), for the Documents tab in ops-ui.

GET /cases/{case_id}/documents/{doc_id}/preview serves the file a document came from. The client never sends a path:
the file is found from the `raw_name` the pipeline recorded, and only inside SOURCE_DIRS: the files the autopilot already
took from the intake portal (registries/inbox/processed, then failed) and the demo corpus (registries/documents/).
090: a `raw_name` "portofoliu/<Pxx>/<file>" is a document of the seeded portfolio, served from
registries/portofoliu/documente/ (agent/portfolio.py) and only from there.
A file uploaded straight to POST /cases/{id}/documents is not stored, so it answers 404 and the UI says so.

GET /demo/scan/{n}/file?variant= serves what the bank receives at step n of the guided demo, before or after it is
processed: the scan (registries/documents/scan/) for 2–7, the DGEP batch line for 1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from agent.inbox_portal import INBOX

ROOT = Path(__file__).resolve().parent.parent
CORPUS = (ROOT / "registries" / "documents").resolve()
# what the operator sent through the portal wins over a corpus file of the same name
SOURCE_DIRS = [(INBOX / "processed").resolve(), (INBOX / "failed").resolve(), CORPUS]   # INBOX: isolated instances have their own
PORTFOLIO_PREFIX, PORTFOLIO_DOCS = "portofoliu/", (ROOT / "registries" / "portofoliu" / "documente").resolve()
MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".json": "application/json; charset=utf-8"}


def resolve_source(raw_name: str | None) -> Path | None:
    """The source file for a raw_name, or None if it is empty, outside SOURCE_DIRS, not a known type or missing."""
    if not raw_name:
        return None
    bases = [(base, raw_name) for base in SOURCE_DIRS]
    if raw_name.startswith(PORTFOLIO_PREFIX):
        bases = [(PORTFOLIO_DOCS, raw_name[len(PORTFOLIO_PREFIX):])]
    for base, rel in bases:
        path = (base / rel).resolve()
        if base in path.parents and path.suffix.lower() in MEDIA and path.is_file():
            return path
    return None


def make_router(get_pipeline: Callable[[], object]) -> APIRouter:
    router = APIRouter()

    @router.get("/cases/{case_id}/documents/{doc_id}/preview")
    def preview(case_id: str, doc_id: str) -> FileResponse:
        case = get_pipeline().cases.get(case_id)
        if case is None:
            raise HTTPException(404, "dosar inexistent")
        doc = next((d for d in case.documents if d.id == doc_id), None)
        if doc is None:
            raise HTTPException(404, "document inexistent")
        path = resolve_source(doc.raw_name)
        if path is None:
            raise HTTPException(404, "fișierul sursă nu e păstrat (încărcat direct, nu prin portal)")
        return _serve(path)

    @router.get("/demo/scan/{n}/file")
    def demo_scan(n: int, variant: str = "A") -> FileResponse:
        from agent.demo_documents import DOCUMENTS, scan_file
        if not 1 <= n <= len(DOCUMENTS):
            raise HTTPException(404, "pas inexistent (1..7)")
        path = scan_file(n, variant) or resolve_source(DOCUMENTS[0]["raw_name"] if n == 1 else None)
        if path is None:
            raise HTTPException(404, "documentul pasului nu există pe disc")
        return _serve(path)

    return router


def _serve(path: Path) -> FileResponse:
    return FileResponse(path, media_type=MEDIA[path.suffix.lower()],
                        headers={"Content-Disposition": f'inline; filename="{path.name}"', "X-Content-Type-Options": "nosniff"})
