---
name: dependency-analyzer
description: Review Thea dependency manifests and environment compatibility without changing installed backends.
user-invocable: true
disable-model-invocation: false
---

# Dependency analysis

Follow `AGENTS.md`. Read `pyproject.toml`, `requirements*.txt`,
`docs\setup.md`, and `docs\setup.gpu.md`.

- `requirements.txt` owns common runtime dependencies; packaging reads it.
- CPU/CUDA OpenCV selections remain separate and mutually exclusive.
- Developer tools and optional Git MCP packages have separate manifests.
- Use the compatible shared environment unless backend isolation is required.
  Keep the existing CUDA `.venv` intact; do not reinstall OpenCV as a check.
- Inspect manifests and imports first. Do not install audit tools, request
  package updates, or run network/GPU probes as an automatic review step.
- For requested compatibility/version research, verify official sources and
  distinguish historical setup notes from newly checked evidence.
- Record only relevant compatible versions; never freeze the host environment.
  Validate a dependency change with focused tests; real GPU/media checks require
  explicit authorization.
