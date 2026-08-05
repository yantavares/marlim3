# Copilot instructions

Marlim3 is Petrobras's 1D multiphase flow simulator. Inputs are JSON files (`.mr3`), built and run through the bilingual (EN/PT) Python API (`marlim3.Branch` / `marlim3.Tramo`) or the compiled executable. Authoritative references: [docs/user-guide/](../docs/index.md), [docs/schema_branch.json](../docs/schema_branch.json), [demos/](../demos/simplifiedProduction.mr3), and [tests/README.md](../tests/README.md).

## Simulation agent pipeline

This repo ships custom agents in [.github/agents/](agents/marlim3.agent.md) and skills in `.github/skills/` for building complete simulations. For any "create a simulation" request, prefer delegating to this pipeline instead of improvising:

1. **marlim3** (orchestrator) coordinates everything below and manages the QA fix loop.
2. **marlim3-planner** interviews the user and writes an ADR to `docs/<slug>.adr.md`. It never writes code.
3. **marlim3-specialist** implements the approved ADR: `simulations/<slug>/<slug>.mr3` plus `tests/test_<slug>.py`, following the conventions in `.github/skills/marlim3-testing/SKILL.md`.
4. **marlim3-qa** verifies the implementation against the ADR and writes `docs/<slug>.qa.md` with a PASS/FAIL verdict.

See [README-agents.md](README-agents.md) for the user-facing guide (pt-BR).

## Repo conventions

- Prefer English JSON keys with `"language": "en"` at the root; never mix languages in one file.
- Units: kgf/cm², °C, m, s, sm³/d, angles in radians. Cross-reference and unit rules: `.github/skills/marlim3-json-schema/SKILL.md`.
- Tests use pytest markers `simulacao` (needs the compiled executable, guarded by `executable_exists()`) and `regressao`; run with `uv run pytest tests/ -v`.
- `Branch.simulate()` clears its output directory and writes `<label>.mr3` to the CWD, so always run it inside a temporary directory in tests.
