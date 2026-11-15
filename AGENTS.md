# Thea agent instructions

Apply the parent workspace policy at
`..\.github\instructions\workspace.instructions.md`. These project details
supplement it; they do not override it. Default to RAPID_DEVELOPMENT.

## Repository contract

- Thea analyzes, catalogues and transforms existing footage; video generation is
  out of scope.
- Keep application code in `src\<module>`, unit tests in that module's `tests`,
  real integrations in `src\integration_tests`, and automation in `scripts`.
- Use `utils` for shared helpers, `config` for tracked settings, and `data` for
  generated output. Put machine-specific settings in ignored `*.local.json`.
- Keep docs under `docs`, with root README backlinks. Maintain scoped
  `README.md`/`dev.readme.md` module guides, `docs\analysis.md` decisions, and
  `docs\todo` follow-ups; keep the root README short and linked.
- Use the editable installation and existing imports (`merger`, `tools`,
  `utils`, etc.). Do not add per-file `sys.path` edits or language directories.
- Preserve existing user edits and source videos. Structure changes do not
  authorize changing processing defaults, candidate data, or output contents.

## Environment and validation

Use the shared compatible workspace Python environment by default. The existing
ignored `.venv` is retained as Thea's CUDA/OpenCV isolation exception; never
replace its acceleration stack or switch devices silently. See `docs\setup.md`.

```powershell
python -m pytest -q
python -m ruff check src scripts
python -m main --help
```

Default pytest discovery includes only module unit tests. Mock network,
subprocesses, hardware, real media and model calls there. Real integrations,
full/long suites, dataset loading, GPU probes and inference are opt-in and
require an explicit request; `python -m pytest src\integration_tests` is the
separate integration command, not a routine refactor check.

Run focused tests first. Do not install packages until a manifest changed or a
required validation fails due to a missing dependency. Do not freeze the host
environment or introduce an unrelated audit tool. Report baseline lint failures
separately instead of sweeping unrelated refactors into the task.

## Agent resources

Read `docs\dev.readme.md` for ownership and workflow. Skills and reusable prompts
live in `.github\skills` and `.github\prompts`. `.vscode` contains editor tasks,
debugging settings and MCP **client** configuration, including Thea's root
`mcp_server.py` launcher. The optional server exposes the CLI operations; see
`docs\mcp\README.md` and `.github\skills\thea-mcp\SKILL.md`.
Use built-in tools first; resource files do not authorize enabling
servers, installing tools, exporting repository data or running a model.

`.instructions.md`, `.clinerules`, and `.github\copilot-instructions.md` are
compatibility entry points pointing here, not separate policy copies.
