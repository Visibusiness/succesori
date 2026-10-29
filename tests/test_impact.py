"""082: dovezile de impact — referința independentă dă cifrele din KB, pipeline-ul în proces le reproduce pe dosarul demo,
simularea e deterministă și nu plătește nimic fără aprobare, jurnalul e-2-e și studiul de timp se citesc corect."""
import csv
import json

import pytest

pytest.importorskip("registries.simulare.generator", reason="registries/simulare/ lipsește (ex. repo de predare fără el)")

from registries.simulare import generator, referinta  # noqa: E402
from scripts import impact_automation, impact_simulare, impact_studiu  # noqa: E402


def test_reference_gives_the_kb_values_on_the_demo_case():
    e = referinta.expected(generator.maria_case())   # kb/scenariu-demo/maria-ionescu.md §2
    assert (e["fees_reversed"], e["pension_kept"], e["pension_return"], e["remaining_debt"]) == (6000, 210000, 210000, 2663)
    assert e["net_account"] == 527337 and e["payable_now"] == 428461
    lines = {(l["name"].split()[0], l["product_id"]): (l["amount"], l["blocked"]) for l in e["lines"]}
    assert lines == {("Ion", "CC-1"): (329585, False), ("Andrei", "CC-1"): (98876, False), ("Elena", "CC-1"): (98876, True),
                     ("Ion", "DEP-1"): (1315000, True), ("Andrei", "DEP-1"): (394500, True), ("Elena", "DEP-1"): (394500, True)}


def test_pipeline_in_process_matches_the_reference_on_the_demo_case():
    c = generator.maria_case()
    cmp = impact_simulare.compare(c, referinta.expected(c), impact_simulare.run_case(c))
    assert cmp["issues"] == [] and cmp["lines_ok"] == cmp["lines_total"] == 6


def test_reference_split_is_exact_and_breaks_ties_by_certificate_order():
    from fractions import Fraction as F
    assert referinta.split(100, [F(1, 3)] * 3) == [34, 33, 33]
    assert sum(referinta.split(527337, [F(5, 8), F(3, 16), F(3, 16)])) == 527337


def test_generator_is_deterministic_and_covers_every_trap():
    a, b = generator.generate(82, 200), generator.generate(82, 200)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    exp = [referinta.expected(c) for c in a]
    for key, _, has in impact_simulare.TRAPS:
        assert sum(has(c, e) for c, e in zip(a, exp)) >= 10, key


def test_no_payment_without_approval_at_scale():
    for c in generator.generate(82, 200):
        got = impact_simulare.run_case(c)
        assert got["paid_before_approval"] == 0, c["id"]


def test_automation_reads_the_committed_e2e_run():
    res = impact_automation.analyse(impact_automation.latest_run())
    o = res["operatiuni"]
    assert o["total"] == o["automat"] + o["agent_ai"] + o["uman_executat"] + o["uman_deschis"] > 0
    assert len(res["douasprezece"]) == 12 and all(r["facut"] for r in res["douasprezece"])
    assert res["reactie"]["pipeline_mediana_s"] is not None


def test_time_study_grading(tmp_path):
    key = impact_studiu.KEY
    rows = [["participant", "sarcina", "start", "stop", "camp", "valoare"]]
    for t in impact_studiu.TASKS:
        for i, (c, (kind, v)) in enumerate(key[t]["campuri"].items()):
            val = {"text": "x", "v": "da", "da_nu": v}.get(kind, v)
            rows.append(["ana", t, "10:00:00" if i == 0 else "", "10:05:30" if i == 0 else "", c, val])
    rows[2][5] = "692,39"   # T1 dep_principal → greșit cu un ban (rândul 2 = al doilea câmp din T1)
    p = tmp_path / "ana.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)
    r = impact_studiu.read_participant(p)
    assert r["greseli_total"] == 1 and r["secunde_total"] == 6 * 330
    assert impact_studiu.grade("lei", "5273.37", "5.273,37") and impact_studiu.grade("fractie", "5/8", "10/16")


def test_time_study_scores_the_agent_with_the_same_key():
    ans, times, _ = impact_studiu.agent_answers(impact_automation.latest_run())
    sc = impact_studiu.score(ans)
    for t in ("T1", "T3", "T4", "T5"):
        assert sc[t]["greseli"] == 0, (t, sc[t]["detalii"])
    assert all(times[t] is not None for t in impact_studiu.TASKS)
