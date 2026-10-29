"""The succession case: a state machine fed by documents in any order.

States (kb/scenariu-demo/maria-ionescu.md §3):
  NEW -> FROZEN -> NOTARY_ANSWERED -> INSURANCE_CLAIM_OPEN -> SUPPLEMENT_REQUESTED
      -> INSURANCE_SETTLED -> PAYMENT_PENDING_APPROVAL -> PAID -> CLOSED
Documents may arrive out of order, so the state is derived from WHICH milestones are
done, not from a linear sequence. `state()` picks the most advanced label whose
prerequisites hold; the milestone set is the source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal

Milestone = Literal[
    "death_signalled", "frozen", "fees_reversed", "notary_answered", "insurance_claim_open",
    "insurance_settled", "certificate_received", "supplement_requested", "coverage_complete",
    "payment_plan_ready", "payment_pending_approval", "paid", "notary_answer_signed",
]

ORDER: list[tuple[str, Milestone]] = [
    ("PAID", "paid"),
    ("PAYMENT_PENDING_APPROVAL", "payment_pending_approval"),
    ("PLAN_DRAFTED", "payment_plan_ready"),   # also where a rejected plan returns
    ("INSURANCE_SETTLED", "insurance_settled"),
    ("SUPPLEMENT_REQUESTED", "supplement_requested"),
    ("INSURANCE_CLAIM_OPEN", "insurance_claim_open"),
    ("NOTARY_ANSWERED", "notary_answered"),
    ("FROZEN", "frozen"),
    ("DEATH_SIGNALLED", "death_signalled"),
]


@dataclass
class Event:
    at: str
    kind: str              # document | action | escalation | decision
    summary: str           # Romanian, one line, shown to the operator and the heir
    rule: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    id: str = ""           # E1, E2, ... stable within the case, so the auditor and the UI can cite an event


@dataclass
class Document:
    id: str
    type: str
    received_on: str
    confidence: float
    fields: dict[str, Any]
    raw_name: str | None = None


@dataclass
class Escalation:
    id: str
    reason: str
    detail: str
    document_id: str | None = None
    resolved: bool = False
    data: dict[str, Any] = field(default_factory=dict)   # 076: severity, guard flags + evidence (suspicious_document)


@dataclass
class Case:
    id: str
    cif: str
    customer_name: str
    date_of_death: date | None = None
    learned_on: date | None = None
    milestones: set[str] = field(default_factory=set)
    documents: list[Document] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    escalations: list[Escalation] = field(default_factory=list)
    deadlines: list[dict[str, Any]] = field(default_factory=list)
    heirs: list[dict[str, Any]] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    payment_plan: dict[str, Any] | None = None
    insurance: dict[str, Any] = field(default_factory=dict)
    flags: list[dict[str, Any]] = field(default_factory=list)
    # per heir: preferred channel + verified contact (operational messages need no marketing consent, DECISIONS 034)
    contact_channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    processed_document_keys: set[str] = field(default_factory=set)

    # ---- derived
    def state(self) -> str:
        for label, m in ORDER:
            if m in self.milestones:
                return label
        return "NEW"

    def log(self, kind: str, summary: str, rule: str | None = None, **data: Any) -> Event:
        ev = Event(datetime.now(timezone.utc).isoformat(timespec="seconds"), kind, summary, rule, data,
                   id=f"E{len(self.events) + 1}")
        self.events.append(ev)
        return ev

    def escalate(self, reason: str, detail: str, document_id: str | None = None, data: dict[str, Any] | None = None) -> Escalation:
        # max + 1, not len + 1: a document taken out of the case again (POST /demo/reset?case=) must not reuse an id
        n = max((int(e.id.split("-")[-1]) for e in self.escalations if e.id.split("-")[-1].isdigit()), default=0) + 1
        esc = Escalation(f"ESC-{n}", reason, detail, document_id, data=data or {})
        self.escalations.append(esc)
        self.log("escalation", f"Escaladare: {detail}", reason=reason, document_id=document_id)
        return esc

    def missing(self) -> list[str]:
        """What the heir / operator still has to bring. Plain Romanian."""
        out = []
        if "death_signalled" in self.milestones and "certificate_received" not in self.milestones:
            out.append("certificatul de moștenitor (de la notar)")
        if self.coverage_gaps:
            out.append(f"certificat suplimentar pentru: {', '.join(self.coverage_gaps)}")
        for h in self.heirs:
            if h.get("minor") and not h.get("representation_docs"):
                out.append(f"acordul scris al reprezentantului legal pentru {h['name']} (minor)")
        if self.insurance.get("claim_open") and not self.insurance.get("settled"):
            if self.insurance.get("claim_documents"):
                out.append(f"documentele pentru dosarul de daună la asigurător: {'; '.join(self.insurance['claim_documents'])}")
            out.append("răspunsul asigurătorului la dosarul de daună")
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Case":
        """The inverse of to_dict (agent/store.py): derived keys (state, missing) are recomputed, never read back."""
        return cls(id=d["id"], cif=d["cif"], customer_name=d["customer_name"],
                   date_of_death=date.fromisoformat(d["date_of_death"]) if d.get("date_of_death") else None,
                   learned_on=date.fromisoformat(d["learned_on"]) if d.get("learned_on") else None,
                   milestones=set(d.get("milestones") or []),
                   documents=[Document(**x) for x in d.get("documents") or []],
                   events=[Event(**x) for x in d.get("events") or []],
                   escalations=[Escalation(**x) for x in d.get("escalations") or []],
                   deadlines=list(d.get("deadlines") or []), heirs=list(d.get("heirs") or []),
                   coverage_gaps=list(d.get("coverage_gaps") or []), payment_plan=d.get("payment_plan"),
                   insurance=dict(d.get("insurance") or {}), flags=list(d.get("flags") or []),
                   contact_channels=dict(d.get("contact_channels") or {}),
                   processed_document_keys=set(d.get("processed_document_keys") or []))

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        d = asdict(self)
        d["state"] = self.state()
        d["missing"] = self.missing()
        d["milestones"] = sorted(self.milestones)
        d["processed_document_keys"] = sorted(self.processed_document_keys)
        d["date_of_death"] = self.date_of_death.isoformat() if self.date_of_death else None
        d["learned_on"] = self.learned_on.isoformat() if self.learned_on else None
        return d
