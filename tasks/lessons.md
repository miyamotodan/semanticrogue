# Lessons

Pattern e correzioni ricevute dall'utente, da rileggere a inizio sessione.

## 2026-07-16 — Shell dell'utente: Git Bash, non PowerShell/cmd

L'utente lavora in Git Bash su Windows (prompt `(.venv)` + `bash:`): i comandi
suggeriti con backslash (`.venv\Scripts\python`) falliscono nella sua shell.

**Perché:** in bash il backslash è escape, non separatore di percorso.

**Come applicare:** suggerire sempre comandi con forward slash
(`.venv/Scripts/python`) o, con venv attivo, semplicemente `python`.
