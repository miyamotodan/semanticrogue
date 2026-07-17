# Design: fog-of-war — stanze visitate sulla mappa

Data: 2026-07-17
Stato: approvato

## Obiettivo

Distinguere sulla mappa le stanze già visitate da quelle ancora ignote:
le visitate si disegnano com'è ora (nome, occupanti, stato), le non visitate
come nodi scuri anonimi (`???`), rivelando la topologia ma non il contenuto.
È fog-of-war da roguelike, e rende la mappa un vero strumento di "cosa so
finora della partita", non solo dello stato del mondo.

Il "visitato" è stato di partita (cambia durante la run, è diverso per ogni
partita): vive nel runtime graph, non nel contenuto authored.

## Decisioni prese

| Decisione | Scelta | Alternative scartate |
|---|---|---|
| Cosa mostra una stanza non visitata | Solo esistenza + connessioni; nome e contenuto nascosti (`???`) | Nome visibile (fog leggero); tutto visibile con solo stile scuro (evidenziatore, non fog) |
| Distinzione tra nodi bui | Nodo distinto con id tecnico invariato ed etichetta `???` | Numero progressivo (instabile tra i turni); mostrare solo le adiacenti (fog più stretto, più lavoro) |
| Chi marca il visitato | Il motore, entrando: `move_to` marca la destinazione, `new_state` marca la start room | Azione esplicita del giocatore (innaturale) |
| Quando vale il fog | Solo con uno stato di partita (`--save`); senza stato la mappa del mondo authored resta piena | Fog sempre attivo (perde l'uso da studio del mondo) |

## Vocabolario runtime (`ontology/runtime.ttl`)

Nuova datatype property `sr:visited` (Room → boolean), stile di `sr:isOpen`:

- Convenzione: **assenza di tripla = non visitata**; si scrive solo `sr:visited true`.
- Annotazioni bilingui `@it`/`@en` (label + comment) obbligatorie.

## Motore (`tools/engine.py`)

- `new_state(world)`: aggiunge `(start, sr:visited, Literal(True))` — il player
  parte dalla start room, che è quindi visitata dall'inizio.
- `move_to(room)`: dopo aver aggiornato `currentRoom`, aggiunge
  `(room, sr:visited, Literal(True))`.
- Nessun'altra transizione tocca `visited`. I salvataggi precedenti (senza la
  proprietà) restano leggibili: le loro stanze risultano non visitate, coerente
  con un save antecedente alla feature.

## Shape runtime (`shacl/runtime-rules.ttl`)

Property shape su `sr:Room` per `sr:visited`: `sh:maxCount 1`, `sh:datatype
xsd:boolean`. Vincolo di forma, non semantico (una stanza può legittimamente
essere visitata o no). Annotazioni bilingui `sh:name`/`sh:description` come le
altre shape.

## Mappa (`tools/map.py`)

`build_map(world, state)` distingue, **solo quando `state` è presente**, tra
stanza visitata e non:

- **Visitata**: come oggi — nome, mostri (☠ se sconfitti, 👑 per i boss), NPC
  (🧙), ⭐ sulle target di quest attive, 🧝 se è la stanza del player.
- **Non visitata**: nodo con etichetta `???`, contenuto nascosto; id tecnico
  invariato (`local_name`), così connessioni e portali restano corretti.
- Connessioni (`connectedTo`) e portali (🔒/🔓) si disegnano sempre: la
  topologia è nota anche per le stanze ignote.
- `classDef fog` (sfondo scuro) applicato ai nodi non visitati, accanto al
  `classDef player` esistente.

Senza `state`, `build_map` resta identica a oggi: la stanza è trattata come se
non ci fosse fog (mondo authored pieno). La stanza del player è sempre
visitata, quindi non c'è conflitto tra marcatura `player` e `fog`.

## Test

- **Engine**: `new_state` marca la start room; `move_to` marca la destinazione;
  entrare due volte nella stessa stanza resta idempotente (una sola tripla).
- **Shape runtime**: uno stato con `sr:visited` non-boolean fa scattare la nuova
  shape (e non un'altra).
- **Mappa**: con stato parziale (alcune stanze visitate, altre no) l'output
  contiene `???` e la classe fog sulle non visitate, e i dettagli sulle
  visitate; senza stato l'output resta pieno come oggi (nessun `???`).
- I test esistenti di mappa e runtime restano verdi (la firma di `build_map`
  non cambia).

## Fuori scope (deliberato)

Rivelare le adiacenti non visitate (fog più stretto), memoria di "cosa c'era"
in una stanza già lasciata, coordinate/geometria.
