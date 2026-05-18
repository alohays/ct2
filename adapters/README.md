# CT2 Adapters

Adapters describe how a host agent runtime performs a CT2 role. The markdown
files in this directory are protocol-facing contracts, not project plans.

Required sections are defined in `spec/adapter-format.md`. Lens adapters must
tell the runtime to write its own sidecar, preserve reviewer independence, call
`ct2-reconcile`, and stop only when no eligible ticket remains for that role.
