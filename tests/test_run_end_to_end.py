"""Una run completa eseguita dal motore: il criterio di successo di M3, dimostrato."""
from rdflib import Graph, Literal

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, Engine, new_state, validate_runtime

WORLD = load_runtime_world()


def test_scripted_winning_run(tmp_path):
    eng = Engine(WORLD, new_state(WORLD), player_success=1.0, seed=42)

    eng.talk_to(EX.graveHermit)          # accetta recoverRelic (target: sanctum01)
    eng.move_to(EX.ossuary02)
    eng.fight()                          # Ratto delle Cripte
    eng.move_to(EX.crypt07)
    eng.fight()                          # Custode d'Ossa -> Chiave d'Avorio
    assert (PLAYER, SR.hasItem, EX.ivoryKey) in eng.state
    eng.open_portal(EX.sealedGate)
    eng.move_to(EX.sanctum01)
    assert eng.outcome() is None         # il Tiranno è ancora vivo
    eng.fight()                          # Tiranno della Cripta -> quest completata

    assert (EX.recoverRelic, SR.questStatus, Literal("completed")) in eng.state
    assert eng.outcome() == "victory"

    # Il grafo finale è conforme alle shape runtime.
    conforms, _, text = validate_runtime(WORLD, eng.state)
    assert conforms, text

    # Il salvataggio è rileggibile e rivalidabile a freddo, senza il motore.
    save = tmp_path / "save.ttl"
    eng.state.serialize(save, format="turtle")
    cold = Graph()
    cold.parse(save, format="turtle")
    assert len(cold) == len(eng.state)
    conforms, _, text = validate_runtime(WORLD, cold)
    assert conforms, text


def test_scripted_losing_run():
    eng = Engine(WORLD, new_state(WORLD), player_success=0.0, seed=42)
    eng.move_to(EX.ossuary02)
    assert eng.fight() is False
    assert eng.outcome() == "defeat"
    conforms, _, text = validate_runtime(WORLD, eng.state)
    assert conforms, text  # anche la morte è uno stato coerente


def test_seeded_combat_is_reproducible():
    for _ in range(2):
        eng = Engine(WORLD, new_state(WORLD), player_success=0.5, seed=123)
        eng.move_to(EX.ossuary02)
        first = eng.fight()
        eng2 = Engine(WORLD, new_state(WORLD), player_success=0.5, seed=123)
        eng2.move_to(EX.ossuary02)
        assert eng2.fight() == first
