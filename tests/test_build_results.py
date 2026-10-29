"""079: ecranul „Rezultate” — fiecare cifră din results.json are sursa și data, iar ce lipsește are motivul."""
import json

from scripts import build_results


def _metrics(o, path=""):
    if isinstance(o, dict):
        if "valoare" in o and "unitate" in o:
            yield path, o
        for k, v in o.items():
            yield from _metrics(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _metrics(v, f"{path}[{i}]")


def test_every_figure_has_a_source_or_a_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(build_results, "OUT", tmp_path / "results.json")
    monkeypatch.setattr(build_results, "OUT_JS", tmp_path / "results-data.js")
    build_results.main()
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert {"citire", "cost", "timp", "stabilitate", "siguranta", "date_reale", "invatare"} <= set(data)
    figures = list(_metrics(data))
    assert len(figures) > 20
    for path, m in figures:
        if m["valoare"] is None:
            assert m.get("motiv"), path
        else:
            assert m["sursa"], path
    assert (tmp_path / "results-data.js").read_text(encoding="utf-8").startswith("// generat")


def test_missing_eval_set_is_null_with_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(build_results, "RUNS", tmp_path)
    sets = {s["set"]: s for s in build_results.extraction()["seturi"]}
    assert sets["holdout"]["campuri"]["valoare"] is None and sets["holdout"]["campuri"]["motiv"]
