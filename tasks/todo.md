# Todo — M1 (World Core) + M2 (Semantic QA)

Piano dettagliato: `docs/superpowers/plans/2026-07-16-m1-m2-tooling.md`
Spec: `docs/superpowers/specs/2026-07-16-m1-m2-tooling-design.md`

- [x] Task 1: ambiente Python, caricamento grafi e smoke test
- [x] Task 2: validazione pySHACL eseguibile + prefissi SPARQL + boss del santuario
- [x] Task 3: query SPARQL di lettura con CLI e test (chiude query M1)
- [x] Task 4: mondo espanso al target Fase 1 (con esercizio a mano dell'autore)
- [x] Task 5: shape di progressione + 10 casi volutamente rotti (chiude M2)
- [x] Task 6: comandi in CLAUDE.md + retrospettiva

## Review (2026-07-16)

M1 e M2 completate: 21 test verdi, mondo a 10 stanze conforme, 10 casi rotti
intercettati ciascuno dalla propria shape. Dettagli e lezioni in
`docs/notes/06-retrospettiva-m1-m2.md`. Scoperte lungo la strada: violazione
reale su sanctum01, due gap ontologici (portalInRoom, isStartRoom), bug rdflib
su NOT EXISTS{A UNION B} (vedi CLAUDE.md → Comandi → Attenzione).

Prossimo passo naturale: pianificare M3 (simulatore minimale di run) partendo
dalla sezione "Cosa serve per M3" della retrospettiva.
