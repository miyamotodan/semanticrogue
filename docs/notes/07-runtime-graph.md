# Nota di studio 07 — Il runtime graph: il grafo come world state

Chiude il piano `docs/superpowers/plans/2026-07-17-m3-playable-simulation.md` (spec: `docs/superpowers/specs/2026-07-17-m3-playable-simulation-design.md`). Concetti usati nei Task 1–9 di M3, con esempi dal codice reale: `tools/engine.py`, `tools/play.py`, `ontology/runtime.ttl`, `shacl/runtime-rules.ttl`, `queries/runtime/`, `config.toml`.

## Due grafi, due responsabilità

Fino a M2 esisteva un solo grafo: ontologia + dataset, entrambi statici, uniti solo per la validazione (`tools/common.py::load_graph`). M3 introduce una seconda dimensione — lo **stato di partita**, che cambia turno per turno — e la tiene deliberatamente separata dal contenuto:

- **Content graph**: `ontology/rogue.ttl` + `dataset/dataset.ttl`. Il mondo authored, immutabile durante la run. Caricato con `load_runtime_world()` in `tools/common.py`, che aggiunge anche `ontology/runtime.ttl` al mix.
- **Runtime graph** (`state` in `tools/engine.py`): solo le triple che descrivono *questa* run — dove si trova `ex:player`, cosa ha in inventario, quali mostri sono morti, quali portali sono aperti, a che punto sono le quest. Nasce da `new_state(world)` e vive in memoria come oggetto `rdflib.Graph` separato; non tocca mai il content graph.

`Engine.graph()` è l'unico punto in cui i due si fondono, e lo fanno con `+` (unione di grafi, non mutazione): `self.world + self.state`. Le query e la validazione girano sempre su questa unione, mai sul content graph da solo — un mostro "vivo" non ha una tripla che lo dice, quindi una query che ignorasse lo state vedrebbe solo il mondo authored e non saprebbe chi è già stato sconfitto.

Questa separazione è la stessa idea architetturale di Model/Content/Validation di `obiettivo.md`, estesa con **Runtime**: il vocabolario che descrive lo stato (`sr:Player`, `sr:currentRoom`, `sr:hasItem`, `sr:isAlive`, `sr:isOpen`, `sr:questStatus`, in `ontology/runtime.ttl`) è a sua volta un piccolo Model, distinto dal Model del contenuto (`ontology/rogue.ttl`). Non si mescolano nello stesso file per lo stesso motivo per cui contenuto e vincoli non si mescolano: cambiano a ritmi diversi e li si vuole poter ragionare separatamente.

## La convenzione: assenza di tripla = stato di default

Ogni proprietà runtime è pensata per essere scritta **una sola volta**, nella direzione "eccezionale":

- `sr:isAlive false` si scrive solo alla morte di un mostro o del player — l'assenza della tripla significa vivo.
- `sr:isOpen true` si scrive solo all'apertura di un portale — l'assenza significa chiuso.
- `sr:questStatus` si scrive solo quando una quest diventa `"active"` o `"completed"` — l'assenza significa non ancora accettata.

Il codice la rispetta ovunque: `Engine._check_quest_completion` (in `tools/engine.py`) itera `self.state.subjects(SR.questStatus, Literal("active"))`, non "tutte le quest meno quelle completate"; `queries/runtime/monsters-here.rq` filtra con `FILTER NOT EXISTS { ?mostro sr:isAlive false . }`, non con un controllo positivo su "vivo". Il vantaggio pratico: `new_state(world)` produce un grafo di **due sole triple** (tipo del player + stanza iniziale — verificato da `test_new_state_puts_player_in_start_room` in `tests/test_engine.py`, che asserisce `len(state) == 2`). Tutto il resto del mondo (dieci stanze, otto mostri, dieci oggetti) è già nel content graph e non va duplicato nello stato a ogni nuova run.

Il rovescio della medaglia: la convenzione va rispettata anche nelle shape, non solo nel motore (vedi sotto — `sr:QuestStatusValueShape` non impone `sh:minCount`, solo `sh:maxCount 1` e `sh:in (...)`, perché l'assenza è uno stato legittimo).

## Il ciclo di un turno: read → transizione → validazione → serializzazione

`tools/play.py::main` esegue questo ciclo a ogni comando che modifica lo stato:

1. **Read (SPARQL)**: `Engine.run_query(name)` legge un file `.rq` da `queries/runtime/` e lo esegue su `self.graph()`. Le cinque query (`available-moves.rq`, `openable-portals.rq`, `monsters-here.rq`, `npcs-here.rq`, `quest-status.rq`) sono le uniche fonti di "cosa è ammissibile ora" — il motore non ricalcola la logica in Python, la delega a SPARQL. `available-moves.rq`, ad esempio, è quasi letteralmente `queries/02-connections.rq` di M1 con l'aggiunta dei portali aperti: la retrospettiva 06 lo aveva previsto ("le query di M1 sono già metà del lavoro").

2. **Transizione (triple)**: i metodi `Engine.move_to`, `open_portal`, `fight`, `talk_to` prima ri-eseguono la query di ammissibilità e sollevano `ActionError` se l'azione non è nella lista consentita (grafo **non** modificato), poi scrivono triple nello `state` con `add`/`set`. Nessuna azione tocca `self.world`. `move_to` e `fight` (se vittorioso e ultimo mostro) chiamano `_check_quest_completion`, che è a sua volta lettura (`monsters-here.rq`, iterazione su `questStatus active`) seguita da scrittura (`questStatus completed` + `hasItem` per la reward).

3. **Validazione SHACL**: se `config.toml` ha `validation.mode = "turn"` (default), dopo la transizione `tools/play.py` chiama `validate_runtime(eng.world, eng.state)` prima di salvare. Se il modo è `"on-demand"`, la stessa funzione gira solo quando il giocatore digita il comando `valida`.

4. **Serializzazione**: solo se la validazione (quando richiesta) conforma, `eng.state.serialize(args.save, format="turtle")` scrive `runtime/save.ttl` (o il path passato con `--save`). Il turno zero si salva subito dopo l'inizializzazione, prima di qualunque comando, così la partita è ispezionabile anche se il giocatore esce subito.

## Perché le shape runtime intercettano i bug del motore — e cosa non vedono

`shacl/runtime-rules.ttl` non valida il *contenuto* (quello resta compito di `shacl/rogue-rules.ttl`): valida che lo **stato** prodotto dal motore sia coerente con le regole del gioco. Quattro shape:

- `sr:PlayerStateShape` — il player ha esattamente una `currentRoom`, e deve essere una `sr:Room` vera. Se `move_to` avesse un bug che aggiunge una seconda `currentRoom` invece di sostituirla (`add` invece di `set`), questa shape lo scoprirebbe.
- `sr:QuestStatusValueShape` — `questStatus`, se presente, è solo `"active"` o `"completed"` (`sh:in`), al più una volta. Un refuso tipo `"paused"` viene intercettato — è il caso rotto `broken_quest_status_value` in `tests/test_runtime_validation.py`.
- `sr:OpenPortalNeedsKeyShape` (SPARQL-based) — un portale `isOpen true` deve corrispondere a una chiave posseduta dal player. Intercetta un bug ipotetico in cui `open_portal` scrivesse `isOpen` senza aver verificato `openable-portals.rq`.
- `sr:ItemProvenanceShape` (SPARQL-based) — ogni oggetto in inventario deve avere una provenienza lecita: drop di un mostro **morto**, o reward di una quest **completata**. Intercetta un oggetto comparso "dal nulla".

Le due shape SPARQL-based riusano lo stesso pattern imparato in M2 (nota 05): congiunzione di `FILTER NOT EXISTS` separati invece di `NOT EXISTS { A UNION B }`, per lo stesso bug di rdflib documentato in CLAUDE.md. `sr:ItemProvenanceShape` lo dice esplicitamente in un commento nella query.

`tools/engine.py::validate_runtime(world, state)` ha la stessa firma concettuale di `pyshacl.validate`: `(conforms, results_graph, results_text)`. Se `tools/play.py` la chiama dopo una transizione e trova `not conforms`, stampa il report SHACL, **non salva** il turno ed esce con `exit 3` — distinto da `exit 1` (violazioni di contenuto in `tools.validate`) e `exit 2` (errore di parsing/config). La differenza semantica: `exit 1` dice "il mondo authored ha un difetto", `exit 3` dice "il motore ha rotto le sue stesse regole" — un bug di programmazione, non un problema di game design. Non dovrebbe mai succedere in condizioni normali; è una rete di sicurezza, verificata nei test con stati costruiti ad arte (`tests/test_runtime_validation.py`) piuttosto che aspettando che il motore *effettivamente* la produca durante il gioco.

**Cosa queste shape non possono vedere**: sono vincoli locali (property shape) o su singolo nodo (SPARQL-based con `$this`), quindi non catturano proprietà **globali** della sequenza di transizioni — ad esempio "il player non può aver visitato una stanza prima che fosse raggiungibile" richiederebbe di ricostruire la storia dei turni, non solo lo stato finale. Non è un limite specifico di queste quattro shape ma di SHACL in generale applicato a uno snapshot: valida *questo* stato, non *come* ci si è arrivati.

## Cosa la simulazione scioglie dei limiti di M2

La retrospettiva 06 aveva lasciato due limiti dichiarati:

1. **Cicli lock-key indiretti**: `sr:LockKeyCycleShape` (M2) intercetta solo il ciclo diretto — la chiave di un portale si trova nella stanza che il portale stesso sblocca. Un ciclo indiretto (chiave A oltre il portale B, la cui chiave B è oltre il portale A) richiede di *attraversare* il grafo con memoria di cosa si è già raccolto, cioè simulare — non è più una domanda SPARQL su un solo stato ma una ricerca su sequenze di stati. `Engine.move_to` + `open_portal`, giocati a mano o script in `tests/test_run_end_to_end.py`, fanno esattamente questo attraversamento: se un ciclo indiretto esistesse nel dataset, nessuna sequenza di comandi porterebbe alla vittoria, e lo si scoprirebbe giocando (o testando) la run, non validando un singolo stato.

2. **Completabilità reale delle quest**: `sr:UnreachableRoomShape` (M2) misura raggiungibilità *topologica* (ignora se un portale è apribile). La simulazione misura raggiungibilità *giocabile*: `available-moves.rq` include i portali solo se `isOpen true`, e `isOpen` diventa vero solo se il player possiede davvero la chiave nella stanza giusta (`openable-portals.rq`). Il run end-to-end vincente in `tests/test_run_end_to_end.py` (via `test_play_cli.py::test_victory_run_with_labels`) è la prova costruttiva che almeno una quest è completabile con una sequenza di azioni reali — non un'inferenza sulla struttura del grafo, ma un'esecuzione.

In entrambi i casi il pattern è lo stesso della nota 05: SHACL su un grafo statico risponde a domande "esiste una violazione in questo stato?"; le domande "esiste una sequenza di azioni che porta a X?" sono domande sul comportamento, e la risposta di questo progetto è non provare a esprimerle in SPARQL ma costruire un motore che le esegue davvero.

## Scelte di configurazione (`config.toml`)

`tools/config.py::load_config` legge tre parametri, tutti con default che rendono il gioco deterministico e permissivo:

- **`[validation] mode`**: `"turn"` (default) valida dopo ogni transizione — costoso (una chiamata pySHACL a turno) ma dà un segnale immediato se il motore sbaglia. `"on-demand"` valida solo quando il giocatore digita `valida` — più veloce, adatto a run lunghe o a fidarsi del motore dopo che è stato testato a sufficienza. La scelta è per-run, non hardcoded, perché sono due modalità d'uso legittime (sviluppo vs. gioco) piuttosto che una giusta e una sbagliata.
- **`[combat] player_success`**: probabilità in `[0, 1]` che il player vinca uno scontro (`Engine.fight`, confronto `self.rng.random() < self.player_success`). Default `1.0`: il player vince sempre, quindi l'unico modo di perdere è deliberatamente abbassare questo valore. È una scelta di design esplicita per M3 — il motore *supporta* il combattimento probabilistico (serve per dimostrare l'esito di sconfitta, vedi `test_fight_lost_kills_player`), ma il gioco di default non è punitivo: l'obiettivo di M3 è dimostrare che il ciclo read-transizione-validazione funziona end-to-end, non bilanciare un roguelike.
- **`seed`** (top-level, non annidato — a differenza di `mode` e `player_success`): seme per `random.Random(seed)` in `Engine`, per run riproducibili nei test. `None` (default, commentato nel file) significa casuale. `--seed` da CLI sovrascrive il valore di config — utile per riprodurre un bug segnalato con un seed specifico senza editare il file.

`load_config` rifiuta valori fuori range con `ValueError` (mode sconosciuto, probabilità fuori `[0,1]`, seed non intero) piuttosto che silenziosamente clampare o ignorare: coerente con "niente fix temporanei, standard da sviluppatore senior" — un config malformato deve fermare l'avvio (`exit 2` in `tools/play.py`), non produrre un comportamento inspiegabile a metà partita.
