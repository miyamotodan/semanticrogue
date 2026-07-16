"""Esegue query SPARQL (.rq) sul grafo unito ontologia+dataset.

Uso: python -m tools.query queries/01-rooms-overview.rq [--data FILE.ttl]
     python -m tools.query --all
"""
import argparse
import sys
from pathlib import Path

from tools.common import DATASET, ROOT, load_world


def format_table(result) -> str:
    """Formatta un risultato SELECT di rdflib come tabella testuale allineata."""
    headers = [str(v) for v in result.vars]
    rows = [["" if cell is None else str(cell) for cell in row] for row in result]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]

    def line(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths))

    out = [line(headers), line(["-" * w for w in widths])]
    out += [line(r) for r in rows]
    out.append(f"({len(rows)} righe)")
    return "\n".join(out)


def run_file(world, rq_path: Path) -> int:
    try:
        text = rq_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Query non trovata: {rq_path}", file=sys.stderr)
        return 2
    try:
        result = world.query(text)
    except Exception as e:
        print(f"Query malformata in {rq_path.name}: {e}", file=sys.stderr)
        return 2
    print(f"== {rq_path.name} ==")
    print(format_table(result))
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Esegue query SPARQL sul mondo.")
    parser.add_argument("query", nargs="?", type=Path, help="file .rq da eseguire")
    parser.add_argument("--all", action="store_true", help="esegue tutte le query in queries/")
    parser.add_argument("--data", type=Path, default=DATASET, help="dataset alternativo")
    args = parser.parse_args()

    if not args.all and args.query is None:
        parser.error("indicare un file .rq oppure --all")

    world = load_world(args.data)
    targets = sorted((ROOT / "queries").glob("*.rq")) if args.all else [args.query]
    return max((run_file(world, t) for t in targets), default=0)


if __name__ == "__main__":
    raise SystemExit(main())
