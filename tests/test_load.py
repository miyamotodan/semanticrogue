"""Smoke test: i tre file Turtle si caricano e si fondono in un grafo."""
from rdflib import Graph

from tools.common import DATASET, ONTOLOGY, SHAPES, load_graph, load_world


def test_each_ttl_file_parses():
    for path in (ONTOLOGY, DATASET, SHAPES):
        g = Graph()
        g.parse(path, format="turtle")
        assert len(g) > 0, f"{path} non contiene triple"


def test_load_world_merges_ontology_and_dataset():
    dataset_only = Graph()
    dataset_only.parse(DATASET, format="turtle")
    world = load_world()
    assert len(world) > len(dataset_only)


def test_load_graph_accepts_multiple_paths():
    g = load_graph(ONTOLOGY, DATASET)
    assert len(g) > 0


def test_runtime_world_includes_runtime_vocabulary():
    """load_runtime_world unisce anche il vocabolario runtime (sr:Player ecc.)."""
    from rdflib import Namespace
    from rdflib.namespace import RDF, OWL
    from tools.common import load_runtime_world

    SR = Namespace("http://example.org/semantic-roguelike#")
    world = load_runtime_world()
    assert (SR.Player, RDF.type, OWL.Class) in world
    assert (SR.currentRoom, RDF.type, OWL.ObjectProperty) in world
