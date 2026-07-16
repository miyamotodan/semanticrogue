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
