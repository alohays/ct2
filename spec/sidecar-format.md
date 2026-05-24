---
type: spec
title: "CT2 Sidecar Format"
version: "0.1.0"
---

# CT2 Sidecar Format

Review sidecars are immutable verdict records written by independent reviewers.
They are the only reviewer-authored artifacts the reconciler reads.

## Path

```
.ct2/reviews/{ticket-id}-{cc|cx}-r{round}.md
```

- `ticket-id` is the zero-padded leading ticket id.
- `cc` means the `ct2-lens-cc` role wrote the file.
- `cx` means the `ct2-lens-cx` role wrote the file.
- `round` is the ticket frontmatter `review-round` value at review time.

## Frontmatter

```yaml
---
ticket: 003-refactor-db-pool
reviewer: ct2-lens-cc
round: 1
verdict: rejected
timestamp: 2026-04-13T15:00:00Z
---
```

Required fields:

| Field | Required value |
|---|---|
| `ticket` | Ticket stem, ticket filename, or leading ticket id accepted by conformance tests. |
| `reviewer` | `ct2-lens-cc` for `*-cc-*`; `ct2-lens-cx` for `*-cx-*`. |
| `round` | Integer equal to the reviewed ticket's current `review-round`. |
| `verdict` | `approved` or `rejected`. |
| `timestamp` | UTC ISO8601 timestamp. |

Unknown fields are allowed and ignored by the reconciler.

## Body

The body is human-readable markdown. It must include these headings:

```markdown
## Summary
## Acceptance Criteria Check
## Issues Found
## Recommendation
```

The reconciler does not parse the body. Reviewers use it to explain evidence,
blocking issues, warnings, and remediation.

### Optional PR Inline Fields

`ct2-pr-review` recognizes optional metadata at the top of an issue block:

```markdown
### [BLOCKING] Missing input validation
file: api/handlers/upload.go
line: 142
suggestion: |
  if size > maxUploadBytes:
      raise ValueError("payload too large")

The handler must reject oversized payloads before processing.
```

When `review_publication.inline_comments: true`, `file:` and `line:` cause the
block to be mirrored as an inline GitHub PR review comment. `suggestion:` is
optional and is wrapped in a GitHub suggestion block when present.

## Immutability

Sidecars are immutable after creation. A re-review writes a new sidecar for a
new review round. Hooks and reviews must reject attempts to edit or overwrite an
existing sidecar.

Reviewers publish completed temp files with `ct2-sidecar-publish`. If the
destination sidecar already exists, the helper exits non-zero and leaves the temp
file in place for inspection instead of silently no-oping.

## Independence

A reviewer must not read the matching partner sidecar before writing its own
sidecar for the same ticket round. The partner sidecar may be read only after
the reviewer sidecar exists, normally for reconciliation evidence.
