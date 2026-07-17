# Dungeon Map (Mermaid) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Esportare la topologia del dungeon — e lo stato della partita, se disponibile — come diagramma Mermaid, da CLI (`tools/map.py`) e dal comando di gioco `mappa`.

**Architecture:** Funzione pura `build_map(world, state)` in un modulo nuovo `tools/map.py` che itera le triple rdflib e compone il testo Mermaid; la CLI e il comando `mappa` di `tools/play.py` sono involucri sottili. Gli helper `local_name`/`label_it` salgono da `play.py` a `common.py` per essere riusati senza dipendenze circolari.

**Tech Stack:** Python 3.12 (venv `.venv/`), rdflib, pytest. Nessuna dipendenza nuova.

**Spec:** `docs/superpowers/specs/2026-07-17-dungeon-map-design.md`

## Global Constraints

- Eseguire tutto con `.venv/Scripts/python` (Windows, shell Git Bash → forward slash).
- Nessuna dipendenza nuova in `requirements.txt`.
- Exit code del tool: 0 = ok, 2 = errore di parsing (convenzione repo).
- Il comando `mappa` NON è una transizione di stato (come `stato`/`valida`): nessuna validazione, nessun autosave.
- Su Windows lo stdout dei subprocess usa la codifica di sistema (cp1252): `tools/map.py` deve fare `sys.stdout.reconfigure(encoding="utf-8")` a inizio `main()` o gli emoji crashano nei test via pipe.
- README.md va aggiornato nella stessa modifica dei comandi (regola CLAUDE.md) — Task 3.
- I 61 test esistenti restano verdi a ogni task.
- Commit in italiano, con firma finale `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: helper condivisi + `build_map` (modulo e unit test)

**Files:**
- Modify: `tools/common.py` (aggiunge `local_name`, `label_it`)
- Modify: `tools/play.py:22-30` (rimuove le definizioni locali, importa da common)
- Create: `tools/map.py`
- Test: `tests/test_map.py`

**Interfaces:**
- Consumes: `load_runtime_world` (common), `PLAYER`, `SR`, `EX`, `new_state` (engine).
- Produces: `local_name(node) -> str` e `label_it(graph, node) -> str` in `tools/common.py`; `build_map(world: Graph, state: Graph | None = None) -> str` e `to_markdown(mermaid: str, title: str = "Mappa del dungeon") -> str` in `tools/map.py` (usati dai Task 2 e 3).

- [ ] **Step 1: Scrivere i test che falliscono** — creare `tests/test_map.py`:

```python
"""La mappa Mermaid del dungeon: mondo authored e overlay dello stato di partita."""
from rdflib import Literal

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, new_state
from tools.map import build_map

WORLD = load_runtime_world()


def test_world_map_shows_rooms_floors_and_closed_portals():
    text = build_map(WORLD)
    assert "Ingresso delle Catacombe" in text
    assert "Cripta del Trono" in text
    assert text.count("subgraph P") == 4       # un subgraph per piano
    assert text.count("🔒") == 2                # due portali chiusi
    assert "🧙 Eremita della Tomba" in text
    assert "👑 Re Morto" in text
    assert "🧝" not in text and "subgraph Q" not in text  # niente overlay senza stato


def test_runtime_overlay_marks_player_deaths_and_open_portals():
    state = new_state(WORLD)
    state.set((PLAYER, SR.currentRoom, EX.crypt07))
    state.add((EX.boneWarden, SR.isAlive, Literal(False)))
    state.add((EX.sealedGate, SR.isOpen, Literal(True)))
    state.add((EX.recoverRelic, SR.questStatus, Literal("active")))
    text = build_map(WORLD, state)
    assert "class crypt07 player" in text
    assert "☠ Custode d'Ossa" in text
    assert text.count("🔓") == 1 and text.count("🔒") == 1
    assert "⭐ Recupera la Reliquia" in text    # stella sulla target room (sanctum01)
    assert "▶ Recupera la Reliquia" in text     # legenda quest
```

- [ ] **Step 2: Verificare rosso**

Run: `.venv/Scripts/python -m pytest tests/test_map.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tools.map'`.

- [ ] **Step 3: Spostare gli helper in `tools/common.py`** — in coda a `tools/common.py` aggiungere (e aggiornare gli import del file: `from rdflib import Graph, URIRef` e `from rdflib.namespace import RDFS`):

```python
def local_name(node: URIRef) -> str:
    """Nome locale di una URI (dopo # o /), usato come identificatore leggibile."""
    return str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def label_it(graph: Graph, node: URIRef) -> str:
    """Label italiana di una risorsa; fallback sul nome locale."""
    for lbl in graph.objects(node, RDFS.label):
        if getattr(lbl, "language", None) == "it":
            return str(lbl)
    return local_name(node)
```

In `tools/play.py`: eliminare le definizioni di `local_name` e `label_it` (righe 22-30), togliere l'import ora inutile `from rdflib.namespace import RDFS`, e cambiare l'import da common in:

```python
from tools.common import SAVE_PATH, label_it, load_runtime_world, local_name
```

- [ ] **Step 4: Creare `tools/map.py`**

```python
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
```

(Nota: il suffisso `Q` sui nodi quest evita collisioni di id con le stanze; la CLI arriva nel Task 2.)

- [ ] **Step 5: Verificare verde**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 63 passed (61 esistenti + 2 nuovi; i test di play restano verdi dopo il refactor degli helper).

- [ ] **Step 6: Commit**

```bash
git add tools/common.py tools/play.py tools/map.py tests/test_map.py
git commit -m "Task 1 mappa: build_map Mermaid e helper label condivisi in common"
```

---

### Task 2: CLI di `tools.map`

**Files:**
- Modify: `tools/map.py` (aggiunge `main()`)
- Test: `tests/test_map.py`

**Interfaces:**
- Consumes: `build_map`, `to_markdown` (Task 1); `DATASET`, `SAVE_PATH` (common).
- Produces: comando `python -m tools.map [--data FILE.ttl] [--save FILE.ttl] [-o FILE.md]`.

- [ ] **Step 1: Test che falliscono** — aggiungere a `tests/test_map.py`:

```python
import subprocess
import sys

from tools.common import ROOT


def run_map(args):
    return subprocess.run(
        [sys.executable, "-m", "tools.map", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, timeout=120,
    )


def test_cli_stdout_contains_mermaid_block():
    result = run_map(["--save", "dataset/dataset.ttl"])  # save qualsiasi ma valido: output deterministico
    assert result.returncode == 0, result.stderr
    assert "```mermaid" in result.stdout
    assert "flowchart TD" in result.stdout


def test_cli_writes_markdown_file(tmp_path):
    out = tmp_path / "mappa.md"
    result = run_map(["-o", str(out)])
    assert result.returncode == 0, result.stderr
    content = out.read_text(encoding="utf-8")
    assert content.startswith("# Mappa del dungeon")
    assert "```mermaid" in content


def test_cli_broken_save_exits_2(tmp_path):
    bad = tmp_path / "s.ttl"
    bad.write_text("non è turtle @@@", encoding="utf-8")
    result = run_map(["--save", str(bad)])
    assert result.returncode == 2
    assert result.stderr.strip() != ""
```

(Nel primo test `--save dataset/dataset.ttl` è un trucco lecito: un grafo senza triple runtime equivale a "nessuno stato" e rende il test indipendente da un eventuale `runtime/save.ttl` locale.)

- [ ] **Step 2: Verificare rosso**

Run: `.venv/Scripts/python -m pytest tests/test_map.py -v`
Expected: i 3 test CLI falliscono (`main` non esiste: il modulo esce senza output / `returncode` diverso).

- [ ] **Step 3: Aggiungere `main()` a `tools/map.py`** (in coda al file):

```python
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
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_map.py -v`
Expected: 5 passed (totale suite: 66).

- [ ] **Step 5: Prova manuale**

Run: `.venv/Scripts/python -m tools.map -o mappa-prova.md && rm mappa-prova.md`
Expected: "Mappa scritta in mappa-prova.md"; aprendo il file in VS Code la preview mostra il diagramma.

- [ ] **Step 6: Commit**

```bash
git add tools/map.py tests/test_map.py
git commit -m "Task 2 mappa: CLI tools.map con overlay del salvataggio"
```

---

### Task 3: comando `mappa` in `tools/play.py` + README

**Files:**
- Modify: `tools/play.py` (docstring, `do_command`, call site in `main`)
- Modify: `README.md` (nuovo tool + nuovo comando di gioco)
- Test: `tests/test_play_cli.py`

**Interfaces:**
- Consumes: `build_map`, `to_markdown` (Task 1).
- Produces: comando di gioco `mappa` che scrive `<dir del save>/mappa.md`.

- [ ] **Step 1: Test che fallisce** — aggiungere in coda a `tests/test_play_cli.py`:

```python
def test_mappa_command_writes_map_next_to_save(tmp_path):
    save = tmp_path / "save.ttl"
    result = run_cli(["--new"], ["mappa", "esci"], save)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "mappa.md").read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "🧝" in content  # la stanza del player è marcata
```

Run: `.venv/Scripts/python -m pytest tests/test_play_cli.py::test_mappa_command_writes_map_next_to_save -v`
Expected: FAIL (`comando sconosciuto: 'mappa'` → il file non viene creato → FileNotFoundError).

- [ ] **Step 2: Implementare in `tools/play.py`**

1. Import (dopo gli import da `tools.engine`):

```python
from tools.map import build_map, to_markdown
```

2. Firma di `do_command` (riga 73) e docstring:

```python
def do_command(eng: Engine, line: str, save_path: Path) -> bool:
    """Esegue un comando. Ritorna True se c'è stata una transizione di stato."""
```

3. Nuovo ramo, prima di `raise ActionError(f"comando sconosciuto...")`:

```python
    if verb == "mappa":
        target = save_path.parent / "mappa.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_markdown(build_map(eng.world, eng.state), "Mappa della partita"),
                          encoding="utf-8")
        print(f"Mappa scritta in {target}")
        return False
```

4. Aggiornare il messaggio di comando sconosciuto:

```python
    raise ActionError(f"comando sconosciuto: '{verb}' "
                      "(comandi: vai, apri, combatti, parla, valida, stato, mappa, esci)")
```

5. Call site in `main()` (riga 181): `changed = do_command(eng, line, args.save)`

6. Docstring del modulo (riga 4-5): aggiungere `mappa` all'elenco comandi:

```
Comandi: vai <stanza> | apri <portale> | combatti [mostro] | parla <npc>
         valida | stato | mappa | esci
```

- [ ] **Step 3: Aggiornare README.md** — nella sezione dei comandi:
  - nuova sottosezione per il tool mappa, con le opzioni e un esempio:

````markdown
### Esportare la mappa del dungeon

```bash
python -m tools.map                      # stampa il diagramma Mermaid su stdout
python -m tools.map -o mappa.md          # scrive un markdown (preview in VS Code/GitHub)
python -m tools.map --save runtime/save.ttl -o mappa.md   # con lo stato della partita
```

Senza `--save` usa `runtime/save.ttl` se esiste (altrimenti mostra solo il mondo authored). La mappa raggruppa le stanze per piano e mostra mostri (👹/👑, ☠ se sconfitti), NPC (🧙), portali (🔒 chiusi, 🔓 aperti), la stanza del player (🧝, evidenziata) e lo stato delle quest. Exit code: `0` ok · `2` errore di parsing.
````

  - nell'elenco dei comandi di gioco di `tools.play` aggiungere la riga:

```markdown
| `mappa` | scrive/aggiorna la mappa Mermaid della partita in `mappa.md` accanto al salvataggio |
```

  (adattare al formato reale dell'elenco esistente in README — tabella o lista — mantenendone lo stile.)

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest`
Expected: 67 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/play.py tests/test_play_cli.py README.md
git commit -m "Task 3 mappa: comando mappa nella CLI di gioco e README"
```
