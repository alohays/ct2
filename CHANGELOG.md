# Changelog

All notable changes to CT2 are documented here. The format follows
Keep a Changelog 1.1.0, and the project follows Semantic Versioning 2.0 with
the pre-1.0 compatibility rules documented in `spec/versioning.md`.

## [Unreleased]

### Added

- Added spec ingest and render-side guardrails for the helm canvas. New
  helpers `parse_spec` and `validate_spec` in `bin/_ct2_canvas.py` give
  malformed canvas specs an actionable error (line/column, an excerpt of
  the offending region, named hints for smart quotes, trailing commas,
  and `//` or `/*` comments). The inline `window.CANVAS` config and any
  user-pasted content are now safe against `</script>`, comment-marker,
  and rich-HTML injection; a JS render error surfaces a visible banner
  next to the JSON preview instead of silently blanking the AI judgment
  panel.
- Release commits prepared by `release.yml` now include a `Co-Authored-By`
  trailer pointing at the workflow trigger user. A new repeatable
  `--co-author "Name <user@example.com>"` flag on `ct2-release prepare`
  validates the trailer shape (rejecting embedded `\r`/`\n` and missing
  brackets/`@`) and dedupes repeats; the workflow wires it through
  `${{ github.actor }}` and `${{ github.actor_id }}` via env-var
  indirection.
- Added the 2026-06 dynamic-workflow-era strategy set: the flagship
  position note `docs/ct2-dynamic-workflow-strategy-2026-06.md` (with its
  HTML decision report), the 2026-06 agent-platform feature radar, and the
  agentic-harness trends survey. CT2 is positioned as the verification
  kernel that native workflows must re-enter; the README product-planning
  index links all four.
- Added the runtime-workflow row to the protocol reframe's Boundary
  Decision Table and a Native Workflows rule to `spec/adapter-format.md`:
  adapters may author or invoke native workflows as executors, but a
  workflow never holds terminal authority and the contract is
  vendor-neutral.
- Added the workflow re-entry contract to `spec/conformance.md`: a
  CT2-wrapped workflow run names a ticket, writes only into an isolated
  write target, returns as a patch, PR, inbox message, or evidence
  artifact, keeps its subagents non-role-holding, and leaves authoritative
  CT2 writes to the parent role.
- Added the reviewer-independence prompt-construction invariant to
  `spec/conformance.md` — a verifier subagent's prompt must not contain
  any sibling reviewer's output — with a conformance fixture that fails a
  leaky verify workflow.
- Added the vendor-symmetry guard: the dual-review quorum floor is
  cross-vendor (lens-cc AND lens-cx), never any-2, with a conformance
  check that flags Claude-primary drift.
- Added a CT2-blessed adversarial-verify workflow template under
  `templates/workflows/` that wires reviewer independence by construction.
- Added a network-free workflow-class capability probe to
  `ct2-runtime-doctor`; absence degrades to the serial fallback and never
  errors.
- Added optional `parent_id`/`produced_by_agent` attribution to
  `claims.jsonl` evidence records so fan-out findings roll up to the
  orchestrating role and ticket.
- Added per-run agent count and a fan-out-vs-serial speedup signal to the
  Cost-Latency scorecard axis; budget directives are recorded as advisory
  fan-out width, never enforced as token ceilings.
- Added the M-of-N reviewer-quorum specification with cross-vendor 2-of-2
  (cc AND cx) as the immovable floor; extra same-vendor skeptics are
  advisory unless explicitly promoted.
- Added the workflow determinism boundary: CT2 time/round circuit breakers
  and ID generation run outside deterministic workflows, and CT2-emitted
  scripts derive IDs from stable inputs.
- Added fail-soft native-surface delegation: lens-cc may cite
  `/code-review ultra` in-sidecar and helm discovery may invoke
  `/deep-research`, as evidence only — neither can move a ticket.

### Changed

- `ct2-helm-canvas generate` now validates the spec shape at the
  boundary; specs with an unknown `priority`, out-of-enum scope state,
  or wrong types for list-shaped fields (`scope`, `tickets`,
  `acceptance_criteria`, `constraints`) are rejected with line-level
  errors instead of producing a half-broken canvas. This is intentional
  tightening — any helm session that was emitting non-canonical
  priorities or scope states will need to align with the documented
  enums.
- Re-pinned documented runtime baselines to observed capability rather
  than guessed versions; Codex stable is 0.137.0 (2026-06-04) and CT2's
  serial-by-default, no-fan-out-for-state-writes stance is unchanged
  against Codex multi-agent v2.

### Fixed

### Deprecated

### Removed

### Security

## [0.3.0] - 2026-05-25

### Added

- Added the Protocol Surface catalog, compatibility audit, protocol marker,
  and forward migration helper framework. New specs: `spec/PROTOCOL.md` and
  `spec/protocol-surface.md`.
- Added `ct2-migrate-0.1-0.2`, `ct2-migrate-0.2-0.3`, and
  `ct2-protocol-audit`. Migration helpers write atomic
  `.ct2/.migrations/<stem>.tar.gz` backups and fall back to `shutil.copy2`
  on cross-device `os.link` failures.
- Added `trace_hygiene` config for host-clean branch names and PR bodies and
  `ct2-trace-hygiene-migrate` for switching between `clean` and
  `legacy-branded` presets.
- Added the host-repo cleanliness contract (`spec/host-repo-cleanliness.md`)
  and `ct2-trace-lint` verifier with JSON output, baseline suppression, fix
  suggestions, PR checks, and synthetic CI coverage. Hook adoption is
  opt-in via `ct2-init --install-trace-hook` / `--uninstall-trace-hook` and
  is versioned with `# ct2-trace-hook: v2` for safe upgrades.
- Added the fail-soft GitHub Issue mirror (`ct2-issue-mirror`,
  `ct2-issue-adopt`, `ct2-issue-reconcile`, and `ct2-issue-bootstrap-labels`)
  with ticket frontmatter links, lifecycle label/status-block updates,
  one-shot label bootstrap via `ct2-init --bootstrap-issue-labels`, redacted
  `gh` stderr in pending JSON, and `Closes #<issue>` PR body linkage.
- Added PR-thread review publication helpers (`ct2-pr-review`,
  `ct2-pr-merge-ready`, `ct2-pr-respond`) that mirror sidecars to GitHub PR
  reviews, merge-ready markers, response TODOs, and reconciler summary
  comments. Inline review payloads are sent over stdin, existing
  `<!-- ct2-review: ... -->` and `<!-- ct2-reconciler -->` markers are
  detected to keep publication idempotent, and full `github.com` PR URLs
  are required for inline API calls.

### Changed

- State-mutating helpers now check `.ct2/.protocol-version` before mutating.
  Marker-less legacy ledgers are treated as protocol `0.1` and must run
  `ct2-migrate-0.1-0.2` before continuing.
- Fresh project defaults no longer render visible CT2 ticket paths, numeric
  ticket IDs, role footers, or emoji in host-visible branch and PR artifacts.
  Existing projects without `trace_hygiene` keep legacy behavior.

### Fixed

### Deprecated

### Removed

### Security

## [0.2.0] - 2026-05-24

### Added

- Documented the release train, single version source, and SemVer policy.
- Added release automation scaffolding for manifest synchronization, changelog
  promotion, and GitHub Release creation.

### Fixed

- Sealed ticket baselines are snapshotted at seal time and can be backfilled
  for legacy tickets.
- Review lifecycle recovery and duration breaker safeguards are now covered by
  local regression tests.

## [0.1.0] - 2026-04-01

### Added

- Initial public CT2 protocol implementation with file-backed tickets,
  dual-review sidecars, role skills, and local conformance checks.
