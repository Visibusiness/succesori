#!/usr/bin/env python3
"""Evaluate the LLM extractor against ground truth.

Ground truth: registries/documents/*.mvp.json (01–07) and registries/documents/hard/*.mvp.json (H1–H10), in the
shape of agent/demo_documents.py. Only the canonical fields (CANONICAL) are scored; the extra domain fields in
.mvp.json and the rich schema in the sibling *.json are ignored here. The text given to the extractor is the
sibling .md; for structured inputs without .md (01, H2: the DGEP feed line) it is the raw sibling .json.
Writes runs/eval-<ts>.json and runs/eval-latest.json; prints per document, per field and per set (main / hard).
Exit code 1 if accuracy is below --min (used by scripts/retro.py as the no-regression guard).

Sets: `train` (= main + hard + augmented, default) feeds runs/eval-latest.json, the only eval file retro-learner reads;
`holdout` (registries/documents/holdout/, unseen by the learner) goes to runs/eval-holdout-latest.json; `all` runs both and
reports them separately. --min is checked against the holdout when only the holdout runs, otherwise against train.
`holdout-aug` (061) = registries/documents/holdout-augmented/: the same three variants of holdout/ (`python -m
registries.generator.augment --source holdout`, other seed), also unseen by the learner; never part of `train`.
`--set holdout` stays the clean holdout. `holdout-aug` writes runs/eval-holdout-aug-latest.json and prints per variant.
`augmented` = registries/documents/augmented/ (059: variants ocr / fara-diacritice / formate of main + hard, from
`python -m registries.generator.augment`); its accuracy is also printed per variant (`_variant` in .mvp.json).
`real-text` (064) = registries/documents/real-text/: passages of REAL documents (blank forms, a notary's model letter,
quotes from judgments) plus real non-documents (forum posts, judgment paragraphs) that must come out `unknown`; never part
of `train`, forbidden to retro-learner; writes runs/eval-real-text-latest.json.

Usage: .venv/bin/python scripts/eval_extract.py [--set train|holdout|holdout-aug|real-text|all|main|hard|augmented] [--min 0.0] [--only 04]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "registries" / "documents"
SETS = {"main": DOCS, "hard": DOCS / "hard", "augmented": DOCS / "augmented", "holdout": DOCS / "holdout",
        "holdout-aug": DOCS / "holdout-augmented", "real-text": DOCS / "real-text"}
# 062: official forms filled with fictitious data, read as FILES (pdf / 300 dpi scan / phone photo) by agent.extract.extract_file.
# `forms` = the train certificates (retro-learner sees them), `forms-holdout` = CD09–12, CD19–22 (never shown to it).
FORMS = DOCS / "forms-real" / "certificat-deces"
FORM_SETS = {"forms": "train", "forms-holdout": "holdout"}
# fields scored on the forms in addition to CANONICAL (they exist only there)
FORM_FIELDS = {"name", "birth_date", "father", "mother", "death_record_number"}
TRAIN = ("main", "hard", "augmented")  # what retro-learner may see; `holdout` is never written to runs/eval-latest.json (048/049)
# DECISIONS „Evaluarea extracției”: ground truth = ce scrie în document. `reference`/`products` rămân în .mvp.json doar
# pentru pipeline (marcate `_deprecated_fields`) și nu se punctează.
CANONICAL = {"cnp", "date_of_death", "case_file", "document_number", "document_series", "initial_certificate",
             "claim_number", "notary_office", "notary_name", "hearing_date", "policy_id", "insurer", "loan_contract",
             "ibans", "testament", "heirs", "decision", "amount"}
import os  # noqa: E402

os.environ.setdefault("DEMO_MODE", "1")  # ground truth uses masked CNP/IBAN; without it every document caps at 0.5 (gate)
sys.path.insert(0, str(ROOT))
from agent.extract import FILE_TYPES, extract, extract_file  # noqa: E402


def norm(v):
    if isinstance(v, str):
        s = v.strip()
        try:
            return str(Fraction(s)) if "/" in s else s.lower()
        except (ValueError, ZeroDivisionError):
            return s.lower()
    if isinstance(v, list):
        return sorted(json.dumps(norm(x), sort_keys=True, ensure_ascii=False) for x in v)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return v


def _plain(v) -> str:
    """Majuscule, fără diacritice, spații simple."""
    s = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _frac(v):
    try:
        return Fraction(str(v).strip())
    except (ValueError, ZeroDivisionError):
        return v


def _heirs_ok(tv, gv) -> bool:
    """Nume (mulțime de cuvinte, majuscule, fără diacritice) + share ca fracție + minor ca bool; id și chei în plus ignorate."""
    if not isinstance(gv, list) or len(gv) != len(tv):
        return False
    key = lambda h: frozenset(_plain(h.get("name", "")).split())
    got = {key(h): h for h in gv if isinstance(h, dict)}
    for h in tv:
        g = got.get(key(h))
        if g is None or _frac(g.get("share")) != _frac(h.get("share")) or bool(g.get("minor")) != bool(h.get("minor")):
            return False
    return True


def field_ok(k, tv, gv) -> bool:
    if k in ("heirs", "ibans") and tv is None:  # real-text: blank form, nothing to copy
        return gv in (None, [])
    if k == "heirs":
        return _heirs_ok(tv, gv)
    if k == "insurer":  # prefixul ajunge: „UNIQA” == „UNIQA Asigurări de viață S.A.”
        return tv is None and gv is None or (bool(tv) and bool(gv) and _plain(tv).split()[0] == _plain(gv).split()[0])
    if k in ("name", "father", "mother"):  # aceleași cuvinte, orice ordine („RADU TRAIAN” == „Traian Radu”)
        return (tv is None and gv is None) or (bool(tv) and bool(gv) and sorted(_plain(tv).split()) == sorted(_plain(gv).split()))
    if k == "death_record_number" and gv is not None:
        return str(tv).strip().lstrip("0") == str(gv).strip().lstrip("0")
    if k in ("cnp", "ibans"):  # fără spații/puncte/cratime; X-urile mascate rămân (DEMO_MODE)
        clean = lambda x: re.sub(r"[\s.\-]", "", str(x)).upper()
        if k == "ibans":
            return isinstance(gv, list) and sorted(map(clean, tv)) == sorted(map(clean, gv))
        return (tv is None and gv is None) or (tv is not None and gv is not None and clean(tv) == clean(gv))
    return norm(tv) == norm(gv)


def compare(truth: dict, got: dict) -> dict:
    fields = {}
    tf, gf = truth.get("fields", {}), got.get("fields", {})
    deprecated = set(truth.get("_deprecated_fields", []))
    scored = CANONICAL | (FORM_FIELDS if truth.get("_split") else set())
    for k, tv in tf.items():
        if k not in scored or k in deprecated:
            continue
        fields[k] = {"ok": field_ok(k, tv, gf.get(k)), "truth": tv, "got": gf.get(k)}
    type_ok = truth.get("document_type") == got.get("document_type")
    # confidence gate must agree with truth: illegible docs must come out < 0.8
    gate_truth = float(truth.get("confidence", 1)) >= 0.8
    gate_got = float(got.get("confidence", 0)) >= 0.8
    return {"type_ok": type_ok, "gate_ok": gate_truth == gate_got, "fields": fields,
            "field_acc": (sum(f["ok"] for f in fields.values()) / len(fields)) if fields else 1.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["train", "holdout", "holdout-aug", "real-text", "all", *TRAIN, *FORM_SETS], default="train")
    ap.add_argument("--jobs", type=int, default=int(os.environ.get("EVAL_JOBS", "6")),
                    help="apeluri de extracție în paralel (setul forms: ~16 s/document)")
    ap.add_argument("--min", type=float, default=0.0)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    pairs = []  # (set, source text file, ground truth)
    for set_name, d in SETS.items():
        wanted = {"train": TRAIN, "holdout": ("holdout",), "holdout-aug": ("holdout-aug",), "real-text": ("real-text",),
                  "all": tuple(SETS)}.get(a.set, (a.set,))
        if set_name not in wanted:
            continue
        for js in sorted(d.glob("*.mvp.json")):
            stem = js.name.removesuffix(".mvp.json")
            src = d / f"{stem}.md" if (d / f"{stem}.md").exists() else d / f"{stem}.json"
            if src.exists():
                pairs.append((set_name, src, js))
    if a.set in FORM_SETS:
        for js in sorted(FORMS.glob("CD*.mvp.json")):
            truth = json.loads(js.read_text(encoding="utf-8"))
            if truth.get("_split") == FORM_SETS[a.set]:
                pairs.append((a.set, DOCS / truth["raw_name"], js))
    if a.only:
        pairs = [p for p in pairs if a.only in p[1].name]
    if not pairs:
        print(f"nu există ground truth *.mvp.json în {DOCS}", file=sys.stderr)
        return 2
    def run_one(item):
        set_name, md, js = item
        truth = json.loads(js.read_text(encoding="utf-8"))
        try:
            if md.suffix.lower() in FILE_TYPES:   # forms: the model reads the file, not our text
                got = extract_file(md, md.name)
            else:
                got = extract(md.read_text(encoding="utf-8"), md.name)
            err = None
        except Exception as e:  # noqa: BLE001
            got, err = {"document_type": "unknown", "confidence": 0, "fields": {}}, str(e)
        cmp = compare(truth, got)
        return {"set": set_name, "document": md.name, "truth": truth, "got": got, "error": err, **cmp}

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        results = list(pool.map(run_one, pairs))
    for r in results:
        bad = [k for k, f in r["fields"].items() if not f["ok"]]
        print(f"{r['document']:40s} tip={'ok' if r['type_ok'] else 'GREȘIT'} gate={'ok' if r['gate_ok'] else 'GREȘIT'} "
              f"câmpuri={r['field_acc']:.0%} {'greșite: ' + ', '.join(bad) if bad else ''}{' EROARE: ' + r['error'] if r['error'] else ''}")
    print("\nPe câmp (toate documentele în care câmpul apare în ground truth):")
    for k in sorted({k for r in results for k in r["fields"]}):
        oks = [r["fields"][k]["ok"] for r in results if k in r["fields"]]
        print(f"  {k:16s} {sum(oks)}/{len(oks)}")
    by_set = {}
    for set_name in [*SETS, *FORM_SETS]:
        rs = [r for r in results if r["set"] == set_name]
        if rs:
            by_set[set_name] = {"n": len(rs), "field_accuracy": sum(r["field_acc"] for r in rs) / len(rs),
                                "type_accuracy": sum(r["type_ok"] for r in rs) / len(rs),
                                "gate_accuracy": sum(r["gate_ok"] for r in rs) / len(rs)}
            b = by_set[set_name]
            print(f"SET {set_name:4s} (n={b['n']}): câmpuri {b['field_accuracy']:.1%} · tip {b['type_accuracy']:.1%} · "
                  f"prag {b['gate_accuracy']:.1%}")
    by_variant_of = {}
    for set_name in ("augmented", "holdout-aug", *FORM_SETS):
        groups = {}
        for r in results:
            if r["set"] == set_name:
                groups.setdefault(r["truth"].get("_variant", "?"), []).append(r)
                if set_name in FORM_SETS:   # also per form model: new physical / new electronic / old
                    groups.setdefault("model " + r["truth"].get("_model", "?"), []).append(r)
        by_variant_of[set_name] = {
            v: {"n": len(rs), "field_accuracy": sum(r["field_acc"] for r in rs) / len(rs),
                "type_accuracy": sum(r["type_ok"] for r in rs) / len(rs),
                "gate_accuracy": sum(r["gate_ok"] for r in rs) / len(rs)} for v, rs in sorted(groups.items())}
        for v, b in by_variant_of[set_name].items():
            print(f"  {set_name} / {v:16s} (n={b['n']}): câmpuri {b['field_accuracy']:.1%} · tip {b['type_accuracy']:.1%} · "
                  f"prag {b['gate_accuracy']:.1%}")
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ts = at.replace(":", "")
    gate_acc = None
    for kind, names, prefix in (("train", TRAIN, "eval"), ("holdout", ("holdout",), "eval-holdout"),
                                ("holdout-aug", ("holdout-aug",), "eval-holdout-aug"), ("real-text", ("real-text",), "eval-real-text"),
                                ("forms", ("forms",), "eval-forms"), ("forms-holdout", ("forms-holdout",), "eval-forms-holdout")):
        rs = [r for r in results if r["set"] in names]
        if not rs:
            continue
        acc = sum(r["field_acc"] for r in rs) / len(rs)
        types = sum(r["type_ok"] for r in rs) / len(rs)
        gates = sum(r["gate_ok"] for r in rs) / len(rs)
        summary = {"at": at, "kind": kind, "n": len(rs), "field_accuracy": acc, "type_accuracy": types,
                   "gate_accuracy": gates, "by_set": {k: v for k, v in by_set.items() if k in names},
                   **({"by_variant": bv} if (bv := by_variant_of.get({"train": "augmented"}.get(kind, kind))) else {}),
                   "results": rs}
        out = runs / f"{prefix}-{ts}.json"
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        (runs / f"{prefix}-latest.json").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\n{kind.upper():8s}: câmpuri {acc:.1%} · tip {types:.1%} · prag de încredere {gates:.1%} · {out.relative_to(ROOT)}")
        if gate_acc is None or kind == "train":
            gate_acc = acc
    if a.set == "all":
        tr = [r["field_acc"] for r in results if r["set"] in TRAIN]
        ho = [r["field_acc"] for r in results if r["set"] == "holdout"]
        if tr and ho:
            print(f"DIFERENȚĂ train - holdout: {(sum(tr)/len(tr) - sum(ho)/len(ho))*100:+.1f} pct (mare = supra-învățare)")
    return 0 if gate_acc >= a.min else 1

if __name__ == "__main__":
    raise SystemExit(main())
