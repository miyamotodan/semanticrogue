# Nota di studio 04 — Modellazione: quando i dati chiedono nuove proprietà

Concetti emersi nel Task 4 (espansione del mondo al target di Fase 1).

## I gap che l'espansione ha reso visibili

Con 3 stanze il modello sembrava completo. Provando a costruirne 10 con progressione lock-key sono emersi due buchi:

1. **Il portale non aveva un luogo.** `sr:Portal` sapeva cosa richiede (`sr:requiresItem`) e cosa sblocca (`sr:unlocksRoom`), ma non *dove si trova*: impossibile rispondere a "da quale stanza attraverso la Porta Sigillata?". Nuova proprietà: `sr:portalInRoom`.
2. **Nessuna stanza era l'inizio.** Senza un punto di partenza, "questa stanza è raggiungibile?" non è nemmeno una domanda ben posta. Nuova proprietà: `sr:isStartRoom` (booleano).

Lezione generale: i gap di un'ontologia non si vedono leggendola, si vedono **usandola** — scrivendo dati veri e query vere.

## Domain/range non sono vincoli

```turtle
sr:portalInRoom a owl:ObjectProperty ;
  rdfs:domain sr:Portal ;
  rdfs:range sr:Room .
```

In OWL, `rdfs:domain`/`rdfs:range` non *impediscono* nulla: senza reasoner sono documentazione; con un reasoner *inferirebbero* che il soggetto è un portale (anche quando è un refuso!). Chi blocca davvero i dati sbagliati sono le shape SHACL. Da qui la regola del progetto: **ogni proprietà nuova valuta la sua shape** — `sr:portalInRoom` ha guadagnato `sh:minCount 1` in `sr:PortalShape` (un portale senza luogo non è attraversabile), `sr:isStartRoom` solo `sh:maxCount 1` + `sh:datatype` in `sr:RoomShape` (è opzionale, ma se c'è dev'essere un booleano singolo).

## Il pattern: ontologia → shape → dati

L'ordine seguito nel task non è casuale:

1. estendi l'**ontologia** (le proprietà esistono);
2. aggiorna le **shape** (i vincoli le pretendono) — a questo punto la validazione *fallisce* sul dataset esistente (`ex:sealedGate` senza stanza): il rosso è il segnale che il vincolo funziona;
3. aggiorna i **dati** finché la validazione torna verde.

È TDD applicato al knowledge graph: la shape è il test, il dataset è l'implementazione.

## Scelte di naming e stile

- Istanze `ex:` in camelCase con suffisso numerico per gli elementi topologici (`ex:sporeNest02`) e senza per gli unici (`ex:sporeMother`);
- ogni entità ha label e comment bilingui `@it`/`@en`: le query filtrano con `lang()`, le UI future scelgono la lingua;
- il commento è design, non decorazione: "custodisce nel proprio corpo il Cuore di Spore" documenta *perché* `sporeMother dropsItem sporeHeart`.

## Bilanciamento leggibile dal grafo

La danger curve dell'espansione è interrogabile con `01-rooms-overview.rq`: 1→2 al piano 1, 3→4 al piano 2, 5→6 al piano 3, 8 al piano 4. Non è ancora *verificata* da una shape (le shape attuali controllano solo il range 1–10): un possibile vincolo futuro è "il pericolo non decresce scendendo di piano".
