"""La configurazione del simulatore si carica con default sensati e rifiuta valori fuori range."""
import pytest

from tools.config import CONFIG_PATH, Config, load_config


def test_default_config_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "assente.toml")
    assert cfg == Config(validation_mode="turn", player_success=1.0, seed=None, auto_map=False)


def test_repo_config_is_valid():
    cfg = load_config(CONFIG_PATH)
    assert cfg.validation_mode in ("turn", "on-demand")
    assert 0.0 <= cfg.player_success <= 1.0


def test_config_reads_values(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text('seed = 42\n[validation]\nmode = "on-demand"\n[combat]\nplayer_success = 0.5\n'
                 '[map]\nauto = true\n',
                 encoding="utf-8")
    cfg = load_config(f)
    assert cfg == Config(validation_mode="on-demand", player_success=0.5, seed=42, auto_map=True)


def test_config_reads_seed_zero(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text("seed = 0\n", encoding="utf-8")
    assert load_config(f).seed == 0


def test_auto_map_defaults_to_false(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text("seed = 1\n", encoding="utf-8")
    assert load_config(f).auto_map is False


@pytest.mark.parametrize("body", [
    '[validation]\nmode = "sempre"\n',
    '[combat]\nplayer_success = 1.5\n',
    '[combat]\nplayer_success = -0.1\n',
    'seed = "quaranta"\n',
    '[map]\nauto = "si"\n',
])
def test_config_rejects_bad_values(tmp_path, body):
    f = tmp_path / "c.toml"
    f.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(f)
