"""Documente cu lipsuri (sarcina 078): ce e în neregulă cu un document primit și cui îi scriem să-l repare.

Funcții pure (fără API, fără LLM):
  detect(doc, ctx)            -> problemele documentului: cod, text pentru om, cui trebuie să i se ceară
  resolve_sender(...)         -> cine l-a trimis: linkul de încărcare, persoana care a notificat decesul, destinatarul
                                 ultimului mesaj; altfel None (nu ghicim: operatorul)
  subject(doc)                -> „care document” e (tip + număr): dedupe pe același document
  reconcile(records, ...)     -> un document refăcut (același tip, fără problema respectivă) o închide; certificatul
                                 suplimentar închide lipsa de acoperire
  pending_notice(record)      -> problemele deschise încă necomunicate expeditorului (dedupe: o problemă o singură dată)
  ladder_items(records)       -> ce intră în scara de contact (077) cât timp problema e deschisă

Secret bancar: textele nu conțin solduri, sume sau date ale altor moștenitori; produsul lipsă din certificat e numit doar
dacă expeditorul e moștenitor în certificat. Documentul suspect (076) primește doar textul neutru, fără motivele gărzii.
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

THRESHOLD = 0.80          # agent/pipeline.py::CONFIDENCE_THRESHOLD
FIELD_THRESHOLD = 0.80     # a zone named as unreadable when the whole document is
FIELD_LOW = 0.50           # an accepted document: only a mandatory field this low is worth asking again (skill: ≤ 0,5)

TYPE_LABEL = {"dgep_signal": "semnalul DGEP", "notary_request": "adresa notarului",
              "insurance_certificate": "certificatul de asigurare", "heir_certificate": "certificatul de moștenitor",
              "insurer_response": "răspunsul asigurătorului", "supplementary_certificate": "certificatul de moștenitor suplimentar",
              "death_certificate": "certificatul de deces", "unknown": "documentul", "quarantined": "documentul"}
# documents that come from an institution, not from the family: without an upload link the sender is the institution
INSTITUTIONAL = {"dgep_signal": "DGEP", "notary_request": "notarul", "insurer_response": "asigurătorul"}
# who issues (and can correct) each document
ISSUER = {"heir_certificate": ("notary", "notarul care a emis certificatul"),
          "supplementary_certificate": ("notary", "notarul care a emis certificatul"),
          "notary_request": ("notary", "notarul"),
          "death_certificate": ("civil_registry", "serviciul de stare civilă (primăria) care a emis certificatul"),
          "insurance_certificate": ("insurer", "asigurătorul"),
          "insurer_response": ("insurer", "asigurătorul"),
          "dgep_signal": ("dgep", "DGEP")}
FIELD_LABEL = {"cnp": "CNP-ul persoanei decedate", "date_of_death": "data decesului",
               "case_file": "numărul dosarului succesoral", "hearing_date": "data dezbaterii succesiunii",
               "policy_id": "numărul poliței de asigurare", "insurer": "numele asigurătorului",
               "heirs": "lista moștenitorilor și partea fiecăruia", "decision": "decizia asigurătorului",
               "amount": "suma aprobată", "ibans": "conturile (IBAN) pe care le cuprinde", "name": "numele persoanei decedate",
               "birth_date": "data nașterii persoanei decedate", "document_number": "numărul documentului"}
# skill extract-documents, „Câmpuri obligatorii per tip”: each entry is a set of alternatives (any one is enough)
REQUIRED: dict[str, list[tuple[tuple[str, ...], ...]]] = {
    "dgep_signal": [(("cnp",),), (("date_of_death",),)],
    "notary_request": [(("cnp",), ("name", "birth_date")), (("case_file",), ("reference",)), (("hearing_date",),)],
    "insurance_certificate": [(("cnp",),), (("policy_id",),), (("insurer",),)],
    "heir_certificate": [(("cnp",),), (("case_file",), ("reference",)), (("heirs",),)],
    "insurer_response": [(("policy_id",),), (("decision",),)],
    "supplementary_certificate": [(("cnp",),), (("case_file",), ("reference",)), (("ibans",), ("products",))],
    "death_certificate": [(("cnp",), ("name", "birth_date")), (("date_of_death",),)],
}
# what the person was asked for (case.missing() strings) -> the document type that answers it
MISSING_TYPE = [("certificat suplimentar", "supplementary_certificate"), ("certificatul de moștenitor", "heir_certificate"),
                ("certificat de moștenitor", "heir_certificate"), ("certificatul de deces", "death_certificate")]
NEUTRAL_SUSPICIOUS = ("Nu am putut procesa documentul trimis online. Vă rugăm să îl aduceți, în original, la o agenție "
                      "Raiffeisen Bank; colegii noștri îl preiau acolo.")
_PAGE = re.compile(r"\bpag(?:ina|\.)?\s*(\d{1,2})\s*(?:din|/|of)\s*(\d{1,2})\b", re.I)


def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _cnp_match(a: str | None, b: str | None) -> bool:
    """Equal CNPs; an `X` (masked digit, DEMO_MODE) matches any digit."""
    if not a or not b:
        return True   # nothing to compare: not a mismatch
    a, b = re.sub(r"[\s.]", "", a), re.sub(r"[\s.]", "", b)
    return len(a) == len(b) and all(x == y or "X" in (x, y) for x, y in zip(a, b))


def expected_types(asked: list[str] | None) -> list[str]:
    out: list[str] = []
    for item in asked or []:
        low = item.lower()
        t = next((t for k, t in MISSING_TYPE if k in low), None)
        if t and t not in out:
            out.append(t)
    return out


def _problem(code: str, text: str, ask: tuple[str, str] | None = None, field: str | None = None,
             **extra: Any) -> dict[str, Any]:
    return {"code": code, "key": f"{code}:{field}" if field else code, "field": field, "text": text,
            "ask_role": ask[0] if ask else "sender", "ask": ask[1] if ask else "dumneavoastră", **extra}


def pages_missing(text: str | None, page_count: int | None) -> list[int]:
    """„Pagina 1 din 3” in the text: the pages announced but not present (by number, or by the file's page count)."""
    if not text:
        return []
    seen, total = set(), 0
    for m in _PAGE.finditer(text):
        n, t = int(m.group(1)), int(m.group(2))
        if 1 <= n <= t <= 30:
            seen.add(n)
            total = max(total, t)
    if not total or (page_count and page_count >= total):
        return []   # nothing announced, or the file has every page (a page number may just not have been read)
    return sorted(set(range(1, total + 1)) - seen)


def detect(doc: dict[str, Any], ctx: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """doc = the extracted document (document_type, confidence, fields, field_confidence, validation, raw_name).
    ctx (all optional): quarantined, pipeline_reason (escalation code the pipeline raised for this document),
    deceased_cnp (when the document was sent for a known case), expected_types, coverage_gaps [product labels],
    sender_is_heir, text, page_count, minor_docs_missing.
    Returns [{code, key, field, text, ask_role, ask}] in the order a person would fix them."""
    ctx = ctx or {}
    dtype = doc.get("document_type") or "unknown"
    if ctx.get("quarantined") or dtype == "quarantined":
        # 076: nothing about why (the flags stay with the operator); the person brings the original to an agency
        return [_problem("suspicious", NEUTRAL_SUSPICIOUS, ("agency", "agenția Raiffeisen Bank"), neutral=True)]
    f = doc.get("fields") if isinstance(doc.get("fields"), dict) else {}
    fc = doc.get("field_confidence") if isinstance(doc.get("field_confidence"), dict) else {}
    conf = float(doc.get("confidence") or 0)
    issuer = ISSUER.get(dtype)
    reason = ctx.get("pipeline_reason")
    out: list[dict[str, Any]] = []

    # 1. legibility: the whole document, then the zones (fields) that could not be read
    unreadable = [k for k in FIELD_LABEL if k in f and (_empty(f.get(k)) or (fc.get(k) is not None and float(fc[k]) < FIELD_THRESHOLD))]
    unreadable += [k for k in fc if k not in unreadable and k in FIELD_LABEL and float(fc[k] or 0) < FIELD_THRESHOLD]
    masked = [k for k, v in f.items() if k.endswith("_raw") and isinstance(v, str) and re.search(r"[#█]|\[ilizibil\]", v)]
    unreadable += [k[:-4] for k in masked if k[:-4] in FIELD_LABEL and k[:-4] not in unreadable]
    if dtype == "unknown" or conf < THRESHOLD or reason == "document_illegible":
        zones = ", ".join(FIELD_LABEL[k] for k in unreadable) if unreadable else ""
        what = TYPE_LABEL.get(dtype, "documentul")
        out.append(_problem("illegible",
                            (f"Nu am putut citi clar {what}" if dtype != "unknown" else "Nu am putut citi clar documentul și nu "
                             "am recunoscut ce fel de document este")
                            + (f": nu se văd {zones}." if zones else ".")
                            + " Vă rugăm să trimiteți o fotografie sau o scanare clară a întregului document (toate "
                              "paginile, fără umbre, fără părți acoperite sau tăiate).",
                            zones=unreadable))
    elif unreadable:
        mandatory = {k for alts in REQUIRED.get(dtype, []) for alt in alts for k in alt}
        for k in unreadable:
            if _empty(f.get(k)) or k not in mandatory or float(fc.get(k) or 0) >= FIELD_LOW:
                continue   # empty: reported below as missing; else the pipeline already used the document
            out.append(_problem("field_unreadable", f"Pe document nu se citește clar {FIELD_LABEL[k]}. Vă rugăm să "
                                f"trimiteți o fotografie mai clară a zonei respective.", field=k))

    # 2. pages
    gone = pages_missing(ctx.get("text"), ctx.get("page_count"))
    if gone:
        out.append(_problem("pages_missing", ("Lipsește pagina " if len(gone) == 1 else "Lipsesc paginile ")
                            + ", ".join(map(str, gone)) + " din document. Vă rugăm să trimiteți documentul complet.",
                            pages=gone))

    # 3. mandatory fields for the type (only once the document was readable: an unreadable one is point 1)
    if not any(p["code"] == "illegible" for p in out):
        for alts in REQUIRED.get(dtype, []):
            if any(all(not _empty(f.get(k)) for k in alt) for alt in alts):
                continue
            k = alts[0][0]
            out.append(_problem("field_missing", f"Pe {TYPE_LABEL.get(dtype, 'document')} nu apare {FIELD_LABEL.get(k, k)}. "
                                + (f"Cereți-i {issuer[1]} un exemplar complet." if issuer else
                                   "Vă rugăm să trimiteți documentul complet."), issuer, field=k))
        if dtype == "insurer_response" and f.get("decision") == "approved" and _empty(f.get("amount")):
            out.append(_problem("field_missing", "Răspunsul asigurătorului nu menționează suma aprobată.", ISSUER[dtype],
                                field="amount"))
        if dtype == "heir_certificate":
            for h in f.get("heirs") or []:
                if isinstance(h, dict) and (_empty(h.get("name")) or _empty(h.get("share"))):
                    out.append(_problem("field_missing", "Certificatul nu arată, pentru fiecare moștenitor, numele și "
                                        "partea lui din moștenire. Cereți-i notarului un exemplar complet.", ISSUER[dtype],
                                        field="heirs"))
                    break

    # 4. CNP of someone else than the deceased of the case the document was sent for
    if (reason in ("cnp_mismatch", "customer_not_found") and ctx.get("on_case")) or \
            not _cnp_match(f.get("cnp") if isinstance(f.get("cnp"), str) else None, ctx.get("deceased_cnp")):
        out.append(_problem("cnp_mismatch", "CNP-ul de pe document nu este al persoanei decedate pentru care am deschis "
                            "dosarul. Verificați că ați trimis documentul potrivit; dacă documentul e greșit, "
                            + (f"cereți-i {issuer[1]} să îl corecteze." if issuer else "trimiteți-l pe cel corect."),
                            issuer, field="cnp"))
    if reason == "identity_unconfirmed":
        out.append(_problem("identity_unconfirmed", "Documentul nu are CNP-ul persoanei decedate, iar după nume și data "
                            "nașterii nu am putut confirma că este aceeași persoană. Vă rugăm să trimiteți un document "
                            "care conține CNP-ul.", field="cnp"))

    # 5. shares
    heirs = [h for h in f.get("heirs") or [] if isinstance(h, dict) and not _empty(h.get("share"))]
    if heirs and dtype == "heir_certificate":
        try:
            total = sum(Fraction(str(h["share"])) for h in heirs)
        except (ValueError, ZeroDivisionError):
            total = None
        if total != 1 or reason == "shares_invalid":
            out.append(_problem("shares_invalid", "Părțile moștenitorilor din certificat nu adună împreună întreaga "
                                "moștenire. Cereți-i notarului care l-a emis să verifice certificatul și, dacă e cazul, "
                                "să emită o încheiere de îndreptare.", ISSUER["heir_certificate"]))
        if any(h.get("minor") and _empty(h.get("legal_representative")) for h in heirs):
            out.append(_problem("minor_without_representative", "Certificatul arată un moștenitor minor, dar nu numește "
                                "reprezentantul lui legal. Pentru partea minorului avem nevoie de actul de identitate și de "
                                "acordul scris al reprezentantului legal (părinte sau tutore).",
                                ("legal_representative", "reprezentantul legal al minorului")))
    if reason == "product_unknown":
        out.append(_problem("product_unknown", "Certificatul menționează un cont care nu aparține persoanei decedate la "
                            "banca noastră. Cereți-i notarului care l-a emis să verifice conturile trecute în certificat.",
                            ISSUER.get(dtype, ISSUER["heir_certificate"])))

    # 6. heir certificate that does not cover every product: the supplement is the notary's
    gaps = ctx.get("coverage_gaps") or []
    if gaps and dtype in ("heir_certificate", "supplementary_certificate"):
        what = (" (" + ", ".join(gaps) + ")") if ctx.get("sender_is_heir") else ""
        out.append(_problem("certificate_incomplete", f"Certificatul nu cuprinde toate bunurile persoanei decedate aflate "
                            f"la banca noastră{what}. Cereți-i notarului care a emis certificatul un certificat de "
                            "moștenitor suplimentar pentru bunurile care lipsesc; banca i-a scris și ea notarului.",
                            ISSUER["heir_certificate"], gaps=list(gaps), handled_by_bank=True))

    # 7. another document than the one asked for
    exp = ctx.get("expected_types") or []
    if exp and dtype not in exp and dtype not in ("unknown",) and not any(p["code"] == "illegible" for p in out):
        out.append(_problem("wrong_type", f"Am primit {TYPE_LABEL.get(dtype, 'un alt document')}, dar documentul pe care "
                            f"vi l-am cerut este {' sau '.join(TYPE_LABEL.get(t, t) for t in exp)}. Pe acesta îl păstrăm, "
                            "dar documentul cerut încă lipsește.", expected=exp))
    return out


def resolve_sender(dtype: str, token_to: str | None = None, notifier: dict[str, Any] | None = None,
                   last_message_to: str | None = None) -> dict[str, Any] | None:
    """Who sent the document, in this order: the person the upload link was sent to; an institution, for its own
    document types; the person who notified the death; the recipient of the last message sent before the document.
    None ⇒ unknown: the operator decides, we never guess."""
    if token_to:
        return {"name": token_to, "source": "upload_token", "label": "persoana căreia i-am trimis linkul de încărcare"}
    if dtype in INSTITUTIONAL:
        return {"name": None, "institution": INSTITUTIONAL[dtype], "source": "institution",
                "label": f"instituția care emite documentul ({INSTITUTIONAL[dtype]})"}
    if notifier and notifier.get("name"):
        return {"name": notifier["name"], "source": "notifier", "label": "persoana care a notificat decesul",
                "role": "notifier"}
    if last_message_to:
        return {"name": last_message_to, "source": "last_message", "label": "destinatarul ultimului mesaj din dosar"}
    return None


def subject(doc: dict[str, Any]) -> str:
    """Which document this is (dedupe: the same problem on the same document is not sent again)."""
    f = doc.get("fields") if isinstance(doc.get("fields"), dict) else {}
    num = f.get("document_number") or f.get("case_file") or f.get("reference") or "-"
    return f"{doc.get('intended_type') or doc.get('document_type') or 'unknown'}:{num}"


def intended_type(doc: dict[str, Any], expected: list[str] | None = None) -> str:
    """The type the document was meant to be: the extracted one (even with low confidence), else the only one asked for."""
    t = doc.get("document_type") or "unknown"
    if t not in ("unknown", "quarantined"):
        return t
    g = doc.get("declared_type")
    if g and g not in ("unknown", "quarantined"):
        return g
    return expected[0] if expected and len(expected) == 1 else "unknown"


def asked_types(record: dict[str, Any]) -> list[str]:
    """What the new upload link of a DOCUMENT_DEFICIENT message asks for: the supplement for a certificate that does not
    cover everything, else the same document, redone."""
    if any(p["code"] == "certificate_incomplete" for p in record["problems"] if p.get("status") != "closed"):
        return ["supplementary_certificate"]
    t = record.get("intended_type")
    return [t] if t and t not in ("unknown", "quarantined") else []


def reconcile(records: list[dict[str, Any]], new: dict[str, Any] | None = None,
              coverage_gaps: list[str] | None = None, at: str | None = None) -> list[str]:
    """Close what a later document fixed. Mutates the records' problems (`status`, `closed_by`, `closed_at`); returns the
    keys closed. A newer document of the same intended type (from the same sender, or an unknown one) without a problem
    closes it on the older records; `certificate_incomplete` closes when the case is covered."""
    closed: list[str] = []
    gaps = set(coverage_gaps or [])
    for r in records:
        if new is not None and r["document_id"] == new["document_id"]:
            continue
        for p in r["problems"]:
            if p.get("status") == "closed":
                continue
            why = None
            if p["code"] == "certificate_incomplete" and coverage_gaps is not None and not gaps & set(p.get("gaps") or []):
                why = "certificatul suplimentar acoperă bunurile care lipseau"
            elif new is not None and p["code"] != "certificate_incomplete":
                same_type = r["intended_type"] == new["intended_type"] or (r["intended_type"] == "unknown"
                                                                           and new["intended_type"] != "unknown")
                same_sender = not r.get("sender") or not new.get("sender") or \
                    (r["sender"].get("name") or "").lower() == (new["sender"].get("name") or "").lower()
                fixed = new.get("accepted") and not any(q["key"] == p["key"] for q in new["problems"])
                if same_type and same_sender and fixed:
                    why = f"documentul refăcut ({new['document_id']}) nu mai are problema"
            if why:
                p.update(status="closed", closed_by=why, closed_at=at)
                closed.append(f"{r['document_id']}:{p['key']}")
        if r["problems"] and all(p.get("status") == "closed" for p in r["problems"]):
            r["status"] = "closed"
    return closed


def pending_notice(record: dict[str, Any], notified: set[str]) -> list[dict[str, Any]]:
    """Open problems of a record not yet told to its sender. `notified` = dedupe keys already sent in the case
    (`<subject>|<problem key>`), so the same problem on the same document goes out once."""
    if not record.get("sender") or not record["sender"].get("name"):
        return []
    return [p for p in record["problems"] if p.get("status") != "closed" and
            f"{record['subject']}|{p['key']}" not in notified]


def dedupe_key(record: dict[str, Any], problem: dict[str, Any]) -> str:
    return f"{record['subject']}|{problem['key']}"


def ladder_items(records: list[dict[str, Any]]) -> list[str]:
    """077: an open problem we told the sender about stays in the contact ladder (reminder at 14 days etc.) until a
    corrected document closes it. The bank's own requests (supplement asked from the notary) are already in `missing`."""
    out: list[str] = []
    for r in records:
        open_ = [p for p in r["problems"] if p.get("status") != "closed" and p.get("notified_at")
                 and not p.get("handled_by_bank")]
        if not open_:
            continue
        what = "documentul trimis online (de adus la agenție)" if any(p.get("neutral") for p in open_) else \
            f"{TYPE_LABEL.get(r['intended_type'], 'documentul')}, refăcut ({r.get('received_on') or ''}): " + \
            "; ".join(p["code"].replace("_", " ") for p in open_)
        if what not in out:
            out.append(what)
    return out


def public_view(record: dict[str, Any]) -> dict[str, Any]:
    """What goes to heir-communicator: the document, the problems (human text, who to ask) and nothing else
    (no guard flags, no amounts, no other heirs)."""
    neutral = any(p.get("neutral") for p in record["problems"])
    return {"document": {"label": "documentul" if neutral else TYPE_LABEL.get(record["intended_type"], "documentul"),
                         "name": None if neutral else record.get("name"), "received_on": record.get("received_on")},
            "problems": [{"code": p["code"], "text": p["text"], "ask": p["ask"], "ask_role": p["ask_role"]}
                         for p in record["problems"] if p.get("status") != "closed"]}
