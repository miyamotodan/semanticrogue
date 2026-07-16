# Nota di studio 01 — RDF e Turtle

Concetti usati nel Task 1, con esempi presi da `dataset/dataset.ttl`.

## La tripla: soggetto, predicato, oggetto

RDF rappresenta tutto come triple *soggetto → predicato → oggetto*. Questa riga del dataset:

```turtle
ex:crypt07 sr:dangerLevel 4 .
```

è la tripla: soggetto `ex:crypt07`, predicato `sr:dangerLevel`, oggetto `4`. Un grafo RDF è semplicemente un insieme di triple; i nodi sono soggetti/oggetti, gli archi sono i predicati.

## IRI e prefissi

Ogni risorsa è identificata da un IRI completo. Scrivere IRI interi è illeggibile, quindi Turtle usa i prefissi dichiarati in testa al file:

```turtle
@prefix sr: <http://example.org/semantic-roguelike#> .
@prefix ex: <http://example.org/id/> .
```

`ex:crypt07` è un'abbreviazione di `http://example.org/id/crypt07`. Nel progetto la separazione è una regola precisa:

- `sr:` — il **vocabolario**: classi (`sr:Room`) e proprietà (`sr:dangerLevel`), definite in `ontology/rogue.ttl`;
- `ex:` — le **istanze**: gli individui concreti del mondo (`ex:crypt07`, `ex:boneWarden`), definiti in `dataset/dataset.ttl`.

Così Model e Content restano moduli distinti anche a livello di namespace.

## La scorciatoia `a`

```turtle
ex:crypt07 a sr:Room ;
```

`a` è sintassi Turtle per `rdf:type`: "crypt07 è un'istanza della classe Room". È la tripla più importante del dataset: tutto ciò che le shape SHACL bersagliano (`sh:targetClass`) parte dai tipi.

## `;` e `.`

Il punto e virgola ripete il soggetto, il punto chiude:

```turtle
ex:hall08 a sr:Room ;
  sr:dangerLevel 3 ;
  sr:floorIndex 2 .
```

sono tre triple con lo stesso soggetto `ex:hall08`.

## Letterali: tipizzati e con lingua

L'oggetto di una tripla può essere un letterale invece che una risorsa:

- `sr:dangerLevel 4` — il `4` nudo in Turtle è uno `xsd:integer` implicito; le shape lo verificano con `sh:datatype xsd:integer`;
- `rdfs:label "Cripta 07"@it` — letterale con **language tag**. La stessa risorsa ha anche `"Crypt 07"@en`: non è duplicazione, sono due triple distinte, e le query possono filtrare con `lang(?l) = "it"`.

## rdflib: `Graph.parse()` e la fusione dei grafi

In `tools/common.py`:

```python
g = Graph()
g.parse(path, format="turtle")
```

`parse()` legge un file Turtle e **aggiunge** le sue triple al grafo (non lo sostituisce): chiamarlo due volte su file diversi fonde i grafi. È il motivo per cui `load_world()` restituisce più triple del solo dataset: contiene anche l'ontologia. Questa fusione non è un dettaglio: le shape SHACL e le query con `rdfs:subClassOf*` funzionano solo se le triple del vocabolario (es. `sr:Boss rdfs:subClassOf sr:Monster`) sono nello stesso grafo dei dati.
