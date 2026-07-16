# Nota di studio 03 — SPARQL: leggere il mondo dal grafo

Concetti usati nel Task 3, con riferimento ai file in `queries/`.

## Struttura di una SELECT

Una query SPARQL è un **pattern di triple con variabili** (basic graph pattern): il motore trova tutte le combinazioni di nodi che soddisfano il pattern. Da `01-rooms-overview.rq`:

```sparql
SELECT ?stanza ?bioma ?pericolo ?piano
WHERE {
  ?room a sr:Room ;
        rdfs:label ?stanza ;
        sr:dangerLevel ?pericolo .
}
```

`?room` compare nel `WHERE` ma non nella `SELECT`: serve solo a legare le triple tra loro. La sintassi `;` è la stessa di Turtle — una query è "Turtle con buchi".

## Property path

I path permettono di attraversare più archi in un solo passo:

- `/` (sequenza) — `sr:locatedInBiome/rdfs:label ?bioma` in `01`: "vai al bioma e prendi la sua label", senza variabile intermedia;
- `*` (chiusura riflessivo-transitiva) — `?cls rdfs:subClassOf* sr:Item` in `06`: matcha `sr:Item` stesso (zero passi), `sr:KeyItem` (un passo), e qualunque profondità futura. È il modo per chiedere "è un Item, direttamente o per gerarchia" **senza reasoner OWL**: basta che l'ontologia sia nel grafo interrogato.

## OPTIONAL e i suoi annidamenti

`OPTIONAL` aggiunge informazione se c'è, senza scartare la riga se manca. Il caso interessante è `04-lock-key-chain.rq`, dove gli OPTIONAL sono **annidati**:

```sparql
OPTIONAL {
  ?m sr:dropsItem ?k ; rdfs:label ?droppataDa .
  OPTIONAL {
    ?room sr:hostsMonster ?m ; rdfs:label ?stanzaDrop .
  }
}
```

Lettura: "il portale compare comunque; se qualcuno droppa la chiave, di' chi; e se quel qualcuno sta in una stanza, di' anche dove". L'annidamento conta: la stanza del drop ha senso solo *dentro* il ramo in cui il drop esiste. Due OPTIONAL fratelli avrebbero una semantica diversa (stanze cercate anche senza drop).

Questa query è il prototipo delle domande di progressione: campi vuoti nella tabella = buchi nel design del mondo.

## FILTER e lang()

Le label sono bilingui, quindi ogni `rdfs:label` matcherebbe due volte (una riga per lingua). Il filtro:

```sparql
FILTER(lang(?stanza) = "it" && lang(?bioma) = "it")
```

tiene solo le label italiane. È anche il motivo per cui i letterali con language tag non si confrontano con `= "Cripta 07"` nudo: `"x"@it` e `"x"` sono termini diversi.

## ORDER BY / DESC

`ORDER BY ?piano ?pericolo` (in `01`) ordina la mappa per profondità; `ORDER BY DESC(?rarita)` (in `05` e `06`) mette in cima il loot prezioso. L'ordinamento è dell'output, non del grafo: RDF non ha ordine intrinseco.

## rdflib in pratica

`Graph.query(testo)` esegue la query sul grafo in memoria; il risultato è iterabile per righe, con `result.vars` come intestazioni (usato da `format_table` in `tools/query.py`). I file `.rq` dichiarano i propri `PREFIX`: sono autonomi, eseguibili anche con altri motori (Jena, endpoint SPARQL) senza modifiche.
