"""Caricamento dei grafi del progetto: Model (ontologia), Content (dataset), Validation (shape)."""
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY = ROOT / "ontology" / "rogue.ttl"
DATASET = ROOT / "dataset" / "dataset.ttl"
SHAPES = ROOT / "shacl" / "rogue-rules.ttl"
RUNTIME_ONTOLOGY = ROOT / "ontology" / "runtime.ttl"
RUNTIME_SHAPES = ROOT / "shacl" / "runtime-rules.ttl"
SAVE_PATH = ROOT / "runtime" / "save.ttl"


def load_graph(*paths: Path) -> Graph:
    """Carica e fonde uno o più file Turtle in un unico grafo."""
    g = Graph()
    for path in paths:
        g.parse(path, format="turtle")
    return g


def load_world(data_path: Path = DATASET) -> Graph:
    """Grafo unito ontologia + dataset: la base per query e validazione."""
    return load_graph(ONTOLOGY, data_path)


def load_runtime_world(data_path: Path = DATASET) -> Graph:
    """Grafo di lavoro del simulatore: ontologia statica + ontologia runtime + dataset."""
    return load_graph(ONTOLOGY, RUNTIME_ONTOLOGY, data_path)


def local_name(node: URIRef) -> str:
    """Nome locale di una URI (dopo # o /), usato come identificatore leggibile."""
    return str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def label_it(graph: Graph, node: URIRef) -> str:
    """Label italiana di una risorsa; fallback sul nome locale."""
    for lbl in graph.objects(node, RDFS.label):
        if getattr(lbl, "language", None) == "it":
            return str(lbl)
    return local_name(node)
