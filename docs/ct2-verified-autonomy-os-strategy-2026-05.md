# CT2 Verified Autonomy OS Strategy

조사 기준일: 2026-05-10 KST / 2026-05-09 US
통합 작성 기준: `docs/agent-platform-feature-radar-2026-05.md`, `docs/ct2-product-strategy-2026-05.md`, 사용자 인터뷰 합의
대상 런타임: Codex CLI 0.130.0, Claude Code 2.1.138

## 0. Executive Decision

CT2의 다음 제품 정체성은 **Verified Autonomy OS**다.

단, 여기서 OS는 보편적 agent OS가 아니다. CT2는 Cursor, Devin, AutoGen, Jira/Linear, cloud SaaS orchestrator가 되지 않는다. CT2가 지향하는 것은 **file-first dual-review engineering workflow를 위한 protocol kernel**이다. `.ct2/`의 ticket, sidecar, inbox, ledger, evidence, runtime mirror가 권위이고, Claude/Codex runtime은 driver, observer, advisor, executor로만 참여한다.

한 문장으로 요약하면:

> Any agent can act, but only verified evidence can move state.

이번 통합 전략의 핵심 결정은 다음 여섯 가지다.

| 결정 | 합의 |
|---|---|
| Canonical name | Verified Autonomy OS |
| 범위 | File-first dual-review workflow를 위한 protocol kernel |
| 문서 구조 | Feature Radar는 vendor-surface map, Product Strategy는 bet/risk 문서, 본 문서는 canonical strategy |
| 측정 | 단일 north star가 아니라 Trust, Evidence, Autonomy, Cost/Latency balanced scorecard |
| 첫 실행 | Capability Registry + empirical baseline이 Bet 1보다 먼저 |
| Runtime 권한 | Native scheduler, task, cloud, remote-control은 advisory-only |

## 1. Document Set

세 문서는 역할이 다르다.

| 문서 | 역할 | 유지 이유 |
|---|---|---|
| `agent-platform-feature-radar-2026-05.md` | Vendor-surface map | Codex/Claude의 최신 기능, 안정도, 흡수 후보를 넓게 추적한다. |
| `ct2-product-strategy-2026-05.md` | Bet/risk strategy | 무엇을 먼저 하고, 무엇을 하지 않으며, 어떤 조건에서 멈출지 결정한다. |
| `ct2-verified-autonomy-os-strategy-2026-05.md` | Canonical integrated plan | 두 문서와 인터뷰 합의를 합쳐 최종 제품 방향, scorecard, release train을 정한다. |

읽는 순서:

1. 본 문서 §0-§5로 최종 방향을 잡는다.
2. Feature Radar에서 vendor evidence와 capability 세부를 확인한다.
3. Product Strategy에서 bet별 risk, kill criteria, implementation sketch를 확인한다.
4. 코드나 spec 변경은 본 문서의 release train과 기존 `spec/` 권위 원칙을 따른다.

## 2. Product Identity

### 2.1 What CT2 Is

CT2는 agent 실행을 더 많이 만드는 도구가 아니라, agent 실행이 **검증 가능한 상태 전이**로 귀결되도록 하는 protocol kernel이다.

CT2의 제품 약속:

- agent work는 ticket과 acceptance criteria에서 출발한다.
- 실행 결과는 sidecar, command evidence, verifier output, review verdict로 남는다.
- state transition은 atomic `mv`로만 발생한다.
- reviewer independence는 편의보다 우선한다.
- vendor runtime state는 `.ct2/` state를 대체하지 않는다.

### 2.2 What CT2 Is Not

| 아님 | 이유 |
|---|---|
| 보편적 agent OS | 범위가 넓어지면 `.ct2/` authority와 dual-review invariant가 흐려진다. |
| Cloud SaaS orchestrator | CT2의 핵심은 local file authority와 git-adjacent evidence다. |
| Jira/Linear 대체재 | ticket은 코드 옆에 있어야 하며, PM database가 권위가 되면 안 된다. |
| 단일 LLM framework | Claude와 Codex의 독립 검토가 차별점이다. |
| 자동 LLM router | 정적 role contract가 안정되기 전에는 변동성을 키운다. |

### 2.3 Reliability Platform과의 관계

`Reliability Platform`은 폐기하지 않는다. 다만 canonical 이름은 아니다.

정리하면:

- **Verified Autonomy OS**: 제품 정체성.
- **Protocol kernel**: 구현 범위.
- **Reliability platform**: 사용자가 체감하는 운영 가치.

즉 CT2는 Verified Autonomy OS이고, 그 결과 multi-agent engineering reliability를 제공한다.

## 3. OS Primitives

Verified Autonomy OS는 기존 CT2 primitive를 운영체제 관점으로 재정렬한다.

| OS primitive | CT2 equivalent | 6-12주 내 제품화 |
|---|---|---|
| Filesystem | `.ct2/` ticket, sidecar, inbox, ledger, artifacts | 기존 authority 유지, evidence/artifact path 명확화 |
| Commit/syscall | `ct2-seal`, `ct2-revise`, `ct2-status`, reconciler, atomic `mv` | decision bridge와 policy compiler로 강화 |
| Process table | active roles, Codex threads, Claude sessions, tmux, goals | runtime twin과 capability registry |
| Scheduler | reviewer loops, watchers, monitor/cron adapters | advisory watcher plane |
| Permission model | role ownership, hook guardrails, sandbox/approval policy | provider hook package + script-level enforcement |
| Flight recorder | command logs, sidecars, hook events, OTel correlation | evidence graph + observability ledger |
| Device drivers | Codex app-server/remote-control, Claude CLI/SDK/remote-control | runtime driver hardening |

권위는 항상 아래로 흐른다.

```text
Vendor runtime events
  -> CT2 adapter/driver
  -> .ct2/inbox | .ct2/runtime | .ct2/evidence
  -> script/spec verifier
  -> atomic state transition
```

반대로 native task, scheduler, remote-control, Slack/Discord command가 직접 ticket state를 바꾸는 흐름은 금지한다.

## 4. Balanced Scorecard

단일 north star는 쓰지 않는다. Verified Autonomy OS는 네 축이 동시에 건강해야 한다.

| 축 | 90일 목표 | 실패 신호 |
|---|---:|---|
| Trust | Trust ratio ≥ 0.92; first-pass approval baseline +15pp | done 이후 revise/revert/reopen 증가 |
| Evidence | Evidence coverage ≥ 0.90; uncited verifier 0건 | sidecar가 prose만 있고 command/evidence id가 없음 |
| Autonomy | lens latency p95 ≤ 90초; blocked->unblocked p95 baseline -70%; stale runtime twin 0건 | watcher는 있는데 stale role을 못 깨움 |
| Cost/Latency | $/ticket p50 baseline -30%; p50 ticket latency baseline 이하 | 비용은 줄었지만 trust/evidence가 하락 |

Baseline 없이 목표를 주장하지 않는다. Phase 0의 첫 산출물은 `ct2-baseline`과 `.ct2/telemetry/baseline-2026-05.json`이다.

필수 baseline:

| Baseline | 수집 방법 | 최소 표본 |
|---|---|---:|
| Trust ratio | `done/` 도달 후 revise/revert/reopen 여부 | 20 done tickets |
| First-pass approval | review round 0 sidecar verdict | 20 review events |
| Evidence coverage | done 전이별 sidecar/evidence/verifier 연결 여부 | 20 done tickets |
| Ticket latency | sealed -> done 시간 | 20 tickets |
| Review latency | in-review entry -> reconciler verdict | 20 reviews |
| Blocked latency | blocked inbox -> answer/retry | 5 events |
| Cost | 신규 telemetry sink에서 수집 시작 | sprint 전수 |

표본이 부족하면 숫자를 과장하지 않는다. 해당 metric은 "measurement started"로 표시하고 6주 후 sprint data로 갱신한다.

## 5. Release Train

### 5.1 Sequence

실행 순서는 다음으로 고정한다.

```text
Phase 0: Registry + Baseline
  -> Bet 1: Cost-aware Role Contracts
  -> Bet 2: Plan-mode-first Forge
  -> Bet 4: Eval Harness for Roles
  -> Bet 3: Ambient CT2 Advisory Bridge
  -> Bet 5: Native Task Graph Mirror (advisory spike only)
```

이 순서의 이유:

- Registry+Baseline은 모든 bet의 admission gate다.
- Cost contracts는 비용/지연을 측정 가능하게 만든다.
- Plan evidence는 trust와 evidence coverage를 직접 올린다.
- Eval harness는 role/prompt 변경 회귀를 막는다.
- Ambient bridge는 UX 효과가 크지만 external channel 위험이 있어 뒤로 둔다.
- Native task mirror는 가장 매혹적이지만 state authority 분기 위험이 커서 마지막이다.

### 5.2 Six-week Plan

| 주차 | 산출물 | Exit criteria |
|---|---|---|
| 0-1 | `ct2-runtime-doctor`, `ct2-baseline`, capability schema | Codex/Claude capability와 scorecard baseline 기록; state mutation 없음 |
| 1 | Codex flag 실측, role contract draft | 5개 role contract 초안; config surface 확인 |
| 2 | `ct2-role-run`, `ct2-cost`, telemetry sink | real ticket 실행에서 cost.jsonl 기록 |
| 3 | `.ct2/plans/`, plan-evidence rule, forge flow | 5개 ticket에서 plan-first 처리와 review 비교 |
| 4 | `.ct2/evals/` role eval baseline | role MD 의도적 회귀 1건을 eval이 잡음 |
| 5 | `ct2-bridge` notify-only pilot | 외부 알림 5건; ticket 직접 수정 0건 |
| 6 | retro, scorecard report, Bet 5 spike report | scorecard 갱신; native mirror는 advisory feasibility만 판단 |

### 5.3 First Seven Days

| Day | 작업 | 결과물 |
|---|---|---|
| 1 | capability probe 설계 | `ct2-runtime-doctor` spec/ticket draft |
| 1 | baseline script 설계 | `bin/ct2-baseline` draft |
| 2 | Codex/Claude runtime capability schema | `.ct2/runtime/capabilities.json` schema draft |
| 3 | scorecard baseline dry run | `.ct2/telemetry/baseline-2026-05.json` sample |
| 4 | Codex config surface spike | `.ct2/runtime/codex-flags-actual.md` |
| 5 | role contract spec PR draft | `spec/role-contracts.md` proposal |
| 6 | cost telemetry wrapper sketch 검증 | sample `cost.jsonl` |
| 7 | go/no-go review | Phase 0 report and Bet 1 readiness decision |

## 6. Workstreams

### 6.1 Kernel Admission Layer

Source documents: Feature Radar P0, Product Strategy Phase 0.

Deliverables:

- `ct2-runtime-doctor`
- `.ct2/runtime/capabilities.json`
- `.ct2/runtime/degradations.md`
- `ct2-status --doctor` one-screen output

Rules:

- No state mutation.
- No network required for basic local probe.
- Under-development vendor features are never silently used for core transitions.

### 6.2 Decision and Permission Layer

Deliverables:

- `.ct2/decisions/{pending,answered,expired,audit}/`
- provider adapters for Codex requestUserInput and Claude AskUserQuestion
- hook guardrails for state transition, sidecar independence, reviewer source writes
- policy compiler that emits provider hook declarations and shell validators

Rules:

- Lens roles cannot use decisions to waive review criteria.
- Hooks are defense-in-depth, not sole authority.
- Scripts still enforce invariants when hooks are missing.

### 6.3 Evidence and Observability Layer

Deliverables:

- `.ct2/evidence/claims.jsonl`
- `.ct2/evidence/commands/`
- `.ct2/evidence/artifacts/`
- `.ct2/telemetry/events.jsonl`
- scorecard summary in `ct2-status`

Rules:

- Prompt/tool contents are not stored by default.
- Every done transition should be traceable to sidecar verdicts and evidence claims.
- Missing evidence is visible before review, not discovered only by lens roles.

### 6.4 Role Contract and Eval Layer

Deliverables:

- `spec/role-contracts.md`
- role contract block in `config/harness.yaml`
- `ct2-role-run`
- `ct2-cost`
- `.ct2/evals/{ct2-helm,ct2-forge,ct2-lens-cc,ct2-lens-cx}/`

Rules:

- Static contracts first; no automatic LLM router.
- Eval is regression defense, not self-improving role evolution.
- Eval budget is separate from ticket budget.

### 6.5 Advisory Runtime Layer

Deliverables:

- `.ct2/watchers/*.json`
- notify-only `ct2-bridge`
- remote re-entry protocol
- native task mirror spike report

Rules:

- Watchers wake or notify; they do not move terminal states.
- External channels never write ticket files directly.
- Cloud/remote outputs return as patch, PR, inbox message, evidence artifact, or advisory report.
- Native task graph is CT2 -> native only; native -> CT2 state mutation is blocked.

## 7. Spec PR Plan

CT2 is spec-first. Code PRs should follow spec PRs for behavior changes.

| Order | Spec PR | Purpose |
|---:|---|---|
| 1 | `spec/runtime-capabilities.md` | Capability registry, degraded paths, local version gates |
| 2 | `spec/balanced-scorecard.md` | Trust/Evidence/Autonomy/Cost definitions and baseline rules |
| 3 | `spec/role-contracts.md` | model/effort/budget/personality/latency contract per role |
| 4 | `spec/plan-evidence.md` | plan-first forge and plan adherence review rule |
| 5 | `spec/role-evals.md` | role MD/skill regression tests and pass criteria |
| 6 | `spec/decision-bridge.md` | user question, approval, policy exception schema |
| 7 | `spec/evidence-graph.md` | claim/evidence/verifier/verdict model |
| 8 | `spec/external-channels.md` | advisory bridge, notification, external command whitelist |
| 9 | `spec/runtime-mirror.md` | runtime twin, process table, native mirror advisory-only |

Existing specs likely touched:

- `spec/state-machine.md`
- `spec/ticket-format.md`
- `spec/review-protocol.md`
- `spec/directory-structure.md`
- `spec/git-workflow.md`

Per project rule, changes to `spec/` require explicit approval before implementation.

## 8. Anti-bets

These are explicitly rejected for this cycle.

| Anti-bet | Rejection |
|---|---|
| Vendor scheduler moves ticket to `done` | Breaks dual-review authority. |
| Image-only evidence | Cannot reconstruct why approval happened. |
| Cloud routine owns ticket lifecycle | `.ct2/` authority is lost. |
| TeamCreate/SendMessage replaces inbox | Runtime-instance persistence is weaker than file inbox. |
| Automatic LLM router | Adds unexplained variance before static contracts are stable. |
| LLM self-evolves roles | Role definitions must remain human-readable and reviewable. |
| Broad agent OS expansion | Dilutes CT2's file-first dual-review kernel. |

## 9. Kill Criteria

| Workstream | Kill or reshape trigger |
|---|---|
| Registry+Baseline | Capability report cannot run offline or mutates state. |
| Cost contracts | $/ticket reduction fails and Trust/Evidence fall together. |
| Plan-mode-first | first-pass approval fails to improve and p50 latency rises >20%. |
| Eval harness | runner cost exceeds budget or catches no real regression over four weeks. |
| Ambient bridge | any external channel directly edits ticket state. |
| Native task mirror | native task mismatch occurs daily or metadata cannot be blocked by hooks/scripts. |

Kill decisions produce `.ct2/postmortems/bet-{n}-kill-{date}.md`.

## 10. Product Requirements

### VAO-1 Capability Registry

CT2 must detect local Codex/Claude runtime capabilities, record degraded paths, and expose them in `ct2-status`.

### VAO-2 Balanced Scorecard

CT2 must collect enough local evidence to compute Trust, Evidence, Autonomy, and Cost/Latency metrics.

### VAO-3 Role Contracts

Each role must have explicit model/effort/budget/latency/personality policy, with enforcement or degradation visible.

### VAO-4 Plan Evidence

Forge must produce plan evidence before execution unless a ticket is explicitly plan-exempt.

### VAO-5 Role Evals

Role definitions and skills must be regression-testable with fixed inputs and machine-readable expected outputs.

### VAO-6 Decision Bridge

Human questions, approvals, and policy exceptions must map to a provider-neutral `.ct2/decisions/` schema.

### VAO-7 Hook Guardrails

Provider hooks should block or warn on invariant violations, while core scripts remain authoritative.

### VAO-8 Evidence Graph

Tickets and sidecars must be able to cite stable evidence ids for commands, screenshots, verifier output, and hook events.

### VAO-9 Advisory Runtime

Watchers, native tasks, cloud routines, Slack/Discord/Gmail/Notion bridges, and remote-control sessions may create advisory records only.

## 11. Decision Log

| Decision | Outcome |
|---|---|
| Use `Verified Autonomy OS` as canonical name | Accepted |
| Limit OS scope to protocol kernel | Accepted |
| Keep `Reliability Platform` as value framing | Accepted as secondary |
| Use a single north star metric | Rejected |
| Use balanced scorecard | Accepted |
| Start with Cost Contracts before measurement | Rejected |
| Start with Registry+Baseline | Accepted |
| Allow native/cloud runtime to mutate ticket state | Rejected |
| Keep runtime/cloud integrations advisory-only | Accepted |
| Rewrite Product Strategy around OS primitives | Accepted |

## 12. Immediate Next Tickets

1. `ct2-runtime-doctor`: probe Codex/Claude versions, features, app-server schema, MCP lists, and role compatibility.
2. `ct2-baseline`: compute initial Trust/Evidence/Autonomy baselines from `.ct2/` and git history.
3. `ct2-balanced-scorecard`: add scorecard rendering to `ct2-status`.
4. `ct2-role-contracts-spec`: draft `spec/role-contracts.md` and `config/harness.yaml` role contract block.
5. `ct2-cost-telemetry`: add `ct2-role-run`, `ct2-cost`, and cost JSONL sink.
6. `ct2-plan-evidence-spec`: define `.ct2/plans/` and plan adherence review requirements.
7. `ct2-role-evals-baseline`: create first eval fixtures for helm, forge, lens-cc, lens-cx.
8. `ct2-decision-bridge-spec`: define `.ct2/decisions/` schema and provider mappings.
9. `ct2-hook-guardrails`: implement hook scripts and script-level validators for core invariants.
10. `ct2-evidence-graph-spec`: define claim/evidence/verifier/verdict records.
11. `ct2-ambient-bridge-notify`: notify-only external bridge with strict whitelist.
12. `ct2-native-task-mirror-spike`: advisory feasibility spike, no production mirror.

## 13. Final Position

CT2 should not chase every new Claude or Codex feature as a product feature. The correct move is to treat vendor capabilities as device drivers behind a stable protocol kernel. The product is not "more agents." The product is **verified autonomy**: every role can act, every action leaves evidence, every state transition is auditable, and no runtime outside `.ct2/` can silently become authority.

The next six weeks should therefore optimize for one thing: proving that this kernel can measure and improve Trust, Evidence, Autonomy, and Cost/Latency at the same time. If that works, CT2 has a defensible product category. If it does not, more automation will only make the system harder to trust.
