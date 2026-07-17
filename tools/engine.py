"""Motore di M3: lo stato di partita è solo triple RDF nel runtime graph.

Letture via SPARQL (queries/runtime/), transizioni come modifiche di triple,
nessuno stato duplicato in oggetti Python.
"""
import random

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from tools.common import ROOT, RUNTIME_SHAPES, load_graph

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
    g.add((start, SR.visited, Literal(True)))
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

    def move_to(self, room: URIRef) -> None:
        """Sposta il player in una stanza raggiungibile (passaggio o portale aperto)."""
        moves = {row.stanza for row in self.run_query("available-moves.rq")}
        if room not in moves:
            raise ActionError(f"stanza non raggiungibile da qui: {room}")
        self.state.set((PLAYER, SR.currentRoom, room))
        self.state.add((room, SR.visited, Literal(True)))
        self._check_quest_completion()

    def open_portal(self, portal: URIRef) -> None:
        """Apre un portale chiuso nella stanza corrente, se la chiave è in inventario."""
        openable = {row.portale for row in self.run_query("openable-portals.rq")}
        if portal not in openable:
            raise ActionError(f"portale non apribile ora: {portal}")
        self.state.add((portal, SR.isOpen, Literal(True)))

    def _check_quest_completion(self) -> None:
        """Le quest attive con target = stanza corrente e nessun mostro vivo si completano."""
        if self.run_query("monsters-here.rq"):
            return
        room = self.current_room()
        for quest in list(self.state.subjects(SR.questStatus, Literal("active"))):
            if (quest, SR.questTargetRoom, room) in self.world:
                self.state.set((quest, SR.questStatus, Literal("completed")))
                for reward in self.world.objects(quest, SR.questReward):
                    self.state.add((PLAYER, SR.hasItem, reward))

    def fight(self, monster: URIRef | None = None) -> bool:
        """Affronta un mostro vivo nella stanza corrente. True = vinto, False = player morto."""
        alive = [row.mostro for row in self.run_query("monsters-here.rq")]
        if not alive:
            raise ActionError("nessun mostro da combattere qui")
        if monster is None:
            if len(alive) > 1:
                raise ActionError("più mostri presenti: indica quale combattere")
            monster = alive[0]
        elif monster not in alive:
            raise ActionError(f"mostro non presente o già sconfitto: {monster}")

        if self.rng.random() < self.player_success:
            self.state.add((monster, SR.isAlive, Literal(False)))
            for item in self.world.objects(monster, SR.dropsItem):
                self.state.add((PLAYER, SR.hasItem, item))
            self._check_quest_completion()
            return True
        self.state.add((PLAYER, SR.isAlive, Literal(False)))
        return False

    def talk_to(self, npc: URIRef) -> list[URIRef]:
        """Parla con un NPC nella stanza corrente: attiva le sue quest non ancora accettate."""
        offers = [row.quest for row in self.run_query("npcs-here.rq") if row.npc == npc]
        if not offers:
            raise ActionError(f"nessun NPC con quest da offrire qui: {npc}")
        for quest in offers:
            self.state.add((quest, SR.questStatus, Literal("active")))
        self._check_quest_completion()
        return offers

    def outcome(self) -> str | None:
        """Esito della run: \"defeat\" se il player è morto, \"victory\" alla prima quest completata."""
        if (PLAYER, SR.isAlive, Literal(False)) in self.state:
            return "defeat"
        if next(self.state.subjects(SR.questStatus, Literal("completed")), None) is not None:
            return "victory"
        return None


def validate_runtime(world: Graph, state: Graph):
    """Valida lo stato di partita contro le shape runtime. Ritorna (conforms, results_graph, text)."""
    shapes = load_graph(RUNTIME_SHAPES)
    return validate(world + state, shacl_graph=shapes, advanced=True)
