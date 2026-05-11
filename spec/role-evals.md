---
type: spec
title: "CT2 - Role Evals"
version: "0.1.0"
---

# CT2 Role Evals

Role evals are regression tests for role definitions, skills, and policy
surfaces. They are not a mechanism for roles to self-modify.

## Layout

Fixtures live under:

- `.ct2/evals/ct2-helm/cases/`
- `.ct2/evals/ct2-forge/cases/`
- `.ct2/evals/ct2-lens-cc/cases/`
- `.ct2/evals/ct2-lens-cx/cases/`

Repo-default fixtures live under `config/evals/` and are copied by `ct2-init`
when a project is initialized or repaired. Eval results are appended to
`.ct2/evals/results.jsonl` and each role's own `results.jsonl`.

## Runner

`ct2-role-eval` runs fixed JSON cases against role definition files. A case has
fixed input, a target file, expected machine-readable output, required strings,
and optional forbidden strings. `--target-override role=/path` lets the harness
prove that an intentional role markdown regression is caught before role prompt
changes are accepted.

## Pass Criteria

An eval must have fixed input, expected machine-readable output, and a clear
failure mode. At least one intentional role regression should be caught before
role prompt changes are accepted.
