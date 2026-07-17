"""CLI interattiva del simulatore di run: il grafo RDF è il world state.

Uso: python -m tools.play [--new] [--seed N] [--save FILE.ttl] [--config FILE.toml]
Comandi: vai <stanza> | apri <portale> | combatti [mostro] | parla <npc>
         valida | stato | esci
Exit code: 0 = run terminata o uscita, 2 = errore config/parsing,
           3 = stato runtime non conforme (al resume o dopo una transizione).
"""
import argparse
import sys
from pathlib import Path

from rdflib import Graph, URIRef

from tools.common import SAVE_PATH, label_it, load_runtime_world, local_name
from tools.config import CONFIG_PATH, load_config
from tools.engine import (PLAYER, SR, ActionError, Engine, new_state,
                          validate_runtime)


def pick(graph: Graph, candidates, text: str) -> URIRef | None:
    """Trova il candidato con nome locale o label italiana uguale a text (case-insensitive)."""
    text = text.strip().lower()
    for c in candidates:
        if text in (local_name(c).lower(), label_it(graph, c).lower()):
            return c
    return None


def show_turn(eng: Engine) -> None:
    g = eng.graph()
    room = eng.current_room()
    print(f"\n== {label_it(g, room)} ==")
    for row in eng.run_query("monsters-here.rq"):
        print(f"  Mostro: {label_it(g, row.mostro)}")
    for npc in sorted({row.npc for row in eng.run_query("npcs-here.rq")}, key=str):
        print(f"  NPC: {label_it(g, npc)}")
    for row in eng.run_query("openable-portals.rq"):
        print(f"  Portale apribile: {label_it(g, row.portale)}")
    moves = sorted({label_it(g, row.stanza) for row in eng.run_query("available-moves.rq")})
    print("  Uscite: " + (", ".join(moves) if moves else "nessuna"))


def show_status(eng: Engine) -> None:
    g = eng.graph()
    print(f"Posizione: {label_it(g, eng.current_room())}")
    items = sorted(label_it(g, i) for i in eng.state.objects(PLAYER, SR.hasItem))
    print("Inventario: " + (", ".join(items) if items else "vuoto"))
    for row in eng.run_query("quest-status.rq"):
        status = str(row.status) if row.status else "non accettata"
        print(f"Quest: {label_it(g, row.quest)} [{status}] -> {label_it(g, row.target)}")


def run_validation_report(eng: Engine) -> bool:
    conforms, _, text = validate_runtime(eng.world, eng.state)
    if not conforms:
        print(text)
    return conforms


def do_command(eng: Engine, line: str) -> bool:
    """Esegue un comando. Ritorna True se c'è stata una transizione di stato."""
    verb, _, arg = line.strip().partition(" ")
    verb, arg = verb.lower(), arg.strip()
    g = eng.graph()

    if verb == "vai":
        rooms = {row.stanza for row in eng.run_query("available-moves.rq")}
        room = pick(g, rooms, arg)
        if room is None:
            raise ActionError(f"nessuna uscita chiamata '{arg}'")
        eng.move_to(room)
        return True
    if verb == "apri":
        portals = {row.portale for row in eng.run_query("openable-portals.rq")}
        portal = pick(g, portals, arg)
        if portal is None:
            raise ActionError(f"nessun portale apribile chiamato '{arg}'")
        eng.open_portal(portal)
        return True
    if verb == "combatti":
        monsters = [row.mostro for row in eng.run_query("monsters-here.rq")]
        target = pick(g, monsters, arg) if arg else None
        if arg and target is None:
            raise ActionError(f"nessun mostro chiamato '{arg}' qui")
        if eng.fight(target):
            print("Hai vinto lo scontro.")
        else:
            print("Sei stato sconfitto.")
        return True
    if verb == "parla":
        npcs = {row.npc for row in eng.run_query("npcs-here.rq")}
        npc = pick(g, npcs, arg)
        if npc is None:
            raise ActionError(f"nessun NPC chiamato '{arg}' con cui parlare")
        for quest in eng.talk_to(npc):
            print(f"Quest attivata: {label_it(g, quest)}")
        return True
    if verb == "valida":
        print("Stato conforme." if run_validation_report(eng) else "Stato NON conforme.")
        return False
    if verb == "stato":
        show_status(eng)
        return False
    raise ActionError(f"comando sconosciuto: '{verb}' "
                      "(comandi: vai, apri, combatti, parla, valida, stato, esci)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulatore di run sul knowledge graph.")
    parser.add_argument("--new", action="store_true", help="inizia una run nuova")
    parser.add_argument("--seed", type=int, help="seme RNG (sovrascrive config.toml)")
    parser.add_argument("--save", type=Path, default=SAVE_PATH, help="file di salvataggio")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="file di configurazione")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (ValueError, OSError) as e:
        print(f"Configurazione non valida: {e}", file=sys.stderr)
        return 2

    world = load_runtime_world()
    resumed = not args.new and args.save.exists()
    if resumed:
        state = Graph()
        try:
            state.parse(args.save, format="turtle")
        except Exception as e:
            print(f"Salvataggio illeggibile ({e}); usa --new per ricominciare.", file=sys.stderr)
            return 2
        print(f"Run ripresa da {args.save}.")
    else:
        state = new_state(world)
        print("Nuova run iniziata.")

    seed = args.seed if args.seed is not None else cfg.seed
    eng = Engine(world, state, player_success=cfg.player_success, seed=seed)

    if resumed and not run_validation_report(eng):
        print("Salvataggio non conforme alle shape runtime; usa --new per ricominciare.",
              file=sys.stderr)
        return 3

    args.save.parent.mkdir(parents=True, exist_ok=True)
    eng.state.serialize(args.save, format="turtle")  # turno zero: stato subito ispezionabile

    while True:
        outcome = eng.outcome()
        if outcome == "victory":
            print("\nVITTORIA: quest completata. Fine della run.")
            return 0
        if outcome == "defeat":
            print("\nSCONFITTA: il giocatore è morto. Fine della run.")
            return 0

        show_turn(eng)
        try:
            line = input("> ")
        except EOFError:
            return 0
        if not line.strip():
            continue
        if line.strip().lower() == "esci":
            print("Uscita: la run resta salvata.")
            return 0

        try:
            changed = do_command(eng, line)
        except ActionError as e:
            print(f"Azione non ammissibile: {e}")
            continue

        if changed:
            if cfg.validation_mode == "turn" and not run_validation_report(eng):
                print("Violazione runtime dopo la transizione: bug del motore, "
                      "turno NON salvato.", file=sys.stderr)
                return 3
            eng.state.serialize(args.save, format="turtle")


if __name__ == "__main__":
    raise SystemExit(main())
