"""Valida il dataset contro le shape SHACL.

Uso: python -m tools.validate [--data FILE.ttl]
Exit code: 0 = conforme, 1 = violazioni, 2 = errore di parsing.
"""
import argparse
import sys
from pathlib import Path

from pyshacl import validate

from tools.common import DATASET, ONTOLOGY, SHAPES, load_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida il mondo contro le shape SHACL.")
    parser.add_argument("--data", type=Path, default=DATASET,
                        help="file Turtle del dataset da validare (default: dataset/dataset.ttl)")
    args = parser.parse_args()

    try:
        data = load_graph(ONTOLOGY, args.data)
        shapes = load_graph(SHAPES)
    except FileNotFoundError as e:
        print(f"File non trovato: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # errori di sintassi Turtle (BadSyntax) e simili
        print(f"Errore di parsing: {e}", file=sys.stderr)
        return 2

    conforms, _, text = validate(data, shacl_graph=shapes, advanced=True)
    print(text)
    return 0 if conforms else 1


if __name__ == "__main__":
    raise SystemExit(main())
