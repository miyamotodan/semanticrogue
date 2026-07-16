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

La suite verifica che i tre file Turtle si carichino, che il dataset authored sia conforme alle shape, che ogni query restituisca risultati e che ognuno dei casi rotti in `tests/invalid/` venga intercettato dalla shape giusta.

## Struttura del progetto

```
ontology/rogue.ttl      # Model: classi e proprietà (OWL)
dataset/dataset.ttl     # Content: il mondo authored
shacl/rogue-rules.ttl   # Validation: le shape SHACL
queries/*.rq            # le query SPARQL elencate sopra
tools/                  # le CLI (validate, query)
tests/                  # pytest + casi volutamente rotti (tests/invalid/)
docs/notes/             # note di studio, una per fase di sviluppo
obiettivo.md            # visione e roadmap del progetto
```
