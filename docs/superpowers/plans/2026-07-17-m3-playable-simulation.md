# M3 Playable Simulation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un simulatore CLI a turni in cui il grafo RDF è il world state: leggi stato → azioni ammissibili (SPARQL) → transizione (rdflib) → validazione SHACL → autosave su `runtime/save.ttl`.

**Architecture:** Lo stato di partita vive **solo** in un runtime graph rdflib separato dal content graph (mai oggetti Python con stato). `tools/engine.py` espone transizioni pure sul grafo; `tools/play.py` è la CLI sottile che orchestra turno, validazione e salvataggio; le precondizioni sono query SPARQL in `queries/runtime/`.

**Tech Stack:** Python 3.12 (venv in `.venv/`), rdflib, pySHACL, pytest, `tomllib` (stdlib) per `config.toml`.

**Spec:** `docs/superpowers/specs/2026-07-17-m3-playable-simulation-design.md`

## Global Constraints

- Ambiente: eseguire tutto con `.venv/Scripts/python` (Windows, shell Git Bash → forward slash, es. `.venv/Scripts/python -m pytest`).
- Namespace: `sr:` = `http://example.org/semantic-roguelike#` (vocabolario), `ex:` = `http://example.org/id/` (istanze). Mai istanze in `sr:` né vocabolario in `ex:`.
- **Annotazioni bilingui obbligatorie** su ogni risorsa nuova (classi, proprietà, shape, istanze): `rdfs:label` e `rdfs:comment` sia `@it` sia `@en`; le shape hanno anche `sh:name`, `sh:description`, `sh:message` bilingui.
- Bug rdflib: nelle query SPARQL delle shape MAI `FILTER NOT EXISTS { { A } UNION { B } }`; usare più `FILTER NOT EXISTS` separati.
- Convenzione runtime: **assenza di tripla = stato di default** (mostro vivo, portale chiuso, quest non accettata). `sr:isAlive false` si scrive solo alla morte, `sr:isOpen true` solo all'apertura.
- Exit code: 0 = ok, 1 = violazioni contenuto (validate), 2 = errore parsing/config, 3 = violazione runtime dopo una transizione (bug del motore).
- Ogni modifica a comandi/opzioni/query va riflessa in README.md (regola CLAUDE.md) — il piano lo fa nel Task 10.
- Messaggi di commit in italiano, stile del repo (`Task N: ...`), con firma `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- I test esistenti (21) devono restare verdi a ogni task.

---

### Task 1: Gap ontologico `sr:npcInRoom` + posizionamento NPC + shape di contenuto

**Files:**
- Modify: `ontology/rogue.ttl` (nuova object property, dopo `sr:questReward`, riga ~190)
- Modify: `dataset/dataset.ttl` (posizionamento dei 2 NPC, in coda al file)
- Modify: `shacl/rogue-rules.ttl` (nuova property shape, dopo `sr:NPCQuestShape`, riga ~211)
- Create: `tests/invalid/npc-nowhere.ttl`
- Modify: `tests/test_validation.py` (nuova riga in `BROKEN_CASES`)

**Interfaces:**
- Consumes: convenzioni esistenti (shape property-based come `sr:PortalShape`).
- Produces: `sr:npcInRoom` (NPC→Room) usato dalla query `npcs-here.rq` (Task 4) e dall'azione `parla` (Task 6); `ex:graveHermit` in `ex:entrance01`, `ex:ashPriest` in `ex:chapel03`.

- [ ] **Step 1: Scrivere il test che fallisce** — aggiungere il caso rotto a `BROKEN_CASES` in `tests/test_validation.py`:

```python
    ("npc-nowhere.ttl", EX.brokenNPC, ("path", SR.npcInRoom)),
```

e creare `tests/invalid/npc-nowhere.ttl`:

```turtle
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix ex:   <http://example.org/id/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# NPC senza stanza: offre una quest ma non si trova da nessuna parte.
ex:brokenNPC a sr:NPC ;
  rdfs:label "NPC senza dimora"@it ;
  rdfs:label "Homeless NPC"@en .
```

- [ ] **Step 2: Eseguire il test e verificarlo rosso**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py -k npc-nowhere -v`
Expected: FAIL (`npc-nowhere.ttl dovrebbe violare le shape` — la shape non esiste ancora).

- [ ] **Step 3: Implementare** — in `ontology/rogue.ttl`, dopo il blocco di `sr:questReward`:

```turtle
sr:npcInRoom a owl:ObjectProperty ;
  rdfs:domain sr:NPC ;
  rdfs:range sr:Room ;
  rdfs:label "si trova nella stanza"@it ;
  rdfs:label "located in room"@en ;
  rdfs:comment "Indica la stanza in cui il personaggio non giocante si trova e in cui il giocatore può interagirci."@it ;
  rdfs:comment "Indicates the room where the non-player character is located and where the player can interact with it."@en .
```

In `shacl/rogue-rules.ttl`, dopo `sr:NPCQuestShape`:

```turtle
sr:NPCPlacementShape a sh:NodeShape ;
  sh:targetClass sr:NPC ;
  rdfs:label "Collocazione degli NPC"@it ;
  rdfs:label "NPC placement"@en ;
  rdfs:comment "Shape che impone che ogni personaggio non giocante si trovi in esattamente una stanza, altrimenti è irraggiungibile dal giocatore."@it ;
  rdfs:comment "Shape enforcing that every non-player character is located in exactly one room, otherwise the player cannot reach it."@en ;

  sh:property [
    sh:path sr:npcInRoom ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:class sr:Room ;
    sh:name "stanza dell'NPC"@it ;
    sh:name "NPC room"@en ;
    sh:description "Ogni NPC deve trovarsi in una e una sola stanza valida del mondo."@it ;
    sh:description "Each NPC must be located in one and only one valid room of the world."@en ;
  ] .
```

In `dataset/dataset.ttl`, in coda (dopo `ex:sanctum01 sr:connectedTo ex:boneBridge04 .`):

```turtle
### M3 — collocazione degli NPC (gap emerso progettando il simulatore)

ex:graveHermit sr:npcInRoom ex:entrance01 .
ex:ashPriest sr:npcInRoom ex:chapel03 .
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 22 passed (21 esistenti + npc-nowhere). Poi `.venv/Scripts/python -m tools.validate` → exit 0, "Conforms: True".

- [ ] **Step 5: Commit**

```bash
git add ontology/rogue.ttl dataset/dataset.ttl shacl/rogue-rules.ttl tests/invalid/npc-nowhere.ttl tests/test_validation.py
git commit -m "Task 1 M3: sr:npcInRoom, NPC collocati e shape di collocazione"
```

---

### Task 2: Vocabolario runtime (`ontology/runtime.ttl`) + caricamento in `common.py`

**Files:**
- Create: `ontology/runtime.ttl`
- Modify: `tools/common.py`
- Modify: `.gitignore` (aggiungere `runtime/`)
- Test: `tests/test_load.py` (aggiungere un test)

**Interfaces:**
- Consumes: `load_graph(*paths)` esistente.
- Produces: costanti `RUNTIME_ONTOLOGY`, `RUNTIME_SHAPES`, `SAVE_PATH` e funzione `load_runtime_world(data_path: Path = DATASET) -> Graph` (ontologia statica + ontologia runtime + dataset) in `tools/common.py`. Vocabolario: `sr:Player`, `sr:currentRoom`, `sr:hasItem`, `sr:isAlive`, `sr:isOpen`, `sr:questStatus`.

- [ ] **Step 1: Test che fallisce** — in coda a `tests/test_load.py`:

```python
def test_runtime_world_includes_runtime_vocabulary():
    """load_runtime_world unisce anche il vocabolario runtime (sr:Player ecc.)."""
    from rdflib import Namespace
    from rdflib.namespace import RDF, OWL
    from tools.common import load_runtime_world

    SR = Namespace("http://example.org/semantic-roguelike#")
    world = load_runtime_world()
    assert (SR.Player, RDF.type, OWL.Class) in world
    assert (SR.currentRoom, RDF.type, OWL.ObjectProperty) in world
```

Run: `.venv/Scripts/python -m pytest tests/test_load.py -v` → FAIL (`ImportError: load_runtime_world`).

- [ ] **Step 2: Creare `ontology/runtime.ttl`**

```turtle
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

sr:RuntimeOntology a owl:Ontology ;
  rdfs:label "Ontologia runtime del Roguelike Semantico"@it ;
  rdfs:label "Semantic Roguelike runtime ontology"@en ;
  rdfs:comment "Vocabolario minimo per lo stato di partita: giocatore, posizione, inventario, vita, aperture e stato delle quest. Convenzione: assenza di tripla = stato di default (mostro vivo, portale chiuso, quest non accettata)."@it ;
  rdfs:comment "Minimal vocabulary for the game state: player, position, inventory, life, openings, and quest status. Convention: absence of a triple = default state (monster alive, portal closed, quest not accepted)."@en .

sr:Player a owl:Class ;
  rdfs:label "Giocatore"@it ;
  rdfs:label "Player"@en ;
  rdfs:comment "Entità controllata da chi gioca: ha una posizione corrente e un inventario nel grafo runtime."@it ;
  rdfs:comment "Entity controlled by the person playing: it has a current position and an inventory in the runtime graph."@en .

sr:currentRoom a owl:ObjectProperty ;
  rdfs:domain sr:Player ;
  rdfs:range sr:Room ;
  rdfs:label "stanza corrente"@it ;
  rdfs:label "current room"@en ;
  rdfs:comment "Posizione corrente del giocatore: esattamente una stanza per tutta la durata della run."@it ;
  rdfs:comment "Current position of the player: exactly one room for the whole duration of the run."@en .

sr:hasItem a owl:ObjectProperty ;
  rdfs:domain sr:Player ;
  rdfs:range sr:Item ;
  rdfs:label "possiede oggetto"@it ;
  rdfs:label "has item"@en ;
  rdfs:comment "Oggetto presente nell'inventario del giocatore, ottenuto come drop di un mostro sconfitto o ricompensa di una quest completata."@it ;
  rdfs:comment "Item in the player's inventory, obtained as a defeated monster's drop or a completed quest's reward."@en .

sr:isAlive a owl:DatatypeProperty ;
  rdfs:range xsd:boolean ;
  rdfs:label "è vivo"@it ;
  rdfs:label "is alive"@en ;
  rdfs:comment "Stato vitale di un mostro o del giocatore; si scrive solo alla morte (false), l'assenza della tripla significa vivo. Nessun dominio rigido: vale per mostri e giocatore."@it ;
  rdfs:comment "Life state of a monster or the player; written only on death (false), absence of the triple means alive. No strict domain: applies to monsters and the player."@en .

sr:isOpen a owl:DatatypeProperty ;
  rdfs:domain sr:Portal ;
  rdfs:range xsd:boolean ;
  rdfs:label "è aperto"@it ;
  rdfs:label "is open"@en ;
  rdfs:comment "Stato di apertura di un portale; si scrive solo all'apertura (true), l'assenza della tripla significa chiuso."@it ;
  rdfs:comment "Open state of a portal; written only when opened (true), absence of the triple means closed."@en .

sr:questStatus a owl:DatatypeProperty ;
  rdfs:domain sr:Quest ;
  rdfs:range xsd:string ;
  rdfs:label "stato della quest"@it ;
  rdfs:label "quest status"@en ;
  rdfs:comment "Stato di avanzamento della quest nella run corrente: \"active\" o \"completed\"; l'assenza della tripla significa non ancora accettata."@it ;
  rdfs:comment "Progress state of the quest in the current run: \"active\" or \"completed\"; absence of the triple means not yet accepted."@en .
```

- [ ] **Step 3: Estendere `tools/common.py`** — aggiungere dopo le costanti esistenti:

```python
RUNTIME_ONTOLOGY = ROOT / "ontology" / "runtime.ttl"
RUNTIME_SHAPES = ROOT / "shacl" / "runtime-rules.ttl"
SAVE_PATH = ROOT / "runtime" / "save.ttl"
```

e in coda al file:

```python
def load_runtime_world(data_path: Path = DATASET) -> Graph:
    """Grafo di lavoro del simulatore: ontologia statica + ontologia runtime + dataset."""
    return load_graph(ONTOLOGY, RUNTIME_ONTOLOGY, data_path)
```

Aggiungere `runtime/` in coda a `.gitignore` (il salvataggio è stato locale, non contenuto).

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 23 passed.

- [ ] **Step 5: Commit**

```bash
git add ontology/runtime.ttl tools/common.py .gitignore tests/test_load.py
git commit -m "Task 2 M3: vocabolario runtime e load_runtime_world"
```

---

### Task 3: `config.toml` + `tools/config.py`

**Files:**
- Create: `config.toml` (radice del repo, versionato)
- Create: `tools/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` (dataclass frozen: `validation_mode: str`, `player_success: float`, `seed: int | None`) e `load_config(path: Path = CONFIG_PATH) -> Config` che alza `ValueError` con messaggio chiaro su valori fuori range; costante `CONFIG_PATH`. Usati da `tools/play.py` (Task 8).

- [ ] **Step 1: Test che fallisce** — creare `tests/test_config.py`:

```python
"""La configurazione del simulatore si carica con default sensati e rifiuta valori fuori range."""
import pytest

from tools.config import CONFIG_PATH, Config, load_config


def test_default_config_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "assente.toml")
    assert cfg == Config(validation_mode="turn", player_success=1.0, seed=None)


def test_repo_config_is_valid():
    cfg = load_config(CONFIG_PATH)
    assert cfg.validation_mode in ("turn", "on-demand")
    assert 0.0 <= cfg.player_success <= 1.0


def test_config_reads_values(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text('[validation]\nmode = "on-demand"\n[combat]\nplayer_success = 0.5\nseed = 42\n',
                 encoding="utf-8")
    cfg = load_config(f)
    assert cfg == Config(validation_mode="on-demand", player_success=0.5, seed=42)


@pytest.mark.parametrize("body", [
    '[validation]\nmode = "sempre"\n',
    '[combat]\nplayer_success = 1.5\n',
    '[combat]\nplayer_success = -0.1\n',
    'seed = "quaranta"\n',
])
def test_config_rejects_bad_values(tmp_path, body):
    f = tmp_path / "c.toml"
    f.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(f)
```

Nota: `seed` è a livello top del TOML (come da spec), `mode` sotto `[validation]`, `player_success` sotto `[combat]`.

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v` → FAIL (`ModuleNotFoundError: tools.config`).

- [ ] **Step 2: Implementare `tools/config.py`**

```python
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


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Carica la configurazione; file assente = tutti i default. ValueError su valori fuori range."""
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    mode = raw.get("validation", {}).get("mode", "turn")
    success = raw.get("combat", {}).get("player_success", 1.0)
    seed = raw.get("seed")

    if mode not in ("turn", "on-demand"):
        raise ValueError(f"validation.mode sconosciuto: {mode!r} (ammessi: \"turn\", \"on-demand\")")
    if not isinstance(success, (int, float)) or isinstance(success, bool) or not 0 <= success <= 1:
        raise ValueError(f"combat.player_success fuori da [0, 1]: {success!r}")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError(f"seed deve essere un intero: {seed!r}")
    return Config(validation_mode=mode, player_success=float(success), seed=seed)
```

- [ ] **Step 3: Creare `config.toml`** (default del repo):

```toml
# Configurazione del simulatore di run (tools/play.py).

[validation]
# "turn" = validazione SHACL runtime dopo ogni transizione (default)
# "on-demand" = solo quando si usa il comando `valida`
mode = "turn"

[combat]
# Probabilità di vittoria del player in combattimento, in [0, 1]. 1 = vince sempre.
player_success = 1.0

# seed = 42   # opzionale: seme RNG per run riproducibili; commentato = casuale
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: 7 passed (totale suite: 30).

- [ ] **Step 5: Commit**

```bash
git add config.toml tools/config.py tests/test_config.py
git commit -m "Task 3 M3: config.toml con modalità validazione e probabilità di combattimento"
```

---

### Task 4: Query runtime + scheletro `Engine` (stato iniziale e letture)

**Files:**
- Create: `queries/runtime/available-moves.rq`, `queries/runtime/openable-portals.rq`, `queries/runtime/monsters-here.rq`, `queries/runtime/npcs-here.rq`, `queries/runtime/quest-status.rq`
- Create: `tools/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `load_runtime_world()` (Task 2).
- Produces (per Task 5–9):
  - `tools/engine.py`: `SR`, `EX` (Namespace), `PLAYER = EX.player` (URIRef), `ActionError(Exception)`,
    `new_state(world: Graph) -> Graph` (grafo runtime iniziale: player nella start room),
    `class Engine` con `__init__(self, world: Graph, state: Graph, player_success: float = 1.0, seed: int | None = None)`,
    `Engine.graph() -> Graph` (unione world+state), `Engine.current_room() -> URIRef`,
    `Engine.run_query(name: str) -> list` (esegue `queries/runtime/<name>` sul grafo unito).
  - Variabili di output delle query (nomi esatti usati da engine e CLI): `available-moves.rq` → `?stanza ?via`; `openable-portals.rq` → `?portale ?chiave ?stanza`; `monsters-here.rq` → `?mostro`; `npcs-here.rq` → `?npc ?quest`; `quest-status.rq` → `?quest ?status ?target`.

Nota: `queries/runtime/` NON viene raccolta da `tools/query.py --all` né da `tests/test_queries.py` (entrambi usano `glob("*.rq")` non ricorsivo su `queries/`): le query runtime hanno senso solo col grafo di stato, va bene così.

- [ ] **Step 1: Test che fallisce** — creare `tests/test_engine.py`:

```python
"""Il motore di M3: stato iniziale, letture SPARQL e transizioni sul runtime graph."""
import pytest
from rdflib import Literal, Namespace
from rdflib.namespace import RDF

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, Engine, new_state

WORLD = load_runtime_world()


@pytest.fixture
def eng():
    return Engine(WORLD, new_state(WORLD))


def test_new_state_puts_player_in_start_room():
    state = new_state(WORLD)
    assert (PLAYER, RDF.type, SR.Player) in state
    assert (PLAYER, SR.currentRoom, EX.entrance01) in state
    assert len(state) == 2  # solo player: assenza di tripla = stato di default


def test_available_moves_from_start(eng):
    moves = {row.stanza for row in eng.run_query("available-moves.rq")}
    assert moves == {EX.ossuary02, EX.chapel03}


def test_monsters_and_npcs_visible(eng):
    assert [r.mostro for r in eng.run_query("monsters-here.rq")] == []  # entrance01 è sicura
    npcs = {(r.npc, r.quest) for r in eng.run_query("npcs-here.rq")}
    assert (EX.graveHermit, EX.recoverRelic) in npcs
    assert (EX.graveHermit, EX.endTheCourt) in npcs


def test_openable_portals_requires_key_and_presence(eng):
    # Il player è all'ingresso senza chiavi: nessun portale apribile.
    assert eng.run_query("openable-portals.rq") == []
    # Con la chiave giusta nella stanza giusta il portale compare.
    eng.state.set((PLAYER, SR.currentRoom, EX.crypt07))
    eng.state.add((PLAYER, SR.hasItem, EX.ivoryKey))
    rows = eng.run_query("openable-portals.rq")
    assert [(r.portale, r.stanza) for r in rows] == [(EX.sealedGate, EX.sanctum01)]


def test_quest_status_reports_all_quests(eng):
    rows = {(r.quest, r.status) for r in eng.run_query("quest-status.rq")}
    assert (EX.recoverRelic, None) in rows
    assert (EX.endTheCourt, None) in rows
    assert (EX.cullTheSpores, None) in rows
```

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v` → FAIL (`ModuleNotFoundError: tools.engine`).

- [ ] **Step 2: Creare le 5 query** (tutte autonome, con i propri PREFIX, commento iniziale con la domanda).

`queries/runtime/available-moves.rq`:

```sparql
# Mosse ammissibili dalla stanza corrente del player: passaggi (in entrambi i versi)
# e portali aperti (in entrambi i versi). Risponde a: "dove posso andare ora?"
PREFIX sr: <http://example.org/semantic-roguelike#>
PREFIX ex: <http://example.org/id/>

SELECT DISTINCT ?stanza ?via
WHERE {
  ex:player sr:currentRoom ?qui .
  {
    ?qui sr:connectedTo ?stanza .
    BIND("passaggio" AS ?via)
  }
  UNION
  {
    ?stanza sr:connectedTo ?qui .
    BIND("passaggio" AS ?via)
  }
  UNION
  {
    ?p a sr:Portal ; sr:portalInRoom ?qui ; sr:unlocksRoom ?stanza ; sr:isOpen true .
    BIND("portale" AS ?via)
  }
  UNION
  {
    ?p a sr:Portal ; sr:unlocksRoom ?qui ; sr:portalInRoom ?stanza ; sr:isOpen true .
    BIND("portale" AS ?via)
  }
}
```

`queries/runtime/openable-portals.rq`:

```sparql
# Portali nella stanza corrente ancora chiusi la cui chiave è nell'inventario.
# Risponde a: "quali portali posso aprire ora?"
PREFIX sr: <http://example.org/semantic-roguelike#>
PREFIX ex: <http://example.org/id/>

SELECT ?portale ?chiave ?stanza
WHERE {
  ex:player sr:currentRoom ?qui .
  ?portale a sr:Portal ;
           sr:portalInRoom ?qui ;
           sr:requiresItem ?chiave ;
           sr:unlocksRoom ?stanza .
  ex:player sr:hasItem ?chiave .
  FILTER NOT EXISTS { ?portale sr:isOpen true . }
}
```

`queries/runtime/monsters-here.rq`:

```sparql
# Mostri ancora vivi nella stanza corrente del player.
# Risponde a: "chi devo affrontare qui?"
PREFIX sr: <http://example.org/semantic-roguelike#>
PREFIX ex: <http://example.org/id/>

SELECT ?mostro
WHERE {
  ex:player sr:currentRoom ?qui .
  ?qui sr:hostsMonster ?mostro .
  FILTER NOT EXISTS { ?mostro sr:isAlive false . }
}
ORDER BY ?mostro
```

`queries/runtime/npcs-here.rq`:

```sparql
# NPC nella stanza corrente con le quest che offrono e che non sono ancora state accettate.
# Risponde a: "con chi posso parlare, e per quale quest?"
PREFIX sr: <http://example.org/semantic-roguelike#>
PREFIX ex: <http://example.org/id/>

SELECT ?npc ?quest
WHERE {
  ex:player sr:currentRoom ?qui .
  ?npc a sr:NPC ;
       sr:npcInRoom ?qui ;
       sr:offersQuest ?quest .
  FILTER NOT EXISTS { ?quest sr:questStatus ?s . }
}
ORDER BY ?npc ?quest
```

`queries/runtime/quest-status.rq`:

```sparql
# Quadro delle quest della run: stato corrente (assente = non accettata) e stanza obiettivo.
# Risponde a: "a che punto sono le quest?"
PREFIX sr: <http://example.org/semantic-roguelike#>

SELECT ?quest ?status ?target
WHERE {
  ?quest a sr:Quest ;
         sr:questTargetRoom ?target .
  OPTIONAL { ?quest sr:questStatus ?status . }
}
ORDER BY ?quest
```

- [ ] **Step 3: Creare `tools/engine.py`** (scheletro: stato iniziale + letture):

```python
"""Motore di M3: lo stato di partita è solo triple RDF nel runtime graph.

Letture via SPARQL (queries/runtime/), transizioni come modifiche di triple,
nessuno stato duplicato in oggetti Python.
"""
import random

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from tools.common import ROOT

SR = Namespace("http://example.org/semantic-roguelike#")
EX = Namespace("http://example.org/id/")
PLAYER = EX.player
RUNTIME_QUERIES = ROOT / "queries" / "runtime"


class ActionError(Exception):
    """Azione non ammissibile: il grafo non viene modificato."""


def new_state(world: Graph) -> Graph:
    """Runtime graph iniziale: il player nella stanza con isStartRoom true, nient'altro."""
    start = world.value(predicate=SR.isStartRoom, object=Literal(True))
    if start is None:
        raise ValueError("nessuna stanza con sr:isStartRoom true nel mondo")
    g = Graph()
    g.bind("sr", SR)
    g.bind("ex", EX)
    g.add((PLAYER, RDF.type, SR.Player))
    g.add((PLAYER, SR.currentRoom, start))
    return g


class Engine:
    """Transizioni di stato sul runtime graph; il content graph è di sola lettura."""

    def __init__(self, world: Graph, state: Graph,
                 player_success: float = 1.0, seed: int | None = None):
        self.world = world
        self.state = state
        self.player_success = player_success
        self.rng = random.Random(seed)

    def graph(self) -> Graph:
        """Grafo unito contenuto+stato su cui girano query e validazione."""
        return self.world + self.state

    def current_room(self) -> URIRef:
        return self.state.value(PLAYER, SR.currentRoom)

    def run_query(self, name: str) -> list:
        """Esegue una query di queries/runtime/ sul grafo unito."""
        text = (RUNTIME_QUERIES / name).read_text(encoding="utf-8")
        return list(self.graph().query(text))
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v`
Expected: 5 passed (totale suite: 35).

- [ ] **Step 5: Commit**

```bash
git add queries/runtime/ tools/engine.py tests/test_engine.py
git commit -m "Task 4 M3: query runtime e scheletro Engine (stato iniziale e letture)"
```

---

### Task 5: Transizioni `move_to` e `open_portal`

**Files:**
- Modify: `tools/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Engine.run_query`, `ActionError`, query di Task 4.
- Produces: `Engine.move_to(room: URIRef) -> None` (ActionError se la stanza non è tra le mosse; aggiorna `currentRoom`; poi `_check_quest_completion()`), `Engine.open_portal(portal: URIRef) -> None` (ActionError se non apribile; scrive `isOpen true`), `Engine._check_quest_completion() -> None` (per ora: quest attive con target = stanza corrente e nessun mostro vivo → `completed` + reward; usata anche da `fight` nel Task 6).

- [ ] **Step 1: Test che falliscono** — aggiungere a `tests/test_engine.py`:

```python
from tools.engine import ActionError


def test_move_to_valid_room(eng):
    eng.move_to(EX.ossuary02)
    assert eng.current_room() == EX.ossuary02
    # Il passaggio è bidirezionale: si può tornare indietro.
    eng.move_to(EX.entrance01)
    assert eng.current_room() == EX.entrance01


def test_move_to_unreachable_room_is_rejected(eng):
    with pytest.raises(ActionError):
        eng.move_to(EX.sanctum01)
    assert eng.current_room() == EX.entrance01  # nessuna modifica


def test_open_portal_requires_key_and_presence(eng):
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # non è nemmeno nella stanza
    eng.state.set((PLAYER, SR.currentRoom, EX.crypt07))
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # manca la chiave
    eng.state.add((PLAYER, SR.hasItem, EX.ivoryKey))
    eng.open_portal(EX.sealedGate)
    assert (EX.sealedGate, SR.isOpen, Literal(True)) in eng.state
    # Ora il portale aperto è una mossa: si può entrare nel santuario.
    moves = {row.stanza for row in eng.run_query("available-moves.rq")}
    assert EX.sanctum01 in moves
    with pytest.raises(ActionError):
        eng.open_portal(EX.sealedGate)  # già aperto


def test_moving_into_cleared_target_room_completes_active_quest(eng):
    # cullTheSpores attiva; il nido è già stato ripulito (mostri segnati sconfitti).
    eng.state.add((EX.cullTheSpores, SR.questStatus, Literal("active")))
    eng.state.add((EX.myceliumBrute, SR.isAlive, Literal(False)))
    eng.state.add((EX.sporeMother, SR.isAlive, Literal(False)))
    eng.state.set((PLAYER, SR.currentRoom, EX.fungalHollow01))
    eng.move_to(EX.sporeNest02)
    assert (EX.cullTheSpores, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.boneBlade) in eng.state
```

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v` → FAIL (`AttributeError: move_to`).

- [ ] **Step 2: Implementare in `tools/engine.py`** (metodi di `Engine`):

```python
    def move_to(self, room: URIRef) -> None:
        """Sposta il player in una stanza raggiungibile (passaggio o portale aperto)."""
        moves = {row.stanza for row in self.run_query("available-moves.rq")}
        if room not in moves:
            raise ActionError(f"stanza non raggiungibile da qui: {room}")
        self.state.set((PLAYER, SR.currentRoom, room))
        self._check_quest_completion()

    def open_portal(self, portal: URIRef) -> None:
        """Apre un portale chiuso nella stanza corrente, se la chiave è in inventario."""
        openable = {row.portale for row in self.run_query("openable-portals.rq")}
        if portal not in openable:
            raise ActionError(f"portale non apribile ora: {portal}")
        self.state.add((portal, SR.isOpen, Literal(True)))

    def _check_quest_completion(self) -> None:
        """Le quest attive con target = stanza corrente e nessun mostro vivo si completano."""
        if self.run_query("monsters-here.rq"):
            return
        room = self.current_room()
        for quest in list(self.state.subjects(SR.questStatus, Literal("active"))):
            if (quest, SR.questTargetRoom, room) in self.world:
                self.state.set((quest, SR.questStatus, Literal("completed")))
                for reward in self.world.objects(quest, SR.questReward):
                    self.state.add((PLAYER, SR.hasItem, reward))
```

- [ ] **Step 3: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v`
Expected: 9 passed (totale suite: 39).

- [ ] **Step 4: Commit**

```bash
git add tools/engine.py tests/test_engine.py
git commit -m "Task 5 M3: transizioni move_to e open_portal con completamento quest"
```

---

### Task 6: Transizioni `fight` e `talk_to`, esito della run

**Files:**
- Modify: `tools/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Engine.rng`, `Engine.player_success`, `_check_quest_completion` (Task 5).
- Produces: `Engine.fight(monster: URIRef | None = None) -> bool` (True = vinto; False = player morto), `Engine.talk_to(npc: URIRef) -> list[URIRef]` (quest appena attivate), `Engine.outcome() -> str | None` (`"victory"` / `"defeat"` / `None`). Usati dalla CLI (Task 8) e dai test end-to-end (Task 9).

- [ ] **Step 1: Test che falliscono** — aggiungere a `tests/test_engine.py`:

```python
def test_fight_defeats_monster_and_collects_drops(eng):
    eng.state.set((PLAYER, SR.currentRoom, EX.ossuary02))
    won = eng.fight()  # un solo mostro: il bersaglio è implicito
    assert won is True
    assert (EX.cryptRat, SR.isAlive, Literal(False)) in eng.state
    assert (PLAYER, SR.hasItem, EX.rustSword) in eng.state
    assert eng.run_query("monsters-here.rq") == []


def test_fight_requires_target_when_room_has_many_monsters(eng):
    eng.state.set((PLAYER, SR.currentRoom, EX.sporeNest02))  # Bruto + Madre delle Spore
    with pytest.raises(ActionError):
        eng.fight()
    assert eng.fight(EX.myceliumBrute) is True


def test_fight_without_monsters_is_rejected(eng):
    with pytest.raises(ActionError):
        eng.fight()  # entrance01 è vuota


def test_fight_lost_kills_player():
    state = new_state(WORLD)
    losing = Engine(WORLD, state, player_success=0.0, seed=1)
    losing.state.set((PLAYER, SR.currentRoom, EX.ossuary02))
    assert losing.fight() is False
    assert (PLAYER, SR.isAlive, Literal(False)) in losing.state
    assert losing.outcome() == "defeat"


def test_fight_last_monster_in_target_room_completes_quest(eng):
    eng.state.add((EX.recoverRelic, SR.questStatus, Literal("active")))
    eng.state.set((PLAYER, SR.currentRoom, EX.sanctum01))
    eng.fight()  # il Tiranno della Cripta è l'unico mostro del santuario
    assert (EX.recoverRelic, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.ivoryKey) in eng.state  # ricompensa della quest
    assert eng.outcome() == "victory"


def test_talk_to_activates_all_unaccepted_quests(eng):
    activated = eng.talk_to(EX.graveHermit)
    assert set(activated) == {EX.recoverRelic, EX.endTheCourt}
    assert (EX.recoverRelic, SR.questStatus, Literal("active")) in eng.state
    with pytest.raises(ActionError):
        eng.talk_to(EX.graveHermit)  # niente più quest da offrire
    with pytest.raises(ActionError):
        eng.talk_to(EX.ashPriest)  # è in un'altra stanza


def test_outcome_none_during_normal_play(eng):
    assert eng.outcome() is None
```

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v` → FAIL (`AttributeError: fight`).

- [ ] **Step 2: Implementare in `tools/engine.py`** (metodi di `Engine`):

```python
    def fight(self, monster: URIRef | None = None) -> bool:
        """Affronta un mostro vivo nella stanza corrente. True = vinto, False = player morto."""
        alive = [row.mostro for row in self.run_query("monsters-here.rq")]
        if not alive:
            raise ActionError("nessun mostro da combattere qui")
        if monster is None:
            if len(alive) > 1:
                raise ActionError("più mostri presenti: indica quale combattere")
            monster = alive[0]
        elif monster not in alive:
            raise ActionError(f"mostro non presente o già sconfitto: {monster}")

        if self.rng.random() < self.player_success:
            self.state.add((monster, SR.isAlive, Literal(False)))
            for item in self.world.objects(monster, SR.dropsItem):
                self.state.add((PLAYER, SR.hasItem, item))
            self._check_quest_completion()
            return True
        self.state.add((PLAYER, SR.isAlive, Literal(False)))
        return False

    def talk_to(self, npc: URIRef) -> list[URIRef]:
        """Parla con un NPC nella stanza corrente: attiva le sue quest non ancora accettate."""
        offers = [row.quest for row in self.run_query("npcs-here.rq") if row.npc == npc]
        if not offers:
            raise ActionError(f"nessun NPC con quest da offrire qui: {npc}")
        for quest in offers:
            self.state.add((quest, SR.questStatus, Literal("active")))
        return offers

    def outcome(self) -> str | None:
        """Esito della run: \"defeat\" se il player è morto, \"victory\" alla prima quest completata."""
        if (PLAYER, SR.isAlive, Literal(False)) in self.state:
            return "defeat"
        if next(self.state.subjects(SR.questStatus, Literal("completed")), None) is not None:
            return "victory"
        return None
```

Nota su `player_success`: `rng.random()` restituisce valori in `[0, 1)`, quindi con `player_success = 1.0` il confronto `<` è sempre vero (vince sempre) e con `0.0` sempre falso (perde sempre) — nessun caso speciale necessario.

- [ ] **Step 3: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v`
Expected: 16 passed (totale suite: 46).

- [ ] **Step 4: Commit**

```bash
git add tools/engine.py tests/test_engine.py
git commit -m "Task 6 M3: fight probabilistico, talk_to ed esito della run"
```

---

### Task 7: Shape SHACL runtime + `validate_runtime` + stati rotti ad arte

**Files:**
- Create: `shacl/runtime-rules.ttl`
- Modify: `tools/engine.py` (funzione `validate_runtime`)
- Test: `tests/test_runtime_validation.py`

**Interfaces:**
- Consumes: `RUNTIME_SHAPES` (Task 2), `Engine.graph()`.
- Produces: `validate_runtime(world: Graph, state: Graph) -> tuple[bool, Graph, str]` in `tools/engine.py` (conforms, results_graph, results_text — stessa forma di `pyshacl.validate`). Shape: `sr:PlayerStateShape`, `sr:QuestStatusValueShape`, `sr:OpenPortalNeedsKeyShape`, `sr:ItemProvenanceShape`. Usata da CLI (Task 8) e test e2e (Task 9).

- [ ] **Step 1: Test che falliscono** — creare `tests/test_runtime_validation.py`:

```python
"""Le shape runtime intercettano stati di partita corrotti — ciascuno dalla shape attesa."""
import pytest
from rdflib import Graph, Literal, Namespace

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, new_state, validate_runtime

SH = Namespace("http://www.w3.org/ns/shacl#")
WORLD = load_runtime_world()


def test_fresh_state_conforms():
    conforms, _, text = validate_runtime(WORLD, new_state(WORLD))
    assert conforms, f"lo stato iniziale deve essere conforme:\n{text}"


def broken_two_rooms():
    state = new_state(WORLD)
    state.add((PLAYER, SR.currentRoom, EX.ossuary02))  # seconda stanza: vietato
    return state, PLAYER, ("path", SR.currentRoom)


def broken_quest_status_value():
    state = new_state(WORLD)
    state.add((EX.recoverRelic, SR.questStatus, Literal("paused")))
    return state, EX.recoverRelic, ("path", SR.questStatus)


def broken_open_portal_without_key():
    state = new_state(WORLD)
    state.add((EX.sealedGate, SR.isOpen, Literal(True)))  # aperto ma chiave mai ottenuta
    return state, EX.sealedGate, ("shape", SR.OpenPortalNeedsKeyShape)


def broken_item_from_living_monster():
    state = new_state(WORLD)
    state.add((PLAYER, SR.hasItem, EX.rustSword))  # il Ratto che la droppa è ancora vivo
    return state, PLAYER, ("shape", SR.ItemProvenanceShape)


BROKEN_STATES = [broken_two_rooms, broken_quest_status_value,
                 broken_open_portal_without_key, broken_item_from_living_monster]


@pytest.mark.parametrize("builder", BROKEN_STATES, ids=lambda b: b.__name__)
def test_broken_state_triggers_expected_shape(builder):
    state, focus, (kind, value) = builder()
    conforms, results, text = validate_runtime(WORLD, state)
    assert not conforms, f"{builder.__name__} dovrebbe violare le shape runtime"
    prop = SH.resultPath if kind == "path" else SH.sourceShape
    matching = [r for r in results.subjects(SH.focusNode, focus)
                if (r, prop, value) in results]
    assert matching, f"attesa violazione {value} su {focus}; report:\n{text}"
```

Run: `.venv/Scripts/python -m pytest tests/test_runtime_validation.py -v` → FAIL (`ImportError: validate_runtime`).

- [ ] **Step 2: Creare `shacl/runtime-rules.ttl`**

```turtle
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

sr:RuntimeShapes a owl:Ontology ;
  rdfs:label "Shape SHACL dello stato di partita"@it ;
  rdfs:label "Game-state SHACL shapes"@en ;
  rdfs:comment "Vincoli di coerenza sul runtime graph: il motore non può corrompere la partita senza che la validazione se ne accorga."@it ;
  rdfs:comment "Consistency constraints on the runtime graph: the engine cannot corrupt the game without validation noticing."@en ;
  sh:declare [
    sh:prefix "sr" ;
    sh:namespace "http://example.org/semantic-roguelike#"^^xsd:anyURI ;
  ] .

sr:PlayerStateShape a sh:NodeShape ;
  sh:targetClass sr:Player ;
  rdfs:label "Stato del giocatore"@it ;
  rdfs:label "Player state"@en ;
  rdfs:comment "Shape che impone che il giocatore si trovi in esattamente una stanza valida del mondo."@it ;
  rdfs:comment "Shape enforcing that the player is located in exactly one valid room of the world."@en ;

  sh:property [
    sh:path sr:currentRoom ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:class sr:Room ;
    sh:name "stanza corrente del giocatore"@it ;
    sh:name "player's current room"@en ;
    sh:description "Il giocatore deve avere una e una sola stanza corrente, e deve essere una stanza del mondo."@it ;
    sh:description "The player must have one and only one current room, and it must be a room of the world."@en ;
  ] .

sr:QuestStatusValueShape a sh:NodeShape ;
  sh:targetClass sr:Quest ;
  rdfs:label "Valori ammessi dello stato quest"@it ;
  rdfs:label "Allowed quest status values"@en ;
  rdfs:comment "Shape che ammette per lo stato di una quest solo i valori \"active\" e \"completed\", al più uno per quest."@it ;
  rdfs:comment "Shape allowing only the values \"active\" and \"completed\" for a quest's status, at most one per quest."@en ;

  sh:property [
    sh:path sr:questStatus ;
    sh:maxCount 1 ;
    sh:in ( "active" "completed" ) ;
    sh:name "stato della quest"@it ;
    sh:name "quest status"@en ;
    sh:description "Lo stato di una quest, se presente, è uno solo tra \"active\" e \"completed\"."@it ;
    sh:description "A quest's status, when present, is exactly one of \"active\" and \"completed\"."@en ;
  ] .

sr:OpenPortalNeedsKeyShape a sh:NodeShape ;
  sh:targetClass sr:Portal ;
  rdfs:label "Un portale aperto richiede la sua chiave"@it ;
  rdfs:label "An open portal requires its key"@en ;
  rdfs:comment "Shape SPARQL-based: un portale può risultare aperto solo se la chiave che richiede è nell'inventario del giocatore."@it ;
  rdfs:comment "SPARQL-based shape: a portal can be open only if the key it requires is in the player's inventory."@en ;
  sh:sparql [
    sh:prefixes sr:RuntimeShapes ;
    sh:message "Portale aperto senza che il giocatore possieda la chiave richiesta: transizione illecita."@it ;
    sh:message "Portal open although the player does not hold the required key: illegal transition."@en ;
    sh:select """
      SELECT $this
      WHERE {
        $this sr:isOpen true ;
              sr:requiresItem ?chiave .
        FILTER NOT EXISTS { ?player a sr:Player ; sr:hasItem ?chiave . }
      }
    """ ;
  ] .

sr:ItemProvenanceShape a sh:NodeShape ;
  sh:targetClass sr:Player ;
  rdfs:label "Provenienza degli oggetti in inventario"@it ;
  rdfs:label "Inventory item provenance"@en ;
  rdfs:comment "Shape SPARQL-based: ogni oggetto in inventario deve avere una provenienza lecita — drop di un mostro sconfitto o ricompensa di una quest completata."@it ;
  rdfs:comment "SPARQL-based shape: every inventory item must have a legitimate provenance — a defeated monster's drop or a completed quest's reward."@en ;
  sh:sparql [
    sh:prefixes sr:RuntimeShapes ;
    sh:message "Oggetto in inventario senza provenienza lecita (nessun mostro sconfitto lo droppa, nessuna quest completata lo premia)."@it ;
    sh:message "Inventory item with no legitimate provenance (no defeated monster drops it, no completed quest rewards it)."@en ;
    sh:select """
      SELECT $this ?value
      WHERE {
        $this sr:hasItem ?value .
        # Nota: due NOT EXISTS separati invece di NOT EXISTS { A UNION B }:
        # logicamente equivalenti, ma il secondo costrutto è valutato male da rdflib.
        FILTER NOT EXISTS { ?m sr:dropsItem ?value . ?m sr:isAlive false . }
        FILTER NOT EXISTS { ?q sr:questReward ?value ; sr:questStatus "completed" . }
      }
    """ ;
  ] .
```

- [ ] **Step 3: Aggiungere `validate_runtime` a `tools/engine.py`**

In testa al file aggiungere gli import:

```python
from pyshacl import validate

from tools.common import ROOT, RUNTIME_SHAPES, load_graph
```

(sostituisce l'import esistente `from tools.common import ROOT`). In coda al file:

```python
def validate_runtime(world: Graph, state: Graph):
    """Valida lo stato di partita contro le shape runtime. Ritorna (conforms, results_graph, text)."""
    shapes = load_graph(RUNTIME_SHAPES)
    return validate(world + state, shacl_graph=shapes, advanced=True)
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_runtime_validation.py -v`
Expected: 5 passed (totale suite: 51).

- [ ] **Step 5: Commit**

```bash
git add shacl/runtime-rules.ttl tools/engine.py tests/test_runtime_validation.py
git commit -m "Task 7 M3: shape runtime e validate_runtime con stati rotti ad arte"
```

---

### Task 8: CLI `tools/play.py` (turni, autosave, resume, config)

**Files:**
- Create: `tools/play.py`
- Test: `tests/test_play_cli.py`

**Interfaces:**
- Consumes: `Engine`, `new_state`, `validate_runtime`, `ActionError` (Task 4–7); `load_config`, `Config` (Task 3); `SAVE_PATH`, `load_runtime_world`, `load_graph` (Task 2).
- Produces: comando `python -m tools.play [--new] [--seed N] [--save FILE.ttl] [--config FILE.toml]`. Comandi di gioco: `vai <stanza>`, `apri <portale>`, `combatti [mostro]`, `parla <npc>`, `valida`, `stato`, `esci`. Exit code: 0 fine run/uscita, 2 errore config/parsing, 3 violazione runtime.

Comportamento (dalla spec):
- `--new` inizializza una run nuova; senza flag riprende `--save` (default `runtime/save.ttl`) se esiste, altrimenti inizia una run nuova.
- Autosave dopo ogni transizione valida; con `validation_mode == "turn"` la validazione precede il salvataggio: se fallisce, stampa il report ed esce con 3 **senza salvare**.
- `--seed` CLI sovrascrive il seed di configurazione.
- Gli argomenti dei comandi accettano il nome locale (`ossuary02`) o la label italiana (`Ossario 02`), case-insensitive.
- Vittoria/sconfitta: annuncio e uscita 0 (il save resta su disco, ispezionabile).
- Save corrotto: messaggio con l'errore di parsing, suggerimento `--new`, exit 2.

- [ ] **Step 1: Test che falliscono** — creare `tests/test_play_cli.py`:

```python
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
```

Run: `.venv/Scripts/python -m pytest tests/test_play_cli.py -v` → FAIL (`No module named tools.play`).

- [ ] **Step 2: Creare `tools/play.py`**

```python
"""CLI interattiva del simulatore di run: il grafo RDF è il world state.

Uso: python -m tools.play [--new] [--seed N] [--save FILE.ttl] [--config FILE.toml]
Comandi: vai <stanza> | apri <portale> | combatti [mostro] | parla <npc>
         valida | stato | esci
Exit code: 0 = run terminata o uscita, 2 = errore config/parsing, 3 = violazione runtime.
"""
import argparse
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from tools.common import SAVE_PATH, load_runtime_world
from tools.config import CONFIG_PATH, load_config
from tools.engine import (PLAYER, SR, ActionError, Engine, new_state,
                          validate_runtime)


def local_name(node: URIRef) -> str:
    return str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def label_it(graph: Graph, node: URIRef) -> str:
    for lbl in graph.objects(node, RDFS.label):
        if getattr(lbl, "language", None) == "it":
            return str(lbl)
    return local_name(node)


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
    for npc in {row.npc for row in eng.run_query("npcs-here.rq")}:
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
    if not args.new and args.save.exists():
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
```

- [ ] **Step 3: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_play_cli.py -v`
Expected: 5 passed (totale suite: 56).

- [ ] **Step 4: Prova manuale rapida** (facoltativa ma consigliata)

Run: `echo "esci" | .venv/Scripts/python -m tools.play --new`
Expected: stampa "Nuova run iniziata.", il quadro dell'Ingresso delle Catacombe e "Uscita: la run resta salvata."; crea `runtime/save.ttl` (gitignored).

- [ ] **Step 5: Commit**

```bash
git add tools/play.py tests/test_play_cli.py
git commit -m "Task 8 M3: CLI play a turni con autosave, resume e validazione configurabile"
```

---

### Task 9: Run end-to-end via engine (vittoria, sconfitta, save rivalidabile a freddo)

**Files:**
- Test: `tests/test_run_end_to_end.py`

**Interfaces:**
- Consumes: tutta l'API di `tools/engine.py` (Task 4–7), `load_runtime_world` (Task 2).
- Produces: la dimostrazione eseguibile del criterio di Fase 3 ("una run semplice può essere eseguita dal motore").

- [ ] **Step 1: Scrivere il test** — creare `tests/test_run_end_to_end.py`:

```python
"""Una run completa eseguita dal motore: il criterio di successo di M3, dimostrato."""
from rdflib import Graph, Literal

from tools.common import load_runtime_world
from tools.engine import EX, PLAYER, SR, Engine, new_state, validate_runtime

WORLD = load_runtime_world()


def test_scripted_winning_run(tmp_path):
    eng = Engine(WORLD, new_state(WORLD), player_success=1.0, seed=42)

    eng.talk_to(EX.graveHermit)          # accetta recoverRelic (target: sanctum01)
    eng.move_to(EX.ossuary02)
    eng.fight()                          # Ratto delle Cripte
    eng.move_to(EX.crypt07)
    eng.fight()                          # Custode d'Ossa -> Chiave d'Avorio
    assert (PLAYER, SR.hasItem, EX.ivoryKey) in eng.state
    eng.open_portal(EX.sealedGate)
    eng.move_to(EX.sanctum01)
    assert eng.outcome() is None         # il Tiranno è ancora vivo
    eng.fight()                          # Tiranno della Cripta -> quest completata

    assert (EX.recoverRelic, SR.questStatus, Literal("completed")) in eng.state
    assert eng.outcome() == "victory"

    # Il grafo finale è conforme alle shape runtime.
    conforms, _, text = validate_runtime(WORLD, eng.state)
    assert conforms, text

    # Il salvataggio è rileggibile e rivalidabile a freddo, senza il motore.
    save = tmp_path / "save.ttl"
    eng.state.serialize(save, format="turtle")
    cold = Graph()
    cold.parse(save, format="turtle")
    assert len(cold) == len(eng.state)
    conforms, _, text = validate_runtime(WORLD, cold)
    assert conforms, text


def test_scripted_losing_run():
    eng = Engine(WORLD, new_state(WORLD), player_success=0.0, seed=42)
    eng.move_to(EX.ossuary02)
    assert eng.fight() is False
    assert eng.outcome() == "defeat"
    conforms, _, text = validate_runtime(WORLD, eng.state)
    assert conforms, text  # anche la morte è uno stato coerente


def test_seeded_combat_is_reproducible():
    for _ in range(2):
        eng = Engine(WORLD, new_state(WORLD), player_success=0.5, seed=123)
        eng.move_to(EX.ossuary02)
        first = eng.fight()
        eng2 = Engine(WORLD, new_state(WORLD), player_success=0.5, seed=123)
        eng2.move_to(EX.ossuary02)
        assert eng2.fight() == first
```

- [ ] **Step 2: Verificare verde** (nessuna implementazione nuova: se qualcosa è rosso, è un bug dei task precedenti — correggerlo lì)

Run: `.venv/Scripts/python -m pytest tests/test_run_end_to_end.py -v`
Expected: 3 passed.

- [ ] **Step 3: Suite completa**

Run: `.venv/Scripts/python -m pytest`
Expected: 59 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_run_end_to_end.py
git commit -m "Task 9 M3: run end-to-end vincente e perdente, save rivalidabile a freddo"
```

---

### Task 10: Documentazione (nota di studio, README, todo)

**Files:**
- Create: `docs/notes/07-runtime-graph.md`
- Modify: `README.md` (sezione comandi: `tools.play`, `config.toml`, exit code 3, query runtime)
- Modify: `CLAUDE.md` (sezione Comandi: aggiungere il comando del simulatore)
- Modify: `tasks/todo.md` (chiusura M3)

**Interfaces:**
- Consumes: tutto il lavoro dei task 1–9.
- Produces: documentazione allineata (regola CLAUDE.md: README aggiornato nella stessa modifica dei comandi — qui chiude il piano).

- [ ] **Step 1: Scrivere `docs/notes/07-runtime-graph.md`** — nota di studio nello stile delle note 01–06 (in italiano, ancorata al codice reale). Contenuti richiesti:
  - il runtime graph separato dal content graph e la convenzione "assenza di tripla = stato di default";
  - il ciclo read (SPARQL) → transizione (triple) → validazione SHACL → serializzazione, con riferimenti a `tools/engine.py` e `queries/runtime/`;
  - validazione di grafi che evolvono: perché le shape runtime (`shacl/runtime-rules.ttl`) intercettano i bug del motore (exit 3) e cosa NON possono vedere;
  - cosa la simulazione rivela dei limiti deliberati di M2 (cicli lock-key indiretti, completabilità reale delle quest);
  - scelte di configurazione (`config.toml`): validazione per turno vs on-demand, probabilità di combattimento, seed.

- [ ] **Step 2: Aggiornare `README.md`** — nella sezione dei comandi aggiungere `python -m tools.play` con tutte le opzioni (`--new`, `--seed`, `--save`, `--config`), i comandi di gioco (`vai`, `apri`, `combatti`, `parla`, `valida`, `stato`, `esci`), gli exit code (incluso il nuovo 3) e una riga su `config.toml`; menzionare `queries/runtime/` (query usate dal motore, non da `tools.query --all`).

- [ ] **Step 3: Aggiornare `CLAUDE.md`** — nella sezione "Comandi" aggiungere una riga:

```markdown
- Giocare una run: `.venv/Scripts/python -m tools.play --new` (comandi: vai, apri, combatti, parla, valida, stato, esci; config in `config.toml`; exit 3 = violazione runtime)
```

e in "Struttura" aggiornare le voci toccate (ontologia runtime, shape runtime, `queries/runtime/`, `tools/engine.py`, `tools/play.py`).

- [ ] **Step 4: Aggiornare `tasks/todo.md`** — sostituire il contenuto con il piano M3 spuntato e una sezione Review con: cosa è stato costruito, numero test, riferimento alla nota 07 e al piano `docs/superpowers/plans/2026-07-17-m3-playable-simulation.md`.

- [ ] **Step 5: Verifica finale completa**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m tools.validate`
Expected: 59 passed; validazione contenuto exit 0.

- [ ] **Step 6: Commit**

```bash
git add docs/notes/07-runtime-graph.md README.md CLAUDE.md tasks/todo.md
git commit -m "Task 10 M3: nota di studio sul runtime graph e documentazione comandi"
```
