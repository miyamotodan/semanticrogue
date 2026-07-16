# Nota di studio 05 — SHACL avanzato: vincoli di completezza e progressione

Concetti usati nel Task 5, con esempi da `shacl/rogue-rules.ttl` e `tests/invalid/`.

## Vincoli core vs vincoli SPARQL-based

I vincoli core (`sh:minCount`, `sh:class`, …) guardano **un nodo alla volta**. Ma le domande di progressione di un roguelike sono globali: "questa chiave si ottiene da qualche parte?", "questa stanza si raggiunge?". Per queste serve `sh:sparql`: ogni riga restituita dalla query è una violazione, con `$this` legato al nodo target.

C'è una differenza concettuale importante: i vincoli core rilevano dati **malformati**; le shape SPARQL di questo task rilevano dati **incompleti**. Una chiave orfana è perfettamente ben formata — è il *resto del mondo* che le manca. È il motivo per cui, prima del Task 5, la validazione non poteva accorgersi delle entità mancanti.

## "Nessuna fonte esiste": NOT EXISTS multipli

`sr:OrphanKeyShape` esprime "la chiave non ha alcuna fonte" come congiunzione di assenze:

```sparql
FILTER NOT EXISTS { ?monster sr:dropsItem $this . }
FILTER NOT EXISTS { ?quest sr:questReward $this . }
```

Due `FILTER NOT EXISTS` in AND: "nessuno la droppa **e** nessuna quest la premia".

### Il bug di rdflib scoperto qui (debugging reale)

La prima stesura usava la forma da manuale `FILTER NOT EXISTS { { A } UNION { B } }`. Logicamente è equivalente a due NOT EXISTS separati (De Morgan: ¬(A ∨ B) = ¬A ∧ ¬B), ma il motore SPARQL di rdflib la valuta male quando i rami contengono `FILTER` su variabili esterne: **tutti** i portali risultavano in violazione, comprese le catene lock-key sane. Il metodo per scoprirlo è da ricordare:

1. la violazione inattesa sul dataset buono è emersa dai test (non a occhio);
2. uno script di probe ha eseguito varianti della stessa query (NOT EXISTS con/senza FILTER interno, con/senza UNION, MINUS, OPTIONAL+!BOUND);
3. isolato il costrutto rotto, la riscrittura equivalente è documentata con un commento nella query stessa.

Morale: i motori SPARQL non sono tutti uguali; le query delle shape vanno *testate*, esattamente come il codice.

## Property path complessi: la raggiungibilità

`sr:UnreachableRoomShape` chiede: esiste un cammino dalla stanza iniziale a `$this`?

```sparql
?start sr:isStartRoom true .
?start (sr:connectedTo|^sr:connectedTo|(^sr:portalInRoom/sr:unlocksRoom))* $this .
```

Lettura del path, pezzo per pezzo:

- `sr:connectedTo` — un passo lungo una connessione;
- `^sr:connectedTo` — il verso opposto (`^` inverte l'arco): le connessioni authored sono dirette ma le trattiamo come percorribili in entrambi i sensi;
- `^sr:portalInRoom/sr:unlocksRoom` — dalla stanza risalgo al portale che la ospita (`^`), poi scendo alla stanza che sblocca: è l'arco "attraverso il portale";
- `(...|...|...)*` — chiusura riflessivo-transitiva: qualunque combinazione dei tre archi, inclusa quella vuota (la start room raggiunge sé stessa).

Limite dichiarato: il path ignora *se il portale è apribile* — misura la raggiungibilità topologica, non giocabile. Se nessuna stanza ha `sr:isStartRoom true`, tutte risultano irraggiungibili: comportamento voluto (segnala il mondo senza inizio).

## Il caso diretto del ciclo lock-key

`sr:LockKeyCycleShape` intercetta il deadlock più semplice: tutte le fonti della chiave stanno nella stanza che il portale sblocca. Non scopre cicli **indiretti** (chiave A oltre il portale B, la cui chiave è oltre il portale A): per quelli serve attraversare il grafo con stato, cioè la simulazione della Fase 3 (M3). È un esempio del confine tra ciò che conviene chiedere a SHACL e ciò che spetta al simulatore.

## Testare le shape: micro-mondi e identità delle violazioni

Ogni file in `tests/invalid/` è un micro-mondo autonomo, valido in tutto tranne che per il difetto voluto. Il test verifica che nel report compaia la violazione *attesa*, non una qualsiasi — con una sottigliezza:

- per le shape SPARQL il report ha `sh:sourceShape` = l'IRI della node shape (confrontabile);
- per le property shape anonime (`sh:property [ ... ]`) il `sh:sourceShape` è un blank node senza identità stabile: si confronta invece la coppia (`sh:focusNode`, `sh:resultPath`).

È il pattern "un test per vincolo": quando una shape nuova romperà qualcosa, il nome del file dirà subito *quale* invariante del mondo è saltata.
