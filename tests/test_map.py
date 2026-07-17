"""La mappa Mermaid del dungeon: mondo authored e overlay dello stato di partita."""
from rdflib import Literal

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, new_state
from tools.map import build_map

WORLD = load_runtime_world()


def test_world_map_shows_rooms_floors_and_closed_portals():
    text = build_map(WORLD)
    assert "Ingresso delle Catacombe" in text
    assert "Cripta del Trono" in text
    assert text.count("subgraph P") == 4       # un subgraph per piano
    assert text.count("🔒") == 2                # due portali chiusi
    assert "🧙 Eremita della Tomba" in text
    assert "👑 Re Morto" in text
    assert "🧝" not in text and "subgraph Q" not in text  # niente overlay senza stato


def test_runtime_overlay_marks_player_deaths_and_open_portals():
    state = new_state(WORLD)
    state.set((PLAYER, SR.currentRoom, EX.crypt07))
    state.add((EX.boneWarden, SR.isAlive, Literal(False)))
    state.add((EX.sealedGate, SR.isOpen, Literal(True)))
    state.add((EX.recoverRelic, SR.questStatus, Literal("active")))
    text = build_map(WORLD, state)
    assert "class crypt07 player" in text
    assert "☠ Custode d'Ossa" in text
    assert text.count("🔓") == 1 and text.count("🔒") == 1
    assert "⭐ Recupera la Reliquia" in text    # stella sulla target room (sanctum01)
    assert "▶ Recupera la Reliquia" in text     # legenda quest
