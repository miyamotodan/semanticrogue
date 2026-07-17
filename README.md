# Semantic Rogue

Un roguelike governato da tecnologie del web semantico: il mondo di gioco (stanze, mostri, oggetti, fazioni, quest, portali) è un knowledge graph RDF, i vincoli di coerenza sono shape SHACL e le domande sul mondo sono query SPARQL.

> Questo README elenca **tutti i comandi disponibili da CLI** e viene aggiornato ogni volta che se ne aggiungono di nuovi.

## Setup (una tantum)

Richiede Python 3.12+.

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash
# oppure: .venv\Scripts\Activate.ps1   (PowerShell)
python -m pip install -r requirements.txt
```

Nei comandi che seguono si assume il venv attivo (altrimenti sostituisci `python` con `.venv/Scripts/python`).

## Comandi

### Validare il mondo

```bash
python -m tools.validate
```

Valida `dataset/dataset.ttl` (unito all'ontologia) contro le shape SHACL di `shacl/rogue-rules.ttl` e stampa il report.

| Opzione | Effetto |
|---|---|
| `--data FILE.ttl` | valida un dataset alternativo (es. un caso rotto di `tests/invalid/`) |

Exit code: `0` conforme · `1` violazioni trovate · `2` errore di parsing.

Esempio su un caso volutamente rotto:

```bash
python -m tools.validate --data tests/invalid/lock-key-cycle.ttl
```

### Interrogare il mondo

```bash
python -m tools.query queries/01-rooms-overview.rq   # una query
python -m tools.query --all                          # tutte le query
```

| Opzione | Effetto |
|---|---|
| `--all` | esegue tutte le query in `queries/` in ordine |
| `--data FILE.ttl` | interroga un dataset alternativo |

Query disponibili:

| File | Risponde a |
|---|---|
| `01-rooms-overview.rq` | com'è fatta la mappa, piano per piano? |
| `02-connections.rq` | da quale stanza si va dove, e cosa serve per passare? |
| `03-monsters-by-room.rq` | chi incontro e dove, e sono pronto per farlo? |
| `04-lock-key-chain.rq` | dove ottengo la chiave che apre questo portale? |
| `05-quests.rq` | quali missioni esistono e cosa premiano? |
| `06-items-by-rarity.rq` | quali oggetti esistono, di che tipo e quanto rari? |

### Eseguire i test

```bash
python -m pytest                 # tutta la suite
python -m pytest -v              # con dettaglio per test
python -m pytest tests/test_validation.py::test_authored_dataset_conforms -v   # un solo test
```

La suite (60 test) verifica che i file Turtle si carichino, che il dataset authored sia conforme alle shape, che ogni query restituisca risultati, che ognuno dei casi rotti in `tests/invalid/` venga intercettato dalla shape giusta, il motore (`tools/engine.py`), la validazione runtime su stati rotti ad arte, la CLI `tools.play` e run end-to-end vincenti/perdenti.

### Giocare una run

```bash
python -m tools.play --new
```

Simulatore CLI a turni: il grafo RDF è il world state. Senza `--new` riprende il salvataggio esistente (default `runtime/save.ttl`) se presente, altrimenti inizia comunque una run nuova.

| Opzione | Effetto |
|---|---|
| `--new` | inizia una run nuova (ignora un eventuale salvataggio) |
| `--seed N` | seme RNG per combattimenti riproducibili (sovrascrive `seed` di `config.toml`) |
| `--save FILE.ttl` | file di salvataggio (default `runtime/save.ttl`) |
| `--config FILE.toml` | file di configurazione (default `config.toml`) |

Comandi di gioco (a runtime, uno per turno):

| Comando | Effetto |
|---|---|
| `vai <stanza>` | si muove verso una stanza raggiungibile (passaggio o portale aperto) |
| `apri <portale>` | apre un portale nella stanza corrente, se la chiave richiesta è in inventario |
| `combatti [mostro]` | affronta un mostro nella stanza corrente (il nome è opzionale se ce n'è uno solo) |
| `parla <npc>` | parla con un NPC nella stanza corrente, attiva le quest che offre |
| `valida` | esegue subito la validazione SHACL runtime e mostra il report |
| `stato` | mostra posizione, inventario e stato di tutte le quest |
| `esci` | esce; la run resta salvata sul file corrente |

Gli argomenti dei comandi accettano il nome locale (`ossuary02`) o la label italiana (`Ossario 02`), case-insensitive. La run termina da sola in vittoria (prima quest completata) o sconfitta (giocatore morto).

Exit code: `0` fine run/uscita normale · `2` errore di configurazione o salvataggio illeggibile (suggerisce `--new`) · `3` violazione runtime dopo una transizione (bug del motore: il turno non viene salvato).

Configurazione in `config.toml` (versionato, alla radice del repo): `[validation] mode` = `"turn"` (valida dopo ogni transizione, default) o `"on-demand"` (solo col comando `valida`); `[combat] player_success` = probabilità di vittoria del player in `[0, 1]` (default `1.0`); `seed` (top-level, opzionale) per run riproducibili.

Le query in `queries/runtime/` (`available-moves.rq`, `openable-portals.rq`, `monsters-here.rq`, `npcs-here.rq`, `quest-status.rq`) sono usate dal motore (`tools/engine.py`) e richiedono il runtime graph di una partita in corso: non sono raccolte da `tools.query --all` né documentate nella tabella query sopra.

## Struttura del progetto

```
ontology/rogue.ttl      # Model: classi e proprietà (OWL) del contenuto
ontology/runtime.ttl    # Model: vocabolario dello stato di partita (Player, currentRoom, ...)
dataset/dataset.ttl     # Content: il mondo authored
shacl/rogue-rules.ttl   # Validation: le shape SHACL del contenuto
shacl/runtime-rules.ttl # Validation: le shape SHACL dello stato di partita
queries/*.rq            # le query SPARQL elencate sopra
queries/runtime/*.rq    # query usate dal motore (tools/engine.py), non da tools.query
tools/                  # le CLI (validate, query, play) e il motore (engine.py, config.py)
tests/                  # pytest + casi volutamente rotti (tests/invalid/)
docs/notes/             # note di studio, una per fase di sviluppo
obiettivo.md            # visione e roadmap del progetto
config.toml             # configurazione del simulatore (tools.play)
```
