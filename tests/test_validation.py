"""La validazione SHACL passa sul dataset authored e fallisce sui dati rotti."""
from pathlib import Path

from pyshacl import validate

from tools.common import DATASET, ONTOLOGY, SHAPES, load_graph


def run_validation(data_path: Path):
    """Valida ontologia+dati contro le shape. Ritorna (conforms, results_graph, results_text)."""
    data = load_graph(ONTOLOGY, data_path)
    shapes = load_graph(SHAPES)
    return validate(data, shacl_graph=shapes, advanced=True)


def test_authored_dataset_conforms():
    conforms, _, text = run_validation(DATASET)
    assert conforms, f"Il dataset authored deve essere conforme alle shape:\n{text}"


import pytest
from rdflib import Namespace

SR = Namespace("http://example.org/semantic-roguelike#")
EX = Namespace("http://example.org/id/")
SH = Namespace("http://www.w3.org/ns/shacl#")
INVALID = Path(__file__).resolve().parent / "invalid"

# (file, focus node atteso, ("path", resultPath) per property shape
#  oppure ("shape", NodeShape) per vincoli SPARQL-based)
BROKEN_CASES = [
    ("room-no-biome.ttl", EX.brokenRoom, ("path", SR.locatedInBiome)),
    ("room-danger-out-of-range.ttl", EX.brokenRoom, ("path", SR.dangerLevel)),
    ("monster-no-faction.ttl", EX.brokenMonster, ("path", SR.belongsToFaction)),
    ("boss-no-loot.ttl", EX.brokenBoss, ("path", SR.dropsItem)),
    ("portal-nowhere.ttl", EX.brokenPortal, ("path", SR.portalInRoom)),
    ("dangerous-room-empty.ttl", EX.brokenRoom, ("shape", SR.DangerousRoomMustHaveContent)),
    ("portal-unobtainable-key.ttl", EX.brokenPortal, ("shape", SR.RequiredKeyMustExistInWorld)),
    ("orphan-key.ttl", EX.orphanKey, ("shape", SR.OrphanKeyShape)),
    ("unreachable-room.ttl", EX.lostRoom, ("shape", SR.UnreachableRoomShape)),
    ("lock-key-cycle.ttl", EX.cyclePortal, ("shape", SR.LockKeyCycleShape)),
]


@pytest.mark.parametrize("fname,focus,expected", BROKEN_CASES, ids=[c[0] for c in BROKEN_CASES])
def test_broken_case_triggers_expected_shape(fname, focus, expected):
    conforms, results, text = run_validation(INVALID / fname)
    assert not conforms, f"{fname} dovrebbe violare le shape"
    kind, value = expected
    prop = SH.resultPath if kind == "path" else SH.sourceShape
    matching = [r for r in results.subjects(SH.focusNode, focus)
                if (r, prop, value) in results]
    assert matching, f"attesa violazione {value} su {focus} in {fname}; report:\n{text}"
