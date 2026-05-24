---
type: spec
title: "CT2 — Versioning and Release Policy"
since: "0.2.0"
---

# CT2 Versioning and Release Policy

CT2 uses Semantic Versioning 2.0. The repository-root `VERSION` file is the
single source of truth for the project version. Plugin manifests, installer
version hints, release tags, and status output must match `VERSION`.

## Version Source

`VERSION` contains exactly one SemVer string:

```text
0.2.0
```

Derived artifacts are synchronized by:

```bash
ct2-release sync
```

The release helper refuses non-SemVer values and keeps the Claude and Codex
plugin manifests aligned with the root version.

## SemVer Rules

After CT2 reaches `1.0.0`:

- **MAJOR** changes are backward-incompatible protocol changes.
- **MINOR** changes are backward-compatible features, optional protocol fields,
  new tools, or default changes with a documented compatibility path.
- **PATCH** changes are bug fixes, documentation fixes, and internal refactors
  that do not change protocol behavior.

While CT2 is in the `0.x` pre-1.0 phase:

- MINOR bumps may include breaking protocol changes.
- PATCH bumps must remain bug-fix-only and must not require migration.
- Any breaking MINOR must document the breakage in `CHANGELOG.md` and ship a
  migration helper once the protocol migration framework exists.

## Protocol Compatibility

Protocol-impacting changes include ticket frontmatter fields, sidecar fields,
state-transition semantics, `.ct2/.meta/` markers, `harness.yaml` schema,
reconciler exit codes, and adapter contracts. The protocol surface catalog
tracks those contracts in `spec/protocol-surface.yaml`.

Each initialized project records its ledger protocol in `.ct2/.protocol-version`
as `MAJOR.MINOR`. PATCH versions never require migration. State-mutating helpers
compare that marker with the installed CT2 protocol before mutating `.ct2/`:

| Project marker | Installed CT2 | Action |
|---|---|---|
| same `MAJOR.MINOR` | same `MAJOR.MINOR` | proceed |
| older `MAJOR.MINOR` | newer `MAJOR.MINOR` | refuse and print `ct2-migrate-<from>-<to>` |
| newer `MAJOR.MINOR` | older `MAJOR.MINOR` | refuse and ask the user to upgrade CT2 |
| missing marker | any | treat as `0.1` |

Breaking protocol changes must include:

- a version bump consistent with this policy;
- a changelog entry under a breaking or changed section;
- migration instructions or a migration helper;
- tests that prove old-protocol fixtures migrate or fail with a clear message.

Migration helpers are named `ct2-migrate-<from>-<to>`, are forward-only,
idempotent, write a `.ct2/.migrations/<timestamp>-<from>-to-<to>.tar.gz`
backup before mutation, log the run, and stamp `.ct2/.protocol-version` only on
full success.

## Release Flow

The supported local release preparation command is:

```bash
ct2-release prepare patch
```

It computes the next version, updates `VERSION`, synchronizes derived artifacts,
promotes `[Unreleased]` into a dated changelog section, and creates one release
commit.

The GitHub release workflow wraps the same command, runs the normal test suite,
creates a `vX.Y.Z` tag, and publishes a GitHub Release from the changelog body.

## Installer Pinning

Users can pin installs to a release tag:

```bash
bash install.sh --version v0.2.0
```

Omitting `--version` installs the latest tagged stable version when one exists,
falling back to `main` only when no stable tag can be discovered.
