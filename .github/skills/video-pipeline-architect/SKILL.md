---
name: video-pipeline-architect
description: Review Thea module boundaries and pipeline changes against its implemented video-processing contracts.
user-invocable: true
disable-model-invocation: false
---

# Video pipeline architecture

Follow `AGENTS.md`. Use `docs\dev.readme.md` for the verified ownership map and
`docs\analysis.md` for current decisions.

Trace the relevant path in `src\main.py` before proposing a change. The pipeline
downscales for analysis, detects stable windows, and slices the **original**
video. Merge, crop/pan and captioning are separate operations exposed through
Python, CLI and MCP; captioning is not an implicit pipeline/model dependency.
Use `.github\skills\thea-mcp\SKILL.md` for command/tool usage and
`docs\mcp\README.md` for the shared argument contract.

Keep application modules under `src`, shared helpers in `utils`, configuration
under `config`, and module unit tests beside their owners. Prefer existing
functions over a speculative framework or service abstraction.

Preserve source-video ownership, timing/encoding behavior, cache semantics,
selected device, and public arguments. Document intentional changes and their
alternatives in the owning guides and decision table. Use focused mocked unit
tests; do not run real pipelines, GPU checks, or inference automatically.
