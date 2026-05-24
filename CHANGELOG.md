# Changelog

All notable changes to CT2 are documented here. The format follows
Keep a Changelog 1.1.0, and the project follows Semantic Versioning 2.0 with
the pre-1.0 compatibility rules documented in `spec/versioning.md`.

## [Unreleased]

### Added

- Added the Protocol Surface catalog, compatibility audit, protocol marker,
  and forward migration helper framework.
- Added `ct2-migrate-0.1-0.2`, `ct2-migrate-0.2-0.3`, and
  `ct2-protocol-audit`.
- Added `trace_hygiene` config for host-clean branch names and PR bodies.
- Added the host-repo cleanliness contract and `ct2-trace-lint` verifier with
  JSON output, baseline suppression, fix suggestions, PR checks, and synthetic
  CI coverage.

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
