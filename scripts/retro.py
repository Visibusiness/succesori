#!/usr/bin/env python3
"""The learning loop: eval -> retro-learner updates skills -> eval again -> keep only if no regression.

  .venv/bin/python scripts/retro.py            # one cycle
  .venv/bin/python scripts/retro.py --cycles 3 # repeat; each cycle sees the previous errors
The learner sees only train (main+hard+augmented) errors; the keep/revert guard is measured on registries/documents/holdout/
(049) and, when it exists, on holdout-augmented/ (061): the mean of the two accuracies.

"Training" here means growing the skills in .claude/skills from evidence (eval errors,
operator corrections, auditor findings), guarded by a measurable metric. Code is never
changed by the loop; proposals for code/rule changes land in docs/DECISIONS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
PY = ROOT / ".venv" / "bin" / "python"
LOCK = ROOT / "runs" / ".retro.lock"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:   # exists, owned by someone else
        return True
    return True


def acquire_lock() -> None:
    """Only one learning loop at a time: two runs share .claude/skills (git add -A) and runs/eval-latest.json and
    contaminate each other's before/after numbers (039). O_EXCL lock with PID + time; a lock left by a dead
    process is detected by its PID and taken over."""
    LOCK.parent.mkdir(exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                info = json.loads(LOCK.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                info = {}
            pid = int(info.get("pid") or 0)
            if pid and _pid_alive(pid):
                raise SystemExit(f"retro.py rulează deja (PID {pid}, pornit la {info.get('started_at')}, "
                                 f"de {info.get('user')}). Așteaptă să termine; lock: {LOCK.relative_to(ROOT)}")
            print(f"lock rămas de la un proces oprit (PID {pid or '?'}); îl preiau")
            LOCK.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "user": os.environ.get("CLAUDE_CONFIG_DIR", os.environ.get("USER", "?")).rsplit("-", 1)[-1],
                       "argv": sys.argv[1:]}, f)
        return
    raise SystemExit("nu pot lua lock-ul retro")


def release_lock() -> None:
    try:
        if json.loads(LOCK.read_text(encoding="utf-8")).get("pid") == os.getpid():
            LOCK.unlink()
    except (OSError, ValueError):
        pass


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)


EVAL_FILES = {"train": "eval-latest.json", "holdout": "eval-holdout-latest.json",
              "holdout-aug": "eval-holdout-aug-latest.json",
              # 062: official forms read as files; learner sees `forms`, guard is `forms-holdout` (CD09–12, CD19–22)
              "forms": "eval-forms-latest.json", "forms-holdout": "eval-forms-holdout-latest.json"}
DOMAIN = "text"   # set from --domain


MAX_FAILED_CALLS = 0.2  # over 20% failed calls => the eval is not a measurement


def evaluate(which: str = "train") -> float | None:
    """Field accuracy on `train` (main+hard+augmented; writes runs/eval-latest.json, the file retro-learner reads), on
    `holdout` (unseen by the learner; runs/eval-holdout-latest.json) or on `holdout-aug` (augmented holdout, also unseen;
    runs/eval-holdout-aug-latest.json). None when the set has no documents."""
    p = subprocess.run([str(PY), "scripts/eval_extract.py", "--set", which], cwd=ROOT, text=True, capture_output=True)
    print(p.stdout[-1500:])
    if p.returncode == 2:
        if which == "train":
            raise SystemExit("nu există documente de evaluat (registries/documents/*.md + .json)")
        return None
    data = json.loads((ROOT / "runs" / EVAL_FILES[which]).read_text(encoding="utf-8"))
    # An eval where the model calls failed (rate limit, usage limit, network) measures nothing; comparing it would
    # "revert" good lessons or keep bad ones. Stop the run instead and say why (28 oct: 24/24 calls failed, 1,6%).
    results = data.get("results") or []
    failed = [r for r in results if r.get("error")]
    if results and len(failed) / len(results) > MAX_FAILED_CALLS:
        raise SystemExit(f"eval {which} invalid: {len(failed)}/{len(results)} apeluri la model au eșuat "
                         f"(ex.: {failed[0]['error'][:120]}). Verifică limita contului / API-ul; nimic nu s-a schimbat.")
    return data["field_accuracy"]


def guard_score(ho: float | None, ha: float | None, tr: float) -> float:
    """What the keep/revert guard compares: the mean of holdout and holdout-aug (those that exist), else train."""
    vals = [v for v in (ho, ha) if v is not None]
    return sum(vals) / len(vals) if vals else tr


def fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def retro(round_no: int) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if DOMAIN == "forms":
        prompt = (
            f"Ești agentul retro-learner (.claude/agents/retro-learner.md). Runda {round_no}. Domeniul: certificate de deces "
            f"reale (formulare oficiale MAI 2024 și model vechi HG 64/2011) citite de extractor DIRECT din fișier (PDF, scan, "
            f"fotografie). Citește runs/eval-forms-latest.json (erorile pe certificatele de antrenare) și actualizează "
            f".claude/skills/extract-documents/SKILL.md cu lecții concrete despre citirea acestor formulare (unde e fiecare "
            f"rubrică, cum se scriu valorile, ce câmpuri lipsesc). Poți deschide imaginile certificatelor de antrenare "
            f"(registries/documents/forms-real/certificat-deces/CD01–CD08, CD13–CD18). Scrie raportul în runs/retro-{ts}.md. "
            f"Nu modifica agent/, tests/, kb/, scripts/. INTERZIS: certificatele CD09–CD12 și CD19–CD22 (orice fișier al lor) "
            f"și runs/eval-forms-holdout*.json: sunt setul de validare; nu le citi și nu pune nimic din ele în skill-uri. "
            f"La fel de interzise: registries/documents/real-text/ și runs/eval-real-text*.json (064).")
        p = subprocess.run(["claude", "-p", "--model", "sonnet", "--dangerously-skip-permissions", prompt],
                           cwd=ROOT, text=True, capture_output=True, timeout=1200)
        print(p.stdout[-2000:])
        if p.returncode != 0:
            print(p.stderr[-500:], file=sys.stderr)
        return
    prompt = (
        f"Ești agentul retro-learner (.claude/agents/retro-learner.md). Runda {round_no}. "
        f"Citește runs/eval-latest.json, ultimele runs/*/trace.jsonl, runs/*/operator.jsonl și runs/*/audit.md (dacă există), "
        f"apoi actualizează skill-urile din .claude/skills conform instrucțiunilor tale. Scrie raportul în runs/retro-{ts}.md. "
        f"Nu modifica agent/, tests/, kb/. Setul de validare registries/documents/holdout/ și runs/eval-holdout*.json sunt "
        f"interzise: nu le citi și nu pune exemple din ele în skill-uri (măsurăm dacă lecțiile generalizează). "
        f"La fel sunt interzise registries/documents/holdout-augmented/ (varianta stricată a holdout-ului) și "
        f"runs/eval-holdout-aug*.json. Interzise și registries/documents/real-text/ (setul din text real, 064) și "
        f"runs/eval-real-text*.json."
    )
    p = subprocess.run(["claude", "-p", "--model", "sonnet", "--dangerously-skip-permissions", prompt],
                       cwd=ROOT, text=True, capture_output=True, timeout=900)
    print(p.stdout[-2000:])
    if p.returncode != 0:
        print(p.stderr[-500:], file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--tolerance", type=float, default=1.0,
                    help="puncte procentuale de scădere acceptate (zgomotul evalului LLM ~0,8)")
    ap.add_argument("--domain", choices=["text", "forms"], default="text",
                    help="text = documentele .md (main/hard/augmented + holdout); forms = certificatele oficiale citite din fișier (062)")
    a = ap.parse_args()
    global DOMAIN
    DOMAIN = a.domain
    acquire_lock()
    try:
        return run(a.cycles, a.tolerance)
    finally:
        release_lock()


def run(cycles: int, tolerance: float) -> int:
    """Learner sees only train errors; the keep/revert guard is measured on the holdout and holdout-aug (048/049/061), so
    overfitting to the train documents shows up as a drop (or no gain) there instead of hiding behind a train score of 100%."""
    sh("git", "add", "-A", str(SKILLS))
    sh("git", "commit", "-qm", "[retro] baseline skills before cycle", check=False)
    if DOMAIN == "forms":
        return run_forms(cycles, tolerance)
    tr_before = evaluate("train")
    ho_before = evaluate("holdout")
    ha_before = evaluate("holdout-aug")
    guard = "+".join(n for n, v in (("holdout", ho_before), ("holdout-aug", ha_before)) if v is not None) or "train"
    before = guard_score(ho_before, ha_before, tr_before)
    print(f"\n== acuratețe înainte: train {tr_before:.1%} · holdout {fmt(ho_before)} · holdout-aug {fmt(ha_before)}"
          f" (garda pe media {guard}: {before:.1%})")
    for i in range(1, cycles + 1):
        print(f"\n== retro-learner, ciclul {i}")
        retro(i)
        tr_after = evaluate("train")
        ho_after = evaluate("holdout")
        ha_after = evaluate("holdout-aug")
        after = guard_score(ho_after, ha_after, tr_after)
        print(f"== după ciclul {i}: train {tr_before:.1%} -> {tr_after:.1%} · holdout {fmt(ho_before)} -> {fmt(ho_after)} · "
              f"holdout-aug {fmt(ha_before)} -> {fmt(ha_after)} (garda pe {guard}: {before:.1%} -> {after:.1%})")
        tag = (f"train {tr_before:.1%}->{tr_after:.1%}" + (f", holdout {ho_before:.1%}->{ho_after:.1%}" if ho_after is not None else "")
               + (f", holdout-aug {ha_before:.1%}->{ha_after:.1%}" if ha_after is not None else ""))
        if after + 1e-9 < before - tolerance / 100.0:
            # Only extract-documents is measured by the eval; the other skills (heir-messaging,
            # correspondence, escalation-playbook, succession-domain) hold operator-reviewed lessons
            # and must not be thrown away because of extraction noise.
            print(f"REGRESIE pe {guard} peste toleranță ({tolerance} pct): revin doar la extract-documents")
            sh("git", "checkout", "--", str(SKILLS / "extract-documents"))
            sh("git", "add", "-A", str(SKILLS))
            sh("git", "commit", "-qm", f"[retro] ciclul {i}: lecții non-extracție păstrate; extract-documents revenit ({tag})", check=False)
            tr_after, ho_after, ha_after = tr_before, ho_before, ha_before  # state is back to what was measured before the cycle
        else:
            sh("git", "add", "-A", str(SKILLS))
            sh("git", "commit", "-qm", f"[retro] ciclul {i}: {tag}", check=False)
            before = after
        tr_before, ho_before, ha_before = tr_after, ho_after, ha_after
    return 0


def run_forms(cycles: int, tolerance: float) -> int:
    """062: learn from the train certificates (forms), keep a cycle only if forms-holdout does not drop beyond tolerance."""
    tr_before, ho_before = evaluate("forms"), evaluate("forms-holdout")
    print(f"\n== certificate înainte: train {fmt(tr_before)} · holdout {fmt(ho_before)}")
    for i in range(1, cycles + 1):
        print(f"\n== retro-learner (forms), ciclul {i}")
        retro(i)
        tr_after, ho_after = evaluate("forms"), evaluate("forms-holdout")
        tag = f"forms train {fmt(tr_before)}->{fmt(tr_after)}, holdout {fmt(ho_before)}->{fmt(ho_after)}"
        print(f"== după ciclul {i}: {tag}")
        if ho_after + 1e-9 < ho_before - tolerance / 100.0:
            print(f"REGRESIE pe forms-holdout peste toleranță ({tolerance} pct): revin la extract-documents")
            sh("git", "checkout", "--", str(SKILLS / "extract-documents"))
            sh("git", "commit", "-qm", f"[retro] forms ciclul {i}: revenit ({tag})", check=False)
            continue
        sh("git", "add", "-A", str(SKILLS))
        sh("git", "commit", "-qm", f"[retro] forms ciclul {i}: {tag}", check=False)
        tr_before, ho_before = tr_after, ho_after
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
