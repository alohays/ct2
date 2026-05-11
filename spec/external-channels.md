---
type: spec
title: "CT2 - External Channels"
version: "0.1.0"
---

# CT2 External Channels

External channels are advisory surfaces. Slack, Discord, Gmail, Notion, cloud
routines, remote-control sessions, and vendor native tasks may notify CT2 roles,
but they do not mutate ticket state.

## Notify-Only Bridge

`ct2-bridge notify` writes inbox messages and telemetry events. It may create
advisory records, evidence artifacts, or patches for review.

## Watchers

Watcher definitions live in `.ct2/watchers/*.json`. They describe notify-only
inputs such as source, recipient role, and allowed actions. Default templates
live under `config/watchers/` and are copied by `ct2-init`. Watchers may wake or
notify roles, but ticket movement remains owned by CT2 scripts.

## Remote Re-entry Protocol

Remote-control or cloud runs re-enter CT2 by producing one of these artifacts:
patch, PR link, inbox message, evidence artifact, or advisory report. A local
CT2 role then decides whether normal scripts should move state. Remote output is
never treated as a reconciler verdict.

## Rules

- External channels never write ticket files directly.
- External commands never move tickets to terminal states.
- Cloud or remote output returns as patch, PR, inbox message, evidence artifact,
  or advisory report.
- Native task graph flow is CT2 to native only; native to CT2 state mutation is
  blocked.
