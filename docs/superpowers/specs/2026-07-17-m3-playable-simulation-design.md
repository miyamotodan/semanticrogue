# Design: M3 — Playable Simulation (simulatore minimale di run)

Data: 2026-07-17
Stato: approvato

## Obiettivo

Completare la milestone M3 di `obiettivo.md`: un simulatore CLI a turni in cui una run
semplice può essere eseguita dal motore. Il grafo RDF diventa world state vivo:
a ogni turno il motore legge lo stato, calcola le azioni ammissibili, applica una
transizione e rivalida la coerenza. Anticipa della Fase 4 solo il minimo indispensabile
(runtime graph con poche entità nuove).

Criterio di successo (da `obiettivo.md`, Fase 3): "una run semplice può essere eseguita
dal motore" — dimostrato da una run vincente end-to-end nei test, non dichiarato.

## Decisioni prese

| Decisione | Scelta | Alternative scartate |
|---|---|---|
| Guida della run | CLI interattiva: l'umano sceglie le mosse | Bot automatico (rimandato alle simulazioni di Fase 6); entrambi subito (scope) |
| Persistenza | Runtime graph serializzato su `runtime/save.ttl`, autosave a ogni turno, resume all'avvio | Solo in memoria (non ispezionabile); dump solo finale (niente resume) |
| Combattimento | Azione esplicita `combatti`; esito governato da una probabilità di successo configurabile (default 1 = vince sempre); fallimento = morte del player, run persa | HP e danno (bilanciamento prematuro); risoluzione automatica all'ingresso (turno illeggibile); riprova senza conseguenze (probabilità senza significato) |
| Validazione SHACL runtime | Shape dedicate allo stato di partita; modalità da configurazione: a ogni turno (default) o solo su richiesta | Nessuna validazione runtime (rimanda il cuore didattico di M3) |
| Fine run | Vittoria alla prima quest completata; sconfitta se il player muore; `esci` sempre disponibile | Tutte le quest (run lunga, più stati intermedi); esplorazione libera (non misurabile) |
| Motore | Stato solo nel grafo: letture via SPARQL, transizioni come funzioni Python su triple rdflib, SHACL a valle | Oggetti Python + proiezione RDF (stato duplicato); transizioni SPARQL UPDATE (bug rdflib noti, debugging difficile — possibile evoluzione futura) |
| Configurazione | `config.toml` in radice, letto con `tomllib` (stdlib, Python 3.12) | TTL (overkill), JSON (scomodo da annotare), INI (tipi deboli) |

## Architettura

Il principio: **lo stato di partita è solo triple RDF** in un grafo runtime separato dal
content graph; nessuno stato duplicato in oggetti Python. Chi apre `runtime/save.ttl`
vede tutta la partita.

```
semanticrogue/
├─ ontology/rogue.ttl         # Model statico: si aggiunge solo sr:npcInRoom
├─ ontology/runtime.ttl       # Model runtime: sr:Player, currentRoom, hasItem, isAlive, isOpen, questStatus
├─ dataset/dataset.ttl        # Content: si aggiunge il posizionamento degli NPC
├─ shacl/rogue-rules.ttl      # Validation contenuto (invariato)
├─ shacl/runtime-rules.ttl    # Validation stato di partita
├─ queries/runtime/*.rq       # azioni ammissibili e viste di stato
├─ tools/engine.py            # transizioni di stato: funzioni pure sul grafo
├─ tools/play.py              # CLI interattiva a turni
├─ config.toml                # validazione runtime, probabilità combattimento, seed
├─ runtime/save.ttl           # salvataggio (gitignored: stato locale, non contenuto)
└─ tests/test_engine.py       # transizioni, shape runtime, run end-to-end
```

Il grafo di lavoro a runtime è l'unione ontologia (statica + runtime) + dataset +
runtime graph. Il salvataggio serializza **solo** il runtime graph: il contenuto non
si duplica mai.

### Vocabolario runtime (`ontology/runtime.ttl`)

Fase 4 anticipata al minimo, come da retrospettiva M1+M2:

- `sr:Player` (classe) — istanza `ex:player` creata a inizio run nella stanza con `sr:isStartRoom true`.
- `sr:currentRoom` (Player→Room) — posizione corrente, esattamente una.
- `sr:hasItem` (Player→Item) — inventario.
- `sr:isAlive` (Monster o Player → boolean) — scritta solo alla morte (`false`); assenza = vivo.
- `sr:isOpen` (Portal→boolean) — scritta solo all'apertura (`true`); assenza = chiuso.
- `sr:questStatus` (Quest→string) — `"active"` o `"completed"`; assenza = non accettata.

Convenzione: **assenza di tripla = stato di default** (mostro vivo, portale chiuso,
quest non accettata). Il runtime graph iniziale contiene solo il player e la sua stanza.

### Gap ontologico da colmare: `sr:npcInRoom`

Gli NPC (`ex:graveHermit`, `ex:ashPriest`) offrono quest ma non si trovano in nessuna
stanza — stesso pattern dei gap emersi in M1 (`portalInRoom`, `isStartRoom`).
`sr:npcInRoom` (NPC→Room) va nel vocabolario **statico** (`ontology/rogue.ttl`) con
posizionamento nel dataset: la posizione dell'NPC è contenuto authored, non stato.
Valutare una shape SHACL di contenuto corrispondente (ogni NPC ha esattamente una
stanza), come da convenzione "ogni vincolo di design diventa un vincolo eseguibile".

Tutte le risorse nuove (classi, proprietà, shape, istanze) hanno annotazioni bilingui
`@it`/`@en` come da convenzioni; le shape hanno anche `sh:name`, `sh:description`,
`sh:message` bilingui.

## Configurazione (`config.toml`)

```toml
[validation]
mode = "turn"        # "turn" = SHACL runtime dopo ogni transizione (default)
                     # "on-demand" = solo col comando `valida`

[combat]
player_success = 1.0 # probabilità di vittoria del player in [0,1]; 1 = vince sempre

# seed = 42          # opzionale: seme RNG per run riproducibili; assente/commentato = casuale
```

File versionato in git con i default. Letto da `tools/play.py` all'avvio con `tomllib`;
valori fuori range (es. `player_success` fuori da [0,1], `mode` sconosciuto) →
messaggio chiaro ed exit code 2, coerente con gli errori di configurazione/parsing
degli altri tool.

## Ciclo di turno e azioni

Ogni turno: **leggi stato → mostra situazione e azioni ammissibili (SPARQL) →
applica transizione (rdflib) → valida (secondo `validation.mode`) → autosalva**.

| Azione | Precondizione (query SPARQL) | Effetto (triple) |
|---|---|---|
| `vai <stanza>` | `sr:connectedTo` dalla stanza corrente, oppure portale **aperto** che la sblocca | aggiorna `currentRoom`; poi check completamento quest (sotto) |
| `apri <portale>` | portale nella stanza corrente, chiave richiesta in `hasItem`, non già aperto | `isOpen true` |
| `combatti` | mostro con `isAlive` non false nella stanza corrente | estrazione con `player_success`: successo → mostro `isAlive false`, i suoi `dropsItem` entrano in `hasItem`; fallimento → player `isAlive false`, run persa |
| `parla <npc>` | NPC nella stanza corrente (via `npcInRoom`) con quest senza `questStatus` | `questStatus "active"` |
| `valida` | — | validazione SHACL runtime su richiesta (utile con `mode = "on-demand"`) |
| `stato` | — | posizione, inventario, quest e loro status, mostri sconfitti |
| `esci` | — | termina; lo stato resta salvato per il resume |

**Completamento quest**: quando il player entra nella `questTargetRoom` di una quest
`"active"` e nella stanza non restano mostri vivi, la quest passa a `"completed"` e la
`questReward` entra in `hasItem`. Il check scatta anche dopo `combatti` (caso: il player
è già nella target room e sconfigge l'ultimo mostro).

**Fine run**: vittoria alla prima quest `"completed"`; sconfitta se il player muore.
In entrambi i casi il motore lo annuncia e la run termina (il save resta ispezionabile).

**Avvio**: `play.py --new` inizializza il runtime graph (player nella start room);
senza flag riprende `runtime/save.ttl` se esiste, altrimenti inizia una run nuova.
`--seed N` da CLI sovrascrive il seed di configurazione.

Le query in `queries/runtime/` seguono lo stile esistente: autonome, prefissi propri,
commento iniziale con la domanda a cui rispondono. Le query 02 (connessioni) e 04
(catena lock-key) di M1 sono la base per mosse possibili e porte apribili.

## Validazione runtime e gestione errori

Shape in `shacl/runtime-rules.ttl`, target sulle entità runtime:

1. Il player ha esattamente una `currentRoom` (property shape).
2. `questStatus` solo con valori `"active"`/`"completed"` (property shape, `sh:in`).
3. Portale `isOpen true` ⇒ la chiave richiesta è in `hasItem` (SPARQL-based).
4. Item in `hasItem` ⇒ il mostro che lo droppa è sconfitto, oppure l'item è reward di
   una quest `"completed"` (SPARQL-based).

Attenzione al bug rdflib noto: niente `FILTER NOT EXISTS { { A } UNION { B } }` nelle
query delle shape; usare più `FILTER NOT EXISTS` separati (CLAUDE.md → Comandi).

- **Violazione dopo una transizione = bug del motore**: il turno non viene salvato,
  si stampa il report SHACL e si esce con exit code 3 (nuovo, distinto da 1 = mondo
  non conforme e 2 = errore parsing/config). Niente rollback sofisticato: fallire
  rumorosamente è il criterio di M2 esteso al runtime.
- **Input non valido** (azione non ammissibile, argomento sconosciuto): messaggio
  chiaro e nuovo prompt; nessuna transizione, nessun salvataggio.
- **Save corrotto o incompatibile**: errore di parsing → messaggio con file e
  posizione, suggerimento `--new`, exit code 2.

## Test

Come per M2, i vincoli si dimostrano rotti ad arte:

- **Unit sulle transizioni**: ogni azione testata su micro-stati costruiti in memoria
  (precondizioni rispettate → triple attese; precondizioni violate → transizione
  rifiutata senza modifiche al grafo).
- **Stati runtime rotti**: per ogni shape runtime, uno stato costruito ad arte che la
  fa scattare — e che venga intercettata **dalla shape attesa**, non da una qualsiasi.
- **Run end-to-end**: una run vincente scriptata direttamente via `engine.py` (senza
  CLI, seed fissato, `player_success = 1.0`): parte dalla start room, accetta una
  quest, ottiene la chiave, apre il portale, ripulisce la target room, vince; il grafo
  finale è conforme alle shape runtime. Una variante con `player_success = 0.0`
  verifica la sconfitta.
- **Combattimento probabilistico**: con seed fissato, l'esito è riproducibile.
- Il dataset authored resta conforme alle shape di contenuto dopo l'aggiunta di
  `npcInRoom` (i test M1/M2 esistenti restano verdi).

## Documentazione

- Nota di studio `docs/notes/07-*.md`: validazione di grafi RDF che evolvono, pattern
  read-query-update-validate, scelte del runtime graph.
- README.md aggiornato con i comandi nuovi (`play.py`, `config.toml`) — obbligatorio
  da CLAUDE.md.
- La simulazione permette di verificare i due limiti deliberati di M2 (cicli lock-key
  indiretti, completabilità vera delle quest): da annotare in retrospettiva ciò che
  la run rivela.

## Criteri di successo

- `python -m tools.play --new` esegue una run interattiva completa fino a vittoria.
- La run end-to-end nei test passa con grafo finale conforme; pytest tutto verde,
  inclusi i test M1/M2 esistenti.
- `runtime/save.ttl` è leggibile, interrogabile con SPARQL e rivalidabile a freddo.
- Interrompere e riprendere una run funziona.
- Con `player_success < 1` la sconfitta è possibile e gestita.

## Fuori scope (deliberato, da obiettivo.md)

HP/danno/statistiche di combattimento, bot automatico e simulazioni batch (Fase 6),
generazione di contenuti (M4), triple store/endpoint SPARQL, più giocatori, UI oltre
la CLI testuale, reasoning OWL.
