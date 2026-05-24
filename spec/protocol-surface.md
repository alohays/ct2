---
type: spec
title: "CT2 — Protocol Surface"
since: "0.2.0"
---

# CT2 Protocol Surface

`spec/protocol-surface.yaml` is the machine-readable catalog of protocol
contracts that CT2 scripts read or write. The catalog is intentionally small and
field-oriented in protocol 0.2: ticket frontmatter, sidecar frontmatter, inbox
frontmatter, filesystem markers, and `harness.yaml` keys.

Every entry records:

- a stable `id`;
- a `kind` that identifies the protocol plane;
- a concrete `field` or config key;
- required/default semantics where applicable;
- a stability level and owner.

Compatibility is classified from this catalog:

| Change class | Version impact | Examples |
|---|---|---|
| Compatible | PATCH or MINOR | optional fields, new config keys with defaults, additive tools |
| Breaking | MAJOR; MINOR before 1.0 | required fields, removed fields, changed state semantics, non-overridable default flips |
| Cosmetic | PATCH | docs-only changes or internal refactors outside the catalog |

Entries marked `stable` are covered by the compatibility policy. Entries marked
`unstable` may change before promotion. Anything not listed in the catalog is
internal by default and receives no compatibility guarantee.

Run the audit with:

```bash
ct2-protocol-audit
```

The audit scans `bin/` for known frontmatter/config field access patterns and
fails when a referenced field is missing from the catalog. Future protocol
changes must update the catalog and, when compatibility is broken, include a
matching migration helper and fixture test.
