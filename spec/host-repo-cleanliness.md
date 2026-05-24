---
type: spec
title: "CT2 - Host-Repo Cleanliness Contract"
since: "0.2.0"
---

# Host-Repo Cleanliness Contract

This contract defines the host repository footprint CT2 is allowed to leave
when running under the default configuration. It is the policy implemented by
`trace_hygiene` defaults and verified by `ct2-trace-lint`.

## Contract v1

When CT2 runs under default configuration:

1. Commits authored through CT2 guidance contain no CT2-specific scope, tag,
   trailer, emoji, or CT2 URL.
2. Branch names contain no CT2 ticket IDs.
3. PR titles and PR bodies contain no human-visible CT2 strings. HTML comments
   used only for internal CT2-to-PR mapping are permitted.
4. No CT2-internal directory, including `.ct2/` and `.ct2/.tmp/`, is staged.
5. CI configuration, hooks, `AGENTS.md`, `CLAUDE.md`, and files under
   `.github/` are not modified by CT2 without explicit user action.
6. The host repository's committed git configuration is not modified by CT2.

Default CT2 initialization writes `.ct2/` to `.git/info/exclude`, not to the
committed `.gitignore`. Projects that want a shared ignore rule can add
`.ct2/` to `.gitignore`; `ct2-trace-lint` treats either location as satisfying
the ignore check.

## Exceptions

The following CT2-identifiable strings can appear by design when the
corresponding GitHub integration is enabled:

- PR review publication markers:
  `<!-- ct2-merge-ready: ... -->` and `<!-- ct2-reconciler -->`.
- GitHub Issue mirror status blocks:
  `<!-- ct2-ticket-status:begin -->` through
  `<!-- ct2-ticket-status:end -->`.
- Hidden PR mapping comments:
  `<!-- ct2-ticket: ... / pr-managed -->`.

The first two exception groups are visible audit trails for the GitHub review
and issue-mirror flows. They are reported only when `ct2-trace-lint` is run
with `--include-exceptions`. Hidden PR mapping comments are allowed because they
do not render in the host PR body.

## Linter Categories

`ct2-trace-lint` reports these categories:

| Category | Surface | Severity |
|---|---|---|
| `commit-scope-ticket-id` | commit subject | error |
| `commit-trailer-ct2-path` | commit body | error |
| `commit-trailer-structured-uninvited` | commit body | warn |
| `pr-title-ct2-token` | PR title | error |
| `pr-body-branded-footer` | PR body | error |
| `pr-body-ct2-path` | PR body | error |
| `branch-name-ticket-id` | local and remote refs | warn |
| `tracked-ct2-dir` | tracked files | error |
| `tmp-leakage` | tracked files | error |
| `gitignore-missing-ct2` | ignore configuration | info |
| `hooks-committed-without-policy` | tracked files | info |
| `agents-md-mentions-ct2-internal` | tracked docs | warn |
| `ci-workflow-references-ct2` | tracked CI config | warn |
| `exception-review-thread-marker` | PR body | info |
| `exception-issue-status-marker` | PR body | info |

## JSON Contract

`ct2-trace-lint --json` emits a stable versioned object:

```json
{
  "version": 1,
  "repo": "/path/to/host",
  "range": "origin/main..HEAD",
  "pr": "7",
  "baseline": "legacy.json",
  "findings": [
    {
      "category": "commit-scope-ticket-id",
      "severity": "error",
      "surface": "commit",
      "message": "Commit subject exposes a CT2 ticket-id scope.",
      "ref": "c0246a1",
      "match": "fix(t-017):",
      "fix": "Rewrite the commit subject without the t-NNN scope, or baseline accepted legacy history.",
      "fingerprint": "8e5e9f8a4e17bb69"
    }
  ],
  "summary": {
    "error": 1,
    "warn": 0,
    "info": 0
  }
}
```

Finding fingerprints are stable for the same category, ref, path, line, and
matched text. `--baseline FILE` accepts a previous JSON result or a JSON array
of fingerprints and suppresses those findings so legacy projects can adopt the
linter without rewriting history.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | No findings at or above the active threshold. |
| 1 | Operational failure, such as not being in a git repo or failed `gh` access. |
| 2 | At least one finding is at or above the active threshold. |

The default threshold is `warn`: `error` and `warn` findings exit 2, while
`info` findings are reported but do not fail the command. `--strict` lowers the
threshold to `info`.

## SemVer Weight

Breaking this contract in a default-state CT2 release is a compatibility event.
After CT2 reaches `1.0.0`, a default-state breach is a major-version event
unless a documented migration path preserves the existing host-repo promise.
