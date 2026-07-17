"""Il motore di M3: stato iniziale, letture SPARQL e transizioni sul runtime graph."""
import pytest
from rdflib import Literal, Namespace
from rdflib.namespace import RDF

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, Engine, ActionError, new_state

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


def test_move_to_valid_room(eng):
    eng.move_to(EX.ossuary02)
    assert eng.current_room() == EX.ossuary02
    # Il passaggio è bidirezionale: si può tornare indietro.
    eng.move_to(EX.entrance01)
    assert eng.current_room() == EX.entrance01


def test_move_to_unreachable_room_is_rejected(eng):
    with pytest.raises(ActionError):
        eng.move_to(EX.sanctum01)
    assert eng.current_room() == EX.entrance01  # nessuna modifica


def test_open_portal_requires_key_and_presence(eng):
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # non è nemmeno nella stanza
    eng.state.set((PLAYER, SR.currentRoom, EX.crypt07))
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # manca la chiave
    eng.state.add((PLAYER, SR.hasItem, EX.ivoryKey))
    eng.open_portal(EX.sealedGate)
    assert (EX.sealedGate, SR.isOpen, Literal(True)) in eng.state
    # Ora il portale aperto è una mossa: si può entrare nel santuario.
    moves = {row.stanza for row in eng.run_query("available-moves.rq")}
    assert EX.sanctum01 in moves
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # già aperto


def test_moving_into_cleared_target_room_completes_active_quest(eng):
    # cullTheSpores attiva; il nido è già stato ripulito (mostri segnati sconfitti).
    eng.state.add((EX.cullTheSpores, SR.questStatus, Literal("active")))
    eng.state.add((EX.myceliumBrute, SR.isAlive, Literal(False)))
    eng.state.add((EX.sporeMother, SR.isAlive, Literal(False)))
    eng.state.set((PLAYER, SR.currentRoom, EX.fungalHollow01))
    eng.move_to(EX.sporeNest02)
    assert (EX.cullTheSpores, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.boneBlade) in eng.state
