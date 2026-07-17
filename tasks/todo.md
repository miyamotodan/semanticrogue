# Todo — M3 (Playable Simulation)

Piano dettagliato: `docs/superpowers/plans/2026-07-17-m3-playable-simulation.md`
Spec: `docs/superpowers/specs/2026-07-17-m3-playable-simulation-design.md`

- [x] Task 1: gap ontologico `sr:npcInRoom`, NPC collocati e shape di collocazione
- [x] Task 2: vocabolario runtime (`ontology/runtime.ttl`) e `load_runtime_world`
- [x] Task 3: `config.toml` + `tools/config.py` (modalità validazione, probabilità combattimento, seed)
- [x] Task 4: query runtime (`queries/runtime/`) e scheletro `Engine` (stato iniziale e letture)
- [x] Task 5: transizioni `move_to` e `open_portal` con completamento quest
- [x] Task 6: transizioni `fight` (probabilistico) e `talk_to`, esito della run
- [x] Task 7: shape SHACL runtime (`shacl/runtime-rules.ttl`) + `validate_runtime` con stati rotti ad arte
- [x] Task 8: CLI `tools/play.py` a turni con autosave, resume e validazione configurabile
- [x] Task 9: run end-to-end vincente e perdente, save rivalidabile a freddo
- [x] Task 10: nota di studio sul runtime graph e documentazione comandi

## Review (2026-07-17)

M3 completata: il grafo RDF è ora anche world state. Costruito un runtime graph
separato dal content graph (`ontology/runtime.ttl`, convenzione "assenza di
tripla = stato di default"), un motore a transizioni pure su triple
(`tools/engine.py`: `move_to`, `open_portal`, `fight`, `talk_to`,
`_check_quest_completion`, `outcome`), query di lettura in `queries/runtime/`,
shape SHACL sullo stato di partita (`shacl/runtime-rules.ttl`, incluso il
pattern dei due `FILTER NOT EXISTS` separati già imparato in M2) e una CLI
a turni con autosave, resume e validazione configurabile (`tools/play.py`,
`config.toml`). Vittoria = prima quest completata; sconfitta = player morto;
exit code 3 dedicato alle violazioni runtime dopo una transizione (bug del
motore, distinto dalle violazioni di contenuto di `tools.validate`).

Suite a 61 test verdi (59 dal piano + un test di regressione in più dal
Task 3, sul seed letto solo a livello top, + un test dalla review finale
sul resume di un salvataggio non conforme). Dettagli architetturali, il ciclo
read→transizione→validazione→serializzazione e cosa la simulazione scioglie
dei limiti dichiarati in M2 (cicli lock-key indiretti, completabilità reale
delle quest) sono in `docs/notes/07-runtime-graph.md`.

Verifica finale: `.venv/Scripts/python -m pytest` → 61 passed;
`.venv/Scripts/python -m tools.validate` → exit 0, dataset conforme.

Prossimo passo naturale: valutare la Fase successiva di `obiettivo.md`
(generazione procedurale) solo dopo aver consolidato M3 con più run giocate
a mano, secondo il principio di sviluppo incrementale del progetto.

## Backlog per M4 (dalla review finale M3)

- Shape di contenuto di unicità per `sr:isStartRoom` (+ caso rotto): indispensabile prima della generazione procedurale.
- `talk_to` dovrebbe chiamare `_check_quest_completion` (caso: quest accettata quando si è già nella target room ripulita).
- `tools/config.py`: guard sui tipi non-tabella (`validation = 5` oggi produce AttributeError/exit 1 invece di exit 2).
