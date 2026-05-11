# CT2 Agent Platform Feature Radar

조사 기준일: 2026-05-10 KST / 2026-05-09 US
대상: OpenAI Codex CLI/App/App Server, Anthropic Claude Code/Agent SDK/Desktop/Web
목적: Codex와 Claude Code의 최신 릴리스, 공식 문서, 로컬 설치 상태를 근거로 CT2의 다음 제품 방향을 제안한다.

문서 세트 안에서의 역할: 이 문서는 **Verified Autonomy OS의 vendor-surface map**이다. 즉 "무엇이 가능한가", "어떤 기능이 안정/실험/미성숙인가", "CT2 protocol kernel로 흡수할 때 어떤 guardrail이 필요한가"를 정리한다. 실행 순서와 최종 제품 전략은 `docs/ct2-verified-autonomy-os-strategy-2026-05.md`가 canonical로 잡고, 본 문서는 그 전략의 증거 지도와 후보 backlog 역할을 한다.

## Executive Summary

CT2는 이미 Codex 0.128.0의 `/goal`, app-server, request-input, plugin/skill 표면을 상당히 흡수했다. 이번 조사 기준으로 로컬 Codex는 `codex-cli 0.130.0`이고 최신 안정 릴리스도 0.130.0이다. GitHub에는 0.131.0-alpha 프리릴리스가 보이지만 CT2 기준선으로 삼을 안정 릴리스는 아니다. 로컬 Claude Code는 업데이트 후 `2.1.138`이며 공식 changelog 최신과 일치한다. 이로써 Claude Code의 worktree 기준점, hook effort 입력, subagent skill discovery fixes, AskUserQuestion multi-select, CronList, MCP/connector 안정성, OTel survey, auto-mode hard deny, Remote Control CLI 표면을 CT2가 바로 기준선으로 삼을 수 있다.

가장 큰 제품 기회는 세 가지다.

1. **CT2를 파일 기반 kanban에서 runtime-aware control plane으로 확장**한다. `.ct2/`는 계속 source of truth로 유지하되, Codex app-server/remote-control과 Claude Agent SDK/Remote Control/Channels를 CT2가 관찰하고 재개할 수 있는 런타임 계층으로 모델링한다.
2. **질문, 승인, 스케줄, 모니터링을 CT2 프로토콜로 정규화**한다. Codex `item/tool/requestUserInput`, Claude `AskUserQuestion`, Claude `CronCreate/CronList/CronDelete`, Claude Monitor, Codex app Automations를 모두 `.ct2/decisions/`, `.ct2/watchers/`, `.ct2/runtime/`으로 흡수한다.
3. **리뷰 독립성과 안전성을 hook/package 레벨에서 강제**한다. Codex hooks와 Claude hooks가 모두 안정적/문서화된 표면을 갖고 있으므로, "lens가 상대 sidecar를 먼저 읽지 않는다", "state transition은 `mv`만 쓴다", "reviewer는 source를 쓰지 않는다"를 텍스트 지침이 아니라 실행 전후 검증으로 끌어올릴 수 있다.

더 큰 제품 thesis는 이것이다. **CT2는 agent orchestration tool이 아니라 Verified Autonomy OS가 되어야 한다.** 단, 여기서 OS는 보편적 agent OS가 아니라 CT2의 file-first dual-review workflow를 보호하는 **protocol kernel**이다. Claude와 Codex가 각자 더 강력한 runtime, scheduler, UI, cloud delegation을 갖게 될수록 CT2의 가치는 "실행" 자체가 아니라 "실행이 신뢰 가능한 증거와 상태 전이로 귀결되게 하는 kernel"에 있다.

본 문서만 놓고 보면 권장 순서는 P0 Capability Registry, P0 Decision Bridge, P0 Hook Guardrails, P0 Runtime Twin, P1 Watch/Monitor Plane, P1 App-Server/SDK Driver Hardening, P1 Evidence Graph, P1 Dual Plugin Distribution, P2 Multimodal Evidence, P2 Cloud/Remote Delegation이다. 최종 통합 전략에서는 이를 한 단계 더 좁혀 **Registry+Baseline -> Role Contracts -> Plan Evidence -> Role Evals -> Ambient Advisory Bridge -> Native Mirror** 순서로 실행한다.

## Evidence Base

로컬 확인:

| 항목 | 결과 | 제품적 의미 |
|---|---:|---|
| `codex --version` | `codex-cli 0.130.0` | 현재 CT2 Codex 기준을 0.128.0에서 0.130.0으로 재검토해야 한다. |
| `codex features list` | `apps`, `browser_use`, `computer_use`, `hooks`, `image_generation`, `multi_agent`, `plugins`, `tool_search`, `tool_suggest`, `tool_call_mcp_elicitation`, `unified_exec` stable enabled. `goals` experimental enabled. `default_mode_request_user_input` under development disabled. | goal은 사용 가능하지만 request-input은 여전히 profile/preflight gate가 필요하다. hooks와 multi_agent는 CT2가 더 적극적으로 활용할 수 있다. |
| `codex app-server generate-json-schema --experimental` | `thread/goal/*`, `thread/turns/list`, `hooks/list`, `plugin/read`, `fs/watch`, `model/list`, `experimentalFeature/list`, `item/tool/requestUserInput`, `remoteControl/status/changed`, image input/generation/view schema 확인. | CT2 app-driver의 역할을 "turn 실행"에서 "runtime inventory + event subscription + filesystem watch"로 확장할 근거가 있다. |
| `claude --version` | `2.1.138 (Claude Code)` | 로컬 Claude가 공식 최신 changelog와 일치한다. CT2 Claude 기준선을 최신 scheduler/hook/remote-control fixes 이후로 올릴 수 있다. |
| `claude --help` | `--agent`, `--agents`, `--worktree`, `--tmux`, `--json-schema`, `--max-budget-usd`, `--remote-control`, `--remote-control-session-name-prefix`, `--include-hook-events`, `agents`, `auto-mode`, `plugin`, `ultrareview` 확인. | CT2 Claude roles도 native subagent/worktree/headless JSON/remote control 표면을 활용할 수 있다. |
| `claude mcp list` | Google Drive, PDF Viewer, Gmail, Slack, Notion, Context7, Discord connected. | CT2가 "available connectors"를 status/preflight에 노출하고 role별 MCP policy를 만들 수 있다. |

공식 출처:

- OpenAI Codex docs index: https://developers.openai.com/codex/llms.txt
- OpenAI Codex changelog: https://developers.openai.com/codex/changelog
- OpenAI Codex 0.130.0 GitHub release: https://github.com/openai/codex/releases/tag/rust-v0.130.0
- OpenAI Codex feature maturity: https://developers.openai.com/codex/feature-maturity
- OpenAI Codex app-server: https://developers.openai.com/codex/app-server
- OpenAI Codex automations: https://developers.openai.com/codex/app/automations
- OpenAI Codex hooks: https://developers.openai.com/codex/hooks
- OpenAI Codex subagents: https://developers.openai.com/codex/subagents
- OpenAI Codex plugins: https://developers.openai.com/codex/plugins
- Claude Code docs index: https://code.claude.com/docs/llms.txt
- Claude Code changelog: https://code.claude.com/docs/en/changelog
- Claude Code scheduled tasks: https://code.claude.com/docs/en/scheduled-tasks
- Claude Agent SDK user input: https://code.claude.com/docs/en/agent-sdk/user-input
- Claude Code tools reference: https://code.claude.com/docs/en/tools-reference
- Claude Code monitoring: https://code.claude.com/docs/en/monitoring-usage
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code hooks: https://code.claude.com/docs/en/hooks

문서 상태:

| Product | Official docs shape | Freshness signal | CT2 interpretation |
|---|---|---|---|
| Codex | `llms.txt` index plus `llms-full.txt`; each Codex page has a Markdown twin. | Changelog and GitHub release both show Codex CLI 0.130.0 on 2026-05-08; 0.131.0-alpha exists as pre-release. | Use 0.130.0 as the implementation baseline. Track alpha only as a forward-looking signal. |
| Claude Code | `llms.txt` index across CLI, Desktop, Web, Agent SDK, hooks, MCP, plugins, monitoring, scheduling; changelog generated from GitHub. | Changelog latest is 2.1.138 on 2026-05-09; local install is now 2.1.138. | Treat 2.1.138 as the local planning baseline; still version-gate features for other users. |
| CT2 repo | `spec/` is authoritative; existing Codex PRD/runtime contract target 0.128.0+. | README already documents Codex goals, app-driver, doctor, plugin, and skill roles. | New planning should not rewrite spec immediately; convert proposals into tickets first. |

## Current CT2 Baseline

이미 구현/문서화된 것:

- `spec/codex-full-support-prd.md`와 `spec/codex-runtime-contract.md`가 Codex `/goal`, app-server, request-input, skills/plugins, preflight, subagent guardrail을 정의한다.
- `ct2-codex-doctor`가 Codex version, features, app-server schema, request-input, MCP, skills를 점검한다.
- `ct2-codex-goal`이 CT2-local goal metadata와 scope/audit를 만든다.
- `ct2-codex-app-driver`가 app-server stdio thread/goal/turn/request-input 일부를 다룬다.
- Codex skills는 `ct2-helm`, `ct2-forge`, `ct2-lens-cx`, `ct2-helm-auto-cx`, `ct2-status`로 이미 나뉘어 있다.
- `ct2-lens-cx-tui`는 visible Codex reviewer loop를 제공하고, `ct2-lens-cx-daemon`은 headless fallback을 제공한다.

아직 약한 부분:

- Claude Code의 최신 native scheduler, Monitor, AskUserQuestion, channels, OTel, Remote Control, subagent worktree isolation을 CT2 protocol로 흡수하지 못했다.
- Codex 0.130.0의 `remote-control`, `thread/turns/list`, `fs/watch`, `plugin/read`, hook metadata를 CT2 app-driver가 충분히 활용하지 않는다.
- Hook 기반 enforcement가 없다. 현재 reviewer independence와 atomic transition은 주로 역할 지침과 script convention에 의존한다.
- `.ct2/`에는 runtime feature/capability registry가 없어서 "이 프로젝트에서 어떤 agent runtime 기능을 안전하게 쓸 수 있는가"가 매번 암묵적이다.
- 스케줄/모니터링은 `ct2-lens-cx-tui`의 tmux scheduler가 중심이고, provider-native scheduled tasks와 event channels는 미통합이다.

## Product Thesis

CT2의 차별점은 "agent가 알아서 한다"가 아니라 "agent work가 검증 가능한 protocol로 남는다"이다. 따라서 새로운 Codex/Claude 기능은 CT2 내부 상태를 대체하면 안 된다. 대신 다음 네 가지 계층으로 흡수해야 한다.

| 계층 | CT2 역할 | 흡수할 vendor 기능 |
|---|---|---|
| State plane | ticket, sidecar, inbox, ledger의 authoritative state | 유지. vendor runtime state는 advisory. |
| Runtime plane | session/thread/agent/worktree/goal/schedule/monitor metadata | Codex app-server/remote-control, Claude Agent SDK/session/remote-control/worktree. |
| Decision plane | human clarification, approvals, policy block, escalation | Codex requestUserInput, Claude AskUserQuestion, approval callbacks/hooks. |
| Observation plane | heartbeat, OTel, logs, filesystem watch, PR/CI status | Claude Monitor/Cron/OTel/Channels, Codex fs/watch/OTel/Automations. |

통합 전략과의 합의:

- **Authority:** `.ct2/` ticket, sidecar, inbox, ledger가 state authority다. Vendor runtime은 advisory signal만 제공한다.
- **Scope:** Verified Autonomy OS는 protocol kernel이다. 보편적 cloud agent OS, SaaS orchestration, Jira/Linear 대체재가 아니다.
- **Measurement:** 단일 north star 대신 balanced scorecard를 쓴다: Trust, Evidence, Autonomy, Cost/Latency.
- **Execution:** 본 문서의 feature radar는 backlog 후보를 넓게 유지하되, 실제 6주 실행은 Capability Registry와 baseline 측정으로 시작한다.

## North Star: Verified Autonomy OS

CT2의 장기 제품 형태는 "여러 에이전트를 띄우는 도구"가 아니라 "에이전트 실행을 운영체제처럼 관리하는 검증 계층"이다. OS 비유를 쓰면 다음처럼 정리된다.

| OS primitive | CT2 equivalent | Vendor features to bind |
|---|---|---|
| Process table | active roles, sessions, threads, goals, monitors, schedules | Claude `agents`, `--remote-control`, `/tasks`; Codex app-server `thread/list`, `thread/loaded/list`, remote-control status |
| Filesystem | tickets, sidecars, inbox, ledgers, artifacts | `.ct2/` atomic state tree |
| Syscalls | seal, revise, submit, reconcile, ask, watch, audit | CT2 CLI commands plus Codex/Claude SDK adapters |
| Scheduler | watcher plane and autonomy SLA | Claude Cron/Monitor/Routines, Codex Automations/fs.watch |
| Permission model | role-bound reads/writes and approval policy | Claude permissions/auto-mode hard deny/hooks; Codex sandbox/requirements/hooks |
| Flight recorder | telemetry ledger and evidence graph | Claude/Codex OTel, stream-json, app-server events, hook events |
| Device drivers | provider-specific runtime drivers | Codex app-server/remote-control, Claude Agent SDK/CLI/Remote Control |

이 관점에서 CT2의 product promise는 다음 한 문장으로 압축된다.

> "Any agent can act, but only verified evidence can move state."

## Second-Order Insights

1. **질문 기능은 UX가 아니라 state transition blocker다.** Codex requestUserInput과 Claude AskUserQuestion은 "대화 편의"가 아니라 불명확한 요구사항을 CT2 state machine 안에서 멈추고, 답변을 audit trail로 남기게 하는 decision primitive다.
2. **스케줄러는 polling 대체재가 아니라 autonomy budget manager다.** `/loop`, Cron, Monitor, Automations는 반복 실행 자체보다 "언제 더 돈을 써도 되는가", "언제 조용히 있어야 하는가", "언제 인간에게 escalate해야 하는가"를 표현해야 한다.
3. **Hooks는 policy enforcement와 product analytics가 만나는 지점이다.** 단순히 위험 명령을 막는 것을 넘어, 왜 role이 멈췄는지, 어떤 invariant가 자주 위반되는지, 어느 ticket type이 review churn을 만드는지 측정할 수 있다.
4. **Subagents는 CT2 roles가 아니다.** Subagent는 role 안에서 쓰는 CPU core에 가깝다. CT2 role이 state write를 소유하고, subagent는 bounded read/patch/evidence만 반환해야 한다.
5. **Images/browser/computer use는 "UI evidence pipeline"이 될 때만 CT2에 중요하다.** 이미지 생성 자체보다 before/after screenshot, viewport matrix, visual diff, reviewer annotation이 sidecar와 연결되는 것이 핵심이다.
6. **Remote/cloud runtimes는 state authority를 더 위험하게 만든다.** remote control, web sessions, routines, Codex cloud는 강력하지만 `.ct2/` 밖에서 일이 벌어진다. CT2는 remote executor를 받아들이되, remote output을 ticket/PR/inbox/evidence로 재수렴시키는 re-entry protocol이 필요하다.
7. **최고의 CT2 UX는 dashboard가 아니라 "불안 제거"다.** 사용자는 agent가 많이 돈다는 사실보다, 무엇이 막혔고 무엇이 검증됐고 무엇이 아직 위험한지 즉시 알고 싶다.

## Codex Feature Radar

| Capability | Current state | CT2 opportunity | Priority |
|---|---|---|---|
| `/goal` | Already adopted in CT2. Still experimental in Codex feature maturity terms. | Keep as role-local continuation only. Add explicit goal health in `ct2-status`: active, paused, budget-limited, stale, schema-compatible. | P0 maintain |
| `codex remote-control` | 0.130.0 adds a simpler headless app-server entrypoint. | Replace tmux-only background control with a `ct2-codex-remote` driver for long-lived lens/forge/status sessions. Store connection status from `remoteControl/status/changed`. | P1 |
| App-server thread paging | 0.130.0 lets clients page large threads with unloaded/summary/full item views. | `ct2-codex-app-driver` should stop loading full transcripts by default. Use summary views for status and audit, full views only for evidence extraction. | P0 |
| App-server `fs/watch` | Schema exposes watch/unwatch/change notifications. | Build `.ct2/watchers/` so CT2 can wake reviewers when tickets enter `in-review/`, not only poll. | P1 |
| App-server `plugin/read`, `hooks/list` | Schema exposes plugin details and hook summaries. 0.130.0 release highlights bundled hook visibility. | `ct2-codex-doctor` should verify CT2 plugin bundled skills/hooks instead of checking only skill symlinks. | P0 |
| `experimentalFeature/list` | App-server exposes feature flags with stage metadata. | Replace parsing of `codex features list` text with structured app-server inspection when available. Use stage to block under-development features from default paths. | P0 |
| `requestUserInput` | Schema available, but local `default_mode_request_user_input` disabled. | Build provider-neutral `.ct2/decisions/` and only use runtime request UI when available; otherwise write inbox blocked/clarification. | P0 |
| Hooks | Stable feature flag locally. Official docs say hooks can intercept Bash/apply_patch/MCP paths, with limitations. | Codex hook package for CT2 invariants: forbid reviewer source writes, forbid partner sidecar reads before own sidecar, validate state transitions, surface warnings to app-server/TUI. | P0 |
| Plugins | Stable locally. 0.130.0 improves plugin hook metadata and sharing discoverability. | Ship CT2 as a real Codex plugin with skills, hooks, optional MCP, display metadata, dependency hints, and marketplace entry. | P1 |
| Subagents | Stable locally and enabled by default. Built-ins include default/worker/explorer. Codex spawns only when explicitly asked. | Add ticket-level `parallelism:` opt-in and disjoint write-set checks. Parent role owns CT2 state writes. | P2 |
| Automations | Codex app can schedule recurring tasks, thread wakeups, project/worktree runs, and skill-driven automation. | Offer `ct2 automation install` recipes: nightly backlog triage, PR babysitter, stale review wakeup. Treat results as inbox messages, not direct state changes. | P2 |
| Image input/generation/view | Local feature flag `image_generation` enabled; app-server schema includes image input/generation/view; 0.130.0 improves `view_image` in multi-environment sessions. | Add multimodal ticket attachments: screenshots, UI diffs, generated asset provenance, reviewer screenshot evidence. | P2 |
| In-app browser/computer use | Stable feature flags locally, docs cover browser and computer use. | Use only for UI validation tickets. Store screenshots and test notes as evidence. Do not make GUI side effects part of core CT2 state transitions. | P2 |
| OTel/analytics | Docs describe opt-in telemetry; 0.130.0 release adds configurable trace metadata and richer analytics. | Add CT2 correlation ids to Codex serviceName/trace metadata: ticket id, role, goal slug, review round. | P1 |
| Managed config and permission profiles | Docs cover sandbox, approval policy, requirements. Schema exposes active permission profile. | `ct2-codex-doctor` should report effective permission profile and whether role policy is stronger than runtime policy. | P1 |

## Claude Code Feature Radar

| Capability | Current state | CT2 opportunity | Priority |
|---|---|---|---|
| Changelog latest | Official changelog latest is 2.1.138 on May 9, 2026. Local is also 2.1.138. | Add `ct2-claude-doctor` so other machines get the same version-gated clarity and this repo can record baseline evidence. | P0 |
| AskUserQuestion | Agent SDK `canUseTool` callback handles clarifying questions via `AskUserQuestion`; 2.1.136 fixed multi-select answer arrays and dialog behavior. | Create unified decision bridge with Codex requestUserInput. Helm can ask bounded questions; forge/lens mostly block through inbox. | P0 |
| `/loop` and Cron tools | Scheduled tasks require 2.1.72+. Tools: `CronCreate`, `CronList`, `CronDelete`; session-scoped, 50 tasks, 7-day recurring expiry. | Replace ad hoc reviewer loops with declarative CT2 loops where suitable. Add `.claude/loop.md` template for lens-cc and forge babysitting. | P1 |
| Monitor tool | v2.1.98+. Watches logs, CI, PRs, directories, long-running scripts in background and streams events. Not available with some telemetry-disable/provider settings. | Use for `ct2-watch`: CI failure, PR review comment, `.ct2/in-review` entry, long test output. More responsive than polling. | P1 |
| Channels | MCP servers can push CI/chat/monitoring events into a running session. | CT2 can expose an MCP channel bridge that turns external events into `.ct2/inbox/` messages and wakes roles. | P2 |
| Routines/Desktop scheduled tasks | Cloud and desktop scheduling survive beyond a terminal session. | Durable CT2 automations for daily backlog health, dependency audit, review stale tickets. Use only for advisory ticket/inbox creation. | P2 |
| Hooks | Docs cover command, prompt, HTTP, MCP hooks and lifecycle events. SubagentStart/Stop and Stop hooks enable completion gates. | Claude hook package for CT2 invariants and completion audit. Stop hook can block "done" claims until checks pass. | P0 |
| Hook effort metadata | 2.1.133 adds active effort level to hook input and `$CLAUDE_EFFORT`. | Review hooks can require higher scrutiny for `high/xhigh/max` tasks or annotate telemetry. | P2 |
| Subagents | Frontmatter supports model, tools, disallowedTools, permissionMode, MCP, hooks, maxTurns, skills, memory, effort, background, isolation, color. | Map CT2 explorer/worker/reviewer assistants to Claude subagents. Use `isolation: worktree` for implementation subagents and hooks for disjoint write sets. | P1 |
| Worktree controls | 2.1.133 adds `worktree.baseRef` to choose fresh vs head base. CLI supports `--worktree`, `--tmux`. | CT2 should explicitly set worktree base per ticket. For unpushed local plan work, use `head`; for clean backlog work, use `fresh`. | P1 |
| Agent SDK sessions | SDK docs cover session continue/resume/fork, streaming input/output, structured outputs, permissions, hooks, plugins, subagents. | Long-term replacement for purely interactive Claude roles: `ct2-claude-driver` with JSON schema outputs and resumable sessions. | P2 |
| Structured output | `claude --json-schema` and SDK structured output. | Use for machine-written sidecars, status summaries, ticket draft validation. | P1 |
| OTel monitoring | Claude Code exports metrics/logs/traces, with optional detailed prompt/tool content gates. | CT2-wide observability: ticket id, role, review round, command duration, permission waits, tool failures. Avoid prompt content by default. | P1 |
| LSP tool | Docs describe code intelligence from language servers after edits. | Forge can receive type errors automatically. CT2 should record LSP diagnostics in ticket evidence when available. | P2 |
| Checkpointing/rewind | Docs cover tracking and rewinding file changes and conversation. | Add guidance for forge rework: checkpoint before broad edits, rewind when review rejection indicates wrong direction. | P2 |
| `/ultrareview` and `/review` | Claude Code has local PR review and deeper cloud multi-agent review. | Optional advisory third-pass for high-risk tickets. Must not replace dual sidecar rule. | P2 |
| Remote Control/deep links | CLI supports remote-control session naming; docs cover opening sessions from links and browser/mobile continuation. | `ct2-status` can print deep links to active role sessions when available. | P2 |
| Auto mode hard deny | 2.1.136 adds unconditional auto-mode deny rules. | Managed enterprise CT2 profiles can hard-deny destructive commands across roles. | P1 |
| Image paste/computer/Chrome | Latest fixes improve image paste; docs cover Chrome/computer use. | UI and desktop-app tickets can attach screenshots and browser traces as review evidence. | P2 |

## Strategic Gaps And Proposed Product Bets

### P0 - Runtime Twin

Add a CT2-local "runtime twin" for every active role. This is not a transcript copy and not a replacement for vendor sessions. It is a compact operational mirror that answers: what is running, why, under which permissions, with what objective, what is it waiting on, and how can it be resumed?

```text
.ct2/
`-- runtime/
    |-- roles/
    |   |-- ct2-helm.json
    |   |-- ct2-forge.json
    |   |-- ct2-lens-cc.json
    |   `-- ct2-lens-cx.json
    |-- sessions/
    |   |-- claude-{session-id}.json
    |   `-- codex-{thread-id}.json
    `-- process-table.json
```

Runtime twin fields:

- role id, runtime, runtime version, mode, pid/tmux/session/thread id;
- active ticket or goal scope;
- permission/sandbox profile and whether it matches role policy;
- active watchers, schedules, monitors, and background tasks;
- wait state: `idle`, `working`, `blocked_on_user`, `blocked_on_review`, `blocked_on_ci`, `budget_limited`, `policy_denied`, `stale`;
- resume command or deep link when available;
- last verified evidence and last unsafe/degraded event.

Acceptance:

- `ct2-status` can render an operator-grade process table.
- No vendor transcript is required to know whether CT2 is healthy.
- Stale runtime twin records are explicitly marked stale instead of silently trusted.

### P0 - Autonomy SLA

CT2 needs a first-class notion of expected autonomous behavior. A role should not merely be "running"; it should be meeting an autonomy contract.

Example SLA dimensions:

| SLA dimension | Example threshold | Failure action |
|---|---:|---|
| Heartbeat freshness | role heartbeat < 5 min old | mark role stale and notify helm |
| Review latency | in-review ticket without both sidecars after 30 min | wake lens roles or create watcher alert |
| Rework latency | rejected ticket untouched after 60 min | notify forge |
| User decision latency | pending decision > configured time | escalate or narrow scope |
| Verification debt | in-review ticket missing test evidence | block submission or mark review warning |
| Budget drift | token/cost/time exceeds goal budget | pause goal and request operator decision |

This converts "autonomous" from a vague promise into measurable service behavior.

### P0 - Capability Registry

Create `ct2-runtime-doctor` or expand `ct2-status --doctor` to write:

```text
.ct2/
`-- runtime/
    |-- capabilities.json
    |-- codex-app-server-schema.json
    |-- claude-capabilities.json
    `-- degradations.md
```

Fields:

- runtime version: Codex, Claude, tmux, git, Python;
- feature flags/stages: Codex `experimentalFeature/list`, `codex features list`;
- app-server methods: `thread/goal/*`, `thread/turns/list`, `fs/watch`, `requestUserInput`, `plugin/read`, `hooks/list`;
- Claude command availability: `--agent`, `--worktree`, `--json-schema`, `--include-hook-events`, `agents`, `plugin`, `ultrareview`;
- scheduler/monitor availability: Claude version >= 2.1.98 for Monitor, >= 2.1.72 for scheduled tasks;
- MCP/app connectors: `codex mcp list`, `claude mcp list`;
- policy fit by role: helm, forge, lens-cc, lens-cx, status.

Acceptance:

- `ct2-status` shows a one-screen "runtime health" section.
- Degraded features always name fallback behavior.
- Under-development vendor features are never silently used in core transitions.

### P0 - Unified Decision Bridge

Add a CT2-level decision protocol:

```text
.ct2/
`-- decisions/
    |-- pending/
    |-- answered/
    |-- expired/
    `-- audit/
```

Canonical decision record:

```json
{
  "id": "dec-20260510-001",
  "role": "ct2-helm",
  "runtime": "codex|claude|manual",
  "ticket": "optional",
  "kind": "clarification|approval|policy-exception|scope-choice",
  "questions": [
    {
      "id": "scope",
      "prompt": "Which subsystem is in scope?",
      "options": ["codex-runtime", "review-protocol", "docs-only"],
      "multi_select": false
    }
  ],
  "status": "pending|answered|expired|denied",
  "redaction": "none|secret"
}
```

Mapping:

- Codex app-server `item/tool/requestUserInput` -> `.ct2/decisions/pending`.
- Claude SDK `AskUserQuestion` -> same.
- CLI fallback -> `.ct2/inbox/ct2-helm` blocked/clarification message.
- Answers that change scope/AC/priority must append a ticket note or planning ledger entry.

Acceptance:

- Helm and helm-auto-cx can ask one to three bounded questions through either runtime.
- Lens roles cannot use the bridge to waive review criteria.
- Secret answers never land in tickets, sidecars, or telemetry.

### P0 - Hook Guardrails Package

Ship `.ct2/hooks/` plus Codex/Claude plugin hook declarations.

Guardrails:

- block `cp` between CT2 state directories;
- block state transitions not using `mv`;
- block lens-cx from reading `*-cc-rN.md` before its own `*-cx-rN.md` exists;
- block lens-cc from reading `*-cx-rN.md` before its own `*-cc-rN.md` exists;
- warn or block source writes by lens roles;
- run sidecar validator after reviewer sidecar writes;
- run ticket format validator before `ct2-seal`;
- run completion audit before a role stop/goal-complete claim.

Vendor mapping:

- Codex: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `SessionStart`, `Stop` where supported; note current hook docs say interception is not complete for every tool path, so scripts remain the source of enforcement.
- Claude: `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionStart`, plus command/prompt hooks.

Acceptance:

- Hook package is installable without external Python packages.
- Hook output is human-readable and machine-parsable.
- Core CT2 scripts still enforce invariants even if hooks are unavailable.

### P1 - Watch And Monitor Plane

Introduce `ct2-watch` as a provider-neutral wrapper for wakeups.

Sources:

- local filesystem: `.ct2/backlog`, `.ct2/in-review`, `.ct2/rejected`, `.ct2/inbox`;
- GitHub/CI via MCP, `gh`, or Claude Monitor;
- Codex app-server `fs/watch`;
- Claude `/loop`/Cron tools;
- Codex app thread automations;
- external event push through Claude Channels or future CT2 MCP.

Output:

- `.ct2/watchers/{id}.json` for configured watchers;
- `.ct2/logs/ct2-watch.log`;
- inbox messages for role wakeups;
- heartbeat updates for active role sessions.

Principle: watchers wake or notify; they do not move tickets to terminal states.

### P1 - Runtime Driver Hardening

Codex:

- Extend `ct2-codex-app-driver` to use `thread/turns/list` and `thread/read` with summary/unloaded views.
- Add remote-control mode around `codex remote-control`.
- Persist remote-control status, environment id, thread id, permission profile, goal state.
- Use `fs/watch` for `.ct2/` changes when app-server is available.

Claude:

- Add `ct2-claude-doctor`.
- Prototype `ct2-claude-exec` around `claude -p --output-format stream-json --json-schema`.
- Add `ct2-claude-loop-template` for `.claude/loop.md`.
- Support `--include-hook-events` in debug runs to verify hook behavior.

### P1 - Dual Plugin Distribution

Codex plugin is already present but should be upgraded from "role skills" to "runtime package":

- plugin manifest;
- skills;
- hooks;
- optional MCP server definitions;
- optional assets/templates;
- marketplace metadata;
- compatibility metadata: minimum Codex version, required feature flags, degraded paths.

Claude plugin should mirror it:

- `/ct2:helm`, `/ct2:forge`, `/ct2:lens-cc`, `/ct2:status`, `/ct2:loop`;
- CT2 subagents for explorer/worker/reviewer assistance;
- hooks package;
- monitors or plugin-declared monitors where appropriate;
- version constraints for plugin dependencies.

### P1 - Observability Ledger

Add `.ct2/telemetry/` summaries independent of vendor telemetry backends:

```text
.ct2/
`-- telemetry/
    |-- events.jsonl
    |-- spans.jsonl
    `-- daily-summary.md
```

Do not store prompt contents by default. Store:

- role;
- ticket id;
- review round;
- runtime;
- command/tool category;
- duration;
- exit status;
- approval wait duration;
- token/cost where available;
- goal status transitions;
- watcher events.

If OTel is enabled, attach the same IDs as trace attributes. This makes CT2 useful both for solo local workflows and enterprise dashboards.

### P1 - Evidence Graph

Today CT2 has tickets and sidecars, but evidence is mostly prose. As workflows become multimodal, remote, and scheduled, CT2 needs a graph of claims and proof.

Core model:

```text
claim -> evidence -> verifier -> verdict -> state transition
```

Examples:

- Claim: "AC-2 integration tests pass." Evidence: command log, exit code, timestamp, worktree hash. Verifier: test command. Verdict: pass.
- Claim: "UI matches target screenshot." Evidence: screenshot path, viewport, browser console log. Verifier: screenshot review plus optional pixel diff. Verdict: pass/warn/fail.
- Claim: "Reviewer independence preserved." Evidence: hook log showing no partner sidecar read before own sidecar write. Verifier: hook guardrail. Verdict: pass.

Proposed layout:

```text
.ct2/
`-- evidence/
    |-- claims.jsonl
    |-- artifacts/
    |-- commands/
    |-- screenshots/
    `-- verifiers/
```

Acceptance:

- Every `done/` transition can be traced to sidecar verdicts and evidence claims.
- Reviewers can cite evidence ids instead of re-describing all raw logs.
- Failed or missing evidence is visible before review, not discovered only by lens roles.

### P1 - Policy Compiler

CT2 invariants are currently duplicated across specs, role prompts, scripts, and future hooks. Add a tiny stdlib-only policy compiler that emits provider-specific guardrails from one CT2 policy file.

Source:

```text
config/ct2-policy.yaml
```

Generated outputs:

- Claude `settings.json` hook fragments;
- Codex plugin hook declarations;
- shell validators used by CT2 CLI scripts;
- markdown policy summaries for role skills.

The compiler should be intentionally conservative: it only emits rules CT2 can also enforce in scripts. Hooks remain acceleration and early warning, not sole authority.

### P1 - Re-entry Protocol For Remote Work

Remote Control, Claude web, Codex cloud, routines, Slack, Linear, and GitHub Actions all create work outside the local terminal. CT2 should define a "re-entry" contract:

1. remote task must name a CT2 ticket or create a draft ticket;
2. remote output returns as one of: patch, PR, inbox message, evidence artifact, or advisory report;
3. local CT2 validates the output before moving any state;
4. if the remote branch changed, CT2 records branch, commit, PR, and verification status;
5. no remote automation writes reviewer sidecars unless it is the active lens runtime and independence can be proven.

This is the difference between "we use cloud agents" and "cloud agents participate safely in CT2."

### P2 - Multimodal Evidence

CT2 should treat images as first-class evidence, not transient chat attachments.

Proposed layout:

```text
.ct2/
`-- artifacts/
    |-- tickets/{ticket-id}/
    |   |-- screenshots/
    |   |-- generated-images/
    |   |-- browser-recordings/
    |   `-- manifest.json
    `-- reviews/{ticket-id}-r{n}/
```

Use cases:

- UI implementation ticket includes reference screenshot.
- Forge attaches before/after screenshots.
- Lens roles inspect screenshots with image tools and cite artifact paths in sidecars.
- `image_gen` or Codex image generation creates placeholder assets with provenance and review flags.

Guardrail: generated images can support prototyping, but cannot be sole evidence for product correctness. UI behavior still needs browser/test evidence.

### P2 - Cloud And Remote Delegation

Codex cloud/GitHub Action/Slack/Linear and Claude web/routines/GitHub Actions/Slack are powerful, but they create state outside `.ct2/`.

CT2 should support them as outer executors only if:

- every delegated task maps to a CT2 ticket id;
- remote branch/worktree identity is recorded;
- outputs return as patches, PRs, inbox messages, or sidecars;
- CT2 reconciler remains terminal authority.

Good first pilot:

- `ct2-delegate-pr-babysitter`: scheduled Claude/Codex task watches a PR, posts inbox updates, optionally drafts a fix ticket.
- `ct2-nightly-security-triage`: Codex Security or Claude `/security-review` creates investigation tickets, not direct patches.

## Roadmap

| Phase | Timebox | Deliverables | Exit criteria |
|---|---:|---|---|
| 0 | 1 week | `ct2-runtime-doctor`, runtime capability schema, README update | Reports Codex 0.130.0 and Claude 2.1.138 as local baselines; no state mutation. |
| 1 | 1-2 weeks | Runtime twin, process table, autonomy SLA draft | `ct2-status` can show active/stale/waiting role runtimes without reading vendor transcripts. |
| 2 | 2-3 weeks | Decision bridge, inbox fallback, helm/helm-auto-cx integration | Same question flow works through Codex requestUserInput, Claude AskUserQuestion, and fallback file inbox. |
| 3 | 3-4 weeks | Hook guardrails and policy compiler for Claude and Codex | Deliberate invariant violations are blocked or loudly rejected in scratch CT2 projects. |
| 4 | 4-6 weeks | Watch/monitor plane | Lens wakeup can be driven by watcher/monitor instead of pure polling; polling remains fallback. |
| 5 | 6-8 weeks | App-server remote-control hardening and thread paging | Long-running Codex role can resume by thread id and inspect large transcript without loading all turns. |
| 6 | 8-10 weeks | Claude driver prototype with structured output and hook events | Lens-cc or status can run headless with schema-validated output. |
| 7 | 10-12 weeks | Evidence graph | Done transitions cite evidence ids, sidecars, and verifier output. |
| 8 | 12+ weeks | Dual plugin distribution, multimodal evidence, remote re-entry pilots | CT2 installs as Codex and Claude plugins; remote/cloud tasks return through CT2 re-entry protocol. |

## Prioritization

| Bet | Impact | Confidence | Effort | Why now |
|---|---:|---:|---:|---|
| Capability Registry | High | High | Medium | Local Claude now matches latest, but CT2 still needs version-gated clarity across machines; Codex features have mixed maturity. |
| Runtime Twin | High | High | Medium | Remote Control, app-server, sessions, agents, monitors, and schedules need one CT2 process table. |
| Autonomy SLA | High | Medium | Low-Medium | Turns vague long-running autonomy into measurable latency, freshness, and budget contracts. |
| Decision Bridge | High | High | Medium | Both runtimes now expose structured user-question mechanisms. |
| Hook Guardrails | High | Medium | Medium | CT2's core value is protocol safety; hooks let us enforce before damage happens. |
| Policy Compiler | High | Medium | Medium | Prevents spec/prompt/hook/script drift as CT2 supports two plugin ecosystems. |
| Watch/Monitor Plane | High | Medium | Medium | Claude Cron/Monitor and Codex fs/watch/automations directly address long-running autonomy. |
| App-server Remote Control | Medium-High | Medium | Medium-High | Codex 0.130.0 makes remote-control easier, but APIs remain experimental. |
| Evidence Graph | Medium-High | Medium | Medium | Makes completion auditable across commands, screenshots, reviews, remote tasks, and hooks. |
| Observability Ledger | Medium | High | Medium | OTel exists on both sides; CT2 needs provider-neutral local evidence. |
| Dual Plugin Distribution | Medium | High | Medium | Codex plugin exists; Claude plugin ecosystem is now mature enough to mirror. |
| Multimodal Evidence | Medium | Medium | Medium | Valuable for UI/product work but not central to CT2 state correctness. |
| Cloud Delegation | Medium | Low-Medium | High | Powerful but risks splitting authority away from `.ct2/`. |

## Product Requirements Draft

### FR-1 Runtime Capability Registry

CT2 must detect installed agent runtimes and write a project-local report without mutating global config.

Acceptance:

- Runs with only bash and Python stdlib.
- Checks Codex and Claude independently.
- Records official recommended minimums separately from local installed versions.
- Emits degraded paths and blockers.
- Does not require network for basic local probe; optional `--refresh-docs` can fetch official latest versions.

### FR-2 Decision Bridge

CT2 must provide a single schema for user questions and approvals.

Acceptance:

- Codex request-input and Claude AskUserQuestion map into the same decision record.
- Pending decisions are visible in `ct2-status`.
- Answers can be replayed into the runtime or converted into inbox clarification.
- Lens roles cannot use decisions to bypass review requirements.

### FR-3 Hook Guardrails

CT2 must ship provider-specific hooks that reinforce CT2 invariants.

Acceptance:

- Hook install is optional but detectable.
- Missing hooks degrade to script-only enforcement.
- Hooks never become the only protection for state transitions.
- Partner-sidecar access violation is detectable in normal command/file-read paths.

### FR-4 Watchers

CT2 must model wakeups explicitly.

Acceptance:

- Watchers have ids, source, role target, schedule/event condition, last fire, last error, and enabled state.
- Watchers write inbox messages or heartbeats only.
- `ct2-status` displays active watchers.
- Claude `/loop`, Claude Monitor, Codex app automation, and app-server `fs/watch` have documented mapping.

### FR-5 Runtime Observability

CT2 must collect enough local telemetry to audit long-running autonomous work.

Acceptance:

- Each role action can be correlated with ticket id and review round.
- Telemetry defaults avoid prompt/tool content.
- If vendor OTel is enabled, CT2 correlation ids are included.
- `ct2-status` shows stale heartbeats, repeated failures, and blocked approval waits.

### FR-6 Runtime Twin

CT2 must persist compact runtime mirrors for active roles.

Acceptance:

- Each active role has a runtime record with version, mode, session/thread id, permission profile, wait state, and resume command.
- `ct2-status` renders process-table style output.
- Stale records are detectable without killing or mutating vendor sessions.
- Runtime records are advisory and cannot move ticket state.

### FR-7 Evidence Graph

CT2 must make acceptance and review evidence addressable.

Acceptance:

- Evidence claims have stable ids.
- Tickets and sidecars may cite evidence ids.
- Verifier command output, screenshots, hook events, and remote task reports can all be stored as evidence.
- Reconciler may warn or block when required evidence is absent, depending on role policy.

### FR-8 Remote Re-entry

CT2 must define how cloud/remote agent output returns to the local protocol.

Acceptance:

- Remote work names a CT2 ticket, draft ticket, or planning ledger.
- Remote results enter as patch, PR, inbox message, evidence artifact, or advisory report.
- Local CT2 validates outputs before any state transition.
- Remote reviewer sidecars are forbidden unless independence can be proven.

## Non-Goals

- Replacing `.ct2/` with Codex/Claude session state.
- Letting Claude or Codex scheduler move tickets to `done/`.
- Using cloud routines or automations as hidden CT2 state machines.
- Making under-development vendor features mandatory for core CT2.
- Adding non-stdlib Python dependencies to CT2 core.
- Allowing multimodal/image evidence to replace tests, sidecars, or acceptance criteria.

## Key Product Decisions

| Decision | Recommendation | Rejected alternative |
|---|---|---|
| Where to store runtime data | Dedicated `.ct2/runtime/`, `.ct2/decisions/`, `.ct2/watchers/`, `.ct2/telemetry/` | Overloading `.ct2/.meta/` until it becomes unreadable. |
| Scheduler model | Provider-neutral watcher records with provider-specific executors | One-off tmux loops for every role. |
| Human questions | Canonical decision schema, runtime adapters | Separate Codex and Claude question paths with incompatible audit trails. |
| Hook role | Defense-in-depth guardrail | Hook-only enforcement of CT2 invariants. |
| Runtime state | Runtime twin records under `.ct2/runtime/` | Treat vendor transcripts as the only source of operational truth. |
| Evidence | Addressable evidence graph | Long prose summaries with uncitable raw command output. |
| Cloud tasks | Advisory/delegated executor only | Cloud task owns ticket lifecycle. |
| Images | Evidence artifacts with provenance | Chat-only attachments that disappear from audit. |

## Immediate Next Tickets

1. `ct2-runtime-doctor`: probe Codex and Claude versions, feature flags, app-server schema, MCP lists, and role compatibility.
2. `ct2-runtime-twin`: write role runtime mirrors and process table under `.ct2/runtime/`.
3. `ct2-autonomy-sla`: define stale, blocked, review-latency, decision-latency, and budget thresholds.
4. `ct2-decision-bridge`: implement decision record schema plus status rendering and inbox fallback.
5. `ct2-hook-guardrails`: add hook scripts and plugin declarations for state transition and sidecar independence checks.
6. `ct2-policy-compiler`: generate Claude/Codex hook declarations and script validators from one CT2 policy source.
7. `ct2-watchers`: add watcher schema and one local filesystem watcher pilot for `.ct2/in-review`.
8. `ct2-claude-loop-template`: generate `.claude/loop.md` templates for lens-cc and forge babysitting.
9. `ct2-codex-app-driver-thread-paging`: update app-driver to use summary/unloaded thread reads and `thread/turns/list`.
10. `ct2-evidence-graph`: add stable evidence ids and sidecar/ticket citation rules.
11. `ct2-observability-ledger`: write provider-neutral event JSONL with ticket/role/review correlation ids.
12. `ct2-multimodal-artifacts`: add artifact manifest and sidecar citation rules for screenshots/images.
13. `ct2-remote-reentry`: define and validate how cloud/remote agent outputs return to CT2 state.

## Appendix A - Documentation State

Codex docs currently expose these major areas through the official docs index:

- App: app, features, settings, review, automations, worktrees, local environments, browser, Chrome extension, computer use, commands, Windows.
- CLI: overview, features, command-line options, slash commands.
- Automation: non-interactive mode, SDK, app-server, MCP server, GitHub Action.
- Configuration: config basics/advanced/reference/sample, rules, hooks, AGENTS.md, MCP, plugins, skills, subagents, feature maturity.
- Integrations: GitHub, Slack, Linear, Codex Security.
- Concepts: customization, memories/Chronicle, sandboxing, subagents, workflows, models, cyber safety.
- Release surface: changelog, feature maturity, open source.

Claude Code docs currently expose these major areas through the official docs index:

- Core: overview, how it works, `.claude` directory, context window, memory, permission modes, best practices.
- Runtime and CLI: CLI reference, commands, interactive mode, settings, env vars, tools reference, statusline, fullscreen, terminal config.
- Extensibility: skills, subagents, hooks, MCP, plugins, plugin marketplaces/dependencies, output styles.
- Agent SDK: sessions, streaming, structured outputs, user input, permissions, hooks, subagents, tool search, observability, custom tools, plugins.
- Automation and monitoring: scheduled tasks, routines, desktop scheduled tasks, GitHub Actions, GitLab CI/CD, Monitor tool, channels, OTel monitoring, analytics.
- Platforms: terminal, Desktop, Web, VS Code, JetBrains, Chrome, computer use, remote control, Slack.
- Governance: admin setup, server-managed settings, auto mode config, sandboxing, network, legal/compliance, Bedrock, Vertex, Foundry.
- Advanced workflows: checkpointing, code review, ultrareview, ultraplan, voice dictation, team orchestration.

## Appendix B - Version Notes

Codex 0.130.0, released 2026-05-08, matters to CT2 because it adds or improves:

- `codex remote-control` as a simpler headless app-server entrypoint;
- app-server large-thread paging with unloaded/summary/full turn item views;
- plugin details that expose bundled hooks and plugin sharing/discovery metadata;
- multi-environment `view_image` resolution;
- live app-server config reload fixes;
- turn diff accuracy fixes around apply-patch partial failures;
- configurable OpenTelemetry trace metadata and review/feedback analytics.

Claude Code latest official changelog entries matter to CT2 because:

- 2.1.138 and 2.1.137 are small/internal or VS Code fixes.
- 2.1.136 fixes several CT2-relevant surfaces: MCP persistence after `/clear`, plan mode write blocking, plugin hook stability, `AskUserQuestion` multi-select answers, `CronList` output, MCP tool-result visibility, and adds OTel feedback survey and auto-mode `hard_deny`.
- 2.1.133 adds worktree baseRef selection, hook effort metadata, subagent skill discovery fixes, remote-control cancellation fixes, and managed sandbox binary paths.
- 2.1.132 adds `CLAUDE_CODE_SESSION_ID` for Bash subprocesses and fixes resume/plan/fullscreen/MCP/terminal issues. It is no longer the local version, but it matters as the start of the latest CT2-relevant update window.

## Appendix C - Completion Audit For This Document

| User request | Evidence in this document |
|---|---|
| Latest Codex CLI release notes | Evidence Base, Codex Feature Radar, Appendix B cite and summarize 0.130.0. |
| Latest Claude Code release notes | Evidence Base, Claude Feature Radar, Appendix B cite and summarize 2.1.138 and the 2.1.132-2.1.138 CT2-relevant update window. |
| All document state | Appendix A maps official Codex and Claude documentation indexes into product-relevant categories. |
| Built-in features/internal tools/APIs | Codex Feature Radar and Claude Feature Radar enumerate app-server, request input, hooks, plugins, subagents, scheduling, monitoring, image/browser/computer, OTel, SDK/CLI. |
| `/goal` beyond already applied | Codex Feature Radar treats `/goal` as existing and focuses on adjacent missed features. |
| User interview features | Unified Decision Bridge maps Codex requestUserInput and Claude AskUserQuestion. |
| Image recognition/generation features | Multimodal Evidence covers image input/view/generation and artifact provenance. |
| Cron/monitoring features | Watch And Monitor Plane covers Claude Cron/Monitor, Codex Automations/fs.watch, Channels, OTel. |
| CT2 development proposals | Strategic Gaps, Roadmap, Product Requirements, Immediate Next Tickets. |
| Product-owner quality | Includes evidence, current baseline, product thesis, prioritization, requirements, non-goals, roadmap, and concrete ticket candidates. |
| Local Claude was updated | Evidence Base now records local Claude Code `2.1.138` and removes the stale "local lag" assumption. |
| Deeper creative product thinking | North Star, Second-Order Insights, Runtime Twin, Autonomy SLA, Evidence Graph, Policy Compiler, and Remote Re-entry sections convert raw feature research into a higher-level CT2 product strategy. |
