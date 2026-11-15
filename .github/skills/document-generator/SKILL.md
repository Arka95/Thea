---
name: document-generator
description: Update Thea's scoped documentation from verified code and requested changes.
user-invocable: true
disable-model-invocation: false
---

# Documentation maintenance

Follow `AGENTS.md` and `docs\dev.readme.md`.

1. Inspect the relevant code and diff, preserving existing user edits.
2. Update the existing owning module guide, not a parallel document inventory.
   Keep public usage in `docs\<module>\README.md` and internals/config/tests in
   its `dev.readme.md`.
3. Keep the root README limited to purpose, setup, usage, and the linked module
   index. Update architecture/workflow in `docs\dev.readme.md`, decisions in
   `docs\analysis.md`, and verified follow-ups in `docs\todo`.
4. Every document under `docs` links back to root `README.md`. Use readable
   Markdown rather than HTML layout. Keep images and experimental guides scoped.
5. Verify file references, commands and diagram relationships against code.
   Use the diagram skill when available. Do not invent tools, APIs, measured
   timings, release versions or benchmark gains.
6. Documentation-only changes do not require application execution. Never run
   a GPU pipeline or install tools merely to update documentation.
