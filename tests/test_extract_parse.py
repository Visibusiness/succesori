"""062: the extractor's answer may hold more than one JSON object or a note with braces; take the first object."""
import pytest

from agent.extract import _parse_json


def test_first_object_wins_over_trailing_json_or_braces():
    assert _parse_json('```json\n{"document_type": "death_certificate", "fields": {"cnp": null}}\n```\n{"note": 1}') == {
        "document_type": "death_certificate", "fields": {"cnp": None}}
    assert _parse_json('Notă {fără json} apoi {"a": {"b": 2}} și {x}') == {"a": {"b": 2}}


def test_no_json_raises():
    with pytest.raises(ValueError):
        _parse_json("nimic aici")
