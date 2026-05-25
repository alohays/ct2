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

### Changed

- `ct2-helm-canvas generate` now validates the spec shape at the
  boundary; specs with an unknown `priority`, out-of-enum scope state,
  or wrong types for list-shaped fields (`scope`, `tickets`,
  `acceptance_criteria`, `constraints`) are rejected with line-level
  errors instead of producing a half-broken canvas. This is intentional
  tightening — any helm session that was emitting non-canonical
  priorities or scope states will need to align with the documented
  enums.

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
