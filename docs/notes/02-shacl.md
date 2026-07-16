# Nota di studio 02 — SHACL: shape, target e report

Concetti usati nel Task 2, con esempi da `shacl/rogue-rules.ttl`.

## Node shape e property shape

Una **node shape** dichiara vincoli su un insieme di nodi del grafo dati; una **property shape** (annidata con `sh:property`) vincola i valori raggiungibili da un percorso. `sr:RoomShape` è una node shape con tre property shape:

```turtle
sr:RoomShape a sh:NodeShape ;
  sh:targetClass sr:Room ;
  sh:property [
    sh:path sr:locatedInBiome ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:class sr:Biome ;
  ] ; ...
```

Lettura: "per ogni istanza di `sr:Room`, il valore di `sr:locatedInBiome` esiste (`minCount`), è unico (`maxCount`) ed è un `sr:Biome` (`sh:class`)".

## Il target e le sottoclassi

`sh:targetClass sr:Room` seleziona i nodi con `rdf:type sr:Room` **o un suo sottotipo** — ma il validatore vede `rdfs:subClassOf` solo se le triple dell'ontologia stanno nel grafo validato. È il motivo per cui `run_validation()` valida `load_graph(ONTOLOGY, data_path)` e non il solo dataset: senza `sr:Boss rdfs:subClassOf sr:Monster`, un `ex:cryptTyrant a sr:Boss` sfuggirebbe a `sr:MonsterShape`.

## Vincoli core usati nel progetto

- `sh:minCount` / `sh:maxCount` — cardinalità ("esattamente un bioma");
- `sh:class` — il valore deve essere istanza di una classe ("il drop è un `sr:Item`");
- `sh:datatype` — il letterale deve avere quel tipo (`xsd:integer`);
- `sh:minInclusive` / `sh:maxInclusive` — range numerico (danger 1–10).

## Shape SPARQL-based

Quando il vincolo attraversa più risorse ("una stanza pericolosa deve ospitare un mostro"), i vincoli core non bastano: si scrive una query dentro `sh:sparql`. La query viene eseguita per ogni nodo target, con `$this` legato al nodo; **ogni riga restituita è una violazione**:

```sparql
SELECT $this WHERE {
  $this sr:dangerLevel ?d .
  FILTER(?d >= 6)
  FILTER NOT EXISTS { $this sr:hostsMonster ?m . }
}
```

### `sh:declare` / `sh:prefixes`

Per la spec SHACL-SPARQL i prefissi usati nelle query vanno dichiarati esplicitamente: un nodo `owl:Ontology` porta le `sh:declare` e ogni blocco `sh:sparql` le richiama con `sh:prefixes`:

```turtle
sr:RogueShapes a owl:Ontology ;
  sh:declare [ sh:prefix "sr" ; sh:namespace "..."^^xsd:anyURI ] .
```

Osservazione empirica: pySHACL 0.40 esegue le query anche senza (riusa i prefissi del file Turtle come fallback), ma è un comportamento non standard — altri validatori fallirebbero. La dichiarazione esplicita rende il file portabile.

## Il validation report

Il report è a sua volta un grafo RDF. Per ogni violazione: `sh:focusNode` (il nodo che viola), `sh:resultPath` (il percorso, per le property shape), `sh:sourceShape` (la shape che ha generato la violazione), `sh:resultMessage`. La violazione trovata in questo task è il caso di studio perfetto:

```
Source Shape: sr:DangerousRoomMustHaveContent
Focus Node: ex:sanctum01
```

`ex:sanctum01` aveva `dangerLevel 6` e nessun mostro: il dataset scritto a mano conteneva un errore di bilanciamento che nessuno aveva notato leggendolo — la validazione eseguibile l'ha trovato al primo colpo. Correzione: `ex:cryptTyrant` (boss, che per `sr:BossPlacementShape` deve anche droppare qualcosa → `ex:tyrantSigil`).

## Exit code come contratto

`tools/validate.py` traduce il report in un contratto da pipeline: 0 conforme, 1 violazioni, 2 errore di parsing. Così la validazione è usabile da script, test e (in futuro) CI.
