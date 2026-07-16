# Nota di studio 06 — Retrospettiva M1 + M2

Chiusura del piano `docs/superpowers/plans/2026-07-16-m1-m2-tooling.md` (spec: `docs/superpowers/specs/2026-07-16-m1-m2-tooling-design.md`).

## Stato raggiunto rispetto a obiettivo.md

- **M1 – World Core: completa.** Mondo al target di Fase 1 (10 stanze su 4 piani, 2 biomi, 3 fazioni, 8 mostri di cui 3 boss, 10 oggetti, 3 quest, 2 NPC, 2 portali), 6 query SPARQL eseguibili con `tools/query.py`, naming e annotazioni bilingui stabili.
- **M2 – Semantic QA: completa.** 11 shape (8 property-based, 3+1 SPARQL-based di progressione), validazione con `tools/validate.py` (exit code da pipeline), 10 casi volutamente rotti in `tests/invalid/` ciascuno agganciato alla propria shape da pytest. 21 test verdi.

Il criterio di successo di Fase 2 — "quando rompo il dataset, il sistema se ne accorge" — è dimostrato dai test, non dichiarato.

## Cosa hanno rivelato i vincoli eseguibili

Ogni passaggio da "scritto" a "eseguito" ha trovato un difetto reale che la lettura umana non aveva visto:

1. **Prefissi SPARQL non dichiarati** (Task 2): le shape SPARQL erano formalmente incomplete (`sh:prefixes` assente); pySHACL le tollerava, altri validatori no.
2. **`ex:sanctum01` pericolosa ma vuota** (Task 2): la prima violazione vera trovata dalla validazione, corretta col Tiranno della Cripta.
3. **Il portale non aveva un luogo, il mondo non aveva un inizio** (Task 4): gap ontologici emersi solo provando a scrivere query di raggiungibilità → `sr:portalInRoom`, `sr:isStartRoom`.
4. **Bug rdflib su `NOT EXISTS { A UNION B }`** (Task 5): violazioni spurie su tutti i portali; diagnosticato con query di probe, riscritto in forma equivalente. Le query delle shape vanno testate come il codice.

## Limiti noti (deliberati)

- `sr:LockKeyCycleShape` intercetta solo il ciclo diretto (fonte della chiave nella stanza sbloccata); i cicli indiretti multi-portale richiedono attraversamento con stato → simulatore (M3).
- `sr:UnreachableRoomShape` misura raggiungibilità topologica, non giocabile: ignora se il portale è apribile.
- Le convenzioni di annotazione (label/comment bilingui) non sono ancora shape: una `sh:severity sh:Warning` è un buon candidato futuro.
- La danger curve non è vincolata (solo il range 1–10 lo è).

## Cosa serve per M3 (Playable Simulation)

- Il **runtime graph** separato dal content graph: `sr:Player`, `sr:currentRoom`, `sr:hasItem`, `sr:isOpen`, `sr:questStatus` (Fase 4 di obiettivo.md anticipata quanto basta).
- Un motore di turni minimale: leggi stato → calcola azioni ammissibili (le query di M1 sono già metà del lavoro: `02-connections` = mosse possibili, `04-lock-key-chain` = porte apribili) → applica transizione → rivalida.
- La simulazione scioglierà i limiti di cui sopra: completabilità vera delle quest e cicli indiretti.
