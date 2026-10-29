"""Every document the bank generated for a case, in one registry: what the agents wrote and what the bank's rules
produced, each one viewable and downloadable as PDF, Markdown or text.

GET /cases/{case_id}/generated
    [{id, kind, kind_label, group, title, created, author, recipient, status, formats, url, download_url, urls,
      filename, event_id, escalation_id, message_id}]  (oldest first)
GET /cases/{case_id}/generated/{doc_id}?format=pdf|md|txt[&download=1]
    the document: `inline`, or with download=1 `attachment` with a clear name (SC-2026-0107-raspuns-notar.pdf)

Sources (each one a collector below; a new kind of document is one more entry in a table, not a special case):
  run files     <run>/letters/, messages/, investigations/ (<case>-<key>.md, written by the autopilot and by the guided
                demo's agents; letters/<case>-<action>.pdf = the letter that left, signed), audits/audit-NN.md and
                audit.md (the auditor's reports that name the case). The copies saved in SQLite (state.artifacts,
                agent/store.py) fill in what is no longer on disk.
  outbox.jsonl  the messages that left (POST /messages): matched to the agent's draft, or a document of their own
  case events   what the pipeline generated without an agent: the answer to the notary (balances at the date of death),
                the request for a supplementary certificate, the claim notice to the insurer, the contact ladder's
                steps, the payment plan
  /demo/ai      the guided demo's human gates (letter, message, proposal): their status (draft / approved / rejected)
                goes on the matching document; a gate with no file of its own is listed too

`doc_id` is opaque (a hash of the source) and only looked up in this list: no path ever comes from the client.
The PDF is made by agent/letter_pdf.py, the same generator as the letters of the guided demo (ai_jobs.gate_pdf).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from agent.handoffs import AGENT_LABEL, LETTER_ACTIONS

SYSTEM = "Sistemul (regulile băncii)"
FORMATS = ("pdf", "md", "txt")
MEDIA = {"pdf": "application/pdf", "md": "text/markdown; charset=utf-8", "txt": "text/plain; charset=utf-8"}
# kind -> (label, group): the group says where the UI shows it (corr = letters and messages, ai = agents, pay = payment)
KINDS = {
    "letter": ("Scrisoare", "corr"),
    "notary_answer": ("Răspuns către notar", "corr"),
    "supplement_request": ("Cerere de certificat suplimentar", "corr"),
    "insurance_notice": ("Avizarea asigurătorului", "corr"),
    "message": ("Mesaj către moștenitor", "corr"),
    "deficiency_message": ("Mesaj: document cu probleme", "corr"),
    "contact_step": ("Pas din scara de contact", "corr"),
    "investigation": ("Propunerea investigatorului", "ai"),
    "audit": ("Raportul auditorului", "ai"),
    "payment_plan": ("Planul de plată", "pay"),
}
# a correspondent's letter, by the action that asked for it: title, file name, recipient
LETTERS = {
    "notary_answer_drafted": ("Răspunsul către notar", "raspuns-notar", "notary"),
    "supplement_requested": ("Cererea de certificat suplimentar către notar", "cerere-supliment", "notary"),
    "insurance_claim_opened": ("Avizarea daunei către asigurător", "avizare-asigurator", "insurer"),
    "loan_settled_by_insurance": ("Nota către notar: creditul stins de asigurător", "nota-notar-credit-stins", "notary"),
    "insurance_refused": ("Informarea moștenitorilor: asigurătorul a refuzat plata", "informare-refuz-asigurator", "heirs"),
}
TEMPLATE_LABEL = {"MISSING_DOCS_FIRST": "documente lipsă (prima cerere)", "MISSING_DOCS_REMINDER": "reamintire documente lipsă",
                  "MINOR_REPRESENTATION": "reprezentarea minorului", "SUPPLEMENT_NEEDED": "certificat suplimentar necesar",
                  "PLAN_APPROVED": "plată aprobată", "DEADLINE_SOON": "termen care se apropie",
                  "DOCUMENT_DEFICIENT": "document cu probleme"}
GATE_STATUS = {"pending": "ciornă: așteaptă aprobarea", "approved": "aprobat", "rejected": "respins"}
LINK = re.compile(r"(\{\{UPLOAD_URL\}\}|https?://\S+?)/(cases/\S+/)?upload\?token=(\{\{token\}\}|[\w-]+)")
LINK_TEXT = "[link securizat de încărcare]"


@dataclass
class Sources:
    """What the registry reads, as functions of the API (tests give their own)."""
    run_dir: Callable[[], Path]
    case_view: Callable[[str], dict[str, Any] | None]                 # GET /cases/{id}
    saved_files: Callable[[], dict[str, str]] = lambda: {}             # state.artifacts (SQLite): rel path -> text
    contact_plan: Callable[[str], dict[str, Any] | None] = lambda cid: None
    gates: Callable[[], Iterable[dict[str, Any]]] = lambda: []        # the guided demo's human gates
    gate_pdf: Callable[[dict[str, Any]], bytes] | None = None


@dataclass
class Doc:
    key: str                     # where it comes from (hashed into the id)
    case_id: str
    kind: str
    title: str
    slug: str
    created: str | None = None
    author: str = SYSTEM
    recipient: str | None = None
    text: str = ""               # Markdown body, without the title
    pdf_file: Path | None = None  # the PDF that left the bank, if kept
    pdf_fn: Callable[[], bytes] | None = None
    sign: bool = False           # a letter: the PDF has the signature block
    status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return "g" + hashlib.sha256(f"{self.case_id}|{self.key}".encode()).hexdigest()[:16]

    def formats(self) -> list[str]:
        return list(FORMATS) if self.text.strip() else ["pdf"]


# ---------------------------------------------------------------------------------------------------- helpers
def _strip(text: str) -> tuple[dict[str, Any], str, str]:
    """An artifact file -> (its metadata comment, its title line, the body)."""
    meta: dict[str, Any] = {}
    lines = text.replace("\r\n", "\n").split("\n")
    title = ""
    while lines and (lines[0].startswith("<!--") or lines[0].startswith("# ") or not lines[0].strip()):
        line = lines.pop(0)
        if line.startswith("<!--"):
            try:
                meta = json.loads(line[4:line.rindex("-->")].strip())
            except ValueError:
                pass
        elif line.startswith("# ") and not title:
            title = line[2:].strip()
    return meta, title, "\n".join(lines).strip()


def _norm(text: str) -> str:
    _, _, body = _strip(text or "")
    return re.sub(r"\s+", " ", LINK.sub("LINK", body.replace(LINK_TEXT, "LINK"))).strip().lower()


def _clean_title(title: str, cid: str) -> str:
    t = re.sub(rf"\s*[—-]\s*{re.escape(cid)}\s*$", "", title or "").strip()
    return re.sub(r"^Draft:\s*", "", t)


def _lei(bani: int | float | None) -> str:
    if bani is None:
        return "—"
    s = f"{abs(bani) / 100:,.2f}".replace(",", " ").replace(".", ",")
    return ("−" if bani < 0 else "") + s + " lei"


def _date(s: str | None) -> str:
    if not s:
        return "—"
    try:
        return datetime.fromisoformat(s[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return s


def _fields(view: dict[str, Any], doc_type: str) -> dict[str, Any]:
    for d in reversed(view.get("documents") or []):
        if d.get("document_type") == doc_type:
            return {f["name"]: f.get("value") for f in d.get("fields") or []}
    return {}


def _notary(view: dict[str, Any]) -> str:
    f = _fields(view, "notary_request")
    name = f.get("notary_name") or f.get("notary_office")
    file = f.get("case_file") or f.get("reference")
    return "notarul public" + (f" {name}" if name else "") + (f" (dosarul succesoral {file})" if file else "")


def _insurer(view: dict[str, Any]) -> str:
    for e in view.get("events") or []:
        if m := re.match(r"Dosar de daună deschis la (.+?) pentru polița", e.get("detail") or ""):
            return f"asigurătorul {m[1]}"
    f = _fields(view, "insurance_certificate")
    return f"asigurătorul {f['insurer']}" if f.get("insurer") else "asigurătorul"


def _heirs(view: dict[str, Any]) -> str:
    names = [h.get("name") for h in view.get("heirs") or [] if h.get("name")]
    return "moștenitorii: " + ", ".join(names) if names else "moștenitorii"


RECIPIENT = {"notary": _notary, "insurer": _insurer, "heirs": _heirs}


def _head(view: dict[str, Any]) -> str:
    d = view.get("deceased") or {}
    return (f"**Dosar:** {view.get('case_id')}  \n**Defunct:** {d.get('name') or '—'}"
            f"{', decedat la ' + _date(d.get('date_of_death')) if d.get('date_of_death') else ''}\n")


def _product_label(view: dict[str, Any], pid: str) -> str:
    p = next((x for x in view.get("products") or [] if x.get("id") == pid), None)
    return f"{p.get('label') or p.get('type')} ({pid})" if p else pid


def to_text(md: str) -> str:
    """Markdown -> plain text (the .txt download): no heading marks, no emphasis, tables kept as rows."""
    out = []
    for line in md.split("\n"):
        if re.fullmatch(r"\s*\|?\s*:?-{2,}.*", line):
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m[1] or m[2], line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        if line.strip().startswith("|"):
            line = "  ".join(c.strip() for c in line.strip().strip("|").split("|"))
        out.append(line.rstrip("  ").rstrip())
    return "\n".join(out).strip() + "\n"


# ---------------------------------------------------------------------------------------------------- collectors
def _run_files(src: Sources) -> dict[str, str]:
    """rel path -> text: the run directory, filled in from the SQLite copies of what is no longer on disk."""
    files = dict(src.saved_files() or {})
    base = src.run_dir()
    for sub in ("letters", "messages", "investigations", "audits"):
        d = base / sub
        for p in sorted(d.glob("*.md")) if d.is_dir() else []:
            try:
                files[f"{sub}/{p.name}"] = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
    if (base / "audit.md").is_file():
        files["audit.md"] = (base / "audit.md").read_text(encoding="utf-8")
    return files


def _file_created(meta: dict[str, Any], path: Path) -> str | None:
    if meta.get("generated_at"):
        return str(meta["generated_at"])
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None


def _agent_docs(cid: str, view: dict[str, Any], src: Sources) -> list[Doc]:
    """letters/, messages/, investigations/ (<case>-<key>.md and the letters' PDFs), the auditor's reports."""
    base, files, out = src.run_dir(), _run_files(src), []
    pdfs = {p.stem: p for p in (base / "letters").glob(f"{cid}-*.pdf")} if (base / "letters").is_dir() else {}
    stems = sorted({rel[len("letters/"):-3] for rel in files if rel.startswith(f"letters/{cid}-")} | set(pdfs))
    for stem in stems:
        text = files.get(f"letters/{stem}.md", "")
        meta, title, body = _strip(text)
        rest = stem[len(cid) + 1:]
        known = LETTERS.get(rest)
        out.append(Doc(f"letters/{stem}", cid, "letter", known[0] if known else _clean_title(title, cid) or "Scrisoare",
                       known[1] if known else "scrisoare-" + re.sub(r"^contact-", "", rest), _file_created(meta, base / "letters" / f"{stem}.md"),
                       AGENT_LABEL.get(meta.get("agent") or "correspondent", "Corespondentul"),
                       RECIPIENT[known[2]](view) if known else None, body, pdfs.get(stem), sign=True,
                       status="trimisă, semnată (PDF)" if stem in pdfs else ("blocată de verificarea ieșirii" if meta.get("blocked") else None),
                       extra={"action": rest if known else None, "artifact": f"letters/{stem}.md"}))
    for rel in sorted(r for r in files if r.startswith(f"messages/{cid}-") and r.endswith(".md")):
        meta, title, body = _strip(files[rel])
        rest = rel[len(f"messages/{cid}-"):-3]
        deficient = rest.startswith("deficient-")
        m = re.search(r"(?:Mesaj către|→)\s+(.+?)(?:\s+\(|\s+—|$)", title)
        out.append(Doc(rel, cid, "deficiency_message" if deficient else "message",
                       _clean_title(title, cid) or "Mesaj către moștenitor",
                       "mesaj-" + ("document-" + rest if deficient else rest), _file_created(meta, base / rel),
                       AGENT_LABEL.get(meta.get("agent") or "heir-communicator", "Comunicatorul cu moștenitorii"),
                       m[1] if m else None, body, status="blocat de verificarea ieșirii" if meta.get("blocked") else "ciornă",
                       extra={"artifact": rel}))
    for rel in sorted(r for r in files if r.startswith(f"investigations/{cid}-") and r.endswith(".md")):
        meta, title, body = _strip(files[rel])
        esc = rel[len(f"investigations/{cid}-"):-3]
        out.append(Doc(rel, cid, "investigation", f"Propunerea investigatorului pentru escaladarea {esc}",
                       f"propunere-investigator-{esc.lower()}", _file_created(meta, base / rel),
                       AGENT_LABEL["case-investigator"], "operatorul (decizie, nu pleacă din bancă)", body,
                       extra={"escalation_id": esc, "artifact": rel}))
    audits = sorted(r for r in files if r.startswith("audits/") and r.endswith(".md")) or (["audit.md"] if "audit.md" in files else [])
    for rel in audits:
        meta, title, body = _strip(files[rel])
        if cid not in body:
            continue   # the auditor checks a batch of cases: only the reports that name this one
        n = re.search(r"(\d+)\.md$", rel)
        out.append(Doc(rel, cid, "audit", "Raportul auditorului" + (f" nr. {int(n[1])}" if n else ""),
                       "raport-auditor" + (f"-{n[1]}" if n else ""), _file_created(meta, base / rel), AGENT_LABEL["auditor"],
                       "echipa de succesiuni (intern)", body, extra={"artifact": rel}))
    return out


def _outbox_docs(cid: str, view: dict[str, Any], src: Sources, docs: list[Doc]) -> list[Doc]:
    """The messages that left: the agent's draft becomes the message sent (status, date, channel), else its own document."""
    f = src.run_dir() / "outbox.jsonl"
    msgs = []
    for line in f.read_text(encoding="utf-8").splitlines() if f.is_file() else []:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("case_id") == cid and m.get("kind") != "letter":   # a letter that left is its PDF in letters/
            msgs.append(m)
    drafts = {_norm(d.text): d for d in docs if d.kind in ("message", "deficiency_message") and "message_id" not in d.extra}
    out = []
    for i, m in enumerate(msgs):
        body = LINK.sub(LINK_TEXT, m.get("body") or "")
        tpl = m.get("template_id") or ""
        sent = f"trimis pe {m.get('channel') or '—'}" + (f" ({m['status']})" if m.get("status") else "")
        extra = {"message_id": m.get("message_id"), "template_id": tpl, "channel": m.get("channel")}
        d = drafts.pop(_norm(m.get("body") or ""), None)
        if d:
            d.status, d.text, d.recipient = sent, body, m.get("to") or d.recipient
            d.extra.update(extra)
            continue
        kind = "deficiency_message" if tpl == "DOCUMENT_DEFICIENT" else "message"
        what = TEMPLATE_LABEL.get(tpl, tpl.lower().replace("_", " ") or "mesaj")
        out.append(Doc(f"outbox/{m.get('message_id') or i}", cid, kind, f"Mesaj către {m.get('to') or '—'}: {what}",
                       f"mesaj-{(m.get('message_id') or str(i + 1)).lower()}", m.get("case_date") or m.get("at"),
                       f"aprobat de {m['approved_by']}" if m.get("approved_by") else "Banca (coada de trimitere)",
                       f"{m.get('to') or '—'} ({m.get('channel') or '—'})", body, status=sent, extra=extra))
    return out


# documents the bank's rules generated, from the case's events: predicate on the event -> builder
def _notary_answer(cid: str, view: dict[str, Any], e: dict[str, Any]) -> Doc:
    a = e["data"]["answer"]
    signed = next((x for x in view.get("events") or [] if (x.get("detail") or "").startswith("Răspunsul către notar semnat de")), None)
    rows = "\n".join(f"| {_product_label(view, p['product_id'])} | {_lei(p.get('principal'))} | {_lei(p.get('accrued_interest'))} | "
                     f"{_lei(p.get('total'))} |" for p in a.get("products") or [])
    credits = "\n".join(f"- {_date((c.get('movement') or {}).get('date'))}: {_lei(c.get('amount'))} "
                        f"({'pensie creditată după deces, de returnat la CNPP' if 'pension' in (c.get('code') or '') else c.get('code')})"
                        for c in a.get("post_death_credits") or []) or "- niciuna"
    md = (_head(view) + f"\nCătre {_notary(view)}.\n\nCa răspuns la adresa dumneavoastră în dosarul succesoral "
          f"{a.get('notary_file') or '—'}, vă comunicăm soldurile defunctului la data decesului ({_date(a.get('as_of'))}):\n\n"
          "| Produs | Sold | Dobândă la data decesului | Total |\n|---|---|---|---|\n" + rows +
          f"\n\n**Sume intrate după deces:**\n\n{credits}\n\n**Retrageri ale împuternicitului după deces:** "
          + (", ".join(_lei(x) for x in a.get("mandate_withdrawals") or []) or "niciuna") +
          "\n\n**Asigurări atașate creditelor:** " + (", ".join(a.get("loan_insurance") or []) or "niciuna") +
          f"\n\nTemei: {e.get('rule') or 'Legea 36/1995 art. 81 alin. 2'}.\n")
    return Doc(f"event/{e['id']}", cid, "notary_answer", "Răspunsul către notar: soldurile la data decesului", "raspuns-notar",
               e.get("at"), SYSTEM, _notary(view), md, sign=True,
               status=signed["detail"].split(";")[0].replace("Răspunsul către notar ", "") if signed else "trimis la semnare",
               extra={"event_id": e["id"], "action": "notary_answer_drafted"})


def _supplement(cid: str, view: dict[str, Any], e: dict[str, Any]) -> Doc:
    gaps = re.search(r"nu acoperă:\s*(.+?)\.\s", e.get("detail") or "")
    items = "\n".join(f"- {_product_label(view, g.strip())}" for g in (gaps[1].split(",") if gaps else []))
    md = (_head(view) + f"\nCătre {_notary(view)}.\n\nCertificatul de moștenitor primit de bancă nu cuprinde "
          f"următoarele produse ale defunctului:\n\n{items or '- (vezi dosarul)'}\n\nVă rugăm să emiteți un certificat de "
          f"moștenitor suplimentar pentru acestea; până atunci banca nu le poate plăti moștenitorilor.\n\nTemei: {e.get('rule') or '—'}.\n")
    return Doc(f"event/{e['id']}", cid, "supplement_request", "Cererea de certificat suplimentar către notar", "cerere-supliment",
               e.get("at"), SYSTEM, _notary(view), md, sign=True, extra={"event_id": e["id"], "action": "supplement_requested"})


def _insurance(cid: str, view: dict[str, Any], e: dict[str, Any]) -> Doc:
    d = view.get("deceased") or {}
    md = (_head(view) + f"\nCătre {_insurer(view)}.\n\nVă avizăm decesul asiguratului {d.get('name') or '—'}"
          f"{', survenit la ' + _date(d.get('date_of_death')) if d.get('date_of_death') else ''}, și deschiderea dosarului de daună:\n\n"
          f"{e.get('detail')}\n\nTemei: {e.get('rule') or '—'}.\n")
    return Doc(f"event/{e['id']}", cid, "insurance_notice", "Avizarea daunei către asigurător", "avizare-asigurator",
               e.get("at"), SYSTEM, _insurer(view), md, sign=True, extra={"event_id": e["id"], "action": "insurance_claim_opened"})


def _contact_step(cid: str, view: dict[str, Any], e: dict[str, Any], plan: dict[str, Any] | None) -> Doc:
    code = e["data"]["step"]
    step = next((s for s in (plan or {}).get("steps") or [] if s.get("code") == code), {})
    m = re.match(r"Scara de contact:\s*(.+?)\s*\(([^)]*)\)\s*→\s*(.+?)\.?$", e.get("detail") or "")
    label, how, to = (m[1], m[2], m[3]) if m else (step.get("label") or code, step.get("action_label") or "", "—")
    recips = "\n".join(f"- {r.get('name')}" + (f", {r['channel']}" if r.get("channel") else "") + (f", {r['address']}" if r.get("address") else "")
                       + (f" (reprezentantul legal al lui {r['for_minor']})" if r.get("for_minor") else "")
                       for r in step.get("recipients") or []) or f"- {to}"
    missing = "\n".join(f"- {x}" for x in view.get("missing") or []) or "- nimic"
    tpl = step.get("template_id")
    md = (_head(view) + f"\n**Pasul:** {label}  \n**Cum:** {how or '—'}" + (f" (șablonul „{TEMPLATE_LABEL.get(tpl, tpl)}”)" if tpl else "")
          + f"  \n**Data:** {_date(e.get('at'))}\n\n**Către:**\n\n{recips}\n\n**Ce mai lipsește din dosar (azi):**\n\n{missing}\n\n"
          f"Temei: {e.get('rule') or step.get('basis') or '—'}.\n\nMesaj operațional: fără solduri sau alte date despre conturi (secret bancar).\n")
    return Doc(f"event/{e['id']}", cid, "contact_step", f"Scara de contact: {label}", "scara-contact-" + re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-"),
               e.get("at"), SYSTEM, to, md, status=f"făcut ({how})" if how else "făcut", extra={"event_id": e["id"], "step": code})


EVENT_DOCS: list[tuple[Callable[[dict[str, Any]], bool], Callable[..., Doc]]] = [
    (lambda e: isinstance((e.get("data") or {}).get("answer"), dict), _notary_answer),
    (lambda e: "Cerere de certificat suplimentar generată" in (e.get("detail") or ""), _supplement),
    (lambda e: (e.get("detail") or "").startswith("Dosar de daună deschis la"), _insurance),
]
# the event an agent's letter answers (journal: the entry that produced the document)
LETTER_EVENT = {"notary_answer_drafted": EVENT_DOCS[0][0], "supplement_requested": EVENT_DOCS[1][0],
                "insurance_claim_opened": EVENT_DOCS[2][0],
                "loan_settled_by_insurance": lambda e: (e.get("detail") or "").startswith("Indemnizație primită"),
                "insurance_refused": lambda e: (e.get("data") or {}).get("reason") == "insurance_refused"}


def _plan_doc(cid: str, view: dict[str, Any]) -> Doc | None:
    p = view.get("payment_plan")
    if not p:
        return None
    ev = next((e for e in reversed(view.get("events") or []) if (e.get("detail") or "").startswith("Plan de plată generat")), None)
    rows = "\n".join(f"| {l.get('name')} | {_product_label(view, l.get('product_id'))} | {l.get('share')} | {_lei(l.get('amount'))} | "
                     f"{'blocată: ' + str(l.get('blocked_reason')) if l.get('blocked') else 'de plătit ' + str(l.get('pay_on') or 'acum')} |"
                     for l in p.get("lines") or [])
    free = sum(l.get("amount") or 0 for l in p.get("lines") or [] if not l.get("blocked"))
    withheld = "\n".join(f"- {w.get('label') or w.get('reason')}: {_lei(w.get('amount'))}" for w in p.get("withheld") or [])
    status = {"pending_approval": "așteaptă aprobarea operatorului", "approved": "aprobat", "rejected": "respins", "paid": "plătit"}
    md = (_head(view) + f"\n**Planul:** {p.get('plan_id')} · {p.get('variant_label') or ''}  \n**Stare:** {status.get(p.get('status'), p.get('status'))}\n\n"
          "| Moștenitor | Produs | Partea din produs | Suma | Plata |\n|---|---|---|---|---|\n" + rows +
          f"\n\n**De plătit acum:** {_lei(free)}\n" + (f"\n**Reținut:**\n\n{withheld}\n" if withheld else "") +
          "\nPlata e o acțiune ireversibilă: pleacă doar după aprobarea unui om (C.civ. art. 1114, 2187).\n")
    return Doc("plan", cid, "payment_plan", f"Planul de plată {p.get('plan_id')}", "plan-plata", (ev or {}).get("at"), SYSTEM,
               "operatorul (aprobare)", md, sign=True, status=status.get(p.get("status"), p.get("status")),
               extra={"event_id": ev["id"] if ev else None})


def _event_docs(cid: str, view: dict[str, Any], src: Sources, docs: list[Doc]) -> list[Doc]:
    events, out = view.get("events") or [], []
    artifacts = {d.extra.get("artifact") for d in docs}
    plan = None
    for e in events:
        for match, build in EVENT_DOCS:
            if match(e):
                out.append(build(cid, view, e))
        data = e.get("data") or {}
        if data.get("step") and not (data.get("artifact") and data["artifact"] in artifacts):
            plan = plan if plan is not None else (src.contact_plan(cid) or {})
            out.append(_contact_step(cid, view, e, plan))
    # the journal entry behind each agent document
    escs = [e for e in events if e.get("kind") == "escalation"]
    mail = [e for e in events if (e.get("detail") or "").startswith("Mesaj către ")]
    for d in docs:
        if d.kind == "letter" and d.extra.get("action") in LETTER_EVENT:
            ev = next((e for e in events if LETTER_EVENT[d.extra["action"]](e)), None)
        elif d.kind == "letter":
            ev = next((e for e in events if (e.get("data") or {}).get("artifact") == d.extra.get("artifact")), None)
        elif d.kind == "investigation":
            n = re.fullmatch(r"ESC-(\d+)", d.extra.get("escalation_id") or "")
            ev = escs[int(n[1]) - 1] if n and int(n[1]) <= len(escs) else None
        elif d.extra.get("message_id"):
            ev = next((e for e in mail if f"Mesaj către {d.recipient} pe {d.extra.get('channel')} ({d.extra.get('template_id')})" in e["detail"]
                       and e["id"] not in {x.extra.get("event_id") for x in docs}), None)
        else:
            ev = None
        if ev:
            d.extra["event_id"] = ev["id"]
    if (pd := _plan_doc(cid, view)) is not None:
        out.append(pd)
    return out


def _gate_docs(cid: str, src: Sources, docs: list[Doc]) -> list[Doc]:
    """The guided demo's gates: the status of the draft (pending / approved / rejected); a gate with no file is a document."""
    by_text = {_norm(d.text): d for d in docs if d.text}
    out = []
    for g in src.gates() or []:
        if g.get("case_id") != cid or g.get("kind") not in ("letter", "message", "investigation") or not g.get("preview"):
            continue
        st = GATE_STATUS.get(g.get("status"), g.get("status"))
        if g.get("status") != "pending" and g.get("decided_by"):
            st += f" de {g['decided_by']}"
        d = by_text.get(_norm(g["preview"]))
        if d:
            if not (d.status or "").startswith("trimis"):
                d.status = st
            d.extra["gate"] = f"{g.get('step')}:{g.get('key')}"
            continue
        meta, title, body = _strip(g["preview"])
        kind = {"letter": "letter", "message": "message", "investigation": "investigation"}[g["kind"]]
        known = LETTERS.get(g.get("action") or "")
        d = Doc(f"gate/{g.get('step')}/{g.get('key')}", cid, kind, known[0] if known else g.get("title") or KINDS[kind][0],
                (known[1] if known else f"{kind}-pas-{g.get('step')}"), g.get("opened_at"),
                {"letter": "Corespondentul", "message": "Comunicatorul cu moștenitorii", "investigation": "Investigatorul"}[kind],
                g.get("recipient") or g.get("to"), body, sign=kind == "letter", status=st,
                extra={"gate": f"{g.get('step')}:{g.get('key')}", "escalation_id": g.get("escalation")})
        if kind == "letter" and src.gate_pdf:
            d.pdf_fn = (lambda gg=g: src.gate_pdf(gg))
        out.append(d)
    return out


def collect(cid: str, src: Sources) -> list[Doc] | None:
    """Every generated document of the case, oldest first; None if the case does not exist."""
    view = src.case_view(cid)
    if view is None:
        return None
    docs = _agent_docs(cid, view, src)
    docs += _outbox_docs(cid, view, src, docs)
    docs += _gate_docs(cid, src, docs)
    docs += _event_docs(cid, view, src, docs)
    docs.sort(key=lambda d: (str(d.created or "")[:10], str(d.created or "")))
    taken: set[str] = set()
    for d in sorted(docs, key=lambda x: x.author == SYSTEM):   # one clear, unique file name per document; the agent's
        slug, n = d.slug, 1                                     # letter keeps the plain name, the rules' draft gets "-sistem"
        while slug in taken:
            n += 1
            slug = f"{d.slug}-sistem" if n == 2 and d.author == SYSTEM else f"{d.slug}-{n}"
        d.slug = slug
        taken.add(slug)
    return docs


# ---------------------------------------------------------------------------------------------------- rendering
def render(d: Doc, fmt: str) -> bytes:
    if fmt == "md":
        return (f"# {d.title}\n\n{d.text}\n").encode("utf-8")
    if fmt == "txt":
        return (d.title + "\n" + "=" * len(d.title) + "\n\n" + to_text(d.text)).encode("utf-8")
    if d.pdf_file is not None and d.pdf_file.is_file():
        return d.pdf_file.read_bytes()
    if d.pdf_fn is not None:
        return d.pdf_fn()
    from agent.letter_pdf import letter_pdf
    created = _date(d.created) if d.created else datetime.now(timezone.utc).strftime("%d.%m.%Y")
    return letter_pdf(d.text or "(fără conținut)", case_id=d.case_id, date=created, title=d.title, to=d.recipient, sign=d.sign)


def public(d: Doc, base: str = "") -> dict[str, Any]:
    url = f"{base}/cases/{d.case_id}/generated/{d.id}"
    fmts = d.formats()
    label, group = KINDS[d.kind]
    return {"id": d.id, "case_id": d.case_id, "kind": d.kind, "kind_label": label, "group": group, "title": d.title,
            "created": d.created, "author": d.author, "recipient": d.recipient, "status": d.status, "formats": fmts,
            "url": f"{url}?format=pdf", "download_url": f"{url}?format=pdf&download=1",
            "urls": {f: f"{url}?format={f}" for f in fmts},
            "filename": re.sub(r"[^A-Za-z0-9._-]+", "-", f"{d.case_id}-{d.slug}.pdf"),
            **{k: d.extra.get(k) for k in ("event_id", "escalation_id", "message_id", "action", "step", "gate")}}


def make_router(src: Sources) -> APIRouter:
    router = APIRouter()

    def docs_of(case_id: str) -> list[Doc]:
        docs = collect(case_id, src)
        if docs is None:
            raise HTTPException(404, "dosar inexistent")
        return docs

    @router.get("/cases/{case_id}/generated")
    def generated(case_id: str) -> list[dict[str, Any]]:
        return [public(d) for d in docs_of(case_id)]

    @router.get("/cases/{case_id}/generated/{doc_id}")
    def generated_doc(case_id: str, doc_id: str, format: str = "pdf", download: bool = False) -> Response:
        if format not in FORMATS:
            raise HTTPException(400, f"format necunoscut: {format}; permise: {', '.join(FORMATS)}")
        d = next((x for x in docs_of(case_id) if x.id == doc_id), None)
        if d is None:
            raise HTTPException(404, "document inexistent")
        if format not in d.formats():
            raise HTTPException(404, f"documentul nu există ca {format}")
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{d.case_id}-{d.slug}.{format}")
        return Response(render(d, format), media_type=MEDIA[format],
                        headers={"Content-Disposition": f'{"attachment" if download else "inline"}; filename="{name}"',
                                 "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})

    return router
