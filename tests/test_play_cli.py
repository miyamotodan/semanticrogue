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


def test_prefix_match_when_unambiguous(tmp_path):
    save = tmp_path / "save.ttl"
    # Dall'ingresso le uscite sono "Ossario 02" e "Cappella Profanata":
    # "vai oss" basta perché nessun'altra uscita inizia per "oss".
    result = run_cli(["--new"], ["vai oss", "esci"], save)
    assert result.returncode == 0, result.stderr
    assert "Ossario 02" in result.stdout


def test_prefix_match_is_rejected_when_ambiguous(tmp_path):
    save = tmp_path / "save.ttl"
    # Nella Sala 08 le uscite sono Cappella Profanata, Cripta 07 e Cavità Fungina:
    # "vai c" è ambiguo e deve essere rifiutato senza muovere il player.
    result = run_cli(["--new"], [
        "vai ossario", "vai cripta", "vai sala",  # ingresso -> ossuary02 -> crypt07 -> hall08
        "vai c",                                   # ambiguo: nessuna transizione
        "esci",
    ], save)
    assert result.returncode == 0, result.stderr
    assert "ambigu" in result.stdout.lower()
    # È rimasto nella Sala 08 dopo il comando ambiguo (nessuna transizione).
    assert result.stdout.rstrip().count("Sala 08") >= 2


def test_exact_match_wins_over_being_a_prefix_of_another(tmp_path):
    save = tmp_path / "save.ttl"
    # "vai cripta 07" indica esattamente la Cripta 07: il match esatto ha priorità
    # e non è ambiguo, anche se fosse prefisso di un'altra uscita.
    result = run_cli(["--new"], [
        "vai ossario", "vai cripta", "vai sala",  # -> hall08
        "vai cripta 07",                           # match esatto sulla label
        "esci",
    ], save)
    assert result.returncode == 0, result.stderr
    assert "ambigu" not in result.stdout.lower()


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


def test_nonconformant_save_exits_3_and_is_not_rewritten(tmp_path):
    save = tmp_path / "save.ttl"
    save.write_text(
        """@prefix sr: <http://example.org/semantic-roguelike#> .
@prefix ex: <http://example.org/id/> .
ex:player a sr:Player ; sr:currentRoom ex:crypt07 .
ex:sealedGate sr:isOpen true .
""",
        encoding="utf-8",
    )
    before = save.read_text(encoding="utf-8")
    result = run_cli([], ["esci"], save)
    assert result.returncode == 3
    assert "Conforms: False" in result.stdout
    after = save.read_text(encoding="utf-8")
    assert after == before


def test_mappa_command_writes_map_next_to_save(tmp_path):
    save = tmp_path / "save.ttl"
    result = run_cli(["--new"], ["mappa", "esci"], save)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "mappa.md").read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "🧝" in content  # la stanza del player è marcata


def test_auto_map_regenerates_after_successful_action(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text("[map]\nauto = true\n", encoding="utf-8")
    save = tmp_path / "save.ttl"
    result = run_cli(["--new", "--config", str(cfg)], ["vai ossario", "esci"], save)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "mappa.md").read_text(encoding="utf-8")  # creata senza comando `mappa`
    assert "```mermaid" in content
    assert "🧝 Ossario 02" in content  # il player è sull'Ossario dopo lo spostamento


def test_auto_map_off_does_not_write_map(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text("[map]\nauto = false\n", encoding="utf-8")
    save = tmp_path / "save.ttl"
    result = run_cli(["--new", "--config", str(cfg)], ["vai ossario", "esci"], save)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "mappa.md").exists()


def test_auto_map_writes_map_at_turn_zero(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text("[map]\nauto = true\n", encoding="utf-8")
    save = tmp_path / "save.ttl"
    # Esce subito, senza muoversi: la mappa deve già esistere e riflettere lo stato iniziale.
    result = run_cli(["--new", "--config", str(cfg)], ["esci"], save)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "mappa.md").read_text(encoding="utf-8")
    assert "🧝 Ingresso delle Catacombe" in content  # player nella stanza iniziale
