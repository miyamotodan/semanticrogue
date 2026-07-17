"""Configurazione del simulatore letta da config.toml (tomllib, stdlib)."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

from tools.common import ROOT

CONFIG_PATH = ROOT / "config.toml"


@dataclass(frozen=True)
class Config:
    validation_mode: str = "turn"     # "turn" = SHACL dopo ogni transizione, "on-demand" = solo col comando `valida`
    player_success: float = 1.0       # probabilità di vittoria del player in [0, 1]
    seed: int | None = None           # seme RNG per run riproducibili; None = casuale
    auto_map: bool = False            # se true, riscrive la mappa dopo ogni azione riuscita


def _section(raw: dict, name: str) -> dict:
    """Legge una tabella TOML opzionale; ValueError se la chiave esiste ma non è una tabella."""
    value = raw.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"la sezione [{name}] deve essere una tabella, non {value!r}")
    return value


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Carica la configurazione; file assente = tutti i default. ValueError su valori fuori range."""
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    mode = _section(raw, "validation").get("mode", "turn")
    success = _section(raw, "combat").get("player_success", 1.0)
    seed = raw.get("seed")
    auto_map = _section(raw, "map").get("auto", False)

    if mode not in ("turn", "on-demand"):
        raise ValueError(f"validation.mode sconosciuto: {mode!r} (ammessi: \"turn\", \"on-demand\")")
    if not isinstance(success, (int, float)) or isinstance(success, bool) or not 0 <= success <= 1:
        raise ValueError(f"combat.player_success fuori da [0, 1]: {success!r}")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError(f"seed deve essere un intero: {seed!r}")
    if not isinstance(auto_map, bool):
        raise ValueError(f"map.auto deve essere un booleano: {auto_map!r}")
    return Config(validation_mode=mode, player_success=float(success), seed=seed, auto_map=auto_map)
