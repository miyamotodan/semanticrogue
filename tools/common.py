"""Caricamento dei grafi del progetto: Model (ontologia), Content (dataset), Validation (shape)."""
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY = ROOT / "ontology" / "rogue.ttl"
DATASET = ROOT / "dataset" / "dataset.ttl"
SHAPES = ROOT / "shacl" / "rogue-rules.ttl"


def load_graph(*paths: Path) -> Graph:
    """Carica e fonde uno o più file Turtle in un unico grafo."""
    g = Graph()
    for path in paths:
        g.parse(path, format="turtle")
    return g


def load_world(data_path: Path = DATASET) -> Graph:
    """Grafo unito ontologia + dataset: la base per query e validazione."""
    return load_graph(ONTOLOGY, data_path)
