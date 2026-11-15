---
title: Git Commit Assistant
description: Generate meaningful git commits with proper formatting and message rules
---

# Git Commit Assistant

Follow the inherited workspace policy and `AGENTS.md`.

Invoke by saying: "commit this" or "prepare a commit"

---

## Process:

1. Run `git status --short` to see what's changed
2. Run `git --no-pager diff` and `git --no-pager diff --cached` to review the changes
3. Determine if this should be one commit or multiple (one logical change per commit)
4. Only when a commit was requested, stage the appropriate explicit paths with `git add`
5. Write a commit message following these rules:

## Commit message format:
```
<imperative verb> <concise summary> (< 72 chars)

[optional body: explain WHY, not what — the diff shows what]
[reference issues if applicable: Fixes #123]
```

## Good examples:
```
Add GPU memory monitoring to hardware profiler
Fix off-by-one in stable window merging
Refactor config loader to support custom JSON paths
```

## Bad examples:
```
Updated files          ← too vague
Fixed the bug          ← which bug?
WIP                    ← never commit WIP
changes               ← meaningless
```

## Rules:
- Never commit .env, secrets, or generated files
- Check `git_status` BEFORE and AFTER staging
- If changes span multiple concerns, split into separate commits
