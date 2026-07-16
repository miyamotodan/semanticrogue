# Design: tooling verificabile per M1 (World Core) e M2 (Semantic QA)

Data: 2026-07-16
Stato: approvato

## Obiettivo

Portare il progetto dal suo stato attuale (tre file Turtle scritti a mano, mai eseguiti né validati) al completamento delle milestone M1 e M2 di `obiettivo.md`:

- **M1 – World Core**: ontologia + dataset authored al target di Fase 1 + query SPARQL di lettura eseguibili.
- **M2 – Semantic QA**: validazione SHACL eseguibile con report + casi volutamente errati intercettati automaticamente.

Obiettivo trasversale: ogni incremento produce anche una **nota di studio** in `docs/notes/` che spiega il concetto tecnologico appena usato (RDF, SHACL, SPARQL, rdflib), ancorata al codice reale del progetto. Il repo è anche il quaderno di apprendimento dell'autore.

Criterio guida (da `obiettivo.md`): "quando rompo il dataset, il sistema se ne accorge".

## Decisioni prese

| Decisione | Scelta | Alternative scartate |
|---|---|---|
| Stack | Python: rdflib + pySHACL + pytest | Java/Jena (verboso), Node (SHACL immaturo), soli CLI esterni (limita il simulatore futuro) |
| Orizzonte del piano | Fino a M2, dettagliato | M3/M4 verranno pianificati quando il core è consolidato |
| Apprendimento | Note di studio per fase in `docs/notes/` | Solo chat (si perde), soli commenti nel codice (concetti trasversali senza casa) |
| Struttura | Pipeline CLI + test | Notebook Jupyter (non riusabile), triple store subito (infrastruttura prematura) |

## Architettura

I quattro moduli di `obiettivo.md` restano separati; si aggiungono cartelle per query, tool, test e note:

```
semanticrogue/
├─ ontology/rogue.ttl        # Model (invariato come ruolo)
├─ dataset/dataset.ttl       # Content
├─ shacl/rogue-rules.ttl     # Validation
├─ queries/                  # query SPARQL .rq numerate e commentate
├─ tools/
│  ├─ validate.py            # carica ontologia+dataset, applica shape, report + exit code
│  └─ query.py               # esegue un file .rq (o tutti) sul grafo unito
├─ tests/
│  ├─ invalid/               # dataset rotti ad arte, uno per vincolo
│  └─ test_validation.py     # il dataset buono passa; ogni caso rotto scatta la shape giusta
├─ docs/notes/               # una nota di studio per incremento
└─ tasks/                    # todo.md (piano) e lessons.md (correzioni)
```

Ambiente: `venv` locale + `requirements.txt` (rdflib, pyshacl, pytest). Repo versionato con git (inizializzato in questo incremento).

### Interfacce dei tool

- `python tools/validate.py [--data FILE.ttl]` — di default valida `dataset/dataset.ttl` con ontologia e shape del repo; stampa report leggibile; exit 0 se conforme, exit 1 se ci sono violazioni, exit 2 su errori di parsing (con file e riga).
- `python tools/query.py queries/03-monsters-by-room.rq [--data FILE.ttl]` — esegue la query sul grafo unito ontologia+dataset e stampa i risultati in tabella.

## Incrementi

Ognuno è piccolo, verificabile e chiude con una nota di studio e un commit.

1. **Setup** — git init, `.gitignore`, venv, `requirements.txt`, smoke test che carica i tre TTL con rdflib e ne stampa il numero di triple. *Nota: anatomia di RDF/Turtle (triple, prefissi, letterali tipizzati, `a`).*
2. **Validazione eseguibile** — `tools/validate.py` con pySHACL. Farà emergere la violazione già presente: `ex:sanctum01` ha `dangerLevel 6` ma nessun `sr:hostsMonster` (shape `sr:DangerousRoomMustHaveContent`). Correzione: aggiungere un boss al santuario; per `sr:BossPlacementShape` dovrà droppare almeno un item, che va aggiunto al dataset. *Nota: SHACL — node shape, property shape, target, severità, validation report.*
3. **Query SPARQL (chiude M1)** — 5-6 file `.rq` + `tools/query.py`: panoramica stanze (bioma, pericolo, piano); mappa connessioni; mostri per stanza con fazione; catena lock-key (portale → chiave richiesta → chi la droppa → in quale stanza); quadro quest (giver, target room, reward). *Nota: SPARQL — basic graph pattern, OPTIONAL, FILTER, property path.*
4. **Espansione del mondo** — dataset al target Fase 1: 8-12 stanze, 2 fazioni, 6-8 mostri, 10 item, 3 quest. Convenzioni esistenti obbligatorie (namespace `ex:`, label/comment bilingui `@it`/`@en`). Validazione dopo ogni aggiunta. Parte del contenuto viene scritto a mano dall'autore come esercizio e poi revisionato. *Nota: scelte di modellazione e naming.*
5. **Shape aggiuntive + casi rotti (chiude M2)** — nuove shape per vincoli mancanti: item chiave che nessun mostro droppa e nessuna quest ricompensa (key orfana), stanze non raggiungibili dalla stanza iniziale via `connectedTo`/portali, dipendenze circolari lock-key (la chiave del portale si trova solo oltre il portale stesso). In `tests/invalid/` un dataset minimale rotto per ciascuna shape; `tests/test_validation.py` verifica che il dataset buono passi e che ogni caso rotto venga intercettato **dalla shape attesa** (non da una qualsiasi). *Nota: shape SPARQL-based avanzate.*
6. **Chiusura** — aggiornare CLAUDE.md con i comandi reali, breve retrospettiva in `docs/notes/`.

## Gestione errori

- Errori di parsing Turtle: riportati con file e posizione, exit code dedicato (2), distinti dalle violazioni SHACL (1).
- `query.py` con file `.rq` inesistente o query malformata: messaggio chiaro, non traceback.
- I test non dipendono dall'ordine: ogni caso rotto è un file autonomo che include solo il minimo per far scattare la sua shape.

## Criteri di successo

- `python tools/validate.py` → exit 0 e report "conforme" sul dataset buono.
- Ogni file in `tests/invalid/` fa scattare esattamente la shape a cui è mirato; `pytest` verde.
- Le query rispondono alle domande di design: "dove si ottiene la chiave X?", "quali stanze sono dead-end?", "quali quest premiano item rari?".
- Una nota di studio per incremento in `docs/notes/`.
- Il dataset raggiunge il target quantitativo di Fase 1 restando conforme.

## Fuori scope (deliberato, da obiettivo.md)

Simulatore di run, runtime graph (`sr:Player`, `sr:questStatus`, …), generazione di contenuti, UI, triple store/endpoint SPARQL, reasoning OWL. Verranno pianificati dopo la chiusura di M2.
