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
    # player (tipo + currentRoom) + start room visitata: assenza di tripla = default
    assert len(state) == 3


def test_new_state_marks_start_room_visited():
    state = new_state(WORLD)
    assert (EX.entrance01, SR.visited, Literal(True)) in state


def test_move_to_marks_destination_visited(eng):
    assert (EX.ossuary02, SR.visited, Literal(True)) not in eng.state
    eng.move_to(EX.ossuary02)
    assert (EX.ossuary02, SR.visited, Literal(True)) in eng.state


def test_visited_is_idempotent(eng):
    eng.move_to(EX.ossuary02)
    eng.move_to(EX.entrance01)
    eng.move_to(EX.ossuary02)  # di nuovo
    assert len(list(eng.state.triples((EX.ossuary02, SR.visited, None)))) == 1


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


def test_fight_defeats_monster_and_collects_drops(eng):
    eng.state.set((PLAYER, SR.currentRoom, EX.ossuary02))
    won = eng.fight()  # un solo mostro: il bersaglio è implicito
    assert won is True
    assert (EX.cryptRat, SR.isAlive, Literal(False)) in eng.state
    assert (PLAYER, SR.hasItem, EX.rustSword) in eng.state
    assert eng.run_query("monsters-here.rq") == []


def test_fight_requires_target_when_room_has_many_monsters(eng):
    eng.state.set((PLAYER, SR.currentRoom, EX.sporeNest02))  # Bruto + Madre delle Spore
    with pytest.raises(ActionError):
        eng.fight()
    assert eng.fight(EX.myceliumBrute) is True


def test_fight_without_monsters_is_rejected(eng):
    with pytest.raises(ActionError):
        eng.fight()  # entrance01 è vuota


def test_fight_lost_kills_player():
    state = new_state(WORLD)
    losing = Engine(WORLD, state, player_success=0.0, seed=1)
    losing.state.set((PLAYER, SR.currentRoom, EX.ossuary02))
    assert losing.fight() is False
    assert (PLAYER, SR.isAlive, Literal(False)) in losing.state
    assert losing.outcome() == "defeat"


def test_fight_last_monster_in_target_room_completes_quest(eng):
    eng.state.add((EX.recoverRelic, SR.questStatus, Literal("active")))
    eng.state.set((PLAYER, SR.currentRoom, EX.sanctum01))
    eng.fight()  # il Tiranno della Cripta è l'unico mostro del santuario
    assert (EX.recoverRelic, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.sanctumRelic) in eng.state  # ricompensa della quest
    assert eng.outcome() == "victory"


def test_talk_to_activates_all_unaccepted_quests(eng):
    activated = eng.talk_to(EX.graveHermit)
    assert set(activated) == {EX.recoverRelic, EX.endTheCourt}
    assert (EX.recoverRelic, SR.questStatus, Literal("active")) in eng.state
    with pytest.raises(ActionError):
        eng.talk_to(EX.graveHermit)  # niente più quest da offrire
    with pytest.raises(ActionError):
        eng.talk_to(EX.ashPriest)  # è in un'altra stanza


def test_outcome_none_during_normal_play(eng):
    assert eng.outcome() is None


def test_talk_to_completes_quest_already_satisfied(eng):
    # Il player è nella target room di endTheCourt, già ripulita, e solo ora
    # accetta la quest da un NPC posto lì: deve completarsi subito.
    eng.state.set((PLAYER, SR.currentRoom, EX.throneVault01))
    eng.state.add((EX.deadKing, SR.isAlive, Literal(False)))          # target room ripulita
    eng.state.add((EX.graveHermit, SR.npcInRoom, EX.throneVault01))   # NPC presente qui
    eng.talk_to(EX.graveHermit)
    assert (EX.endTheCourt, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.relicOfDawn) in eng.state          # reward di endTheCourt
