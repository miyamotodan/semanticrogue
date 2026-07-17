"""Il motore di M3: stato iniziale, letture SPARQL e transizioni sul runtime graph."""
import pytest
from rdflib import Literal, Namespace
from rdflib.namespace import RDF

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, Engine, new_state

WORLD = load_runtime_world()


@pytest.fixture
def eng():
    return Engine(WORLD, new_state(WORLD))


def test_new_state_puts_player_in_start_room():
    state = new_state(WORLD)
    assert (PLAYER, RDF.type, SR.Player) in state
    assert (PLAYER, SR.currentRoom, EX.entrance01) in state
    assert len(state) == 2  # solo player: assenza di tripla = stato di default


def test_available_moves_from_start(eng):
    moves = {row.stanza for row in eng.run_query("available-moves.rq")}
    assert moves == {EX.ossuary02, EX.chapel03}


def test_monsters_and_npcs_visible(eng):
    assert [r.mostro for r in eng.run_query("monsters-here.rq")] == []  # entrance01 è sicura
    npcs = {(r.npc, r.quest) for r in eng.run_query("npcs-here.rq")}
    assert (EX.graveHermit, EX.recoverRelic) in npcs
    assert (EX.graveHermit, EX.endTheCourt) in npcs


def test_openable_portals_requires_key_and_presence(eng):
    # Il player è all'ingresso senza chiavi: nessun portale apribile.
    assert eng.run_query("openable-portals.rq") == []
    # Con la chiave giusta nella stanza giusta il portale compare.
    eng.state.set((PLAYER, SR.currentRoom, EX.crypt07))
    eng.state.add((PLAYER, SR.hasItem, EX.ivoryKey))
    rows = eng.run_query("openable-portals.rq")
    assert [(r.portale, r.stanza) for r in rows] == [(EX.sealedGate, EX.sanctum01)]


def test_quest_status_reports_all_quests(eng):
    rows = {(r.quest, r.status) for r in eng.run_query("quest-status.rq")}
    assert (EX.recoverRelic, None) in rows
    assert (EX.endTheCourt, None) in rows
    assert (EX.cullTheSpores, None) in rows
