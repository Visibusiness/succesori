# Agentul de Succesiune: instrucțiuni pentru Claude Code

Context: `BRIEF.md` (problema, scenariul demo), `docs/ARCHITECTURE.md` (module, flux, reproducere), `README.md` (pornire).

## Agenții proiectului
Definițiile sunt în `.claude/agents/` și se apelează cu Agent tool (`subagent_type`): `case-orchestrator` (primește documente,
apelează API-ul, deleagă), `extractor` (text → JSON cu scor), `case-investigator` (escaladări → propunere pentru operator),
`correspondent` (scrisori în română din datele dosarului), `heir-communicator` (cere moștenitorilor documentele lipsă),
`auditor` (verifică regulile după fiecare rulare), `retro-learner` (actualizează skill-urile din erori și din corecțiile
operatorului), `qa-tester` (testează API-ul, UI-ul în Chromium și predările între agenți, pe un server propriu; raport PASS/FAIL).
Skill-urile învățate: `.claude/skills/*/SKILL.md`. Bucla de învățare: `scripts/retro.py` (eval → retro → eval, păstrăm doar fără regresie).
Trace-uri: `runs/`. Codul (`agent/*.py`, `tests/`) nu e modificat de agenți; propunerile merg în `docs/DECISIONS.md`.

## Reguli
- `pytest -q tests` verde înainte de orice commit.
- Calculele (solduri, stornări, cote, plăți) rămân în funcțiile pure din `agent/rules.py`; LLM-ul doar clasifică și extrage.
- Testele cap-coadă rulează pe o instanță izolată (`scripts/test-instance.sh smoke <port>`), nu pe serverul pe care
  lucrează oamenii: smoke-ul face `POST /demo/reset`.
