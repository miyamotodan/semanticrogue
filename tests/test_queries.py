"""Ogni query in queries/ esegue senza errori e restituisce almeno una riga sul mondo authored."""
from pathlib import Path

import pytest

from tools.common import ROOT, load_world

QUERIES = sorted((ROOT / "queries").glob("*.rq"))


def test_query_directory_is_populated():
    assert len(QUERIES) >= 5, "attese almeno 5 query in queries/"


@pytest.mark.parametrize("rq_path", QUERIES, ids=lambda p: p.name)
def test_query_runs_and_returns_rows(rq_path):
    world = load_world()
    result = world.query(rq_path.read_text(encoding="utf-8"))
    assert len(list(result)) >= 1, f"{rq_path.name} non restituisce righe"
