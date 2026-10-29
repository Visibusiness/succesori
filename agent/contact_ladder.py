"""Scara de contact cu moștenitorii care NU aduc documentele (sarcina 077). Funcție pură: dosar + „azi” → pași.

  INITIAL            ziua 0     mesaj cu linkul de încărcare, pe un canal permis
  REMINDER           ziua 14    același mesaj, scurt (heir-messaging: MISSING_DOCS_REMINDER)
  REGISTERED_LETTER  ziua 30    scrisoare recomandată cu confirmare de primire, la domiciliu
  NOTARY             ziua 60    cerere prin notarul din dosar (sau operatorul: banca poate cere deschiderea procedurii)
  DEADLINE_WARNING   deces + 10 luni   „se apropie termenul de 1 an” (doar fără certificat de moștenitor)
  OPTION_EXPIRED     deces + 1 an      prezumată renunțarea / posibil vacantă: fonduri păstrate fără comisioane,
                                       operatorul decide
  MINOR_INITIAL / MINOR_REMINDER_k     minorul: plata părții lui blocată până la documente; reminder lunar către
                                       reprezentantul legal

Zilele 0/14/30/60 se numără de la ultima mișcare din dosar (data aflării decesului sau a ultimului document): sunt
„zile fără răspuns”, o regulă internă propusă, nu un termen legal. Termenele de 10 luni și 1 an se numără de la deces
(C.civ. art. 1.103 alin. 1, art. 2.552). Temeiurile, cu citatele, sunt în kb/legal/mostenitori-inactivi.md.

Un pas se face o singură dată: `done` (ținut de API în dosar) îl marchează făcut. Dacă la aceeași dată sunt scadenți
mai mulți pași nefăcuți ai aceluiași traseu (ceasul a sărit), doar cel mai avansat e scadent; ceilalți sunt „săriți”.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

KB = "kb/legal/mostenitori-inactivi.md"

# (code, offset in days from `since`, action, template_id, label, basis)
MAIN_STEPS: list[tuple[str, int, str, str | None, str, str]] = [
    ("INITIAL", 0, "message", "MISSING_DOCS_FIRST", "Mesaj inițial cu linkul de încărcare",
     "GDPR art. 6 alin. (1) lit. b)/c)/f) și art. 14 (informare la primul contact); mesaj operațional, nu comercial "
     "(Legea 506/2004 art. 12 privește doar comunicările comerciale); secret bancar: fără solduri "
     f"(kb/legal/comunicare-canale-consimtamant.md; {KB} §4)"),
    ("REMINDER", 14, "message", "MISSING_DOCS_REMINDER", "Reminder la 14 zile fără răspuns",
     "heir-messaging: MISSING_DOCS_REMINDER la 14 zile fără răspuns (regulă internă, nu termen legal); "
     f"același temei GDPR ca mesajul inițial ({KB} §4)"),
    ("REGISTERED_LETTER", 30, "registered_letter", None, "Scrisoare recomandată cu confirmare de primire, la domiciliu",
     "dovada comunicării la domiciliul din certificat sau din evidența băncii; aceeași formă pe care C.civ. "
     f"art. 2.190 alin. (2) o cere băncii când notifică titularul (regulă internă, nu termen legal; {KB} §4)"),
    ("NOTARY", 60, "notary_request", None, "Cerere prin notarul din dosar",
     "Legea 36/1995 art. 105 (notarul citează succesibilii), art. 103 alin. (3) (creditorii succesiunii pot cere "
     f"deschiderea procedurii), art. 104 alin. (4) (inventar la cererea creditorilor) ({KB} §2)"),
]
DEADLINE_BASIS = ("C.civ. art. 1.103 alin. (1): opțiunea succesorală se exercită în termen de un an de la deschiderea "
                  "moștenirii; art. 2.552 (calculul pe ani); termenul poate începe mai târziu (art. 1.103 alin. 2) sau "
                  f"poate fi suspendat (art. 1.103 alin. 3, art. 2.532) ({KB} §1)")
EXPIRED_BASIS = ("C.civ. art. 1.112 (prezumția de renunțare: doar dacă succesibilul știa și, la notar, a fost citat), "
                 "art. 1.135–1.139 și Legea 36/1995 art. 117 (vacanța o constată notarul; somația după 1 an și 6 luni, "
                 "art. 1.137), C.civ. art. 2.187 (cont indiviz); fără comisioane după deces (rules.fees_to_reverse) "
                 f"({KB} §1, §3)")
MINOR_BASIS = ("C.civ. art. 41 alin. (2)–(3), 146, 149, 502: minorul de 14–18 ani încasează cu încuviințarea "
               "reprezentantului legal, în cont pe numele lui; până atunci partea lui rămâne blocată; reminder lunar "
               f"(regulă internă) (kb/legal/mostenitor-minor.md; {KB} §5)")

STATUS_LABEL = {"done": "făcut", "due": "scadent", "upcoming": "urmează", "skipped": "sărit (depășit de pasul următor)",
                "waiting": "așteaptă un canal de contact"}
ACTION_LABEL = {"message": "mesaj", "registered_letter": "scrisoare recomandată", "notary_request": "cerere prin notar",
                "operator": "operator"}


def add_months(d: date, n: int) -> date:
    """C.civ. art. 2.552: ziua corespunzătoare din luna de final; dacă nu există, ultima zi a lunii."""
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _d(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    return date.fromisoformat(v[:10]) if isinstance(v, str) and v else None


def is_minor_item(item: str) -> bool:
    return "minor" in item.lower() or "reprezentant" in item.lower()


def permitted_channel(p: dict[str, Any]) -> str | None:
    """Canalul pe care trimitem mesaje operaționale (kb/legal/comunicare-canale-consimtamant.md): e-mail verificat, apoi
    aplicația pentru un client al băncii. SMS / WhatsApp doar cu consimțământ pe canal (politica prudentă din KB)."""
    ch = p.get("channels") or {}
    consent = ch.get("consent") or {}
    if ch.get("email") and ch.get("verified"):
        return "email"
    if ch.get("app"):
        return "app"
    if ch.get("phone") and consent.get("sms"):
        return "sms"
    return None


def _name_key(name: str) -> tuple[str, ...]:
    return tuple(sorted(name.lower().split()))


def _representative(persons: list[dict[str, Any]], ref: str | None) -> dict[str, Any] | None:
    """The certificate names the representative by id (H1) or, from the LLM extractor, by name ("IONESCU ION")."""
    if not ref:
        return None
    return next((x for x in persons if x.get("id") == ref), None) or \
        next((x for x in persons if not x.get("minor") and _name_key(x.get("name") or "") == _name_key(ref)), None)


def _recipients(persons: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    out = []
    for p in persons:
        if p.get("minor"):
            continue   # minorul se contactează prin reprezentantul legal (traseul minorului)
        if kind == "message" and (ch := permitted_channel(p)):
            out.append({"id": p.get("id"), "name": p["name"], "role": p.get("role"), "channel": ch})
        elif kind == "registered_letter" and p.get("address"):
            out.append({"id": p.get("id"), "name": p["name"], "role": p.get("role"), "channel": "posta_recomandata",
                        "address": p["address"], "address_source": p.get("address_source")})
    return out


def _step(code: str, track: str, label: str, due: date, action: str, basis: str, template: str | None = None,
          recipients: list[dict[str, Any]] | None = None, note: str = "") -> dict[str, Any]:
    return {"code": code, "track": track, "label": label, "due": due.isoformat(), "action": action,
            "action_label": ACTION_LABEL.get(action, action), "template_id": template, "recipients": recipients or [],
            "basis": basis, "note": note}


def _resolve(steps: list[dict[str, Any]], done: dict[str, dict[str, Any]], today: date) -> None:
    """status per step: done / due / skipped / upcoming / waiting; within a track only the last undue-but-due step is due."""
    for s in steps:
        if s["code"] in done:
            s["status"], s["done_at"] = "done", done[s["code"]].get("at")
            s["done"] = done[s["code"]]
        elif date.fromisoformat(s["due"]) > today:
            s["status"] = "upcoming"
        else:
            s["status"] = "due"
    for track in {s["track"] for s in steps}:
        mine = [s for s in steps if s["track"] == track]
        last_done = max((i for i, s in enumerate(mine) if s["status"] == "done"), default=-1)
        for s in mine[:max(last_done, 0)]:   # a later step was already made: the earlier ones will not be made any more
            if s["status"] != "done":
                s["status"] = "skipped"
        due = [s for s in mine if s["status"] == "due"]
        for s in due[:-1]:
            s["status"] = "skipped"
    for s in steps:
        if s["status"] == "due" and s.get("wait_without_channel"):
            s["status"] = "waiting"
        s.pop("wait_without_channel", None)
        s["status_label"] = STATUS_LABEL[s["status"]]


def contact_plan(dossier: dict[str, Any], today: date) -> dict[str, Any]:
    """dossier (built by the API from the case; every key optional):
      case_id, date_of_death, learned_on, last_document_on, certificate_on (date of the heir certificate, if any),
      missing: [str] (what the heirs can bring), has_loan: bool,
      persons: [{id, name, role: heir|legal_representative|notifier, minor, representative_id,
                 channels: {email, phone, app, verified, consent: {sms: bool}}, address, address_source}],
      notary: {name, office, case_file} | None,
      done: {step_code: {at, ...}}  (steps already applied, from the case)
    Returns {active, since, steps: [...], next, due_now: [...], blocked: [...], summary}."""
    dod, learned = _d(dossier.get("date_of_death")), _d(dossier.get("learned_on"))
    last_doc = _d(dossier.get("last_document_on"))
    cert_on = _d(dossier.get("certificate_on"))
    done: dict[str, dict[str, Any]] = dossier.get("done") or {}
    persons: list[dict[str, Any]] = dossier.get("persons") or []
    missing = list(dossier.get("missing") or [])
    notary = dossier.get("notary")
    since = max([d for d in (learned, last_doc) if d], default=None)
    out: dict[str, Any] = {"case_id": dossier.get("case_id"), "today": today.isoformat(),
                           "since": since.isoformat() if since else None, "steps": [], "blocked": [], "next": None,
                           "due_now": [], "active": False}
    if since is None:
        out["summary"] = "Decesul nu e încă cunoscut în dosar: nu există scară de contact."
        return out

    steps: list[dict[str, Any]] = []
    main_missing = [m for m in missing if not is_minor_item(m)]
    if main_missing:
        prev_done: date | None = None
        prev_off = 0
        for code, off, action, template, label, basis in MAIN_STEPS:
            due = since + timedelta(days=off)
            if prev_done:   # never sooner after the previous step than the ladder spacing
                due = max(due, prev_done + timedelta(days=off - prev_off))
            note, wait = "", False
            if action == "notary_request":
                if notary:
                    recips = [{"name": notary.get("name") or notary.get("office") or "notarul din dosar",
                               "role": "notary", "channel": "scrisoare", "case_file": notary.get("case_file"),
                               "office": notary.get("office")}]
                else:
                    action, recips = "operator", []
                    note = ("Niciun notar în dosar. Propunere pentru operator: banca, dacă e creditor al succesiunii "
                            "(credit nerambursat), poate cere deschiderea procedurii succesorale sau inventarul "
                            "(Legea 36/1995 art. 103 alin. 3, art. 104 alin. 4)." if dossier.get("has_loan") else
                            "Niciun notar în dosar și niciun credit: banca nu e creditor al succesiunii. Propunere: "
                            "operatorul verifică dacă procedura s-a deschis (registrul Camerei / RNNES, prin notar).")
            else:
                recips = _recipients(persons, action)
                if not recips:
                    if code == "INITIAL":
                        wait = True   # DGEP does not name the heirs: wait for a contact, escalate at the next step
                        note = "Nicio persoană de contact încă (semnalul DGEP nu dă moștenitorii)."
                    else:
                        action = "operator"
                        note = ("Nicio persoană cu canal permis (" + ("domiciliu" if code == "REGISTERED_LETTER" else
                                "e-mail / aplicație") + "). Operatorul caută un contact"
                                + (f" sau trece direct la notar ({notary.get('name') or notary.get('office')})." if notary else "."))
            s = _step(code, "principal", label, due, action, basis, template if action == "message" else None, recips, note)
            s["wait_without_channel"] = wait
            s["missing"] = main_missing
            steps.append(s)
            if code in done:
                prev_done, prev_off = _d(done[code].get("at")) or due, off
    elif done:
        # nothing left to bring: keep the history of what was done, drop the rest
        steps += [{**_step(code, "principal", label, _d(done[code].get("at")) or since, action, basis, template),
                   "missing": []} for code, _off, action, template, label, basis in MAIN_STEPS if code in done]

    if dod and cert_on is None:
        warn_due, exp_due = add_months(dod, 10), add_months(dod, 12)
        recips = _recipients(persons, "message")
        steps.append(_step("DEADLINE_WARNING", "termen", "Avertizare: se apropie termenul de 1 an", warn_due,
                           "message" if recips else "operator", DEADLINE_BASIS, "DEADLINE_SOON" if recips else None,
                           recips, f"Termenul de opțiune (implicit) se împlinește pe {exp_due.isoformat()}."
                           + ("" if recips else " Nicio persoană cu canal permis: operatorul anunță notarul / familia.")))
        steps.append(_step("OPTION_EXPIRED", "termen", "După termen: prezumată renunțarea / posibil vacantă", exp_due,
                           "operator", EXPIRED_BASIS, None, [],
                           "Fondurile rămân în cont, blocate, fără comisioane; nimic nu se transferă fără certificat de "
                           "moștenitor sau de vacanță succesorală. Operatorul decide (de ex. cerere către notar)."))
    elif dod:   # the certificate arrived (the heirs accepted): keep only the history of the deadline track
        steps += [_step(code, "termen", label, _d(done[code].get("at")) or since, action, basis)
                  for code, label, action, basis in (("DEADLINE_WARNING", "Avertizare: se apropie termenul de 1 an",
                                                      "message", DEADLINE_BASIS),
                                                     ("OPTION_EXPIRED", "După termen: prezumată renunțarea / posibil "
                                                      "vacantă", "operator", EXPIRED_BASIS)) if code in done]

    for p in persons:
        if not p.get("minor") or not any(is_minor_item(m) and p["name"].lower() in m.lower() for m in missing):
            continue
        rep = _representative(persons, p.get("representative_id"))
        recips = [{"id": rep.get("id"), "name": rep["name"], "role": "legal_representative", "channel": ch,
                   "for_minor": p["name"]} for ch in [permitted_channel(rep) if rep else None] if ch]
        track, start = f"minor:{p.get('id')}", max(d for d in (since, cert_on) if d)
        out["blocked"].append({"heir": p["name"], "reason": "minor: plata părții lui blocată până la documentele "
                               "reprezentantului legal", "basis": MINOR_BASIS})
        k, prev = 0, None
        while True:
            code = f"MINOR_INITIAL:{p.get('id')}" if k == 0 else f"MINOR_REMINDER_{k}:{p.get('id')}"
            due = start if k == 0 else add_months(prev, 1)
            label = (f"Mesaj către reprezentantul legal al lui {p['name']}" if k == 0 else
                     f"Reminder lunar {k} către reprezentantul legal al lui {p['name']}")
            s = _step(code, track, label, due, "message" if recips else "operator", MINOR_BASIS,
                      "MINOR_REPRESENTATION" if recips else None, recips,
                      "" if recips else "Reprezentantul legal nu are un canal permis: operatorul îl contactează.")
            s["missing"] = [m for m in missing if is_minor_item(m)]
            steps.append(s)
            if code not in done:
                break
            prev, k = _d(done[code].get("at")) or due, k + 1

    _resolve(steps, done, today)
    steps.sort(key=lambda s: (s["due"], {"principal": 0, "termen": 1}.get(s["track"], 2)))
    out["steps"] = steps
    out["due_now"] = [s for s in steps if s["status"] == "due"]
    pending = [s for s in steps if s["status"] in ("due", "upcoming", "waiting")]
    out["next"] = pending[0] if pending else None
    out["active"] = bool(pending)
    if not steps:
        out["summary"] = "Nu lipsește nimic din ce pot aduce moștenitorii: nu e nevoie de scara de contact."
    elif out["next"]:
        n = out["next"]
        out["summary"] = f"Pasul următor: {n['label']} ({n['status_label']}, {n['due']})."
    else:
        out["summary"] = "Toți pașii scării au fost făcuți."
    return out
