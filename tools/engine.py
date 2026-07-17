"""Motore di M3: lo stato di partita è solo triple RDF nel runtime graph.

Letture via SPARQL (queries/runtime/), transizioni come modifiche di triple,
nessuno stato duplicato in oggetti Python.
"""
import random

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from tools.common import ROOT

SR = Namespace("http://example.org/semantic-roguelike#")
EX = Namespace("http://example.org/id/")
PLAYER = EX.player
RUNTIME_QUERIES = ROOT / "queries" / "runtime"


class ActionError(Exception):
    """Azione non ammissibile: il grafo non viene modificato."""


def new_state(world: Graph) -> Graph:
    """Runtime graph iniziale: il player nella stanza con isStartRoom true, nient'altro."""
    start = world.value(predicate=SR.isStartRoom, object=Literal(True))
    if start is None:
        raise ValueError("nessuna stanza con sr:isStartRoom true nel mondo")
    g = Graph()
    g.bind("sr", SR)
    g.bind("ex", EX)
    g.add((PLAYER, RDF.type, SR.Player))
    g.add((PLAYER, SR.currentRoom, start))
    return g


class Engine:
    """Transizioni di stato sul runtime graph; il content graph è di sola lettura."""

    def __init__(self, world: Graph, state: Graph,
                 player_success: float = 1.0, seed: int | None = None):
        self.world = world
        self.state = state
        self.player_success = player_success
        self.rng = random.Random(seed)

    def graph(self) -> Graph:
        """Grafo unito contenuto+stato su cui girano query e validazione."""
        return self.world + self.state

    def current_room(self) -> URIRef:
        return self.state.value(PLAYER, SR.currentRoom)

    def run_query(self, name: str) -> list:
        """Esegue una query di queries/runtime/ sul grafo unito."""
        text = (RUNTIME_QUERIES / name).read_text(encoding="utf-8")
        return list(self.graph().query(text))
