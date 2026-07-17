# Design: chiusura backlog M4 — vincoli di rigore

Data: 2026-07-17
Stato: approvato

## Obiettivo

Chiudere le due voci rimaste nel backlog M4 (dalla review finale di M3), entrambe
sul rigore dei vincoli:

1. **Unicità della stanza iniziale**: una shape di contenuto che impone al mondo
   esattamente una `sr:isStartRoom true`. Oggi nulla lo vincola e `new_state`
   sceglierebbe arbitrariamente se ce ne fossero due.
2. **Completamento quest in `talk_to`**: il motore deve completare una quest
   nell'istante in cui la si accetta, se le condizioni di completamento sono già
   tutte soddisfatte (player nella target room, nessun mostro vivo).

Sono due incrementi piccoli e indipendenti, raccolti in un'unica spec perché
coesi (entrambi rendono eseguibile un vincolo di design finora implicito).

## Parte 1 — Unicità della stanza iniziale

### Il problema

`sr:RoomShape` vincola già `sr:isStartRoom` a `maxCount 1` **per singola stanza**
(il valore è un booleano unico), ma niente impedisce a *due stanze diverse* di
essere entrambe `isStartRoom true`, né al mondo di non averne nessuna.
`sr:UnreachableRoomShape` e `new_state` presuppongono un'unica start room.

### La forma del vincolo

"Il mondo ha esattamente una start room" è un vincolo globale sul grafo, non
per-nodo. Due sotto-casi da intercettare, con due shape SPARQL-based nello stile
di quelle esistenti (target `sr:Room`, `sh:prefixes sr:RogueShapes`):

- **Più di una** — `sr:SingleStartRoomShape`, target `sr:Room`: `$this` viola se
  è `isStartRoom true` ed esiste un'altra stanza diversa anch'essa `isStartRoom
  true`. Ogni start room di troppo diventa un focus node segnalato.

  ```sparql
  SELECT $this
  WHERE {
    $this sr:isStartRoom true .
    ?other sr:isStartRoom true .
    FILTER(?other != $this)
  }
  ```

- **Nessuna** — `sr:StartRoomExistsShape`. Il caso "zero" non ha un nodo naturale
  da targetizzare (nessuna start room = nessun focus). Si usa un target basato su
  query (`sh:target` con `sh:select`) che restituisce **tutte** le stanze quando
  non ne esiste alcuna con `isStartRoom true`, così la violazione ha comunque un
  focus node; se una start room esiste, il target è vuoto e non scatta nulla.

  ```sparql
  # sh:target -> sh:select: nodi target solo se manca del tutto una start room
  SELECT $this
  WHERE {
    $this a sr:Room .
    FILTER NOT EXISTS { ?r sr:isStartRoom true . }
  }
  ```

  Nota (bug rdflib noto): niente `NOT EXISTS { A UNION B }`; qui c'è un solo
  `FILTER NOT EXISTS`, nessun problema.

Entrambe con annotazioni bilingui complete (`rdfs:label`/`comment`,
`sh:name`/`description` dove property-based non è; per le SPARQL-based
`sh:message` bilingue).

### Casi rotti (`tests/invalid/`)

- `two-start-rooms.ttl`: due stanze `isStartRoom true` → `sr:SingleStartRoomShape`.
- `no-start-room.ttl`: un micro-mondo di stanze senza alcuna `isStartRoom true`
  → `sr:StartRoomExistsShape`.

Ciascuno registrato in `BROKEN_CASES` di `tests/test_validation.py` con il focus
node e la shape attesi, come gli altri casi. Il dataset authored (una sola start
room) resta conforme.

## Parte 2 — `talk_to` completa le quest già soddisfatte

### Il problema

`_check_quest_completion` (quest `active` + player nella `questTargetRoom` +
nessun mostro vivo ⇒ `completed` + reward) è invocata dopo `move_to` e dopo
`fight`, ma **non** dopo `talk_to`. Accettando una quest mentre si è già nella
sua target room ripulita, la quest resta `active` finché non si compie un'altra
azione. Irraggiungibile col dataset attuale (gli NPC non stanno nelle target
room), ma è un buco nel motore generico.

### Il fix

Una riga: `self._check_quest_completion()` in fondo a `talk_to`, dopo aver
attivato le quest offerte.

### Test

- Unit su `engine`: player nella target room di una quest, stanza ripulita,
  l'NPC che offre quella quest posto nella stessa stanza (nello stato di test);
  `talk_to` deve portarla direttamente a `completed` e dare il reward, senza
  bisogno di un'azione successiva.
- I test esistenti di `talk_to` restano verdi (nei loro scenari le condizioni di
  completamento non sono soddisfatte, quindi il nuovo controllo è un no-op).

## Fuori scope (deliberato)

Il guard sui tipi non-tabella in `config.py` (terza voce storica del backlog) è
già stato chiuso col parametro `map.auto`. Nessun'altra modifica al motore o al
vocabolario.
