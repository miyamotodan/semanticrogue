"""Esporta la mappa del dungeon come diagramma Mermaid.

Uso: python -m tools.map [--data FILE.ttl] [--save FILE.ttl] [-o FILE.md]
Senza --save usa runtime/save.ttl se esiste; senza -o stampa su stdout.
Exit code: 0 = ok, 2 = errore di parsing.
"""
import argparse
import sys
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from tools.common import (DATASET, SAVE_PATH, label_it, load_runtime_world,
                          local_name)
from tools.engine import PLAYER, SR


def _node_label(world: Graph, state: Graph, room: URIRef,
                player_room: URIRef | None) -> str:
    """Etichetta multiriga del nodo stanza: nome, mostri, NPC, obiettivi di quest."""
    parts = [label_it(world, room)]
    if room == player_room:
        parts[0] = "🧝 " + parts[0]
    for monster in sorted(world.objects(room, SR.hostsMonster), key=str):
        icon = "👑" if (monster, RDF.type, SR.Boss) in world else "👹"
        if (monster, SR.isAlive, Literal(False)) in state:
            icon = "☠"
        parts.append(f"{icon} {label_it(world, monster)}")
    for npc in sorted(world.subjects(SR.npcInRoom, room), key=str):
        parts.append(f"🧙 {label_it(world, npc)}")
    for quest in sorted(state.subjects(SR.questStatus, Literal("active")), key=str):
        if (quest, SR.questTargetRoom, room) in world:
            parts.append(f"⭐ {label_it(world, quest)}")
    return "<br/>".join(parts)


def build_map(world: Graph, state: Graph | None = None) -> str:
    """Diagramma Mermaid del mondo; con state sovrappone la partita in corso."""
    state = state if state is not None else Graph()
    player_room = state.value(PLAYER, SR.currentRoom)
    lines = ["flowchart TD"]

    by_floor: dict[int, list[URIRef]] = {}
    for room in world.subjects(RDF.type, SR.Room):
        by_floor.setdefault(int(world.value(room, SR.floorIndex)), []).append(room)
    for floor in sorted(by_floor):
        lines.append(f'  subgraph P{floor}["Piano {floor}"]')
        for room in sorted(by_floor[floor], key=str):
            lines.append(
                f'    {local_name(room)}["{_node_label(world, state, room, player_room)}"]')
        lines.append("  end")

    for a, b in sorted(world.subject_objects(SR.connectedTo),
                       key=lambda e: (str(e[0]), str(e[1]))):
        lines.append(f"  {local_name(a)} --- {local_name(b)}")

    for portal in sorted(world.subjects(RDF.type, SR.Portal), key=str):
        src = local_name(world.value(portal, SR.portalInRoom))
        dst = local_name(world.value(portal, SR.unlocksRoom))
        key = label_it(world, world.value(portal, SR.requiresItem))
        if (portal, SR.isOpen, Literal(True)) in state:
            lines.append(f'  {src} == "🔓 {key}" ==> {dst}')
        else:
            lines.append(f'  {src} -. "🔒 {key}" .-> {dst}')

    statuses = list(state.subject_objects(SR.questStatus))
    if statuses:
        lines.append('  subgraph Q["Quest"]')
        for quest, status in sorted(statuses, key=lambda e: str(e[0])):
            icon = "✅" if str(status) == "completed" else "▶"
            lines.append(f'    {local_name(quest)}Q["{icon} {label_it(world, quest)}"]')
        lines.append("  end")

    if player_room is not None:
        lines.append(f"  class {local_name(player_room)} player")
        lines.append("  classDef player fill:#ffd54f,stroke:#f57f17,stroke-width:3px")
    return "\n".join(lines)


def to_markdown(mermaid: str, title: str = "Mappa del dungeon") -> str:
    """Documento markdown completo con il blocco mermaid."""
    return f"# {title}\n\n```mermaid\n{mermaid}\n```\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # emoji su pipe Windows (cp1252)
    parser = argparse.ArgumentParser(description="Esporta la mappa del dungeon in Mermaid.")
    parser.add_argument("--data", type=Path, default=DATASET, help="dataset alternativo")
    parser.add_argument("--save", type=Path,
                        help="salvataggio da sovrapporre (default: runtime/save.ttl se esiste)")
    parser.add_argument("-o", "--output", type=Path,
                        help="scrive un file markdown invece di stampare su stdout")
    args = parser.parse_args()

    try:
        world = load_runtime_world(args.data)
    except Exception as e:
        print(f"Errore di parsing del mondo: {e}", file=sys.stderr)
        return 2

    save = args.save if args.save is not None else (SAVE_PATH if SAVE_PATH.exists() else None)
    state = None
    if save is not None:
        state = Graph()
        try:
            state.parse(save, format="turtle")
        except Exception as e:
            print(f"Errore di parsing del salvataggio {save}: {e}", file=sys.stderr)
            return 2

    text = build_map(world, state)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(to_markdown(text), encoding="utf-8")
        print(f"Mappa scritta in {args.output}")
    else:
        print(f"```mermaid\n{text}\n```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
