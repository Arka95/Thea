# Git Commit Assistant

Invoke by saying: "commit this" or "prepare a commit"

---

## Process:

1. Run `git_status` to see what's changed
2. Run `git_diff` to review the actual changes
3. Determine if this should be one commit or multiple (one logical change per commit)
4. Stage appropriate files with `git_add`
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
