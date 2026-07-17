# Reward-gating constraint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendere eseguibile il vincolo "una quest non deve premiare la chiave del portale che sblocca la sua target room", e correggere il dataset perché lo rispetti.

**Architecture:** Una shape SHACL SPARQL-based di contenuto (`sr:QuestRewardNotGatingKeyShape`) con il suo caso rotto permanente; poi un fix del dataset (nuovo item `ex:sanctumRelic` come reward di `recoverRelic` al posto di `ivoryKey`). Due task/commit distinti: prima la shape (il mondo diventa non conforme, dimostrando che il vincolo morde), poi il fix (il mondo torna conforme).

**Tech Stack:** Python 3.12 (venv `.venv/`), rdflib, pySHACL, pytest. Nessuna dipendenza nuova.

**Spec:** `docs/superpowers/specs/2026-07-17-reward-gating-design.md`

## Global Constraints

- Eseguire tutto con `.venv/Scripts/python` (Windows, shell Git Bash → forward slash).
- Namespace: `sr:` = vocabolario, `ex:` = istanze. Annotazioni bilingui `@it`/`@en` su ogni risorsa nuova (shape e item); le shape SPARQL-based hanno `sh:message` bilingue.
- Le shape SPARQL-based usano `sh:sparql`/`sh:select` con `$this` e `sh:prefixes sr:RogueShapes`.
- Bug rdflib: mai `FILTER NOT EXISTS { { A } UNION { B } }`; la query di questa shape è un solo basic graph pattern, nessun rischio.
- I micro-mondi in `tests/invalid/` sono validati uniti all'ontologia: ogni risorsa deve soddisfare le altre shape (stanze con bioma/dangerLevel/floorIndex, portale con requiresItem/unlocksRoom/portalInRoom, item con rarità 1–10, quest con targetRoom+reward) o scatterebbero violazioni diverse da quella attesa.
- Ordine obbligato: **Task 1 (shape) lascia il dataset non conforme di proposito**; `test_authored_dataset_conforms` torna verde solo dopo il **Task 2 (fix)**. Nel Task 1 quel test viene escluso dal comando di verifica; nel Task 2 si riabilita.
- Commit in italiano, con firma finale `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: shape `sr:QuestRewardNotGatingKeyShape` + caso rotto

**Files:**
- Modify: `shacl/rogue-rules.ttl` (shape nuova, in coda al file)
- Create: `tests/invalid/quest-reward-gating-key.ttl`
- Modify: `tests/test_validation.py` (una riga in `BROKEN_CASES`)

**Interfaces:**
- Consumes: convenzioni delle shape SPARQL-based esistenti, `sr:RogueShapes`.
- Produces: `sr:QuestRewardNotGatingKeyShape` (target `sr:Quest`), che scatta quando `questReward` = `requiresItem` di un portale con `unlocksRoom` = `questTargetRoom` della quest.

- [ ] **Step 1: Creare il caso rotto** `tests/invalid/quest-reward-gating-key.ttl`:

```turtle
# Caso rotto: la quest premia la chiave del portale che sblocca la sua target room
# (viola sr:QuestRewardNotGatingKeyShape). Il resto del micro-mondo è ben formato.
@prefix sr:   <http://example.org/semantic-roguelike#> .
@prefix ex:   <http://example.org/id/> .

ex:testBiome a sr:Biome .

ex:startRoom a sr:Room ;
  sr:isStartRoom true ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 1 ;
  sr:floorIndex 1 ;
  sr:connectedTo ex:gateRoom .

ex:gateRoom a sr:Room ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 2 ;
  sr:floorIndex 1 .

ex:lockedTarget a sr:Room ;
  sr:locatedInBiome ex:testBiome ;
  sr:dangerLevel 3 ;
  sr:floorIndex 2 .

ex:gateKey a sr:KeyItem ;
  sr:rarity 4 .

ex:gate a sr:Portal ;
  sr:portalInRoom ex:gateRoom ;
  sr:requiresItem ex:gateKey ;
  sr:unlocksRoom ex:lockedTarget .

# La chiave ha una fonte lecita (drop) così non scatta OrphanKey/LockKeyCycle:
# l'unica violazione attesa è il reward-gating.
ex:guardian a sr:Monster ;
  sr:belongsToFaction ex:testFaction ;
  sr:dropsItem ex:gateKey ;
  sr:spawnWeight 5 ;
  sr:minPlayerLevel 1 .

ex:testFaction a sr:Faction .

ex:gateRoom sr:hostsMonster ex:guardian .

ex:badQuest a sr:Quest ;
  sr:questTargetRoom ex:lockedTarget ;
  sr:questReward ex:gateKey .
```

Aggiungere a `BROKEN_CASES` in `tests/test_validation.py` (dopo la riga `no-start-room.ttl`):

```python
    ("quest-reward-gating-key.ttl", EX.badQuest, ("shape", SR.QuestRewardNotGatingKeyShape)),
```

- [ ] **Step 2: Verificare rosso**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py -k "gating" -v`
Expected: FAIL (la shape non esiste ancora → `not conforms` falso o shape attesa assente).

Nota: `test_authored_dataset_conforms` a questo punto NON va eseguito da solo verde — dopo lo Step 3 fallirà di proposito (il dataset reale viola la nuova shape). È atteso e si risolve nel Task 2.

- [ ] **Step 3: Aggiungere la shape** in coda a `shacl/rogue-rules.ttl`:

```turtle
sr:QuestRewardNotGatingKeyShape a sh:NodeShape ;
  sh:targetClass sr:Quest ;
  rdfs:label "Il premio non è la chiave d'accesso alla target"@it ;
  rdfs:label "Reward is not the target's gating key"@en ;
  rdfs:comment "Shape SPARQL-based: una quest non deve dare come ricompensa l'oggetto richiesto da un portale che sblocca la sua stessa stanza obiettivo (premio che il giocatore deve già possedere per completarla)."@it ;
  rdfs:comment "SPARQL-based shape: a quest must not reward the item required by a portal that unlocks its own target room (a reward the player must already hold to complete it)."@en ;
  sh:sparql [
    sh:prefixes sr:RogueShapes ;
    sh:message "La ricompensa della quest è la chiave del portale che sblocca la sua stanza obiettivo: premio incoerente."@it ;
    sh:message "The quest reward is the key to the portal that unlocks its own target room: incoherent reward."@en ;
    sh:select """
      SELECT $this
      WHERE {
        $this sr:questReward ?item ;
              sr:questTargetRoom ?target .
        ?portal sr:requiresItem ?item ;
                sr:unlocksRoom ?target .
      }
    """ ;
  ] .
```

- [ ] **Step 4: Verificare il caso rotto verde e la violazione reale**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py -k "gating" -v`
Expected: PASS (il micro-mondo scatta sulla shape attesa).

Run: `.venv/Scripts/python -m tools.validate`
Expected: exit 1, "Conforms: False" con una violazione di `sr:QuestRewardNotGatingKeyShape` su `ex:recoverRelic` — è la dimostrazione che il vincolo morde sul mondo reale. Verrà risolta nel Task 2.

- [ ] **Step 5: Commit**

```bash
git add shacl/rogue-rules.ttl tests/invalid/quest-reward-gating-key.ttl tests/test_validation.py
git commit -m "Task 1 reward-gating: shape del premio-chiave e caso rotto (il mondo reale ora la viola)"
```

---

### Task 2: fix del dataset — reward dedicato per `recoverRelic`

**Files:**
- Modify: `dataset/dataset.ttl:89-95` (blocco `ex:recoverRelic`) + nuovo item

**Interfaces:**
- Consumes: `sr:QuestRewardNotGatingKeyShape` (Task 1).
- Produces: `ex:sanctumRelic` (item, reward univoco di `recoverRelic`); `recoverRelic` non premia più `ivoryKey`.

- [ ] **Step 1: Verificare lo stato rosso di partenza**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py::test_authored_dataset_conforms -v`
Expected: FAIL (il dataset reale viola ancora la shape del Task 1). È il punto di partenza atteso.

- [ ] **Step 2: Aggiungere l'item dedicato e cambiare il reward** in `dataset/dataset.ttl`.

Sostituire il blocco `ex:recoverRelic` (righe ~89-95) con — reward aggiornato e commento non più "oggetto chiave":

```turtle
ex:recoverRelic a sr:Quest ;
  rdfs:label "Recupera la Reliquia"@it ;
  rdfs:label "Recover the Relic"@en ;
  rdfs:comment "Quest di recupero che indirizza il giocatore verso il santuario e ricompensa il completamento con una reliquia recuperata sul posto."@it ;
  rdfs:comment "Recovery quest that directs the player toward the sanctum and rewards completion with a relic recovered on site."@en ;
  sr:questTargetRoom ex:sanctum01 ;
  sr:questReward ex:sanctumRelic .

ex:sanctumRelic a sr:Item ;
  rdfs:label "Reliquia del Santuario"@it ;
  rdfs:label "Sanctum Relic"@en ;
  rdfs:comment "Reliquia sacra recuperata nel santuario più profondo, ricompensa per aver portato a termine la ricerca."@it ;
  rdfs:comment "Sacred relic recovered in the deepest sanctum, reward for completing the search."@en ;
  sr:rarity 5 .
```

- [ ] **Step 3: Verificare verde (dataset conforme + suite)**

Run: `.venv/Scripts/python -m pytest tests/test_validation.py::test_authored_dataset_conforms -v`
Expected: PASS.

Run: `.venv/Scripts/python -m tools.validate`
Expected: exit 0, "Conforms: True".

Run: `.venv/Scripts/python -m pytest`
Expected: 85 passed (84 esistenti + il caso rotto del Task 1).

- [ ] **Step 4: Verificare che `recoverRelic` resti completabile** (la chiave d'avorio resta drop del Custode d'Ossa)

Run:
```bash
.venv/Scripts/python -c "from tools.common import load_runtime_world; from tools.engine import EX, SR; w=load_runtime_world(); print('ivoryKey ancora ottenibile:', any(True for _ in w.subjects(SR.dropsItem, EX.ivoryKey))); print('recoverRelic reward:', str(w.value(EX.recoverRelic, SR.questReward)).split('/')[-1])"
```
Expected: `ivoryKey ancora ottenibile: True` e `recoverRelic reward: sanctumRelic`.

- [ ] **Step 5: Commit**

```bash
git add dataset/dataset.ttl
git commit -m "Task 2 reward-gating: recoverRelic premia una reliquia dedicata, non la chiave d'accesso"
```

---

### Task 3: documentazione

**Files:**
- Modify: `README.md` (conteggio test 84 → 85)

**Interfaces:**
- Consumes: il lavoro dei task 1–2.

- [ ] **Step 1: Aggiornare il conteggio test in README.md** — la riga "La suite (84 test)" diventa "La suite (85 test)". Se opportuno, includere fra i casi rotti citati anche il premio-chiave di gating, mantenendo lo stile della frase esistente.

- [ ] **Step 2: Verifica finale**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m tools.validate`
Expected: 85 passed; validazione contenuto exit 0.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Task 3 reward-gating: aggiorna il conteggio test nel README"
```
