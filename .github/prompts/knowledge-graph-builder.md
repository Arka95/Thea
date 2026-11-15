---
title: Knowledge Graph Builder
description: Systematically analyze repository structure and build a knowledge graph
---

# Knowledge Graph Builder

Invoke by saying: "build a knowledge graph of this repo" or "map this codebase"

---

Follow `AGENTS.md`. Analyze the repository with built-in read-only tools first.
Use text or a local diagram unless an existing, approved memory integration was
explicitly requested; do not enable a server or export repository content merely
to build a graph.

## Process:

1. **Scan** the top-level directory structure with filesystem tools
2. **Read** README, main entry point, config files, and package manifests
3. **Describe entities** for each significant component:
   - type: module | service | config | test | entry_point | utility
   - observations: purpose, key functions, dependencies, tech used
4. **Describe relations** between entities:
   - depends_on, imports, tests, configures, extends, calls
5. **Summarize** the architecture in 3-5 sentences

## Entity template:
```
name: "ComponentName"
type: "module"
observations: ["purpose in 1 sentence", "key files", "notable patterns"]
```

## Relation template:
```
from: "ComponentA" → relation: "depends_on" → to: "ComponentB"
```

Output the final graph summary as a brief architecture overview.
