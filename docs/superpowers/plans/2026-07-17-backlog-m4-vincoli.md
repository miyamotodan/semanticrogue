# Backlog M4 (vincoli) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chiudere le due voci del backlog M4: una shape di contenuto che impone esattamente una stanza iniziale, e il completamento delle quest già soddisfatte al momento di `talk_to`.

**Architecture:** Due shape SHACL SPARQL-based nel content graph (una per-nodo per il caso "più di una", una con `sh:target` SPARQL per il caso "nessuna"); una riga nel motore che invoca `_check_quest_completion` dopo `talk_to`. Ogni vincolo ha il suo caso rotto ad arte.

**Tech Stack:** Python 3.12 (venv `.venv/`), rdflib, pySHACL, pytest. Nessuna dipendenza nuova.

**Spec:** `docs/superpowers/specs/2026-07-17-backlog-m4-vincoli-design.md`

## Global Constraints

- Eseguire tutto con `.venv/Scripts/python` (Windows, shell Git Bash → forward slash).
- Namespace: `sr:` = vocabolario, `ex:` = istanze. Annotazioni bilingui `@it`/`@en` su ogni shape nuova; le SPARQL-based hanno `sh:message` bilingue.
- Le shape SPARQL-based usano `sh:sparql`/`sh:select` con `$this` e `sh:prefixes sr:RogueShapes` (il documento shape dichiara già `sr:RogueShapes` con il prefisso `sr`).
- Bug rdflib: mai `FILTER NOT EXISTS { { A } UNION { B } }`; usare `FILTER NOT EXISTS` separati.
- I micro-mondi in `tests/invalid/` sono validati uniti all'ontologia: ogni `sr:Room` deve soddisfare le altre shape (un bioma, `dangerLevel` 1–10, `floorIndex` ≥ 1) o scatterebbero violazioni diverse da quella attesa.
- I test esistenti (81) restano verdi a ogni task.
- Commit in italiano, con firma finale `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: shape di unicità della stanza iniziale + due casi rotti

**Files:**
- Modify: `shacl/rogue-rules.ttl` (due shape nuove, in coda al file)
- Create: `tests/invalid/two-start-rooms.ttl`, `tests/invalid/no-start-room.ttl`
- Modify: `tests/test_validation.py` (due righe in `BROKEN_CASES`)

**Interfaces:**
- Consumes: convenzioni delle shape SPARQL-based esistenti (`sr:UnreachableRoomShape`), `sr:RogueShapes`.
- Produces: `sr:SingleStartRoomShape` (target `sr:Room`, scatta sulle start room in eccesso) e `sr:StartRoomExistsShape` (target SPARQL, scatta se nessuna start room esiste).

- [ ] **Step 1: Scrivere i test che falliscono** — creare i due micro-mondi.

`tests/invalid/two-start-rooms.ttl`:

```turtle
# Caso rotto: due stanze iniziali (viola sr:SingleStartRoomShape).
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix ex:   <http://example.org/id/> .

ex:testBiome a sr:Biome .

ex:startA a sr:Room ;
  sr:isStartRoom true ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 1 ;
  sr:floorIndex 1 .

ex:startB a sr:Room ;
  sr:isStartRoom true ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 1 ;
  sr:floorIndex 1 .

ex:startA sr:connectedTo ex:startB .
```

`tests/invalid/no-start-room.ttl`:

```turtle
# Caso rotto: nessuna stanza iniziale (viola sr:StartRoomExistsShape).
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix ex:   <http://example.org/id/> .

ex:testBiome a sr:Biome .

ex:roomA a sr:Room ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 1 ;
  sr:floorIndex 1 ;
  sr:connectedTo ex:roomB .

ex:roomB a sr:Room ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 1 ;
  sr:floorIndex 1 .
```

Aggiungere a `BROKEN_CASES` in `tests/test_validation.py` (nomi `EX.` e `SR.` già disponibili):

```python
    ("two-start-rooms.ttl", EX.startA, ("shape", SR.SingleStartRoomShape)),
    ("no-start-room.ttl", EX.roomA, ("shape", SR.StartRoomExistsShape)),
```

Nota: `two-start-rooms.ttl` produce due focus node (startA e startB); il test
cerca la shape attesa su `EX.startA`, che è tra i due — il pattern esistente
(`matching` per focus node specifico) lo gestisce.

- [ ] **Step 2: Verificare rosso**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py -k "start" -v`
Expected: entrambi i nuovi casi falliscono (le shape non esistono ancora, quindi
`not conforms` è falso o la shape attesa non compare).

- [ ] **Step 3: Aggiungere le due shape** in coda a `shacl/rogue-rules.ttl`:

```turtle
sr:SingleStartRoomShape a sh:NodeShape ;
  sh:targetClass sr:Room ;
  rdfs:label "Una sola stanza iniziale"@it ;
  rdfs:label "Single start room"@en ;
  rdfs:comment "Shape SPARQL-based: non possono esistere due o più stanze marcate come iniziali; ogni stanza iniziale in eccesso viene segnalata."@it ;
  rdfs:comment "SPARQL-based shape: two or more rooms flagged as start are not allowed; every excess start room is reported."@en ;
  sh:sparql [
    sh:prefixes sr:RogueShapes ;
    sh:message "Esiste più di una stanza iniziale nel mondo: deve essercene esattamente una."@it ;
    sh:message "There is more than one start room in the world: there must be exactly one."@en ;
    sh:select """
      SELECT $this
      WHERE {
        $this sr:isStartRoom true .
        ?other sr:isStartRoom true .
        FILTER(?other != $this)
      }
    """ ;
  ] .

sr:StartRoomExistsShape a sh:NodeShape ;
  rdfs:label "Esiste una stanza iniziale"@it ;
  rdfs:label "A start room exists"@en ;
  rdfs:comment "Shape SPARQL-based: il mondo deve avere una stanza iniziale; se ne manca del tutto, ogni stanza viene segnalata come focus della violazione."@it ;
  rdfs:comment "SPARQL-based shape: the world must have a start room; if none exists, every room is reported as a focus of the violation."@en ;
  sh:target [
    a sh:SPARQLTarget ;
    sh:prefixes sr:RogueShapes ;
    sh:select """
      SELECT ?this
      WHERE {
        ?this a sr:Room .
        FILTER NOT EXISTS { ?r sr:isStartRoom true . }
      }
    """ ;
  ] ;
  sh:sparql [
    sh:prefixes sr:RogueShapes ;
    sh:message "Nessuna stanza è marcata come iniziale: il mondo non ha un punto di partenza."@it ;
    sh:message "No room is flagged as start: the world has no starting point."@en ;
    sh:select """
      SELECT $this
      WHERE { $this a sr:Room . }
    """ ;
  ] .
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py -v`
Expected: tutti verdi (i casi esistenti + i 2 nuovi). Il dataset authored (una
sola start room) resta conforme: `sr:SingleStartRoomShape` non trova un `?other`
diverso, e il target di `sr:StartRoomExistsShape` è vuoto perché una start room
esiste.

Poi verificare il mondo reale: `.venv/Scripts/python -m tools.validate` → exit 0,
"Conforms: True".

- [ ] **Step 5: Commit**

```bash
git add shacl/rogue-rules.ttl tests/invalid/two-start-rooms.ttl tests/invalid/no-start-room.ttl tests/test_validation.py
git commit -m "Task 1 backlog: shape di unicità della stanza iniziale + casi rotti"
```

---

### Task 2: `talk_to` completa le quest già soddisfatte

**Files:**
- Modify: `tools/engine.py:108-115` (`talk_to`)
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `_check_quest_completion`, `talk_to` (esistenti).
- Produces: `talk_to` che, dopo aver attivato le quest, invoca `_check_quest_completion`.

- [ ] **Step 1: Scrivere il test che fallisce** — aggiungere a `tests/test_engine.py`:

```python
def test_talk_to_completes_quest_already_satisfied(eng):
    # Il player è nella target room di endTheCourt, già ripulita, e solo ora
    # accetta la quest da un NPC posto lì: deve completarsi subito.
    eng.state.set((PLAYER, SR.currentRoom, EX.throneVault01))
    eng.state.add((EX.deadKing, SR.isAlive, Literal(False)))   # target room ripulita
    eng.state.add((EX.graveHermit, SR.npcInRoom, EX.throneVault01))  # NPC presente qui
    eng.talk_to(EX.graveHermit)
    assert (EX.endTheCourt, SR.questStatus, Literal("completed")) in eng.state
    assert (PLAYER, SR.hasItem, EX.relicOfDawn) in eng.state    # reward di endTheCourt
```

(`graveHermit` offre `recoverRelic` e `endTheCourt`; `endTheCourt` ha target
`throneVault01` e reward `relicOfDawn`. `recoverRelic` ha target `sanctum01`,
diversa, quindi resta `active`: il test verifica solo `endTheCourt`.)

- [ ] **Step 2: Verificare rosso**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py::test_talk_to_completes_quest_already_satisfied -v`
Expected: FAIL (`endTheCourt` resta `active`: `talk_to` non chiama ancora il check).

- [ ] **Step 3: Implementare** — in `tools/engine.py`, in fondo a `talk_to`, dopo il ciclo che attiva le quest e prima di `return offers`:

```python
        self._check_quest_completion()
        return offers
```

- [ ] **Step 4: Verificare verde**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py -v`
Expected: tutti verdi (il nuovo + gli esistenti di `talk_to`, che non
soddisfano le condizioni di completamento e restano invariati). Poi suite
completa: `.venv/Scripts/python -m pytest` → 84 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/engine.py tests/test_engine.py
git commit -m "Task 2 backlog: talk_to completa le quest già soddisfatte"
```

---

### Task 3: aggiornare README, nota e chiudere il backlog

**Files:**
- Modify: `README.md` (conteggio test)
- Modify: `tasks/todo.md` (rimuovere le due voci chiuse dal backlog M4)

**Interfaces:**
- Consumes: il lavoro dei task 1–2.

- [ ] **Step 1: Aggiornare il conteggio test in README.md** — la riga "La suite (81 test)" diventa "La suite (84 test)"; se opportuno menzionare tra i vincoli anche l'unicità della stanza iniziale (mantenendo lo stile della frase esistente).

- [ ] **Step 2: Aggiornare `tasks/todo.md`** — nella sezione "Backlog per M4" rimuovere le due voci ora chiuse (shape di unicità `isStartRoom`; `talk_to` + `_check_quest_completion`). Se la sezione resta vuota, sostituirla con una riga che nota che il backlog di rigore M3 è chiuso.

- [ ] **Step 3: Verifica finale**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m tools.validate`
Expected: 84 passed; validazione contenuto exit 0.

- [ ] **Step 4: Commit**

```bash
git add README.md tasks/todo.md
git commit -m "Task 3 backlog: aggiorna conteggio test e chiude il backlog M4 di rigore"
```
