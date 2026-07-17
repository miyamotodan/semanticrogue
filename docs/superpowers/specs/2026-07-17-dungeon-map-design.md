# Design: mappa visuale del dungeon dal knowledge graph

Data: 2026-07-17
Stato: approvato

## Obiettivo

Rendere visibile "cosa sta avvenendo nel gioco" senza introdurre geometria né UI:
un tool che esporta la topologia del mondo — e, se disponibile, lo stato della
partita in corso — come diagramma **Mermaid**, renderizzabile ovunque (GitHub,
VS Code, Artifact) senza dipendenze nuove. È il primo passo "visuale" deciso
dopo M3; coordinate e vincoli spaziali restano un'estensione futura.

## Decisioni prese

| Decisione | Scelta | Alternative scartate |
|---|---|---|
| Formato | Mermaid (`flowchart TD`) | Graphviz DOT (richiede binario esterno); HTML interattivo (mini-UI prematura per obiettivo.md) |
| Contenuto | Mondo authored + overlay dello stato runtime se presente | Solo mondo statico (perde "vedere la partita"); solo runtime (inutile senza save) |
| Interfaccia | Tool a sé (`tools/map.py`) + comando `mappa` in `tools/play.py` | Solo tool (mappa non aggiornabile mentre giochi); solo comando in play (perde l'uso da studio) |
| Estrazione dati | Letture rdflib dirette nel modulo (pattern già usato in play.py per letture semplici) | Query SPARQL dedicate in `queries/` (3-4 file con un solo consumatore + vincoli di test senza guadagno); CONSTRUCT verso grafo di presentazione (overkill) |

## Componenti

### `tools/map.py`

- `build_map(world: Graph, state: Graph | None = None) -> str` — funzione pura
  che produce il testo Mermaid:
  - **Stanze** raggruppate in `subgraph` per piano (`sr:floorIndex`), etichetta
    = label italiana; nel nodo anche gli occupanti: mostri (👹, 👑 se `sr:Boss`,
    ☠ se sconfitto nello stato), NPC (🧙), ⭐ se stanza target di una quest
    attiva.
  - **Passaggi** `sr:connectedTo` come archi `---`; **portali** come archi
    tratteggiati `-. 🔒 <chiave> .->` verso `sr:unlocksRoom`, che diventano
    `== 🔓 <chiave> ==>` se `sr:isOpen true` nello stato.
  - **Overlay runtime** (solo con `state`): stanza del player evidenziata via
    `classDef` + 🧝; in coda al diagramma una legenda breve con le quest e il
    loro stato (attive/completate).
- CLI: `python -m tools.map [--data FILE.ttl] [--save FILE.ttl] [-o FILE.md]`
  - senza `--save`: usa `runtime/save.ttl` se esiste, altrimenti solo mondo;
  - senza `-o`: stampa su stdout il blocco ```` ```mermaid ```` pronto da
    incollare; con `-o`: scrive un file markdown completo (titolo + blocco).
  - Errori di parsing → messaggio chiaro su stderr, exit 2 (convenzione repo).

### Comando `mappa` in `tools/play.py`

Comando senza transizione di stato (come `stato`/`valida`): scrive la mappa
della partita corrente con `build_map(eng.world, eng.state)` in un file
`mappa.md` accanto al file di save (`runtime/save.ttl` → `runtime/mappa.md`;
in generale `<dir del save>/mappa.md`), poi stampa il percorso scritto.

## Test (`tests/test_map.py`)

- `build_map(world)` sul mondo authored: contiene le 10 stanze (label
  italiane), i 2 portali con 🔒 e i subgraph dei 4 piani.
- `build_map(world, state)` con stato ad arte (player in `crypt07`,
  `boneWarden` sconfitto, `sealedGate` aperto): compaiono 🧝 sulla stanza
  giusta, ☠ sul mostro, 🔓 sul portale.
- CLI via subprocess: `-o` scrive il file; senza argomenti produce output
  con ` ```mermaid `.
- Comando `mappa` in play: nel flusso CLI esistente (subprocess), crea
  `mappa.md` accanto al save.
- README.md aggiornato con il nuovo tool e il nuovo comando di gioco
  (regola CLAUDE.md).

## Fuori scope (deliberato)

Coordinate e geometria (con relative shape SHACL spaziali: secondo tempo),
export immagine (PNG/SVG), interattività, layout manuale, mappa nella
validazione.
