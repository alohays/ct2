# CT2 — Claude Code Supplement

Project rules are in `AGENTS.md`. This file covers Claude Code-specific behavior only.

## Session Behavior

- When running as a CT2 role (helm/forge/lens), the role's SKILL.md is authoritative. Do not drift from the persona during a session.
- Delegation within a CT2 session follows the CT2 role system (helm plans, forge implements, lens reviews) — not the global CLAUDE.md subagent delegation rules.

## Plugin Runtime

- **Permissions**: `claude-plugin/settings.json` grants Bash, Read, Write, Edit, Glob, Grep.
- **Heartbeat**: `claude-plugin/.claude-plugin/hooks/hooks.json` — every tool use updates `ct2-${CT2_ROLE}.heartbeat` automatically.
- **Env vars**: `CT2_DIR` (set in plugin settings), `CT2_ROLE` (exported by each SKILL.md). Bash scripts derive `.ct2/` from `$PWD` independently.
- **Skill symlinks**: `install.sh` symlinks `claude-plugin/skills/` to `~/.claude/skills/`. Edits to skill files take effect immediately.

## Git Artifact Hygiene

- Structured CT2 trailers, visible `.ct2/` paths, role footers, and ticket-ID branch names are internal conventions. Do not enable them in host projects unless that repository explicitly wants CT2-branded git artifacts.
