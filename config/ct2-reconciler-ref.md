# CT2 Reconciler Reference

This project uses the one-shot reconciler:

```bash
ct2-reconcile {ticket-id} {round}
```

Lens roles call it after writing their own sidecar when the partner sidecar
exists. It is safe and idempotent to call when the partner sidecar is missing;
the command exits successfully and leaves the ticket in `in-review/`.

For self-completing cleanup, run discovery mode:

```bash
ct2-reconcile --discover
```

Discovery scans `.ct2/reviews/` for current sidecar pairs and reconciles any
matching ticket still in `in-review/`.

## Authority

`ct2-reconcile` is the only automatic writer of terminal review state. It:

- acquires `.ct2/.meta/{id}-r{round}-reconcile.lock` with `O_EXCL`;
- reads `.ct2/reviews/{id}-cc-r{round}.md` and
  `.ct2/reviews/{id}-cx-r{round}.md`;
- updates `status`, `updated`, `verdict`, and nested `review-status` fields;
- moves the ticket to `done/`, `rejected/`, or `escalated/` with atomic rename;
- sends an escalation message to `ct2-helm` when max review rounds are reached;
- calls `ct2-git-finalize` fail-soft when available.

Set `CT2_RECONCILER_ACTOR=ct2-lens-cc` or `ct2-lens-cx` when a lens invokes the
command so escalation messages preserve the calling role.
