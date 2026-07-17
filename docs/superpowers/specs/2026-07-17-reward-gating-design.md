# Design: reward-gating — una quest non deve premiare la chiave della propria target room

Data: 2026-07-17
Stato: approvato

## Obiettivo

Rendere eseguibile un vincolo di design emerso giocando: una quest non deve dare
come `questReward` l'item che serve ad aprire il portale verso la propria
`questTargetRoom`. È un reward insensato (lo devi già possedere per completare la
quest) e, soprattutto, è il tipo di incoerenza che un generatore di M4 potrebbe
produrre e che la shape statica sui cicli lock-key non intercetta.

Il caso reale: `recoverRelic` ha target `sanctum01` e reward `ivoryKey`, ma
`ivoryKey` è la chiave della Porta Sigillata che sblocca proprio `sanctum01`. Il
mondo resta giocabile solo perché la chiave ha una seconda fonte (drop del
Custode d'Ossa) — ma il design è debole.

Approccio in due parti, coese: prima la shape (a), che sul dataset attuale
**scatta** e rende il mondo non conforme; poi il fix del dataset (b), che rimette
il mondo conforme con un reward sensato. La storia git dimostra il criterio di
M2: "quando rompo il dataset, il sistema se ne accorge".

## Parte 1 — Shape SHACL di contenuto

Nuova shape SPARQL-based `sr:QuestRewardNotGatingKeyShape` in
`shacl/rogue-rules.ttl`, target `sr:Quest`, stile delle SPARQL-based esistenti
(`sh:prefixes sr:RogueShapes`, `sh:message` bilingue).

### Definizione del vincolo

Una quest `$this` viola se il suo `questReward` è l'item richiesto
(`requiresItem`) da un portale la cui `unlocksRoom` è la `questTargetRoom` della
quest stessa. Un solo basic graph pattern, nessun `NOT EXISTS`/`UNION` (nessun
rischio del bug rdflib noto):

```sparql
SELECT $this
WHERE {
  $this sr:questReward ?item ;
        sr:questTargetRoom ?target .
  ?portal sr:requiresItem ?item ;
          sr:unlocksRoom ?target .
}
```

Portata deliberatamente mirata al **gating esplicito** (chiave di un portale che
sblocca la target), non al calcolo di tutti i cammini di accesso: è il vero
problema di design ed è verificabile in modo semplice e robusto.

### Caso rotto permanente

`tests/invalid/quest-reward-gating-key.ttl`: micro-mondo con una quest il cui
reward è la chiave del portale che sblocca la sua target room. Registrato in
`BROKEN_CASES` di `tests/test_validation.py` con focus node la quest e shape
attesa `sr:QuestRewardNotGatingKeyShape`. Il micro-mondo soddisfa le altre shape
(stanze con bioma/dangerLevel/floorIndex, portale ben formato, item con rarità)
per non far scattare violazioni diverse da quella attesa.

## Parte 2 — Fix del dataset

In `dataset/dataset.ttl`:

- Nuovo item dedicato `ex:sanctumRelic` — "Reliquia del Santuario" / "Sanctum
  Relic", `sr:rarity 5`, annotazioni bilingui (`rdfs:label`/`comment` `@it`/`@en`).
  Provenienza univoca: solo reward di `recoverRelic` (nessun drop), narrativamente
  coerente con "recuperare una reliquia nel Santuario".
- `ex:recoverRelic sr:questReward` passa da `ex:ivoryKey` a `ex:sanctumRelic`.

Dopo il fix il mondo è conforme a tutte le shape, inclusa la nuova.
`ex:ivoryKey` resta ottenibile come drop del Custode d'Ossa, quindi
`recoverRelic` resta completabile (verificato giocando end-to-end).

## Test

- `tests/invalid/quest-reward-gating-key.ttl` intercettato da
  `sr:QuestRewardNotGatingKeyShape` (nuovo caso in `BROKEN_CASES`).
- `test_authored_dataset_conforms` passa **dopo** il fix del dataset (prova che il
  mondo rispetta il nuovo vincolo). Tra il commit della shape e quello del fix il
  dataset è volutamente non conforme.
- README aggiornato: conteggio test 84 → 85.

## Fuori scope (deliberato)

- Accessi alternativi alla target room (`connectedTo` che aggiri il portale): la
  definizione mira al gating esplicito, non ai cammini completi.
- Reward ridondanti in generale (item che il player possiede già per altre vie):
  solo il caso specifico "chiave di gating della propria target".
