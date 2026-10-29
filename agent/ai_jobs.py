"""Guided demo, step by step: the operator starts every AI call (or a step's whole pipeline), sees each one
(queued -> running -> done), and approves everything that leaves the bank before it leaves.

POST /demo/ai/extract/{n}?variant=       AI   the extractor reads the scan of step n, visually (autopilot.to_document)
POST /demo/ai/apply/{n}                  code the bank's rules: the extracted document goes to the pipeline (no AI, instant)
POST /demo/ai/agent/{n}/{key}            AI   one handoff planned at step n: its agent writes a DRAFT (autopilot.run_job)
POST /demo/ai/gate/{n}/{key}/approve     human: the draft is sent / signed / the payment approved; body {by, note}
POST /demo/ai/gate/{n}/{key}/reject      human: nothing leaves; body {by, note}
POST /demo/ai/pipeline/{n}/run|stop      the whole step, station after station, stopping at every human gate
POST /demo/ai/audit                      AI   the auditor checks every case
GET  /demo/ai/jobs | /demo/ai/steps      every AI job of this run; per step: result, gates, pipeline, next station
GET  /demo/scan/{n}.png?variant=         first page of the scan of step n (thumbnail; the full PDF is in the preview)

Every route takes ?case=<case id>: without it (or with SC-2026-0001) it is Maria Ionescu's demo in 7 documents. Any other
case of the bank (the seeded portfolio) has its own steps, independent of Maria's and of each other (CaseRunner): its
documents are the steps already made (read at intake, rules applied), then one step for what the case waits on now (the
agent to start for an open escalation, the answer to the notary to draft, the heir message for what is missing; the
payment to approve), with the same stations, pipeline and human gates. When those are decided and the case needs
something new, the next step appears. GET /demo/ai/jobs without ?case lists the AI calls of every case.

Human gates (status pending -> approved | rejected), created when the thing to check exists:
  extract       the extractor is unsure (confidence < 0.80 or an error): look at the scan before the rules use it
  letter        a letter from the correspondent (to the notary / the insurer); approving the answer to the notary signs it
  message       a heir message from the heir-communicator: it is sent (POST /messages) only when approved
  investigation the investigator's proposal: accepted, the escalation is closed; not accepted, it stays open
  payment       the payment plan: approved or rejected through /payments/{id}/approve|reject
A rejected gate sends nothing. Decisions are recorded with POST /operator/feedback (runs/<run>/operator.jsonl).

The AI jobs run one at a time, in order, in one worker thread, with the autopilot's machinery (same prompts, output
check, handoff log and artifacts). The agents and the gates call this same API over HTTP on loopback. While this mode is
on (POST /demo/reset?manual=true) the autopilot is paused (GET /autopilot/status -> paused). A pipeline runs on the
server (a page reload does not stop it); stop cancels its queued AI calls and ends after the one already running.
"""
from __future__ import annotations

import copy
import json
import os
import queue
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from agent import portfolio
from agent.demo_documents import DOCUMENTS, VARIANT_B, scan_file
from agent.handoffs import AGENT_LABEL, plan_followups

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import autopilot  # noqa: E402  (scripts/autopilot.py: the agents' prompts and calls live there)

AGENT_LABEL = {**AGENT_LABEL, "extractor": "Extractorul"}
CONFIDENCE_GATE = 0.80   # same gate as agent/extract.py
LETTER_TO = {"notary_answer_drafted": "notarul public (dosarul succesoral 123/2026)",
             "supplement_requested": "notarul public (dosarul succesoral 123/2026)",
             "loan_settled_by_insurance": "notarul public (dosarul succesoral 123/2026)",
             "insurance_claim_opened": "asigurătorul, UNIQA Asigurări de viață S.A."}
# The demo has no real notary, insurer or heir mailbox: everything that leaves (letters, heir messages) is addressed to
# this one demo address (DEMO_EMAIL overrides it). With the default MAILER=outbox nothing is really sent; only
# MAILER=smtp + SMTP_HOST (agent/mailer.py) would deliver it. The insurer's real address (asigurari@uniqa.ro) is never used.
DEMO_EMAIL = os.environ.get("DEMO_EMAIL") or "calinanicolas91@gmail.com"
ACTIVE = ("queued", "running")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DemoPilot(autopilot.Autopilot):
    """The autopilot's agent calls, without its heartbeat: status() must not overwrite the real autopilot's
    autopilot-status.json."""

    def __init__(self, base: str):
        self.last_draft: dict[str, Any] | None = None
        super().__init__(base, agents=True, mode="manual", audit="milestones")

    def status(self, state: str = "idle", **extra: Any) -> None:
        pass


DEMO_CASE = "SC-2026-0001"   # Maria Ionescu: the guided demo in 7 documents (agent/demo_documents.py)


class JobQueue:
    """One worker thread for every AI call of the guided demo, of every case: they run one at a time, in order. Each job
    belongs to the case (scope) whose runner submitted it; a runner's reset drops only its own jobs."""

    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []
        self.owner: dict[str, "Runner"] = {}
        self.lock = threading.RLock()
        self.q: queue.Queue = queue.Queue()
        self.pilot: DemoPilot | None = None
        self.n = 0
        threading.Thread(target=self._work, daemon=True, name="demo-ai-jobs").start()

    def submit(self, owner: "Runner", job: dict[str, Any], fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
        with self.lock:
            self.n += 1
            job["id"] = f"J{self.n}"
            self.jobs.append(job)
            self.owner[job["id"]] = owner
        self.q.put((job, fn))
        return job

    def drop(self, scope: str) -> None:
        with self.lock:
            self.jobs = [j for j in self.jobs if j.get("case_scope") != scope]

    def _work(self) -> None:
        while True:
            job, fn = self.q.get()
            owner = self.owner.get(job["id"])
            if owner is None or job["epoch"] != owner.epoch or job["status"] == "cancelled":   # reset or stopped before it started
                continue
            job.update(status="running", started_at=_now())
            t0 = time.time()
            try:
                job["output"] = fn(job)
                job["status"] = "done"
            except Exception as e:  # noqa: BLE001 - a failed AI call is shown, never hidden
                job.update(status="failed", error=f"{type(e).__name__}: {e}"[:400])
            job["seconds"] = round(time.time() - t0, 1)

    def get_pilot(self, base: str) -> DemoPilot:
        if self.pilot is None or self.pilot.base != base.rstrip("/"):
            self.pilot = DemoPilot(base)
        self.pilot.sync_run()   # follows /demo/reset (new epoch: forgets what the agents sent)
        return self.pilot

    def view(self, scope: str | None = None) -> list[dict[str, Any]]:
        now = time.time()
        with self.lock:
            out = []
            for j in self.jobs:
                if scope is not None and j.get("case_scope") != scope:
                    continue
                v = {k: j[k] for k in j if k != "epoch"}
                if j["status"] == "running" and j["started_at"]:
                    v["elapsed"] = round(now - datetime.fromisoformat(j["started_at"]).timestamp(), 1)
                out.append(v)
            return out

    def running(self) -> list[dict[str, Any]]:
        return [j for j in self.view() if j["status"] in ACTIVE]


QUEUE = JobQueue()


class Runner:
    """Maria Ionescu's guided demo (scope SC-2026-0001): 7 documents, each read by the extractor, then the rules, then
    the agents its result hands to, then the human gates. CaseRunner (below) is the same for any other case."""
    scope = DEMO_CASE

    def __init__(self) -> None:
        self.steps: dict[int, dict[str, Any]] = {}   # n -> {"variant", "extracted", "result"}
        self.gates: dict[str, dict[str, Any]] = {}   # "n:key" -> gate
        self.pipes: dict[int, dict[str, Any]] = {}   # n -> {"status", "stage", "error", "stop", "started"}
        self.epoch = 0
        self.lock = threading.RLock()

    # ---------------------------------------------------------------- jobs
    @property
    def jobs(self) -> list[dict[str, Any]]:
        with QUEUE.lock:
            return [j for j in QUEUE.jobs if j.get("case_scope") == self.scope]

    @property
    def receive(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        return HOOKS["receive"]

    @property
    def get_case(self) -> Callable[[str], dict[str, Any] | None]:
        return HOOKS["get_case"]

    def reset(self) -> None:
        with self.lock:
            self.epoch += 1
            for p in self.pipes.values():
                p["stop"] = True
            self.steps, self.gates, self.pipes = {}, {}, {}
            QUEUE.drop(self.scope)

    def submit(self, kind: str, agent: str, label: str, fn: Callable[[dict[str, Any]], Any], **meta: Any) -> dict[str, Any]:
        job = {"id": None, "kind": kind, "agent": agent, "agent_label": AGENT_LABEL.get(agent, agent),
               "label": label, "status": "queued", "queued_at": _now(), "started_at": None, "seconds": None,
               "output": None, "error": None, "epoch": self.epoch, "case_scope": self.scope, **meta}
        return QUEUE.submit(self, job, fn)

    def last_job(self, **match: Any) -> dict[str, Any] | None:
        return next((j for j in reversed(self.jobs) if all(j.get(k) == v for k, v in match.items())), None)

    def get_pilot(self, base: str) -> DemoPilot:
        return QUEUE.get_pilot(base)

    def view(self) -> list[dict[str, Any]]:
        return QUEUE.view(self.scope)

    def running(self) -> list[dict[str, Any]]:
        return [j for j in self.view() if j["status"] in ACTIVE]

    def letter_recipient(self, action: str | None, case: dict[str, Any] | None) -> str | None:
        return LETTER_TO.get(action or "")

    def count(self) -> int:
        return len(DOCUMENTS)

    # what the extractor reads at step n (None: nothing to read, the document goes straight to the rules) and the
    # document of step n as the bank knows it (ground truth: id, receipt date); CaseRunner has its own
    def scan_for(self, n: int, variant: str) -> Path | None:
        return scan_file(n, variant)

    def doc_for(self, n: int, variant: str) -> dict[str, Any]:
        return _step_doc(n, variant)

    def source_name(self, scan: Path) -> str:
        return f"scan/{scan.name}"

    # ---------------------------------------------------------------- stations
    def step(self, n: int) -> dict[str, Any]:
        return self.steps.setdefault(n, {})

    def start_extract(self, n: int, variant: str) -> dict[str, Any]:
        scan = self.scan_for(n, variant)
        if scan is None:
            raise HTTPException(409, "pasul 1 e linia din lotul electronic DGEP: nu are scanare de citit" if self.scope == DEMO_CASE
                                else "documentul vine deja extras: nu are scanare de citit")
        if (job := self.last_job(kind="extract", step=n)) and job["status"] in ACTIVE:
            return job
        meta = self.doc_for(n, variant)
        epoch = self.epoch

        def run(job: dict[str, Any]) -> dict[str, Any]:
            doc = autopilot.to_document(scan)
            # identity of the intake (not read from the paper): the story's id and receipt date, the scan as source
            doc.update(id=meta["id"], raw_name=self.source_name(scan))
            doc.setdefault("received_on", meta.get("received_on"))
            out = {k: doc.get(k) for k in ("document_type", "confidence", "fields", "field_confidence", "error", "raw_name")}
            if epoch != self.epoch:
                return out
            self.step(n)["extracted"] = doc
            conf = doc.get("confidence") or 0.0
            if conf < CONFIDENCE_GATE or doc.get("error"):
                self.open_gate(n, "extract", kind="extract", title="Verifică ce a citit extractorul",
                               why=f"Extractorul nu e sigur (încredere {round(conf * 100)}%"
                                   + (f", {doc['error']}" if doc.get("error") else "") + "): un om se uită la scanare "
                                   "înainte ca regulile să folosească documentul.",
                               to="regulile băncii (pipeline-ul)", preview=None)
            return out

        st = self.step(n)
        st.update(variant=variant, extracted=None, result=None)
        self.gates.pop(f"{n}:extract", None)
        return self.submit("extract", "extractor", f"citește scanarea {scan.name}", run, step=n, file=scan.name)

    def apply(self, n: int, variant: str) -> dict[str, Any]:
        """The rules (pipeline.py, no AI): step 1 is the DGEP line as it came; 2–7 need the extraction first."""
        st = self.step(n)
        if st.get("result"):
            return st["result"]   # idempotent: the same document is not fed twice
        if self.scan_for(n, variant) is None:   # Maria's step 1: the DGEP line as it came (electronic, nothing to read)
            doc = self.doc_for(n, variant)
        elif st.get("extracted"):
            g = self.gates.get(f"{n}:extract")
            if g and g["status"] == "pending":
                raise HTTPException(409, "extracția așteaptă verificarea umană")
            if g and g["status"] == "rejected":
                raise HTTPException(409, "operatorul a respins extracția: documentul nu intră în reguli")
            doc = copy.deepcopy(st["extracted"])
        else:
            raise HTTPException(409, "întâi extractorul trebuie să citească scanarea")
        st["variant"] = st.get("variant") or variant
        st["result"] = {**self.receive(doc), "document_id": doc.get("id"), "source": doc.get("raw_name")}
        cid = st["result"].get("case_id")
        plan = (self.get_case(cid) or {}).get("payment_plan") if cid else None
        if plan and plan.get("status") == "pending_approval" and f"{n}:payment" not in self.gates:
            self.open_gate(n, "payment", kind="payment", title="Aprobă plata către moștenitori",
                           why="Plata e ireversibilă: sistemul nu o face singur. Liniile blocate (minora, depozitul "
                               "nescadent) rămân pe loc.", to="moștenitorii, pe liniile neblocate", preview=None,
                           case_id=cid, plan_id=plan.get("plan_id"))
        return st["result"]

    def start_agent(self, n: int, key: str, base: str) -> dict[str, Any]:
        result = self.step(n).get("result")
        if not result:
            raise HTTPException(409, "întâi se aplică regulile pe document")
        if (job := self.last_job(kind="agent", step=n, key=key)) and job["status"] in ACTIVE:
            return job
        cid = result.get("case_id")
        planned = next((j for j in plan_followups(result, self.get_case(cid) if cid else None) if j["key"] == key), None)
        if planned is None:
            raise HTTPException(404, f"predarea {key} nu e planificată la pasul {n}")
        epoch = self.epoch

        def run(job: dict[str, Any]) -> dict[str, Any]:
            pilot = self.get_pilot(base)
            case = self.get_case(cid) if cid else None   # the case as it is now, when the agent starts
            calls, pilot.last_draft = len(pilot.agent_calls), None
            text = pilot.run_job(planned, cid, case, result.get("source"), send=False)
            call = pilot.agent_calls[calls] if len(pilot.agent_calls) > calls else {}
            if text is None:
                return {"text": None, "skipped": "nimic de trimis: aceeași cerere a plecat deja sau nu există un moștenitor major"}
            if not call.get("ok", True):
                raise RuntimeError(call.get("error") or "agentul nu a produs textul")
            if epoch == self.epoch:
                self.gate_for(n, planned, cid, text, pilot.last_draft)
            return {"text": text, "artifact": call.get("file"), "cost_usd": call.get("cost_usd")}

        self.gates.pop(f"{n}:{key}", None)
        return self.submit("agent", planned["agent"], label_of(planned), run, step=n, key=key, case_id=cid)

    def start_audit(self, base: str) -> dict[str, Any]:
        if (job := self.last_job(kind="audit")) and job["status"] in ACTIVE:
            return job

        def run(job: dict[str, Any]) -> dict[str, Any]:
            pilot = self.get_pilot(base)
            calls = len(pilot.agent_calls)
            pilot.audit("pas cu pas")
            call = pilot.agent_calls[calls] if len(pilot.agent_calls) > calls else {}
            if not call.get("ok", True):
                raise RuntimeError(call.get("error") or "auditorul nu a produs raportul")
            f = pilot.run_dir / "audit.md"
            return {"text": strip_artifact(f.read_text(encoding="utf-8")) if f.is_file() else "", "artifact": "audit.md",
                    "cost_usd": call.get("cost_usd")}

        return self.submit("audit", "auditor", "verifică regulile pe toate dosarele", run)

    # ---------------------------------------------------------------- human gates
    def open_gate(self, n: int, key: str, **gate: Any) -> dict[str, Any]:
        g = {"step": n, "key": key, "status": "pending", "opened_at": _now(), "decided_by": None, "decided_at": None,
             "note": None, **gate}
        self.gates[f"{n}:{key}"] = g
        return g

    def gate_for(self, n: int, planned: dict[str, Any], cid: str | None, text: str, draft: dict[str, Any] | None) -> None:
        """What a human checks after an agent wrote: the letter that would leave, the message to the heir, the proposal."""
        agent, key = planned["agent"], planned["key"]
        if agent == "correspondent":
            signs = planned["action"] == "notary_answer_drafted"
            self.open_gate(n, key, kind="letter", title="Aprobă scrisoarea înainte să plece" + (" (o și semnezi)" if signs else ""),
                           why="Nicio scrisoare nu pleacă din bancă fără ca un om să o citească.",
                           to=DEMO_EMAIL, email=DEMO_EMAIL, recipient=self.letter_recipient(planned["action"], self.get_case(cid) if cid else None),
                           preview=text, case_id=cid, action=planned["action"], pdf=True)
        elif agent == "heir-communicator" and draft:
            self.open_gate(n, key, kind="message", title="Aprobă mesajul către moștenitor",
                           why="Mesajul pleacă doar după ce îl aprobi: secretul bancar și tonul le verifică un om.",
                           to=DEMO_EMAIL, email=DEMO_EMAIL, recipient=draft["to"],
                           preview=text, case_id=cid, draft={**draft, "email": DEMO_EMAIL})
        elif agent == "case-investigator":
            self.open_gate(n, key, kind="investigation", title="Decide pe propunerea investigatorului",
                           why="Investigatorul propune, nu decide: operatorul acceptă sau nu propunerea.",
                           to="operatorul (decizie, nu pleacă nimic din bancă)", preview=text, case_id=cid,
                           escalation=planned.get("escalation"))

    def decide(self, n: int, key: str, approve: bool, by: str, note: str, base: str) -> dict[str, Any]:
        g = self.gates.get(f"{n}:{key}")
        if g is None:
            raise HTTPException(404, "nu există o verificare umană aici")
        if g["status"] != "pending":
            return g   # idempotent: the first decision stands
        if not approve and g["kind"] == "payment" and not note.strip():
            raise HTTPException(422, "motivul respingerii plății e obligatoriu")
        cid, call = g.get("case_id"), lambda m, p, b: _api(base, m, p, b)
        if approve and g["kind"] == "payment":
            _ok(call("POST", f"/payments/{g['plan_id']}/approve", {"approver": by}))
        elif not approve and g["kind"] == "payment":
            _ok(call("POST", f"/payments/{g['plan_id']}/reject", {"reason": note}))
        elif approve and g["kind"] == "letter":
            if g.get("action") == "notary_answer_drafted":
                _ok(call("POST", f"/cases/{cid}/letters/notary/sign", {"signer": by}))
            self.mail_letter(g, by)
        elif approve and g["kind"] == "message":
            _ok(self.get_pilot(base).send_message(g["draft"]))
        elif approve and g["kind"] == "investigation" and g.get("escalation"):
            # the proposal accepted: the escalation it answers is closed (it stays open when the operator says no)
            _ok(call("POST", f"/escalations/{cid}/{g['escalation']}/resolve",
                     {"note": f"propunerea investigatorului acceptată de {by}" + (f": {note}" if note else "")}))
        call("POST", "/operator/feedback", {"kind": f"gate_{g['kind']}_{'approved' if approve else 'rejected'}", "case_id": cid,
                                           "step": n, "key": key, "by": by, "note": note})
        g.update(status="approved" if approve else "rejected", decided_by=by, decided_at=_now(), note=note or None)
        return g

    def mail_letter(self, g: dict[str, Any], by: str) -> None:
        """The approved letter leaves as an e-mail with the letter as PDF (to sign): the PDF is kept next to the
        outbox (runs/<run>/letters/*.pdf) and the e-mail goes through the API's mailer (outbox by default: GET /messages)."""
        from agent.api import _mailer, _outbox   # the API's own (same process; imported late: api imports this module)
        pdf = _outbox().parent / "letters" / f"{g.get('case_id')}-{g.get('action')}.pdf"
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(gate_pdf(g))
        msg = {"message_id": f"MSG-{secrets.token_hex(4)}", "at": _now(), "case_id": g.get("case_id"),
               "to": g.get("recipient") or "destinatarul scrisorii", "address": g.get("email"), "channel": "email",
               "template_id": f"LETTER_{str(g.get('action') or '').upper()}", "kind": "letter",
               "subject": f"{g.get('recipient') or 'Scrisoare'}: dosarul {g.get('case_id')}",
               "body": "Bună ziua,\n\nVă transmitem în atașament scrisoarea băncii (PDF), semnată.\n\nRaiffeisen Bank, Serviciul Succesiuni",
               "attachment_path": str(pdf), "approved_by": by, "status": "queued_mock"}
        _mailer().send(msg)
        g["mail"] = {"message_id": msg["message_id"], "address": msg["address"], "pdf": pdf.name}

    # ---------------------------------------------------------------- the whole step
    def next_action(self, n: int, started: set[str] | None = None) -> dict[str, Any]:
        """The next station of step n: extract | apply | agent (key) | wait_job | wait_gate | failed | blocked | done.
        A job that failed in THIS pipeline run fails the run; one that failed before is retried."""
        started = started or set()
        if n > 1 and not self.step(n - 1).get("result"):
            return {"do": "blocked", "why": f"întâi pasul {n - 1}"}
        st = self.step(n)
        if not st.get("result"):
            if self.scan_for(n, st.get("variant") or "A") is not None:   # a paper to read first (Maria: 2..7)
                j = self.last_job(kind="extract", step=n)
                if j and j["status"] in ACTIVE:
                    return {"do": "wait_job", "job": j}
                if j and j["status"] == "failed" and j["id"] in started:
                    return {"do": "failed", "why": j["error"]}
                if not j or j["status"] != "done" or not st.get("extracted"):
                    return {"do": "extract"}
                g = self.gates.get(f"{n}:extract")
                if g and g["status"] == "pending":
                    return {"do": "wait_gate", "gate": g}
                if g and g["status"] == "rejected":
                    return {"do": "blocked", "why": "operatorul a respins extracția"}
            return {"do": "apply"}
        for p in st["result"].get("handoffs_planned") or []:
            j = self.last_job(kind="agent", step=n, key=p["key"])
            if j and j["status"] in ACTIVE:
                return {"do": "wait_job", "job": j}
            if j and j["status"] == "failed" and j["id"] in started:
                return {"do": "failed", "why": j["error"]}
            if not j or j["status"] != "done":
                return {"do": "agent", "key": p["key"], "label": p["label"]}
            g = self.gates.get(f"{n}:{p['key']}")
            if g and g["status"] == "pending":
                return {"do": "wait_gate", "gate": g}
        g = self.gates.get(f"{n}:payment")
        if g and g["status"] == "pending":
            return {"do": "wait_gate", "gate": g}
        return {"do": "done"}

    def run_pipeline(self, n: int, variant: str, base: str) -> dict[str, Any]:
        with self.lock:
            p = self.pipes.get(n)
            if p and p["status"] in ("running", "awaiting", "stopping"):
                return pipe_view(p)
            if (a := self.next_action(n))["do"] == "blocked":
                raise HTTPException(409, f"pipeline-ul pasului {n} nu poate porni: {a['why']}")
            p = self.pipes[n] = {"status": "running", "stage": "pornește", "error": None, "stop": False, "started": set(),
                                 "started_at": _now()}
        epoch = self.epoch
        threading.Thread(target=self._pipeline, args=(n, variant, base, p, epoch), daemon=True, name=f"pipeline-{n}").start()
        return pipe_view(p)

    def _pipeline(self, n: int, variant: str, base: str, p: dict[str, Any], epoch: int) -> None:
        while epoch == self.epoch:
            if p["stop"]:
                running = self.last_job(step=n, status="running")
                if running and running["id"] in p["started"]:
                    p.update(status="stopping", stage=f"se oprește după {running['agent_label']}")
                    time.sleep(0.4)
                    continue
                p.update(status="stopped", stage="oprit de operator")
                return
            a = self.next_action(n, p["started"])
            try:
                if a["do"] == "extract":
                    p.update(status="running", stage="Extractorul citește scanarea")
                    p["started"].add(self.start_extract(n, self.step(n).get("variant") or variant)["id"])
                elif a["do"] == "apply":
                    p.update(status="running", stage="Regulile băncii")
                    self.apply(n, self.step(n).get("variant") or variant)
                elif a["do"] == "agent":
                    p.update(status="running", stage=a["label"])
                    p["started"].add(self.start_agent(n, a["key"], base)["id"])
                elif a["do"] == "wait_job":
                    p.update(status="running", stage=f"{a['job']['agent_label']}: {a['job']['label']}")
                    time.sleep(0.4)
                elif a["do"] == "wait_gate":
                    p.update(status="awaiting", stage=a["gate"]["title"])
                    time.sleep(0.4)
                elif a["do"] == "failed":
                    p.update(status="failed", stage="un apel AI a eșuat", error=a["why"])
                    return
                elif a["do"] == "blocked":
                    p.update(status="stopped", stage=a["why"])
                    return
                else:
                    p.update(status="done", stage="pasul e complet")
                    return
            except HTTPException as e:
                p.update(status="failed", stage="eroare", error=str(e.detail))
                return

    def stop_pipeline(self, n: int) -> dict[str, Any]:
        with self.lock:
            p = self.pipes.get(n)
            if not p or p["status"] not in ("running", "awaiting", "stopping"):
                raise HTTPException(409, "pipeline-ul pasului nu rulează")
            p["stop"] = True
            for j in self.jobs:   # its AI calls not started yet are dropped; the running one ends normally (same dicts as the queue's)
                if j["id"] in p["started"] and j["status"] == "queued":
                    j.update(status="cancelled", seconds=0)
            if p["status"] == "awaiting":
                p.update(status="stopped", stage="oprit de operator")
            else:   # the pipeline thread ends it after the AI call already running
                p.update(status="stopping", stage="se oprește după apelul AI în curs")
            return pipe_view(p)

    def steps_view(self) -> dict[str, Any]:
        out = {}
        for n in range(1, len(DOCUMENTS) + 1):
            st = self.steps.get(n) or {}
            a = self.next_action(n, (self.pipes.get(n) or {}).get("started"))
            out[str(n)] = {"variant": st.get("variant"), "extracted": bool(st.get("extracted")), "result": st.get("result"),
                           "gates": {g["key"]: _public_gate(g) for g in self.gates.values() if g["step"] == n},
                           "pipeline": pipe_view(self.pipes[n]) if n in self.pipes else {"status": "idle"},
                           "next": {k: v for k, v in a.items() if k in ("do", "key", "label", "why")}}
        return out


DOC_LABEL = {"dgep_signal": "Semnalul DGEP", "notary_request": "Adresa notarului", "insurance_certificate": "Certificatul de asigurare",
             "heir_certificate": "Certificatul de moștenitor", "insurer_response": "Răspunsul asigurătorului",
             "supplementary_certificate": "Certificatul suplimentar", "death_certificate": "Certificatul de deces"}
DOC_FROM = {"dgep_signal": "DGEP · Evidența Persoanelor", "notary_request": "Notarul public", "insurance_certificate": "Asigurătorul creditului",
            "heir_certificate": "Notarul public", "insurer_response": "Asigurătorul creditului",
            "supplementary_certificate": "Notarul public", "death_certificate": "Moștenitorii (ghișeu)"}


def _digest(items: list[str]) -> str:
    import hashlib
    return hashlib.sha1("|".join(items).encode("utf-8")).hexdigest()[:8]


def open_work(case: dict[str, Any]) -> list[dict[str, Any]]:
    """What a case waits on now that an agent can prepare (same job shapes as handoffs.plan_followups): a proposal for
    each open escalation, the answer to the notary when it is not signed yet, the heir message for what is missing."""
    cid = case["case_id"]
    jobs: list[dict[str, Any]] = []
    for e in case.get("escalations") or []:
        if e.get("status") != "închis" and e.get("id"):
            jobs.append({"agent": "case-investigator", "kind": "investigations", "key": f"{cid}-{e['id']}", "escalation": e["id"],
                         "trigger": f"escaladare {e.get('code')}"})
    states = {x.get("state") for x in case.get("state_history") or []}
    if "NOTARY_ANSWERED" in states and any(d.get("code") == "notary_answer" and d.get("status") != "îndeplinit"
                                           for d in case.get("deadlines") or []):
        jobs.append({"agent": "correspondent", "kind": "letters", "key": f"{cid}-notary_answer_drafted",
                     "action": "notary_answer_drafted", "trigger": "notary_answer_drafted"})
    missing = [m for m in case.get("missing") or [] if not m.startswith("răspunsul asigurătorului")]
    if missing and case.get("heirs") and case.get("state") not in ("PAID", "CLOSED"):
        jobs.append({"agent": "heir-communicator", "kind": "messages", "key": f"{cid}-missing-{_digest(missing)}", "missing": missing,
                     "trigger": "lipsesc documente"})
    return jobs


def _what(job: dict[str, Any]) -> str:
    if job["agent"] == "case-investigator":
        return f"propunerea de rezolvare pentru escaladarea {job['escalation']}"
    if job["agent"] == "correspondent":
        return autopilot.LETTER_ACTIONS[job["action"]]
    return "mesajul către moștenitor cu ce mai lipsește: " + "; ".join(job["missing"])


class CaseRunner(Runner):
    """Any case of the bank other than Maria's, step by step with the same stations as hers. Steps 1..k are its
    documents, as they came (read at intake, the rules applied: events and escalations of that document). A portfolio
    client's documents that have not come yet (registries/portofoliu `"pending": true`) follow, each one exactly as
    Maria's: the extractor reads its file, the rules apply it, the agents its result hands to write, the human gates.
    Then a step for what the case waits on now (open_work + the payment plan to approve): the operator starts the
    agents (one by one or the whole step), each draft stops at a human gate (approve / reject), and when the step is
    complete and the case needs something new (e.g. the heir message after the escalations are closed), the next step
    appears. The state is the case's own: deciding here touches no other case, and another case's reset does not touch it."""

    def __init__(self, cid: str) -> None:
        super().__init__()
        self.scope = cid
        self.meta: list[dict[str, Any]] = []   # n-1 -> {kind: doc|action, title, date, from, document_type}
        self.handled: set[str] = set()         # keys planned in an action step already (a rejected proposal is not re-planned)

    def reset(self) -> None:
        super().reset()
        with self.lock:
            self.meta, self.handled = [], set()

    def count(self) -> int:
        self.ensure()
        return len(self.meta)

    # ---------------------------------------------------------------- documents still to come (pending)
    def pending(self, n: int) -> dict[str, Any] | None:
        """The portfolio step of a pending document at step n (None: a document already in the case, or an action)."""
        m = self.meta[n - 1] if 1 <= n <= len(self.meta) else {}
        return m.get("_step") if m.get("pending") else None

    def scan_for(self, n: int, variant: str) -> Path | None:
        step = self.pending(n)
        path = portfolio.received_file(step["doc"]).resolve() if step and step["doc"].get("file") else None
        return path if path and portfolio.DOCS.resolve() in path.parents and path.is_file() else None

    def doc_for(self, n: int, variant: str) -> dict[str, Any]:
        step = self.pending(n)
        if step is None:
            raise HTTPException(409, "documentul e deja în dosar")
        d = step["doc"]   # what the bank knows before reading it: id, receipt date (the reference values only without a file)
        return {"id": d["id"], "received_on": d["received_on"], "raw_name": portfolio.RAW_PREFIX + d["file"],
                "document_type": d.get("expected_type"), "confidence": 0.95, "fields": copy.deepcopy(d.get("expected_fields") or {})}

    def source_name(self, scan: Path) -> str:
        # registries/portofoliu/documente/...: GET /cases/{id}/documents/{doc}/preview finds it (agent/doc_preview.py)
        return portfolio.RAW_PREFIX + str(scan.relative_to(portfolio.DOCS.resolve()))

    def letter_recipient(self, action: str | None, case: dict[str, Any] | None) -> str | None:
        if action == "insurance_refused":
            return "moștenitorii (informarea despre refuzul asigurătorului)"
        if action not in ("notary_answer_drafted", "supplement_requested", "loan_settled_by_insurance") or not case:
            return LETTER_TO.get(action or "") if action == "insurance_claim_opened" else None
        f = next(({x["name"]: x.get("value") for x in d.get("fields") or []} for d in reversed(case.get("documents") or [])
                  if d.get("document_type") == "notary_request"), {})
        who = f.get("notary_office") or f.get("notary_name") or "notarul public"
        return f"{who} (dosarul succesoral {f['case_file']})" if f.get("case_file") else who

    # ---------------------------------------------------------------- the steps
    def ensure(self) -> None:
        """The steps from the case as it is now: a step per document not shown yet, and the next action step when the
        last one is complete and the case waits on something new."""
        with self.lock:
            c = self.get_case(self.scope)
            if c is None:
                raise HTTPException(404, f"dosarul {self.scope} nu există în bancă")
            shown = {m.get("document_id") for m in self.meta}
            client = portfolio.client_of(self.scope)
            later = [st for st in (portfolio.pending(client) if client else []) if "doc" in st]
            events = _events_by_document(c)
            for d in c.get("documents") or []:
                if d["document_id"] in shown or d["document_id"] in {st["doc"]["id"] for st in later}:
                    continue
                n = len(self.meta) + 1
                t = d.get("document_type")
                esc = next((e for e in c.get("escalations") or [] if e.get("document_id") == d["document_id"]), None)
                fields = {x["name"]: x.get("value") for x in d.get("fields") or [] if not str(x.get("name", "")).startswith("_")}
                self.meta.append({"kind": "doc", "document_id": d["document_id"], "document_type": t,
                                  "title": DOC_LABEL.get(t, t), "from": DOC_FROM.get(t, ""), "date": d.get("received_at")})
                self.steps[n] = {"result": {"case_id": self.scope, "document_id": d["document_id"], "document_type": t,
                                            "source": d.get("source"), "history": True, "actions": [], "handoffs_planned": [],
                                            "escalation": esc["id"] if esc else None, "events": events.get(d["document_id"], []),
                                            "extracted": {"document_type": t, "confidence": d.get("confidence"), "fields": fields}}}
            for st in later:   # the documents that have not come yet: one step each, processed like Maria's
                if st["doc"]["id"] in shown:
                    continue
                t = st["doc"].get("expected_type")
                self.meta.append({"kind": "doc", "pending": True, "document_id": st["doc"]["id"], "document_type": t,
                                  "title": DOC_LABEL.get(t, t), "from": DOC_FROM.get(t, ""), "date": st["doc"].get("received_on"),
                                  "scan": st["doc"].get("file"), "_step": st})
                self.steps[len(self.meta)] = {}
            plan = c.get("payment_plan")
            pay_key = f"pay:{plan.get('plan_id')}" if plan and plan.get("status") == "pending_approval" else None
            for i, m in enumerate(self.meta, 1):
                if not m.get("pending"):
                    continue
                if self.next_action(i)["do"] != "done":
                    return   # the documents come in order; what the case waits on is known after the last one
                # what that document handed to an agent or to a human is done: not planned again
                self.handled |= {p["key"] for p in (self.steps[i].get("result") or {}).get("handoffs_planned") or []}
                if f"{i}:payment" in self.gates and pay_key:
                    self.handled.add(pay_key)
            last = self.meta[-1] if self.meta else None
            if last and last["kind"] == "action" and self.next_action(len(self.meta))["do"] != "done":
                return
            # what the case waits on now, in one step, in the order a back-office works it: the escalations, the letter,
            # then the payment (its gate can be decided at any time); the heirs' message comes after, on its own
            work = [j for j in open_work(c) if j["key"] not in self.handled]
            first = [j for j in work if j["agent"] != "heir-communicator"]
            pay = bool(pay_key and pay_key not in self.handled)
            planned = first if first or pay else work[:1]
            if not planned and not pay:
                return
            n = len(self.meta) + 1
            self.handled |= {j["key"] for j in planned} | ({pay_key} if pay else set())
            kind = planned[0]["agent"] if planned else "payment"
            title = {"payment": "Aprobarea plății", "case-investigator": "Escaladarea de rezolvat",
                     "correspondent": "Răspunsul către notar", "heir-communicator": "Mesajul către moștenitori"}[kind]
            self.meta.append({"kind": "action", "action": kind, "title": title,
                              "from": "Regulile băncii → tu" if pay else "Regulile băncii → agentul AI → tu",
                              "date": (c.get("updated_at") or "")[:10] or None})
            self.steps[n] = {"planned": planned, "result": {
                "case_id": self.scope, "kind": "action", "actions": [], "state": c.get("state"),
                "handoffs_planned": [{"agent": j["agent"], "label": AGENT_LABEL.get(j["agent"], j["agent"]), "trigger": j.get("trigger"),
                                      "kind": j["kind"], "key": j["key"], "what": _what(j)} for j in planned],
                "why": "; ".join([j["trigger"] for j in planned] + (["plan de plată de aprobat"] if pay else []))}}
            if pay:
                self.open_gate(n, "payment", kind="payment", title="Aprobă plata către moștenitori",
                               why="Plata e ireversibilă: sistemul nu o face singur. Liniile blocate rămân pe loc.",
                               to="moștenitorii, pe liniile neblocate", preview=None, case_id=self.scope, plan_id=plan.get("plan_id"))

    def start_extract(self, n: int, variant: str) -> dict[str, Any]:
        if self.pending(n):
            return super().start_extract(n, variant)
        raise HTTPException(409, "documentul a fost citit la primire: extracția e făcută")

    def apply(self, n: int, variant: str) -> dict[str, Any]:
        if self.pending(n):
            return super().apply(n, variant)
        st = self.step(n)
        if not st.get("result"):
            raise HTTPException(409, "pas inexistent")
        return st["result"]

    def start_agent(self, n: int, key: str, base: str) -> dict[str, Any]:
        self.ensure()
        if self.pending(n):
            return super().start_agent(n, key, base)
        st = self.step(n)
        planned = next((j for j in st.get("planned") or [] if j["key"] == key), None)
        if planned is None:
            raise HTTPException(404, f"predarea {key} nu e planificată la pasul {n}")
        if (job := self.last_job(kind="agent", step=n, key=key)) and job["status"] in ACTIVE:
            return job
        cid, epoch = self.scope, self.epoch

        def run(job: dict[str, Any]) -> dict[str, Any]:
            pilot = self.get_pilot(base)
            case = self.get_case(cid)   # the case as it is now, when the agent starts
            calls, pilot.last_draft = len(pilot.agent_calls), None
            text = pilot.run_job(planned, cid, case, None, send=False)
            call = pilot.agent_calls[calls] if len(pilot.agent_calls) > calls else {}
            if text is None:
                return {"text": None, "skipped": "nimic de trimis: aceeași cerere a plecat deja sau nu există un moștenitor major cu adresă"}
            if not call.get("ok", True):
                raise RuntimeError(call.get("error") or "agentul nu a produs textul")
            if epoch == self.epoch:
                self.gate_for(n, planned, cid, text, pilot.last_draft)
            return {"text": text, "artifact": call.get("file"), "cost_usd": call.get("cost_usd")}

        self.gates.pop(f"{n}:{key}", None)
        return self.submit("agent", planned["agent"], label_of(planned), run, step=n, key=key, case_id=cid)

    def next_action(self, n: int, started: set[str] | None = None) -> dict[str, Any]:
        if self.pending(n):
            return super().next_action(n, started)
        st = self.step(n)
        if not st.get("planned") and not self.gates.get(f"{n}:payment"):
            return {"do": "done"}   # a document of the case: read and applied at intake
        started = started or set()
        for p in st.get("planned") or []:
            j = self.last_job(kind="agent", step=n, key=p["key"])
            if j and j["status"] in ACTIVE:
                return {"do": "wait_job", "job": j}
            if j and j["status"] == "failed" and j["id"] in started:
                return {"do": "failed", "why": j["error"]}
            if not j or j["status"] != "done":
                return {"do": "agent", "key": p["key"], "label": AGENT_LABEL.get(p["agent"], p["agent"]) + ": " + label_of(p)}
            g = self.gates.get(f"{n}:{p['key']}")
            if g and g["status"] == "pending":
                return {"do": "wait_gate", "gate": g}
        g = self.gates.get(f"{n}:payment")
        if g and g["status"] == "pending":
            return {"do": "wait_gate", "gate": g}
        return {"do": "done"}

    def run_pipeline(self, n: int, variant: str, base: str) -> dict[str, Any]:
        self.ensure()
        return super().run_pipeline(n, variant, base)

    def steps_view(self) -> dict[str, Any]:
        self.ensure()
        out = {}
        for i, m in enumerate(self.meta):
            n = i + 1
            st = self.steps.get(n) or {}
            a = self.next_action(n, (self.pipes.get(n) or {}).get("started"))
            out[str(n)] = {"meta": {k: v for k, v in m.items() if not k.startswith("_")}, "variant": st.get("variant"),
                           "extracted": bool(st.get("extracted")) if m.get("pending") else m["kind"] == "doc", "result": st.get("result"),
                           "gates": {g["key"]: _public_gate(g) for g in self.gates.values() if g["step"] == n},
                           "pipeline": pipe_view(self.pipes[n]) if n in self.pipes else {"status": "idle"},
                           "next": {k: v for k, v in a.items() if k in ("do", "key", "label", "why")}}
        return out


def _events_by_document(case: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The case's journal split on its documents: what follows "Primit: <document>" belongs to it, up to the next one."""
    out: dict[str, list[dict[str, Any]]] = {}
    cur = None
    for e in case.get("events") or []:
        if e.get("kind") == "document" and e.get("document_id") and str(e.get("detail") or "").startswith("Primit:"):
            cur = e["document_id"]
            out.setdefault(cur, [])
            continue
        if cur:
            out[cur].append({k: e.get(k) for k in ("at", "kind", "action", "detail", "rule")})
    return out


def pipe_view(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p[k] for k in ("status", "stage", "error", "started_at")}


def _public_gate(g: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in g.items() if k != "draft"}


def _step_doc(n: int, variant: str) -> dict[str, Any]:
    return copy.deepcopy(VARIANT_B if n == 4 and variant.upper() == "B" else DOCUMENTS[n - 1])


def _api(base: str, method: str, path: str, body: Any = None) -> Any:
    return autopilot.api(base, method, path, body)


def _ok(r: Any) -> Any:
    if isinstance(r, dict) and "_http_error" in r:
        raise HTTPException(502 if r["_http_error"] >= 500 else 409, f"{r['_http_error']}: {r.get('detail')}")
    return r


HOOKS: dict[str, Callable[..., Any]] = {"receive": lambda doc: {}, "get_case": lambda cid: None}
runner = Runner()
RUNNERS: dict[str, Runner] = {DEMO_CASE: runner}


def reset_all() -> None:
    """POST /demo/reset (the whole bank again): every case's steps, gates, pipelines and AI calls are forgotten."""
    for r in list(RUNNERS.values()):
        r.reset()
    for cid in [k for k in RUNNERS if k != DEMO_CASE]:
        RUNNERS.pop(cid)


def runner_for(case: str | None) -> Runner:
    """Maria's runner (no case, or hers), else the case's own (created on first use; 404 for a case the bank lacks)."""
    if not case or case == DEMO_CASE:
        return runner
    if case not in RUNNERS:
        if HOOKS["get_case"](case) is None:
            raise HTTPException(404, f"dosarul {case} nu există în bancă")
        RUNNERS[case] = CaseRunner(case)
    return RUNNERS[case]


def make_router(receive: Callable[[dict[str, Any]], dict[str, Any]], get_case: Callable[[str], dict[str, Any] | None]) -> APIRouter:
    router = APIRouter()
    HOOKS.update(receive=receive, get_case=get_case)

    def base_of(request: Request) -> str:
        """The agents and gates call this same server on loopback, at the port it listens on (the browser may know
        it by another name)."""
        port = (request.scope.get("server") or (None, request.url.port))[1]
        return f"http://127.0.0.1:{port}"

    def check_n(n: int, r: Runner) -> Runner:
        if not 1 <= n <= r.count():
            raise HTTPException(404, f"pas inexistent (1..{r.count()})")
        return r

    @router.post("/demo/ai/extract/{n}")
    def extract(n: int, variant: str = "A", case: str | None = None) -> dict[str, Any]:
        return check_n(n, runner_for(case)).start_extract(n, variant)

    @router.post("/demo/ai/apply/{n}")
    def apply(n: int, variant: str = "A", case: str | None = None) -> dict[str, Any]:
        return check_n(n, runner_for(case)).apply(n, variant)

    @router.post("/demo/ai/agent/{n}/{key}")
    def agent(n: int, key: str, request: Request, case: str | None = None) -> dict[str, Any]:
        return check_n(n, runner_for(case)).start_agent(n, key, base_of(request))

    @router.post("/demo/ai/gate/{n}/{key}/{decision}")
    def gate(n: int, key: str, decision: str, request: Request, body: dict[str, Any] | None = None,
             case: str | None = None) -> dict[str, Any]:
        r = check_n(n, runner_for(case))
        if decision not in ("approve", "reject"):
            raise HTTPException(404)
        by = ((body or {}).get("by") or "operator demo").strip()
        return _public_gate(r.decide(n, key, decision == "approve", by, (body or {}).get("note") or "", base_of(request)))

    @router.post("/demo/ai/pipeline/{n}/{what}")
    def pipeline(n: int, what: str, request: Request, variant: str = "A", case: str | None = None) -> dict[str, Any]:
        r = check_n(n, runner_for(case))
        if what == "run":
            return r.run_pipeline(n, variant, base_of(request))
        if what == "stop":
            return r.stop_pipeline(n)
        raise HTTPException(404)

    @router.post("/demo/ai/audit")
    def audit(request: Request) -> dict[str, Any]:
        return runner.start_audit(base_of(request))

    @router.get("/demo/ai/jobs")
    def jobs(case: str | None = None) -> list[dict[str, Any]]:
        """The AI calls of one case (no ?case: Maria's, with the audit); ?case=all: every case's (the activity feed)."""
        return QUEUE.view() if case == "all" else runner_for(case).view()

    @router.get("/demo/ai/steps")
    def steps(case: str | None = None) -> dict[str, Any]:
        return runner_for(case).steps_view()

    @router.get("/demo/ai/gate/{n}/{key}/pdf")
    def gate_letter_pdf(n: int, key: str, case: str | None = None) -> Response:
        """The letter of a gate as PDF: what the operator checks (and signs) before it leaves, and what is attached."""
        g = runner_for(case).gates.get(f"{n}:{key}")
        if g is None or g.get("kind") != "letter":
            raise HTTPException(404, "nu există o scrisoare aici")
        name = f"{g.get('case_id')}-{g.get('action')}.pdf"
        return Response(gate_pdf(g), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})

    @router.get("/demo/ai/doc/{n}")
    def step_document(n: int, case: str | None = None) -> Response:
        """What the bank received at step n of a case (not Maria's: hers is /demo/scan/{n}/file): the file the extractor
        reads (a document still to come), else the document as it was extracted at intake (JSON)."""
        r = runner_for(case)
        if r is runner:
            raise HTTPException(404, "documentele Mariei: /demo/scan/{n}/file")
        check_n(n, r)
        m = r.meta[n - 1]
        if m["kind"] != "doc":
            raise HTTPException(404, "pasul nu e un document")
        scan = r.scan_for(n, "A")
        if scan is not None:
            return Response(scan.read_bytes(), media_type="text/plain; charset=utf-8",
                            headers={"Content-Disposition": f'inline; filename="{scan.name}"', "X-Content-Type-Options": "nosniff"})
        res = r.step(n).get("result") or {}
        doc = res.get("extracted") or (r.doc_for(n, "A") if r.pending(n) else {})
        body = {"document_id": m.get("document_id"), "document_type": m.get("document_type"), "received_on": m.get("date"),
                "confidence": doc.get("confidence"), "fields": doc.get("fields") or {}}
        return Response(json.dumps(body, ensure_ascii=False, indent=1), media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": f'inline; filename="{m.get("document_id")}.json"'})

    @router.get("/demo/scan/{n}.png")
    def scan_png(n: int, variant: str = "A") -> Response:
        check_n(n, runner)
        scan = scan_file(n, variant)
        if scan is None:
            raise HTTPException(404, "pasul 1 nu are scanare")
        import fitz
        pix = fitz.open(scan)[0].get_pixmap(dpi=45)
        return Response(pix.tobytes("png"), media_type="image/png", headers={"Cache-Control": "max-age=300"})

    return router


def label_of(job: dict[str, Any]) -> str:
    if job["agent"] == "case-investigator":
        return f"propunerea pentru escaladarea {job['escalation']}"
    if job["agent"] == "correspondent":
        return autopilot.LETTER_ACTIONS[job["action"]]
    return "mesajul către moștenitor cu ce mai lipsește"


def gate_pdf(g: dict[str, Any]) -> bytes:
    """The letter of a gate as the PDF that leaves (the same text the operator reads in the preview)."""
    from agent.letter_pdf import letter_pdf
    return letter_pdf(strip_artifact(g.get("preview") or ""), email=g.get("email") or DEMO_EMAIL, case_id=g.get("case_id"),
                      date=datetime.now(timezone.utc).strftime("%d.%m.%Y"), title=autopilot.LETTER_ACTIONS.get(g.get("action"), ""))


def strip_artifact(text: str) -> str:
    """An artifact without its metadata comment and title line (the UI shows its own title)."""
    lines = text.split("\n")
    while lines and (lines[0].startswith("<!--") or lines[0].startswith("# ") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)
