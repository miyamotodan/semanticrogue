# REGOLE GENERALI (stategie da applicare sempre)

## Orchestrazione del lavoro

### 1. Modalità piano come default
- Entrare in modalità piano per QUALSIASI task non banale (3+ passi o decisioni architetturali)
- Se qualcosa va storto, FERMARSI e ripianificare immediatamente — non insistere
- Usare la modalità piano anche per i passi di verifica, non solo per la costruzione
- Scrivere specifiche dettagliate in anticipo per ridurre l'ambiguità

### 2. Strategia subagent
- Usare i subagent liberamente per mantenere pulita la finestra di contesto principale
- Delegare ricerca, esplorazione e analisi parallele ai subagent
- Per problemi complessi, usare più potenza di calcolo tramite subagent
- Un task per subagent per un'esecuzione mirata

### 3. Ciclo di auto-miglioramento
- Dopo QUALSIASI correzione dell'utente: aggiornare `tasks/lessons.md` con il pattern
- Scrivere regole per sé stessi che prevengano lo stesso errore
- Iterare senza pietà su queste lezioni finché il tasso di errore non cala
- Rivedere le lezioni all'inizio della sessione per il progetto rilevante

### 4. Verifica prima di dichiarare completato
- Non marcare mai un task come completato senza dimostrare che funziona
- Confrontare il comportamento tra main e le proprie modifiche quando rilevante
- Chiedersi: "Un senior engineer approverebbe questo?"
- Eseguire test, controllare log, dimostrare la correttezza

### 5. Pretendere eleganza (bilanciata)
- Per modifiche non banali: fermarsi e chiedersi "c'è un modo più elegante?"
- Se un fix sembra un hack: "Sapendo tutto quello che so ora, implementare la soluzione elegante"
- Saltare questo passaggio per fix semplici e ovvi — non sovra-ingegnerizzare
- Mettere in discussione il proprio lavoro prima di presentarlo

### 6. Bug fixing ragionato
- Quando si riceve un bug report: non risolverlo e basta. Chiedere assistenza per verificare se si è corenti con la progettazione generale e le intenzioni dell'utente.
- Indicare log, errori, test che falliscono — poi risolverli

## Gestione dei task

1. **Prima pianificare**: scrivere il piano in `tasks/todo.md` con elementi spuntabili
2. **Verificare il piano**: confrontarsi prima di iniziare l'implementazione
3. **Tracciare il progresso**: marcare gli elementi completati man mano
4. **Spiegare le modifiche**: riepilogo ad alto livello ad ogni passo
5. **Documentare i risultati**: aggiungere sezione di review a `tasks/todo.md`
6. **Catturare le lezioni**: aggiornare `tasks/lessons.md` dopo le correzioni

## Principi fondamentali

- **Semplicità prima di tutto**: ogni modifica il più semplice possibile. Impatto minimo sul codice.
- **Niente pigrizia**: trovare le cause radice. Niente fix temporanei. Standard da sviluppatore senior.
- **Impatto minimale**: le modifiche devono toccare solo il necessario. Evitare di introdurre bug.

# REGOLE SPECIFICHE DEL PROGETTO (regole e appunti sul progetto)

## Cos'è questo progetto

Un sistema basato su tecnologie del web semantico (RDF, OWL, SHACL, SPARQL, in prospettiva RML) per generare e gestire un gioco roguelike: il mondo (stanze, mostri, oggetti, fazioni, quest, portali) è modellato come knowledge graph, i vincoli di coerenza sono shape SHACL, e in futuro il grafo fungerà anche da world state interrogabile e aggiornabile durante la partita.

Il piano completo (fasi, milestone, cosa NON fare ancora) è in `obiettivo.md` — leggerlo prima di proporre estensioni. Principi chiave da rispettare:

- Separazione netta tra i moduli: **Model** (ontologia), **Content** (dataset), **Validation** (SHACL), **Runtime** (stato di partita, futuro). Non mescolare contenuto, stato e regole.
- Sviluppo incrementale: prima core semantico verificabile, poi simulazione, solo alla fine generazione procedurale.
- Poche classi ontologiche chiare, OWL leggero, niente reasoning pesante.
- Il criterio di successo della validazione è: "quando rompo il dataset, il sistema se ne accorge".

## Struttura

- `ontology/rogue.ttl` — ontologia OWL: classi (`sr:Room`, `sr:Monster`/`sr:Boss`, `sr:Item` con sottoclassi `Weapon`/`Consumable`/`KeyItem`, `sr:Faction`, `sr:Quest`, `sr:NPC`, `sr:Portal`, `sr:Biome`), object property e datatype property.
- `dataset/dataset.ttl` — mondo authored a mano (istanze nel namespace `ex:`).
- `shacl/rogue-rules.ttl` — shape SHACL, sia property shape classiche sia SPARQL-based (es. stanze con `dangerLevel >= 6` devono ospitare un mostro; l'oggetto richiesto da un portale deve essere droppato da qualche mostro).
- `obiettivo.md` — visione, roadmap in 6 fasi e 4 milestone.

Non c'è ancora codice eseguibile, build o test suite: la validazione SHACL va eseguita con un tool esterno (es. pySHACL: `pyshacl -s shacl/rogue-rules.ttl -e ontology/rogue.ttl dataset/dataset.ttl`).

## Convenzioni

- **Namespace**: `sr:` = `http://example.org/semantic-roguelike#` per il vocabolario (ontologia e shape); `ex:` = `http://example.org/id/` per le istanze del dataset. Non definire istanze in `sr:` né termini di vocabolario in `ex:`.
- **Annotazioni bilingui obbligatorie**: ogni risorsa (classi, proprietà, shape, istanze) ha `rdfs:label` e `rdfs:comment` sia `@it` sia `@en`. Le shape SHACL hanno anche `sh:name`, `sh:description` e `sh:message` bilingui.
- Le shape SPARQL-based usano `sh:sparql` con `sh:select` e `$this`; i prefissi usati nelle query devono essere dichiarati nel file.
- Quando si aggiunge una classe o proprietà all'ontologia, valutare se serve una shape SHACL corrispondente: ogni vincolo di design del gioco dovrebbe diventare un vincolo eseguibile.
- Quando si estende il dataset, verificare che le nuove istanze soddisfino le shape esistenti (es. ogni `sr:Room` richiede esattamente un bioma, un `dangerLevel` 1–10 e un `floorIndex`; ogni `sr:Item` richiede una `rarity` 1–10).
