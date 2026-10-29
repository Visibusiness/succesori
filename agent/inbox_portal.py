"""Intake portal: documents the operator sends land in registries/inbox/, where scripts/autopilot.py picks them up
(LLM extractor -> pipeline -> agents). Only .pdf/.png/.jpg/.md/.txt/.json, up to 5 MB each (scans and phone photos are read visually); the name is cleaned and nothing is overwritten.

POST /inbox   multipart, field `files` (one or more)  ->  {"saved": [names], "rejected": [{"name", "reason"}]}
GET  /inbox                                           ->  {"waiting": [...], "processed": [...], "failed": [...]}  (names, newest last)
GET  /inbox/quarantine                                ->  [{"name", "risk", "flags"}]  (076: stopped by agent/guard.py)

A file is written under a dot-name and linked into place, so the autopilot (which ignores dot-files) never reads a half-written one.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, UploadFile

INBOX = Path(os.environ.get("AUTOPILOT_INBOX") or Path(__file__).resolve().parent.parent / "registries" / "inbox")   # isolated test instances use their own inbox
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".md", ".txt", ".json"}
MAX_BYTES = 5 * 1024 * 1024


def safe_name(raw: str | None) -> str | None:
    """A file name that is safe to create in the inbox, or None if the extension is not accepted."""
    base = Path((raw or "").replace("\\", "/")).name
    stem, ext = os.path.splitext(base)
    if ext.lower() not in ALLOWED:
        return None
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")[:80]  # no leading dot: the autopilot ignores dot-files
    return f"{stem or 'document'}{ext.lower()}"


def _taken(name: str) -> bool:
    return any((d / name).exists() for d in (INBOX, INBOX / "processed", INBOX / "failed", INBOX / "quarantine"))


def store(name: str, data: bytes) -> str:
    """Write `data` as a new file in the inbox under `name` (or name-2, name-3 … if taken); returns the final name."""
    INBOX.mkdir(parents=True, exist_ok=True)
    tmp = INBOX / f".{secrets.token_hex(6)}.tmp"
    tmp.write_bytes(data)
    stem, ext = os.path.splitext(name)
    n = 1
    try:
        while True:
            final = name if n == 1 else f"{stem}-{n}{ext}"
            if not _taken(final):
                try:
                    os.link(tmp, INBOX / final)  # fails if it appeared meanwhile; never overwrites
                    return final
                except FileExistsError:
                    pass
            n += 1
    finally:
        tmp.unlink(missing_ok=True)


def _names(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    files = [p for p in d.iterdir() if p.is_file() and not p.name.startswith(".")]
    return [p.name for p in sorted(files, key=lambda p: p.stat().st_mtime)]


def listing() -> dict[str, list[str]]:
    return {"waiting": _names(INBOX), "processed": _names(INBOX / "processed")[-20:], "failed": _names(INBOX / "failed")[-20:]}


def archive() -> int:
    """Clean start (POST /demo/reset?inbox=true): waiting, processed/ and failed/ move to .archive/<stamp>/ (nothing is
    deleted; the autopilot ignores dot-dirs). Returns how many files moved."""
    dest = INBOX / ".archive" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    n = 0
    for sub in ("", "processed", "failed", "quarantine"):
        d = INBOX / sub
        for p in d.iterdir() if d.is_dir() else []:
            if p.is_file() and not p.name.startswith("."):
                (dest / sub).mkdir(parents=True, exist_ok=True)
                os.replace(p, dest / sub / p.name)
                n += 1
    return n


def make_router() -> APIRouter:
    router = APIRouter()

    @router.post("/inbox")
    async def put_inbox(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        saved, rejected = [], []
        for f in files:
            name = safe_name(f.filename)
            if name is None:
                rejected.append({"name": f.filename or "?", "reason": "tip neacceptat (doar .pdf, .png, .jpg, .md, .txt, .json)"})
                continue
            data = await f.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                rejected.append({"name": f.filename, "reason": "peste 5 MB"})
            elif not data.strip():
                rejected.append({"name": f.filename, "reason": "fișier gol"})
            else:
                saved.append(store(name, data))
        return {"saved": saved, "rejected": rejected}

    @router.get("/inbox")
    def list_inbox() -> dict[str, Any]:
        return listing()

    @router.get("/inbox/quarantine")
    def list_quarantine() -> list[dict[str, Any]]:
        """076: files the guard stopped (scripts/autopilot.py, POST /cases/{id}/documents), with the verdict next to them."""
        d = INBOX / "quarantine"
        out = []
        for name in _names(d):
            if name.endswith(".guard.json"):
                continue
            rep = d / f"{name}.guard.json"
            try:
                g = json.loads(rep.read_text(encoding="utf-8")) if rep.is_file() else {}
            except ValueError:
                g = {}
            out.append({"name": name, "risk": g.get("risk"), "flags": g.get("flags") or []})
        return out

    return router
