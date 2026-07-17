"""Le shape runtime intercettano stati di partita corrotti — ciascuno dalla shape attesa."""
import pytest
from rdflib import Graph, Literal, Namespace

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, new_state, validate_runtime

SH = Namespace("http://www.w3.org/ns/shacl#")
WORLD = load_runtime_world()


def test_fresh_state_conforms():
    conforms, _, text = validate_runtime(WORLD, new_state(WORLD))
    assert conforms, f"lo stato iniziale deve essere conforme:\n{text}"


def broken_two_rooms():
    state = new_state(WORLD)
    state.add((PLAYER, SR.currentRoom, EX.ossuary02))  # seconda stanza: vietato
    return state, PLAYER, ("path", SR.currentRoom)


def broken_quest_status_value():
    state = new_state(WORLD)
    state.add((EX.recoverRelic, SR.questStatus, Literal("paused")))
    return state, EX.recoverRelic, ("path", SR.questStatus)


def broken_open_portal_without_key():
    state = new_state(WORLD)
    state.add((EX.sealedGate, SR.isOpen, Literal(True)))  # aperto ma chiave mai ottenuta
    return state, EX.sealedGate, ("shape", SR.OpenPortalNeedsKeyShape)


def broken_item_from_living_monster():
    state = new_state(WORLD)
    state.add((PLAYER, SR.hasItem, EX.rustSword))  # il Ratto che la droppa è ancora vivo
    return state, PLAYER, ("shape", SR.ItemProvenanceShape)


BROKEN_STATES = [broken_two_rooms, broken_quest_status_value,
                 broken_open_portal_without_key, broken_item_from_living_monster]


@pytest.mark.parametrize("builder", BROKEN_STATES, ids=lambda b: b.__name__)
def test_broken_state_triggers_expected_shape(builder):
    state, focus, (kind, value) = builder()
    conforms, results, text = validate_runtime(WORLD, state)
    assert not conforms, f"{builder.__name__} dovrebbe violare le shape runtime"
    prop = SH.resultPath if kind == "path" else SH.sourceShape
    matching = [r for r in results.subjects(SH.focusNode, focus)
                if (r, prop, value) in results]
    assert matching, f"attesa violazione {value} su {focus}; report:\n{text}"
