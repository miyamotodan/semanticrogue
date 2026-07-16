"""La validazione SHACL passa sul dataset authored e fallisce sui dati rotti."""
from pathlib import Path

from pyshacl import validate

from tools.common import DATASET, ONTOLOGY, SHAPES, load_graph


def run_validation(data_path: Path):
    """Valida ontologia+dati contro le shape. Ritorna (conforms, results_graph, results_text)."""
    data = load_graph(ONTOLOGY, data_path)
    shapes = load_graph(SHAPES)
    return validate(data, shacl_graph=shapes, advanced=True)


def test_authored_dataset_conforms():
    conforms, _, text = run_validation(DATASET)
    assert conforms, f"Il dataset authored deve essere conforme alle shape:\n{text}"
