"""La mappa Mermaid del dungeon: mondo authored e overlay dello stato di partita."""
import subprocess
import sys

from rdflib import Literal

from tools.common import ROOT, load_runtime_world
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


def run_map(args):
    return subprocess.run(
        [sys.executable, "-m", "tools.map", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, timeout=120,
    )


def test_cli_stdout_contains_mermaid_block():
    result = run_map(["--save", "dataset/dataset.ttl"])  # save valido ma senza triple runtime: output deterministico
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
