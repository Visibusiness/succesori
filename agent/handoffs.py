"""Predările între agenți: după un document, ce agent primește ce (pur: doar din răspunsul pipeline-ului).

Folosit de scripts/autopilot.py (care chiar cheamă agenții) și de API (`handoffs_planned` în răspunsul la un
document), ca ops-ui să arate lanțul document → sistem → agent și când autopilotul nu rulează.
"""
from __future__ import annotations

from typing import Any

ORPHAN_ID = "SC-NEIDENTIFICAT"
LETTER_ACTIONS = {"notary_answer_drafted": "răspunsul băncii către notar (solduri la data decesului)",
                  "supplement_requested": "cererea de certificat de moștenitor suplimentar către notar",
                  "insurance_claim_opened": "avizarea daunei către asigurător",
                  # răspunsul asigurătorului (doc 5): notarul și moștenitorii află ce s-a întâmplat cu creditul
                  "loan_settled_by_insurance": "nota către notar: creditul a fost stins de asigurător (indemnizația primită) "
                                               "și datoria care rămâne în sarcina masei succesorale",
                  "insurance_refused": "informarea moștenitorilor că asigurătorul a refuzat plata: motivul, faptul că "
                                       "datoria rămâne în masa succesorală și că pot accepta sau renunța la moștenire"}
# Every action the pipeline can return is either handed to an agent (LETTER_ACTIONS) or listed here with the reason
# why no agent is needed (tests/test_handoffs.py checks the two lists cover agent/pipeline.py).
NO_AGENT_ACTIONS = {"frozen": "acțiune pe core, reflectată în dosar",
                    "fees_reversed": "acțiune pe core, reflectată în dosar",
                    "freeze_definitive": "acțiune pe core, reflectată în dosar",
                    "heirs_recorded": "moștenitorii intră în dosar; ce lipsește merge la heir-communicator prin `missing`",
                    "coverage_complete": "planul de plată merge la aprobarea omului din ops-ui",
                    "indemnity_mismatch": "escaladare: o preia case-investigator"}
AGENT_LABEL = {"case-investigator": "Investigatorul", "correspondent": "Corespondentul",
               "heir-communicator": "Comunicatorul cu moștenitorii", "auditor": "Auditorul"}


def plan_followups(result: dict[str, Any], case: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Which agents to call after one POST /documents result. Pure: decided only from the API's answer.
    Each job says why (`trigger`), so the handoff log shows who handed what to whom."""
    jobs: list[dict[str, Any]] = []
    cid = result.get("case_id")
    for esc in result.get("escalations") or ([result["escalation"]] if result.get("escalation") else []):
        jobs.append({"agent": "case-investigator", "kind": "investigations", "key": f"{cid}-{esc}",
                     "escalation": esc, "trigger": f"escaladare {esc}"})
    for a in result.get("actions") or []:
        if a in LETTER_ACTIONS:
            jobs.append({"agent": "correspondent", "kind": "letters", "key": f"{cid}-{a}", "action": a, "trigger": a})
    # the heir is asked only for what the heir can bring: the insurer's answer is the bank's to chase, not the heir's
    missing = [m for m in result.get("missing") or [] if not m.startswith("răspunsul asigurătorului")]
    if missing and cid != ORPHAN_ID and case and case.get("heirs"):
        jobs.append({"agent": "heir-communicator", "kind": "messages", "key": f"{cid}-missing", "missing": missing,
                     "trigger": "lipsesc documente"})
    return jobs


def describe(result: dict[str, Any], case: dict[str, Any] | None) -> list[dict[str, Any]]:
    """The planned handoffs in plain Romanian, for the UI: who, why, what they will write."""
    out = []
    for j in plan_followups(result, case):
        if j["agent"] == "case-investigator":
            what = f"propunerea de rezolvare pentru escaladarea {j['escalation']}"
        elif j["agent"] == "correspondent":
            what = LETTER_ACTIONS[j["action"]]
        else:
            what = "mesajul către moștenitor cu ce mai lipsește: " + "; ".join(j["missing"])
        out.append({"agent": j["agent"], "label": AGENT_LABEL.get(j["agent"], j["agent"]), "trigger": j.get("trigger"),
                    "kind": j["kind"], "key": j["key"], "what": what})
    return out
