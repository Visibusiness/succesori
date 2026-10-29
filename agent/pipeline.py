"""Document -> case actions. Deterministic orchestration over the pure rules.

Every incoming document is a dict with at least:
  {"document_type": <type>, "fields": {...}, "confidence": 0..1, "id": "...", "received_on": "YYYY-MM-DD"}
Types: dgep_signal | notary_request | insurance_certificate | heir_certificate |
       insurer_response | supplementary_certificate | death_certificate | unknown
Low confidence or inconsistent data never acts on the bank: it escalates.
"""
from __future__ import annotations

import threading
from datetime import date
from fractions import Fraction
from typing import Any

from agent import guard, insurers, rules
from agent.case_state import Case, Document
from agent.core_mock import Bank

CONFIDENCE_THRESHOLD = 0.80
REVERSIBLE_ONLY_SOURCES = {"dgep_signal", "notary_request"}  # D-DGEP: definitiv doar cu certificat de deces sau operator


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _frac(s: str | int | float) -> Fraction:
    return Fraction(str(s))


def _is_spouse_quality(q: str | None) -> bool:
    """„soț supraviețuitor”, „soție supraviețuitoare”, „sot_supravietuitor”, „soțul” … (diacritics and case ignored)."""
    if not q:
        return False
    s = q.lower().replace("ț", "t").replace("ţ", "t").replace("_", " ").split()
    return bool(s) and s[0] in ("sot", "sotul", "sotie", "sotia")


class Pipeline:
    def __init__(self, bank: Bank):
        self.bank = bank
        self.cases: dict[str, Case] = {}
        # 089: one document at a time (083: two threads lost 7% of the documents, `dict changed size during iteration`
        # and duplicate SC-2026-NNNN ids). Reentrant, so the API can hold it around receive + trace.
        self.lock = threading.RLock()
        # 089: cif -> case id (083: `_case_for` scanned every case for every document). Rebuilt when `cases` is changed
        # from outside (the API's reset clears it); a hit is checked against the case itself.
        self._by_cif: dict[str, str] = {}
        self._indexed = -1

    # ------------------------------------------------------------ entry
    def receive(self, doc: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            return self._receive(doc)

    def _receive(self, doc: dict[str, Any]) -> dict[str, Any]:
        dtype = doc.get("document_type", "unknown")
        fields = doc.get("fields", {})
        conf = float(doc.get("confidence", 0))
        doc_id = doc.get("id") or f"doc-{len(self._all_docs()) + 1}"
        received = doc.get("received_on") or date.today().isoformat()

        # 0. 076: a document that tries to steer the agent (or a dangerous file) acts on nothing: quarantine + human.
        # Before every other gate, so not even a case is opened for it.
        risk = guard.verdict(doc)
        if risk["risk"] == "high":
            return self._quarantine(doc, doc_id, dtype, received, conf, risk)

        # 1. legibility / confidence gate (a document without CNP may still identify the person by name + birth date)
        no_identity = not fields.get("cnp") and not (fields.get("name") and fields.get("birth_date"))
        if dtype == "unknown" or conf < CONFIDENCE_THRESHOLD or no_identity:
            return self._orphan(doc, doc_id, dtype, received, conf, "document_illegible",
                                f"Document „{doc.get('raw_name') or doc_id}” ilizibil sau incomplet "
                                f"(tip={dtype}, încredere={conf:.2f}, CNP={'lipsă' if not fields.get('cnp') else 'ok'}). "
                                "Nicio acțiune automată; operatorul decide.")

        # 2. identify the customer
        if fields.get("cnp"):
            customer = self.bank.find_customer(cnp=fields["cnp"])
            if not customer:
                other = self._case_by_file(fields.get("case_file") or fields.get("reference"))
                if other:   # H4: same succession file, different CNP -> never match on the file number alone
                    return self._orphan(doc, doc_id, dtype, received, conf, "cnp_mismatch",
                                        f"CNP-ul din document ({fields['cnp']}) diferă de al clientului din dosarul "
                                        f"{other.id} (dosar succesoral {fields.get('case_file') or fields.get('reference')}). "
                                        "Documentul nu se atașează; se cere notarului verificarea (409).")
                return self._orphan(doc, doc_id, dtype, received, conf, "customer_not_found",
                                    "CNP din document nu corespunde niciunui client. Răspuns propus: „nu este client”.")
            identity_note = None
        else:
            customer, problem = self._identify_without_cnp(fields)
            if problem:
                return self._orphan(doc, doc_id, dtype, received, conf, "identity_unconfirmed", problem)
            identity_note = (f"Identitate fără CNP: potrivire unică nume + data nașterii ({fields['name']}, "
                             f"{fields['birth_date']}) cu {customer['cif']}, confirmată de data decesului și de soț.")

        case = self._case_for(customer)
        if identity_note:
            case.log("decision", identity_note, rule="H10: nume + prenume + data nașterii, coroborate; altfel identity_unconfirmed",
                     document_id=doc_id, flag="identity_by_name_birthdate")
        self._log_validation(case, doc, doc_id)
        ref = fields.get("document_number") or fields.get("reference") or fields.get("cnp")
        key = f"{dtype}:{ref}:{fields.get('date_of_death', '')}"
        if key in case.processed_document_keys:
            case.log("decision", f"Document duplicat ignorat ({dtype}); idempotent.", document_id=doc_id)
            return {"case_id": case.id, "state": case.state(), "duplicate": True, "actions": []}
        case.processed_document_keys.add(key)
        case.documents.append(Document(doc_id, dtype, received, conf, fields, doc.get("raw_name")))
        case.log("document", f"Primit: {dtype} ({doc.get('raw_name') or doc_id}), încredere {conf:.2f}", document_id=doc_id)

        handler = getattr(self, f"_on_{dtype}", None)
        n_esc = len(case.escalations)
        if handler is None:
            case.escalate("unsupported_document", f"Tip de document netratat: {dtype}", doc_id)
            actions = []
        else:
            actions = handler(case, fields, _d(received) or date.today(), doc_id)
        out = {"case_id": case.id, "state": case.state(), "actions": actions, "missing": case.missing()}
        # escalations raised inside the case (shares_invalid, insurance_refused, indemnity_mismatch, mandate withdrawal…)
        # are named in the answer too, so the autopilot hands each one to case-investigator (not only orphan ones)
        if risk["risk"] == "medium":   # processed, but the operator is told what looked odd
            case.escalate("suspicious_document",
                          f"[informativ] Documentul „{doc.get('raw_name') or doc_id}” a fost procesat, dar are semne de "
                          f"verificat: {guard.reasons_ro(risk['flags'])}.", doc_id,
                          data={"severity": "info", "flags": risk["flags"], "quarantined": False})
        new = case.escalations[n_esc:]
        if new:
            out.update({"escalation": new[0].id, "escalation_reason": new[0].reason, "escalations": [e.id for e in new]})
        return out

    # ------------------------------------------------------------ handlers
    def _on_dgep_signal(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        ref = f.get("document_number") or f.get("reference") or doc_id
        return self._death_known(case, _d(f["date_of_death"]), received, source="dgep_signal",
                                 trigger=f"semnal DGEP {ref} (GDPR art. 22: doar măsuri reversibile)")

    def _on_death_certificate(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        series_no = " ".join(x for x in (f.get("document_series"), f.get("document_number") and f"nr. {f['document_number']}") if x)
        trigger = f"certificat de deces {series_no}".strip()
        was_reversible = bool((self.bank.customers[case.cif].get("frozen") or {}).get("reversible"))
        acts = self._death_known(case, _d(f["date_of_death"]), received, source="death_certificate", trigger=trigger)
        if was_reversible:   # only a reversible block is upgraded; a fresh definitive freeze was already logged above
            acts += self._definitive_freeze(case, trigger)
        return acts

    def confirm_freeze(self, case_id: str, operator: str) -> dict[str, Any]:
        """D-DGEP: an operator may make a reversible block definitive (e.g. after checking the death in person)."""
        with self.lock:
            return self._confirm_freeze(case_id, operator)

    def _confirm_freeze(self, case_id: str, operator: str) -> dict[str, Any]:
        case = self.cases[case_id]
        if "frozen" not in case.milestones or case.date_of_death is None:
            raise ValueError("dosarul nu are o blocare de confirmat")
        if not (self.bank.customers[case.cif].get("frozen") or {}).get("reversible"):
            raise ValueError("blocarea e deja definitivă")
        self._definitive_freeze(case, f"operator {operator}")
        return {"case_id": case_id, "freeze": "definitive", "by": operator}

    def _on_notary_request(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        acts: list[str] = []
        dod = _d(f.get("date_of_death")) or case.date_of_death
        if dod is None:
            case.escalate("missing_date_of_death", "Adresa notarului nu conține data decesului și nu avem semnal anterior.", doc_id)
            return acts
        num = f.get("document_number") or ""
        num = f"{num}/{received.year}" if num and "/" not in num else num
        trigger = f"adresa notarului nr. {num}" if num else f"adresa notarului (dosar {f.get('case_file') or f.get('reference')})"
        acts += self._death_known(case, dod, received, source="notary_request", trigger=trigger)
        hearing = _d(f.get("hearing_date"))
        case.deadlines = [d.__dict__ | {"due": d.due.isoformat()} for d in rules.deadlines(dod, case.learned_on or received, hearing, case.insurance.get("insurer"))]
        valued = rules.balance_at_death(self.bank.products(case.cif), dod)
        movements = self.bank.movements(case.cif)
        answer = {
            "notary_file": f.get("case_file") or f.get("reference"),
            "as_of": dod.isoformat(),
            "products": [v.__dict__ | {"total": v.total} for v in valued],
            "post_death_credits": [fl.__dict__ | {"movement": fl.movement.__dict__ | {"date": fl.movement.date.isoformat()}}
                                   for fl in rules.pension_flags(movements, dod)],
            "mandate_withdrawals": [fl.amount for fl in rules.mandate_withdrawals(movements, dod)],
            "loan_insurance": [p.insurance_policy_id for p in self.bank.products(case.cif) if p.insurance_policy_id],
            "status": "draft_pending_signature",
        }
        case.insurance.setdefault("policies", answer["loan_insurance"])
        case.milestones.add("notary_answered")
        case.log("action", f"Răspuns către notar generat (dosar {answer['notary_file']}): solduri la {dod}; trimis la semnare.",
                 rule="Legea 36/1995 art. 81 alin. 2", answer=answer)
        acts.append("notary_answer_drafted")
        if answer["mandate_withdrawals"] and not any(e.reason == "post_death_mandate_withdrawal" for e in case.escalations):
            case.escalate("post_death_mandate_withdrawal",
                          f"Retrageri de împuternicit după deces: {sum(answer['mandate_withdrawals'])/100:.2f} lei; raportate notarului.", doc_id)
        return acts

    def _on_insurance_certificate(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        loans = [p for p in self.bank.products(case.cif) if p.type == "personal_loan"]
        by_contract = self.bank.product_by_loan_contract(case.cif, f["loan_contract"]) if f.get("loan_contract") else None
        policy_ok = any(p.insurance_policy_id == f.get("policy_id") and (by_contract in (None, p.id)) for p in loans)
        if not policy_ok:
            case.escalate("policy_mismatch", f"Polița {f.get('policy_id')} nu e atașată niciunui credit al clientului.", doc_id)
            return []
        ins = insurers.lookup(f.get("insurer"))
        case.insurance.update({"policy_id": f["policy_id"], "insurer": f.get("insurer"), "claim_open": True,
                               "claim_opened_on": received.isoformat(), "insurer_key": ins.key,
                               "claim_documents": ins.heir_documents(), "payment_term": ins.payment.label})
        case.milestones.add("insurance_claim_open")
        notice = None
        if case.date_of_death:
            notice = rules.insurance_notice_deadline(case.date_of_death, case.learned_on or received, f.get("insurer"))
            case.deadlines = [d for d in case.deadlines if d["code"] != "insurance_claim_notice"]
            if notice:
                case.deadlines.append(notice.__dict__ | {"due": notice.due.isoformat()})
        if notice:
            term, rule = f"avizare până la {notice.due.isoformat()}", notice.basis
        else:
            term, rule = "termen de avizare necunoscut, de confirmat cu banca", f"{ins.name}: termen de avizare nepublicat"
        case.log("action", f"Dosar de daună deschis la {f.get('insurer') or ins.name} pentru polița {f['policy_id']}; {term}. "
                           f"Documente cerute moștenitorilor: {'; '.join(ins.heir_documents())}.",
                 rule=rule, insurer=ins.key, hypothesis=bool(notice and notice.hypothesis))
        return ["insurance_claim_opened"]

    def _on_insurer_response(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        if f.get("decision") != "approved":
            case.insurance.update({"settled": False, "refused_reason": f.get("reason")})
            case.escalate("insurance_refused", f"Asigurătorul a refuzat: {f.get('reason')}. Datoria rămâne în masa succesorală; moștenitorii informați (pot renunța).", doc_id)
            # 089: the plan waited for this answer; with the refusal the whole debt stays in the estate and the plan is
            # made now (before, only the approval branch made it, so the result depended on the order of documents)
            self._try_payment_plan(case, received, doc_id)
            return ["insurance_refused"]
        paid = int(f["amount"])
        # indemnity = principal outstanding at D (+ at most 3 overdue instalments, condiții UNIQA); anything else
        # is escalated, never applied (Ștefan's proposal, 039)
        loan = next((p for p in self.bank.products(case.cif) if p.type == "personal_loan"
                     and (not f.get("policy_id") or p.insurance_policy_id == f.get("policy_id"))), None)
        if loan is not None:
            low, high = loan.outstanding, loan.outstanding + 3 * (self.bank.installment(case.cif, loan.id) or 0)
            if not low <= paid <= high:
                case.escalate("indemnity_mismatch",
                              f"Indemnizația din răspuns ({paid/100:.2f} lei) nu corespunde principalului la data decesului "
                              f"({low/100:.2f} lei" + (f" + max. 3 rate = {high/100:.2f} lei" if high > low else "")
                              + "). Nu se aplică; se verifică cu asigurătorul.", doc_id)
                return ["indemnity_mismatch"]
        # what the indemnity does not cover (interest accrued to D) stays a debt of the estate: computed here, at doc 5, so
        # the correspondent's note to the notary has the figure (QA: before, it existed only in the plan, after doc 6)
        remaining = None
        if case.date_of_death is not None:
            valued = rules.balance_at_death(self.bank.products(case.cif), case.date_of_death)
            remaining = max(-sum(v.total for v in valued if v.type == "personal_loan") - paid, 0)
        case.insurance.update({"settled": True, "paid": paid, "settled_on": received.isoformat(), "remaining_debt": remaining})
        case.milestones.add("insurance_settled")
        self.bank.settle_loan(case.cif, paid)
        case.log("action", f"Indemnizație primită: {paid/100:.2f} lei; creditul stins de asigurător."
                 + (f" Rămâne în sarcina masei succesorale: {remaining/100:.2f} lei (dobânda la data decesului, neacoperită)."
                    if remaining else ""), rule="C.civ. art. 1114", indemnity_bani=paid, remaining_debt_bani=remaining)
        self._try_payment_plan(case, received, doc_id)
        return ["loan_settled_by_insurance"]

    def _on_heir_certificate(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        # The LLM extractor does not invent ids: number the heirs in certificate order (H1 = first listed).
        heirs = [{"id": h.get("id") or f"H{i + 1}", "name": h.get("name") or f"Moștenitor {i + 1}",
                  "share": str(_frac(h["share"])), "minor": bool(h.get("minor")),
                  "legal_representative": h.get("legal_representative"),
                  "relationship": h.get("relationship")} for i, h in enumerate(f.get("heirs", []))]
        try:
            rules.validate_shares([rules.Heir(h["id"], h["name"], _frac(h["share"]), h["minor"], h["legal_representative"]) for h in heirs])
        except ValueError as e:
            case.escalate("shares_invalid", f"Cotele din certificat nu însumează 1 ({e}). Niciun plan de plată.", doc_id)
            return []
        case.heirs = heirs
        case.milestones.add("certificate_received")
        case.log("document", "Certificat de moștenitor: " + ", ".join(f"{h['name']} {h['share']}" for h in heirs),
                 rule="cotele vin din certificat, nu din lege", testament=bool(f.get("testament")))
        acts = ["heirs_recorded"]
        for h in heirs:
            if h["minor"]:
                case.escalate("minor_heir", f"{h['name']} este minor (sub 18 ani): plata părții sale se blochează până la acordul scris al reprezentantului legal (C.civ. art. 41, 144-146).", doc_id)
        self._record_contacts(case)
        products, ok = self._doc_products(case, f, doc_id)
        if not ok:
            return acts
        acts += self._check_coverage(case, products, doc_id, received)
        return acts

    def _on_supplementary_certificate(self, case: Case, f: dict, received: date, doc_id: str) -> list[str]:
        if not case.heirs:
            case.escalate("supplement_without_certificate", "Supliment primit înainte de certificatul de moștenitor.", doc_id)
            return []
        products, ok = self._doc_products(case, f, doc_id)
        if not ok:
            return []
        known = set(self._certified_products(case)) | set(products)
        return self._check_coverage(case, sorted(known), doc_id, received)

    # ------------------------------------------------------------ shared steps
    def _death_known(self, case: Case, dod: date | None, received: date, source: str, trigger: str = "") -> list[str]:
        acts: list[str] = []
        if dod is None:
            return acts
        if case.date_of_death is None:
            case.date_of_death, case.learned_on = dod, received
            case.milestones.add("death_signalled")
            case.log("document", f"Deces confirmat la data {dod} (sursă: {source}); aflat la {received}.")
        if "frozen" not in case.milestones:
            res = self.bank.freeze(case.cif, dod, reversible=source in REVERSIBLE_ONLY_SOURCES)
            case.milestones.add("frozen")
            case.log("action", ("Blocare reversibilă" if res["reversible"] else "Blocare definitivă") +
                     f": {trigger or source}. Debit oprit, mandat suspendat ({', '.join(res['suspended_mandates']) or 'niciunul'}), "
                     f"carduri {', '.join(res['cards']) or '-'}, debitări directe și comision suspendate.",
                     rule="CGB 3.2.5 b/d, 5.10.4 c, 7.7.1 c; C.civ. art. 2030; D-DGEP: semnal DGEP sau adresă de notar ⇒ doar "
                          "reversibil, definitiv doar la certificat de deces sau prin operator (GDPR art. 22)",
                     trigger=trigger, reversible=res["reversible"])
            acts.append("frozen")
            case.deadlines = [d.__dict__ | {"due": d.due.isoformat()} for d in rules.deadlines(dod, received, insurer=case.insurance.get("insurer"))]
        if "fees_reversed" not in case.milestones:
            flags = rules.fees_to_reverse(self.bank.movements(case.cif), dod)
            total = self.bank.reverse_fees(case.cif, [(f.movement.date, f.amount) for f in flags])
            case.milestones.add("fees_reversed")
            case.flags += [{"code": f.code, "amount": f.amount, "date": f.movement.date.isoformat()} for f in flags]
            case.log("action", f"Comisioane după deces stornate: {total/100:.2f} lei ({len(flags)} mișcări).",
                     rule="comision de administrare nejustificat după deces (cazul Bragadiru 2023)")
            acts.append("fees_reversed")
        for fl in rules.mandate_withdrawals(self.bank.movements(case.cif), dod):
            entry = {"code": fl.code, "amount": fl.amount, "date": fl.movement.date.isoformat()}
            if entry not in case.flags:
                case.flags.append(entry)
                case.escalate("post_death_mandate_withdrawal",
                              f"Retragere a împuternicitului după deces ({fl.movement.date}): {fl.amount/100:.2f} lei; "
                              "mandatul a încetat la deces, suma se raportează notarului ca element de recuperat.")
        for fl in rules.pension_flags(self.bank.movements(case.cif), dod):
            entry = {"code": fl.code, "amount": fl.amount, "date": fl.movement.date.isoformat()}
            if entry not in case.flags:
                case.flags.append(entry)
                if fl.code == "pension_return_CNPP":
                    case.log("action", f"Pensie necuvenită ({fl.movement.date}): {fl.amount/100:.2f} lei reținuți pentru retur CNPP.",
                             rule="Legea 360/2023 art. 100, art. 156 alin. 8")
        return acts

    def _definitive_freeze(self, case: Case, trigger: str) -> list[str]:
        self.bank.freeze(case.cif, case.date_of_death, reversible=False)
        case.log("action", f"Blocare confirmată definitiv de {trigger}: cardurile închise, mandatul revocat.",
                 rule="CGB 5.10.4 c; C.civ. art. 2030; D-DGEP", trigger=trigger, reversible=False)
        return ["freeze_definitive"]

    def _certified_products(self, case: Case) -> list[str]:
        out: list[str] = []
        for d in case.documents:
            if d.type in ("heir_certificate", "supplementary_certificate"):
                out += d.fields.get("_matched_products", d.fields.get("products", []))
        return out

    def _check_coverage(self, case: Case, certified: list[str], doc_id: str, on: date) -> list[str]:
        bank_ids = [p.id for p in self.bank.products(case.cif) if p.type not in rules.DEBT_TYPES]
        gaps = rules.coverage_gaps(bank_ids, certified)
        case.coverage_gaps = gaps
        if gaps:
            case.milestones.add("supplement_requested")
            case.log("action", f"Certificatul nu acoperă: {', '.join(gaps)}. Cerere de certificat suplimentar generată către notar.",
                     rule="practica notarială: supliment la certificatul de moștenitor")
            return ["supplement_requested"]
        case.milestones.add("coverage_complete")
        case.log("decision", "Toate produsele sunt acoperite de certificat(e).")
        self._try_payment_plan(case, on, doc_id)
        return ["coverage_complete"]

    def _spouse(self, case: Case) -> tuple[str | None, str | None]:
        """089: the surviving spouse is the heir the certificate names as such („soț supraviețuitor”), never the one on
        the first row. If no heir carries a quality (the demo extraction has none), the spouse is the heir whose name
        matches the spouse known in core (KYC). Returns (heir id or None, problem or None)."""
        from agent.core_mock import _person_key
        named = [h["id"] for h in case.heirs if _is_spouse_quality(h.get("relationship"))]
        if len(named) > 1:
            return None, f"{len(named)} moștenitori au calitatea de soț supraviețuitor în certificat ({', '.join(named)})"
        if named:
            return named[0], None
        if all(h.get("relationship") for h in case.heirs):
            return None, "niciun moștenitor nu are în certificat calitatea de soț supraviețuitor"
        known = (self.bank.customers.get(case.cif) or {}).get("spouse")
        by_name = [h["id"] for h in case.heirs if known and not h.get("relationship")
                   and _person_key(h["name"]) == _person_key(known)]
        if len(by_name) == 1:
            return by_name[0], None
        return None, ("certificatul nu arată calitatea moștenitorilor, iar soțul din evidențe "
                      + (f"({known}) nu e printre ei" if known else "lipsește"))

    def _try_payment_plan(self, case: Case, on: date, doc_id: str | None = None) -> None:
        """`on` is the date of the document that completes the plan (a matured deposit is payable from it)."""
        if "coverage_complete" not in case.milestones or not case.heirs or case.date_of_death is None:
            return
        if case.insurance.get("claim_open") and "settled" not in case.insurance:
            case.log("decision", "Plan de plată amânat: așteptăm răspunsul asigurătorului.")
            return
        if case.payment_plan and case.payment_plan["status"] != "pending_approval":
            case.log("decision", f"Planul {case.payment_plan['id']} e deja {case.payment_plan['status']}: nu se reface.")
            return
        dod = case.date_of_death
        products = self.bank.products(case.cif)
        valued = rules.balance_at_death(products, dod)
        heirs = [rules.Heir(h["id"], h["name"], _frac(h["share"]), h["minor"], h["legal_representative"]) for h in case.heirs]
        spouse = None
        if any(p.estate_fraction != 1 for p in products if p.type != "personal_loan"):
            spouse, problem = self._spouse(case)
            if spouse is None:   # the owner's half of a common good can't be given to anyone by guess: no plan
                if not any(e.reason == "spouse_unidentified" for e in case.escalations):
                    case.escalate("spouse_unidentified",
                                  f"Bunuri comune, dar soțul supraviețuitor nu poate fi identificat: {problem}. Jumătatea de "
                                  "proprietar nu se atribuie din poziția în certificat; niciun plan de plată până confirmă "
                                  "operatorul (C.civ. art. 339, 343).", doc_id)
                return
        net = rules.net_of_debts(valued, self.bank.movements(case.cif), dod, insurance_paid=case.insurance.get("paid", 0))
        unpaid = net.unpaid_debt   # debt above the current account: taken from the deposits, in the core's order
        lines = []
        for p in products:
            if p.type == "current_account":
                lines += rules.split_by_shares(heirs, p.id, net.net, p.estate_fraction, surviving_spouse_id=spouse)
            elif p.type == "term_deposit":
                gross = p.principal + rules.accrued_simple_interest(p.principal, p.rate_pct, (p.maturity - p.start).days)
                taken = min(unpaid, gross)
                unpaid -= taken
                matured = p.maturity <= on
                for l in rules.split_by_shares(heirs, p.id, gross - taken, p.estate_fraction, surviving_spouse_id=spouse):
                    lines.append(rules.PaymentLine(l.heir_id, l.name, l.product_id, l.fraction_of_product, l.amount,
                                                   l.blocked_reason or (None if matured else f"depozit nescadent până la {p.maturity}: plată la scadență (lichidarea anticipată pierde dobânda)")))
        if net.unpaid_debt:
            case.log("decision", f"Datoria peste contul curent ({net.unpaid_debt/100:.2f} lei) se scade din depozit"
                     + (f"; rămân neacoperiți {unpaid/100:.2f} lei." if unpaid else "."),
                     rule="C.civ. art. 1114: moștenitorii răspund în limita activului", debt_from_deposit=net.unpaid_debt - unpaid)
        if unpaid and not any(e.reason == "debt_exceeds_estate" for e in case.escalations):
            case.escalate("debt_exceeds_estate",
                          f"[informativ] Pasivul depășește activul de la bancă: {unpaid/100:.2f} lei din datorie rămân "
                          "neacoperiți după cont și depozit. Moștenitorii răspund doar în limita activului (C.civ. art. "
                          "1114); recuperarea restului se decide de operator, nu din plan.", doc_id,
                          data={"severity": "info", "unpaid_debt": unpaid})
        plan = {
            "id": f"PP-{case.id}",
            "status": "pending_approval",
            "net_account": net.__dict__,
            "withheld": [{"reason": "pension_return_CNPP", "amount": net.withheld}] if net.withheld else [],
            "lines": [l.__dict__ | {"fraction_of_product": str(l.fraction_of_product)} for l in lines],
        }
        case.payment_plan = plan
        case.milestones.add("payment_plan_ready")
        case.milestones.add("payment_pending_approval")
        payable = sum(l.amount for l in lines if l.blocked_reason is None)
        case.log("action", f"Plan de plată generat: {len(lines)} linii, {payable/100:.2f} lei plătibili acum; așteaptă aprobare umană.",
                 rule="C.civ. art. 1114, 2187; plata = acțiune ireversibilă ⇒ aprobare operator")

    def approve_payment(self, case_id: str, approver: str) -> dict[str, Any]:
        with self.lock:   # two approvals of the same plan never both pay
            case = self.cases[case_id]
            if not case.payment_plan or case.payment_plan["status"] != "pending_approval":
                raise ValueError("no plan pending approval")
            paid = [l for l in case.payment_plan["lines"] if l["blocked_reason"] is None]
            if any(l["amount"] < 0 for l in case.payment_plan["lines"]):   # 089: never a payment with a negative amount
                raise ValueError("planul are o linie cu sumă negativă; nu se plătește")
            self.bank.pay(case.cif, [(l["product_id"], l["amount"]) for l in paid])
            case.payment_plan["status"] = "approved"
            case.payment_plan["approved_by"] = approver
            case.milestones.add("paid")
            case.log("decision", f"Plata aprobată de {approver}: {sum(l['amount'] for l in paid)/100:.2f} lei către {len(paid)} moștenitori; "
                     f"{len(case.payment_plan['lines']) - len(paid)} linii rămân blocate.")
            return case.payment_plan

    # ------------------------------------------------------------ helpers
    def _quarantine(self, doc: dict[str, Any], doc_id: str, dtype: str, received: str, conf: float,
                    risk: dict[str, Any]) -> dict[str, Any]:
        """076: no handler, no freeze, no letter, no message, no case opened. The document is kept (type `quarantined`,
        outside coverage / idempotency / file matching) in the case of the client it names, if that case already
        exists, else among the unidentified documents; the escalation carries the flags and the quotes."""
        fields = doc.get("fields") if isinstance(doc.get("fields"), dict) else {}
        cnp = fields.get("cnp") or risk.get("cnp_hint")
        customer = self.bank.find_customer(cnp=cnp) if isinstance(cnp, str) else None
        case = (self._case_of(customer["cif"]) if customer else None) or self._orphan_case()
        case.documents.append(Document(doc_id, "quarantined", received, conf, dict(fields), doc.get("raw_name")))
        detail = (f"Document „{doc.get('raw_name') or doc_id}” pus în carantină (tip declarat/extras: {dtype}): "
                  f"{guard.reasons_ro(risk['flags'])}. Nicio acțiune automată (blocare, scrisori, mesaje, plată); "
                  "un operator verifică documentul la sursă.")
        esc = case.escalate("suspicious_document", detail, doc_id,
                            data={"severity": "blocking", "flags": risk["flags"], "quarantined": True, "declared_type": dtype})
        return {"case_id": case.id, "state": case.state(), "escalation": esc.id, "escalation_reason": "suspicious_document",
                "escalations": [esc.id], "actions": [], "quarantined": True, "guard": {"risk": "high", "flags": risk["flags"]}}

    def _orphan(self, doc: dict[str, Any], doc_id: str, dtype: str, received: str, conf: float,
                reason: str, detail: str) -> dict[str, Any]:
        case = self._orphan_case()
        case.documents.append(Document(doc_id, dtype, received, conf, doc.get("fields", {}), doc.get("raw_name")))
        self._log_validation(case, doc, doc_id)
        esc = case.escalate(reason, detail, doc_id)
        return {"case_id": case.id, "state": case.state(), "escalation": esc.id, "escalation_reason": reason, "actions": []}

    def _case_by_file(self, case_file: str | None) -> Case | None:
        if not case_file:
            return None
        for c in self.cases.values():
            if any(case_file in (d.fields.get("case_file"), d.fields.get("reference")) for d in c.documents
                   if d.type != "quarantined"):
                return c
        return None

    def _identify_without_cnp(self, f: dict) -> tuple[dict | None, str | None]:
        """H10/H11: a unique customer with the same name + birth date, not contradicted by the case on file
        (date of death, spouse). Parents are not in core, so they are never used."""
        from agent.core_mock import _person_key
        cands = self.bank.find_by_name_birth(f["name"], f["birth_date"])
        if len(cands) != 1:
            return None, (f"Fără CNP: {len(cands)} clienți cu numele {f['name']} și data nașterii {f['birth_date']}. "
                          "Nicio acțiune automată.")
        cust = cands[0]
        conflicts = []
        existing = self._case_of(cust["cif"])
        dod = _d(f.get("date_of_death"))
        if existing and existing.date_of_death and dod and dod != existing.date_of_death:
            conflicts.append(f"data decesului {dod} ≠ {existing.date_of_death} din dosar")
        if f.get("spouse") and cust.get("spouse") and _person_key(f["spouse"]) != _person_key(cust["spouse"]):
            conflicts.append(f"soțul {f['spouse']} ≠ {cust['spouse']} din evidențe")
        if conflicts:
            return None, (f"Fără CNP: {f['name']} ({f['birth_date']}) seamănă cu {cust['cif']}, dar: " + "; ".join(conflicts)
                          + ". Documentul nu se atașează și dosarul nu se schimbă.")
        return cust, None

    def _doc_products(self, case: Case, f: dict, doc_id: str) -> tuple[list[str], bool]:
        """Products cited by a certificate -> internal ids. IBANs first (exact), then the deprecated `products`,
        then H5: a product described only by type + amount matches if it is the client's only one of that type."""
        out = list(f.get("products") or [])
        for iban in f.get("ibans") or []:
            pid = self.bank.product_by_iban(case.cif, iban)
            if pid:
                out.append(pid)
            elif iban.replace(" ", "").upper()[4:8] == "RZBR":
                case.escalate("product_unknown", f"IBAN-ul {iban} din certificat nu e un produs al clientului.", doc_id)
                return [], False
            else:
                case.log("decision", f"IBAN {iban} la altă bancă: ignorat pentru planul de plată.", document_id=doc_id)
        for u in f.get("unidentified_products") or []:
            same_type = [p.id for p in self.bank.products(case.cif) if p.type == u.get("type")]
            if len(same_type) != 1:
                case.escalate("product_ambiguous", f"Produs fără IBAN ({u.get('type')}, {u.get('amount')}): "
                              f"{len(same_type)} candidați; potrivirea cere operatorul.", doc_id)
                return [], False
            out.append(same_type[0])
            case.flags.append({"code": "matched_without_iban", "product_id": same_type[0], "amount": u.get("amount")})
            case.log("decision", f"Produs fără IBAN potrivit după tip + sumă: {same_type[0]} (singurul {u.get('type')}).",
                     rule="potrivire unică tip + sumă; două produse de același tip ⇒ escaladare", document_id=doc_id,
                     flag="matched_without_iban")
        out = sorted(set(out))
        doc = next((d for d in reversed(case.documents) if d.id == doc_id), None)
        if doc:
            doc.fields["_matched_products"] = out
        return out, True

    def _record_contacts(self, case: Case) -> None:
        """Preferred channel + verified contact per heir (operational messages, DECISIONS 034). A minor is
        reached through the legal representative."""
        for h in case.heirs:
            via = h.get("legal_representative") if h.get("minor") else None
            who = next((x["name"] for x in case.heirs if x["id"] == via), h["name"]) if via else h["name"]
            c = self.bank.contact(who) or {}
            case.contact_channels[h["id"]] = {"name": h["name"], "via": via, "preferred": c.get("preferred", "email"),
                                              "email": c.get("email"), "sms": c.get("sms"),
                                              "verified": bool(c.get("verified")), "is_client": bool(c.get("is_client"))}

    def _log_validation(self, case: Case, doc: dict[str, Any], doc_id: str) -> None:
        """Extractor validations (agent/extract.py::postprocess) become case events, visible in ops-ui."""
        v = doc.get("validation") or {}
        for fl in v.get("flags", []):
            case.log("decision", f"Extracție: {fl}", rule="validare deterministă după LLM (document-extraction-approach §4)",
                     document_id=doc_id, flag=fl)
        for x in v.get("failed", []):
            case.log("decision", f"Validare picată: {x['code']} pe {x['field']} ({x['severity']}): {x['detail']}",
                     rule="validare deterministă după LLM (document-extraction-approach §4)", document_id=doc_id,
                     validation=x)

    def _case_of(self, cif: str) -> Case | None:
        """The first case opened for this customer (same answer as scanning `cases` in order), via the index."""
        if self._indexed != len(self.cases):
            self._by_cif = {}
            for c in self.cases.values():
                self._by_cif.setdefault(c.cif, c.id)
            self._indexed = len(self.cases)
        c = self.cases.get(self._by_cif.get(cif, ""))
        if c is not None and c.cif == cif:
            return c
        if cif in self._by_cif:   # a case replaced from outside: scan once, as before
            self._indexed = -1
            return next((c for c in self.cases.values() if c.cif == cif), None)
        return None

    def _case_for(self, customer: dict) -> Case:
        c = self._case_of(customer["cif"])
        if c is not None:
            return c
        c = Case(customer.get("case_id") or self._next_case_id(), customer["cif"], customer["name"])
        self.cases[c.id] = c
        if self._indexed == len(self.cases) - 1:
            self._by_cif.setdefault(c.cif, c.id)
            self._indexed = len(self.cases)
        c.log("decision", f"Dosar de succesiune deschis pentru {customer['name']} ({customer['cif']}).")
        return c

    def _next_case_id(self) -> str:
        """SC-2026-0001, 0002 ... in arrival order. Cases of the seeded portfolio carry their own number
        (core: customer["case_id"], registries/portofoliu/) and do not take one, nor does the collector of unmatched
        documents, so Maria stays SC-2026-0001."""
        reserved = {c.get("case_id") for c in self.bank.customers.values()} - {None} | {"SC-NEIDENTIFICAT"}
        n = sum(1 for cid in self.cases if cid not in reserved) + 1
        while f"SC-2026-{n:04d}" in self.cases or f"SC-2026-{n:04d}" in reserved:
            n += 1
        return f"SC-2026-{n:04d}"

    def _orphan_case(self) -> Case:
        cid = "SC-NEIDENTIFICAT"
        if cid not in self.cases:
            self.cases[cid] = Case(cid, "-", "Documente neidentificate")
        return self.cases[cid]

    def _all_docs(self) -> list[Document]:
        return [d for c in self.cases.values() for d in c.documents]
