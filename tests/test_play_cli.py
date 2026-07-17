"""La CLI del simulatore: avvio, comandi, autosave e resume (via subprocess)."""
import subprocess
import sys

from rdflib import Graph

from tools.common import ROOT


def run_cli(args, commands, save_path):
    """Lancia tools.play con input scriptato; ritorna il CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "tools.play", "--save", str(save_path), *args],
        input="\n".join(commands) + "\n",
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, timeout=120,
    )


def test_new_run_shows_start_room_and_quits(tmp_path):
    save = tmp_path / "save.ttl"
    result = run_cli(["--new"], ["esci"], save)
    assert result.returncode == 0, result.stderr
    assert "Ingresso delle Catacombe" in result.stdout
    assert save.exists()  # autosave del turno zero


def test_moves_are_persisted_and_resumed(tmp_path):
    save = tmp_path / "save.ttl"
    first = run_cli(["--new"], ["vai ossuary02", "esci"], save)
    assert first.returncode == 0, first.stderr
    g = Graph()
    g.parse(save, format="turtle")
    assert "ossuary02" in g.serialize(format="turtle")
    resumed = run_cli([], ["esci"], save)  # senza --new: resume
    assert resumed.returncode == 0, resumed.stderr
    assert "Ossario 02" in resumed.stdout


def test_invalid_action_does_not_crash(tmp_path):
    save = tmp_path / "save.ttl"
    result = run_cli(["--new"], ["vai sanctum01", "esci"], save)
    assert result.returncode == 0, result.stderr
    assert "non" in result.stdout.lower()  # messaggio di azione rifiutata


def test_victory_run_with_labels(tmp_path):
    save = tmp_path / "save.ttl"
    result = run_cli(["--new", "--seed", "7"], [
        "parla graveHermit",       # attiva recoverRelic (target: sanctum01) e endTheCourt
        "vai ossuary02",
        "combatti",                # Ratto delle Cripte
        "vai crypt07",
        "combatti",                # Custode d'Ossa -> Chiave d'Avorio
        "apri sealedGate",
        "vai Santuario 01",        # label italiana, case-insensitive
        "combatti",                # Tiranno della Cripta -> quest completata
    ], save)
    assert result.returncode == 0, result.stderr
    assert "vittoria" in result.stdout.lower()


def test_corrupted_save_exits_2(tmp_path):
    save = tmp_path / "save.ttl"
    save.write_text("questo non è turtle @@@", encoding="utf-8")
    result = run_cli([], ["esci"], save)
    assert result.returncode == 2
    assert "--new" in result.stderr
