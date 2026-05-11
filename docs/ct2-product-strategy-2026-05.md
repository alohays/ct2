# CT2 Product Strategy — From Kanban Harness to Verified Autonomy OS

조사 기준일: 2026-05-10 KST / 2026-05-09 US
대상 런타임: Codex CLI 0.130.0 (실측), Claude Code 2.1.138 (실측, 최신)
작성 의도: `docs/agent-platform-feature-radar-2026-05.md`(이하 "Feature Radar")와 **나란히 읽히는 자매 문서**. Feature Radar가 vendor 표면을 카탈로그화하고 흡수 프로토콜을 정규화한다면, 본 문서는 **Verified Autonomy OS라는 제품 정체성 아래 앞으로 6–12주 동안 무엇을 하지 *않고*, 무엇에 *베팅*할지**를 결정한다. 최종 canonical 계획은 `docs/ct2-verified-autonomy-os-strategy-2026-05.md`로 수렴한다.

## 0. 한 페이지 요약

### 0.1 Feature Radar와의 차이를 한눈에

| 축 | Feature Radar | 본 문서 |
|---|---|---|
| 본질 | **카탈로그** — 모든 표면을 빠짐없이 매핑 | **결심** — Verified Autonomy OS를 위한 5개 베팅 + 6개 anti-bet |
| 권고 형태 | P0/P1/P2 메뉴(9개) | Registry+Baseline 이후 sequenced bets (5개, 죽일 조건 포함) |
| 측정 | OTel/Observability Ledger 인프라 제안 | Trust, Evidence, Autonomy, Cost/Latency balanced scorecard |
| 비용 | 부수적 언급 | Bet 1로 *제품의 1번 lever*로 격상 |
| 사용자 경험 | "검증가능성" 강조 | "검증가능성 + 자고 일어나도 OK" 까지 확장 (Bet 3) |
| Plan-mode | 미언급 | Bet 2의 핵심 (workflow 재정렬) |
| 회귀 방어 | hook guardrails | Bet 4 eval harness로 보강 (role MD 자체를 코드처럼) |
| 경쟁 | 미다룸 | §10.5에서 8+ 인접 시스템과 명시적 대조 |
| 구체 산출물 | 8개 ticket 후보 | spec PR list + 7-day plan + 실 wrapper sketch (부록 C/D/E) |
| 권위 분기 | Native task/scheduler 흡수 시 위험 인식 | *5번째* 베팅으로 의도적 후순위 (가장 매혹적이고 가장 위험) |

읽는 순서 권고: **최종 통합 문서 §0–§5 먼저(canonical direction) → Feature Radar §1–§3(evidence base) → 본 문서 §4–§6(bets/anti-bets) → Feature Radar §4(P0/P1/P2)** — 세 문서를 single review 묶음으로.

### 0.2 결심

**결론.** CT2의 다음 진화는 새 기능을 더 흡수하는 것이 아니라 *제품 정체성*을 한 단계 끌어올리는 것이다. 지금까지 CT2는 "atomic `mv` kanban + dual-review"라는 protocol harness였다. 다음 라운드에서 CT2는 **Verified Autonomy OS** — 즉 여러 agent runtime 위에서 `.ct2/` state, review independence, evidence, budget, schedule, permission을 운영체제 primitive처럼 관리하는 file-first protocol kernel — 이 되어야 한다.

이 framing은 다섯 가지 product bet을 자연스럽게 따라오게 한다:

1. **Cost-aware role contracts** — `--max-budget-usd`, `--effort`, `enable_request_compression`, `fast_mode`, `personality` 같은 "지금 vendor가 stable로 내놓았지만 CT2가 거의 손대지 않은" 표면을 SLO/error-budget 형태로 묶어, 역할별 비용·지연·품질을 *측정 가능한 contract*로 만든다.
2. **Plan-mode-first forge** — Claude `EnterPlanMode/ExitPlanMode`와 Codex `goals` + `tool_search`를 결합해, forge가 *항상 plan을 먼저 sealing*하고 그 plan이 ticket의 일부로 sidecar에 남는 구조로 전환한다.
3. **Ambient CT2 over async channels** — Discord/Slack/MCP channels + `PushNotification`/`RemoteTrigger`를 통해 CT2를 "터미널을 열어야 시작되는 도구"에서 "이메일처럼 알아서 들어오고, 위임할 수 있는 always-on 백그라운드 동료"로 끌어올린다.
4. **Eval harness for roles** — `skill-creator`의 evals 패턴 + `claude --json-schema` + `/ultrareview`를 활용해, 역할 정의(skill MD, role MD, prompt) 자체를 회귀 테스트 가능한 코드로 만든다.
5. **Native task graph mirror (advisory)** — Claude `TaskCreate`/`TaskUpdate`(의존성 `blockedBy` 포함)와 Codex `multi_agent`를 CT2 ticket과 *일대일이 아닌 일대N으로* 거울처럼 비춰, runtime 가시성을 끌어올리되 `.ct2/`의 권위는 유지한다.

**우선 순위.** Phase 0 Registry+Baseline → Bet 1 → Bet 2 → Bet 4 → Bet 3 → Bet 5. Bet 5는 의도적으로 마지막. 가장 *반짝거리지만 가장 위험한* 베팅이라서다(자세한 이유는 §5에서).

**버리는 것.** §6에서 6개 anti-bet을 명시한다 — 화려해 보이지만 CT2의 검증가능성을 깨뜨리는 시도들(클라우드 라우팅에 ticket lifecycle을 위임, 이미지를 단독 evidence로 채택, vendor scheduler에 done 권한 위임 등).

**Feature Radar와의 차이.** Feature Radar는 **포괄성**(Capability Registry, Decision Bridge, Hook Guardrails, Watch Plane, Plugin Distribution …)을 우선했다. 본 문서는 **결심**(어디에 베팅하고 어디에 안 하는지)을 우선한다. 두 문서를 함께 채택하면 Feature Radar의 "P0 Capability Registry / Decision Bridge / Hook Guardrails"는 본 문서의 다섯 bet의 *기반 인프라*로 합류한다 — 부정하는 것이 아니라 그 위에 결심을 올린다.

## 1. Scorecard와 First Principles

### 1.1 Balanced scorecard

CT2는 단일 north star만으로 운영하면 위험하다. Trust만 보면 비용과 지연이 폭증할 수 있고, cost만 보면 검토 품질이 떨어질 수 있으며, autonomy만 보면 잘못된 자동화가 조용히 state authority를 침식할 수 있다. 따라서 Verified Autonomy OS의 성공은 다음 네 축을 함께 본다.

| 축 | 핵심 metric | 의미 |
|---|---|---|
| **Trust** | `done` 후 90일 내 revise/revert/reopen 없는 비율, first-pass approval | 한 번 done 된 결과가 다시 깨지지 않는가 |
| **Evidence** | state transition 중 evidence id와 verifier를 가진 비율 | 왜 approved/done 됐는지 사후 재구성 가능한가 |
| **Autonomy** | heartbeat freshness, blocked->unblocked latency, review latency p95 | 자율 실행이 멈추거나 조용히 stale되지 않는가 |
| **Cost/Latency** | $/ticket p50, ticket latency p50/p95, budget violation | 신뢰성을 유지한 채 비용과 시간을 통제하는가 |

Trust ratio는 scorecard의 첫 축이지만 유일한 north star는 아니다. 정의:

```
Trust ratio (90d rolling) =
  count(tickets that reached `done` and were not revised/reverted/reopened within 90d)
  ──────────────────────────────────────────────────────────────────────────
  count(tickets that reached `done` in window)
```

초기 목표는 Trust ratio ≥ 0.92, Evidence coverage ≥ 0.90, autonomy SLA violation 0건, $/ticket p50 baseline -30%다. 네 축이 같이 좋아지거나 최소한 한 축의 개선이 다른 축의 붕괴를 만들지 않을 때만 제품 개선으로 본다.

### 1.2 First principles 재확인

- **Tickets는 *프로그램*이지 *대화*가 아니다.** Ticket 본문 + frontmatter + sidecar는 declarative spec이고, role은 그것을 실행하는 *runtime*이다. Vendor가 추가하는 어떤 기능도 이 분리를 흐리면 거부한다.
- **`mv`는 commit이다.** State transition을 atomic file rename으로 모델링한 것은 *분산 시스템의 commit*에 해당한다. 이 단순함은 "vendor가 기능을 추가했다고 여기 비비지 마라"는 뜻이다.
- **Reviewer independence ≥ reviewer convenience.** dual-review의 가치는 두 reviewer가 서로의 결과를 *못 본 채로* 결론을 낸다는 데 있다. 이 invariant를 깨는 어떤 productivity 기능도 거절한다.
- **`spec/`이 권위다.** Vendor가 hot한 기능을 내놓아도 spec을 수정하지 않으면 CT2 안에 들어오지 않는다. 본 문서가 만드는 베팅은 *모두* 결국 spec PR로 귀결되어야 한다.
- **External 의존성 0.** bash + python stdlib. 본 문서의 어떤 베팅도 이 룰을 깨지 않는다(JSON schema validator는 stdlib `json` + 수기 검증으로 가능).

### 1.3 CT2가 *아닌* 것

- ❌ "보편적 agent OS" — Cursor, Aider, Claude Project 등이 노리는 자리. CT2는 *opinionated dual-review pipeline*이다.
- ❌ 클라우드 SaaS — `.ct2/`는 로컬, single-user, file-system-first.
- ❌ Linear/Jira 대체재 — ticket은 코드 옆에 산다. 인간 PM 도구를 흉내내지 않는다.
- ❌ 단일 LLM에 묶인 framework — Codex와 Claude의 *동시 활용*이 dual-review의 본질.

## 2. Frame Shift — Verified Autonomy OS as Protocol Kernel

Verified Autonomy OS는 "모든 agent를 포괄하는 범용 OS"가 아니다. CT2가 이미 가진 `.ct2/`, spec-first ticket, atomic `mv`, dual-review sidecar, inbox, reconciler를 **OS primitive처럼 운영 가능하게 만든 protocol kernel**이다. Reliability Platform은 이 kernel이 사용자에게 주는 운영 가치다.

SRE 비유는 여전히 유효하다. 다만 상위 이름은 Reliability Platform이 아니라 Verified Autonomy OS다.

> SRE의 통찰: "복잡한 분산 시스템은 결국 *SLO + error budget + observability + postmortem*의 사이클로 운영된다."
> CT2의 다음 단계: "복잡한 multi-agent 협업 또한 *kernel authority + SLO + budget + evidence + postmortem*의 사이클로 운영된다."

이 비유는 단순한 마케팅 framing이 아니다. 다섯 가지 구체적 product 의사결정을 강제한다:

| SRE 개념 | CT2 매핑 | 즉시 따라오는 의사결정 |
|---|---|---|
| **Service** | Role (helm/forge/lens-cc/lens-cx/status/reconciler) | 각 role은 자기 description, owner, 변경 절차, eval suite를 가진다 |
| **SLO** | role마다 정의된 latency/cost/quality 목표 | `harness.yaml`에 SLO field 추가; 위반 시 자동 escalation |
| **Error budget** | 일/주 단위 누적 *허용 위반량* | budget 소진 시 auto-mode 차단, manual로만 진행 |
| **On-call** | 사람이 있어야 풀리는 inbox 메시지의 *대기 시간* | 일정 시간 미해결 시 PushNotification/Discord ping |
| **Postmortem** | escalated/rejected ticket의 사후 분석 | `.ct2/postmortems/` 디렉터리, monthly summary |

이 framing을 받아들이면 Feature Radar의 P0 세 가지(Capability Registry, Decision Bridge, Hook Guardrails)는 자연스럽게 *기반 인프라* — capacity inventory, request mediator, admission control — 의 위치를 차지하고, 본 문서의 다섯 bet은 그 위에 *서비스 운영* 계층을 올린다. 두 문서가 다투지 않고 위아래로 합류한다.

### 2.1 Layered architecture — 두 문서의 합류 그림

```
        Layer 4 — Visibility (advisory only, no authority)
        ┌────────────────────────────────────────────────────┐
        │  Bet 5: Native task graph mirror (Claude Task*)    │
        │         "ticket → native task" advisory sync       │
        └────────────────────────────────────────────────────┘
        Layer 3 — Operations (UX + quality safety net)
        ┌──────────────────────────┬─────────────────────────┐
        │ Bet 3: Ambient channels  │ Bet 4: Eval harness     │
        │  Discord/Slack bridge,   │  fixed-input regression │
        │  Push/RemoteTrigger,     │  for role MDs / skills  │
        │  inbox amplification     │  (--bare + --json-schema)│
        └──────────────────────────┴─────────────────────────┘
        Layer 2 — Service contract (the SRE-style core)
        ┌──────────────────────────┬─────────────────────────┐
        │ Bet 2: Plan-mode-first   │ Bet 1: Cost contracts   │
        │  EnterPlanMode + goals;  │  per-role model/effort/ │
        │  plans become evidence;  │  budget; SLO violation  │
        │  forge-pre-execution     │  → bounce / hard_deny   │
        └──────────────────────────┴─────────────────────────┘
        Layer 1 — Admission control (Feature Radar P0/P1)
        ┌────────────────────────────────────────────────────┐
        │ Capability Registry · Decision Bridge ·            │
        │ Hook Guardrails · Watch Plane · Observability      │
        └────────────────────────────────────────────────────┘
        Layer 0 — Authority (unchanged, foundational)
        ┌────────────────────────────────────────────────────┐
        │   .ct2/  ·  spec/  ·  AGENTS.md  ·  CLAUDE.md       │
        │       (atomic mv kanban + dual review)              │
        └────────────────────────────────────────────────────┘
```

읽는 룰:

- **위 계층은 아래 계층에 의존하지만, 아래 계층은 위에 의존하지 않는다.** Bet 1–5 모두 죽어도 Layer 0–1은 그대로 작동.
- **권위는 한 방향 — 위로 못 올라간다.** Bet 5가 native task에 무엇을 적든 그것이 Layer 0의 ticket을 못 바꾼다(§4.5와 §6 anti-bet 4번이 같이 박는 룰).
- **트래픽은 양방향 — 정보는 위아래 모두 흐른다.** Layer 0의 ticket 상태 변화 → Layer 4 mirror 업데이트. Layer 3의 외부 메시지 → Layer 1의 Decision Bridge → Layer 0의 inbox.

## 3. Vendor 표면 재감사 — Feature Radar가 충분히 다루지 못한 부분

Feature Radar는 거의 모든 vendor 표면을 짚었다. 그러나 *비용/품질 trade-off* 차원에서 stable로 풀려있는데도 CT2가 손대지 않은 표면이 다섯 개 있다. 본 문서의 베팅들은 이 다섯 개에 직접 의존한다.

| 표면 | 현 상태 | 왜 Feature Radar가 가볍게 다뤘나 | 본 문서가 활용하는 방식 |
|---|---|---|---|
| Codex `personality` (stable) | feature flag로 stable enabled | "tone"은 protocol과 무관하다고 보기 쉽다 | Bet 1: role마다 personality preset을 강제(예: lens는 "skeptical/short", helm은 "interrogative") — 결과의 *style 분산*을 줄여 평가 가능성 ↑ |
| Codex `fast_mode` (stable) | flag stable enabled | latency 최적화는 product 결정이 아닌 줄 알기 쉽다 | Bet 1: status/reconciler처럼 *판단이 거의 없는 역할*은 fast_mode pin |
| Codex `enable_request_compression` (stable) | flag stable enabled | "토큰 압축"은 internal 최적화로 보임 | Bet 1: 큰 thread를 가진 role(helm-auto-cx 같은)에 강제 — token cost 의 가장 큰 단일 lever |
| Codex `guardian_approval` (stable) + Claude `auto-mode hard_deny` (2.1.136) | 양쪽 다 stable | Hook Guardrails로 다뤄졌으나 *role policy*와의 결합은 미정 | Bet 1: lens 역할은 자동 admin 작업 *항상* hard_deny; helm은 budget 초과 시 hard_deny |
| Claude `--max-budget-usd` (CLI) + Claude `--effort` (CLI/`/effort` slash) | 둘 다 stable | "비용은 사용자가 알아서"라고 보기 쉽다 | Bet 1: ticket 우선순위(p0/p1/p2)와 effort/budget pin을 매핑 |
| Claude `--bare` (CLI) | 2.1.x 이후 stable | 디버깅용 모드로 보임 | Bet 4: eval harness가 매 회귀 실행을 `--bare`로 — 실험을 hook/auto-memory 등 외부 변동 변수로부터 격리 |
| Claude `EnterPlanMode/ExitPlanMode` (tool) | stable | "plan mode는 옵션 UX"로 보임 | Bet 2의 핵심 — plan mode를 *기본 forge 진입점*으로 |
| Claude `Monitor` (tool, v2.1.98+) | stable but 일부 환경 미지원 | Watch Plane으로 다뤘지만 *role lifecycle 신호*로의 활용 미정 | Bet 3: monitor → inbox 메시지 → role wakeup 체인 |
| Claude `TaskCreate/TaskUpdate` (tool) | stable, `blockedBy` 의존성 그래프 지원 | "todo list 흉내"로 보일 수 있다 | Bet 5: ticket을 native task로 mirror — runtime 가시성, *권위는 ticket이 유지* |
| Claude `--brief` + `SendUserMessage` (tool) | stable, opt-in | 단순 채팅 채널로 보임 | Bet 3: forge가 짧은 progress message를 user에게 직접 push (inbox 우회 X — *추가* 채널) |
| Codex `tool_search`, `tool_suggest` (stable) | flag stable enabled | "discovery는 LLM이 알아서"로 보임 | Bet 4: eval suite가 tool_search 결과를 결정론적으로 fix하여 회귀 테스트 가능 |
| Codex `unified_exec` (stable) | flag stable enabled | "exec 모드는 한 종류"로 통합돼 안 보이는 것 | Bet 1의 cost SLO 측정 단위 — exec 호출당 token/latency 표준화 |
| Claude `worktree.baseRef` (2.1.133) | stable | Feature Radar에 다뤄졌지만 ticket lifecycle과의 결합 미정 | Bet 2: forge가 plan-mode를 거친 후에만 worktree 생성, baseRef는 ticket frontmatter에서 결정 |
| Claude `--from-pr` (CLI) | stable | 단순 편의 기능 | Bet 4: ultrareview eval 시 PR 컨텍스트 자동 로드 |

(주: `personality`/`fast_mode`/`enable_request_compression`은 0.130.0의 `codex features list`에 stable enabled로 표시되며, 정확한 CLI surface는 `~/.codex/config.toml` profile/flag로 제어된다. 본 문서의 베팅은 "config을 만든다"는 수준이며, 미공개 internal API에 의존하지 않는다.)

## 3.5 Subagent + Memory subsystems — 한 번 더 짚어둘 두 표면

### 3.5.1 Subagent (Agent tool, multi_agent flag)

Claude `Agent` 도구와 Codex `multi_agent` (stable) 둘 다 *spawned worker*를 만든다. CT2의 현 모델은 "lens-cc는 Claude 세션 자체, lens-cx는 Codex 세션 자체" — 즉 *프로세스 단위 격리*. 하지만 forge가 큰 ticket을 처리할 때 *내부적으로* explorer/reviewer 보조 subagent를 부르는 것은 가능하고, 실제로 빈번해진다.

CT2에 즉시 적용할 룰:

- **Subagent는 ticket 권위를 가질 수 없다.** subagent는 ticket frontmatter, sidecar, inbox 메시지를 *작성하지 않는다*. 부모 role이 모은 결과를 작성한다.
- **Subagent budget는 부모의 budget envelope에 포함**(Bet 1과 결합). 즉 forge가 subagent를 3개 띄우면 그 token cost는 forge ticket budget에 합산.
- **Subagent isolation은 worktree로** (Claude `isolation: worktree`, Codex `multi_agent` cap). disjoint write set 검증은 부모 role 책임.
- **lens 역할은 subagent를 띄우지 않는다.** independence가 본질이므로, 검토자가 보조 LLM을 부르는 것 자체가 *외부 신호 유입*. 이 룰은 spec/review-protocol.md에 명문화.

### 3.5.2 Memory subsystem — 기존이 있는데 무엇을 더?

Claude은 `~/.claude/projects/<encoded-cwd>/memory/MEMORY.md` + 개별 메모리 파일로 *프로젝트 단위 자동 메모리*를 가진다. Codex는 `memories` (experimental) + Chronicle. CT2는 spec/CLAUDE.md/AGENTS.md를 *명시적 권위 문서*로 두는 protocol이라 vendor memory와 충돌 가능성이 있다.

CT2의 명시적 입장:

| 정보 종류 | 어디에 사는가 | 왜 |
|---|---|---|
| 프로젝트 사실(아키텍처, 파일 위치, 코딩 컨벤션) | `spec/`, `AGENTS.md`, `CLAUDE.md` | 권위 문서, PR 추적 가능 |
| 사용자 선호(수동/자동) | vendor memory (Claude `MEMORY.md`, Codex memories) | 사용자 단위, 프로젝트 간 이동 |
| 사용자 ↔ CT2 협업 규칙(예: "lens는 항상 skeptical short") | role-contract YAML(Bet 1), eval rubric(Bet 4) | 측정 가능, 회귀 잡힘 |
| 진행 중 ticket/sidecar/inbox | `.ct2/` | single source of truth |
| 세션 간 *agent의 이전 추론 흔적* | vendor memory에 기록되도록 *허용* — 단, ticket 결정은 그것에 의존 안 함 | "agent가 어제 본 내용"이 ticket 권위가 되면 안 됨 |

**spec 추가 룰 (Bet 1 PR과 함께)**: "vendor memory에서 읽은 정보는 ticket frontmatter/sidecar에 *근거 출처*로 인용될 수 없다. ticket의 결정 근거는 ticket 본문, spec, 그리고 명시적으로 cite된 코드 hunk만."

이것은 Bet 4 eval에서도 검증 가능: 같은 input + 같은 role MD에 대해 *memory state가 다른* 두 환경에서 결과가 크게 갈리면 → role MD가 implicit memory에 의존하고 있다는 신호.

## 4. Five Product Bets

각 베팅은 다음 형식이다: **문제 → 가설 → 형상 → 성공 지표 → scope-out → 의존성 → 위험.**

---

### Bet 1: Cost-Aware Role Contracts

#### 4.1.1 문제

CT2는 현재 모든 role이 *동일한 모델·동일한 effort·동일한 personality*를 (사실상) 사용한다. 이는 (a) 비용 비효율, (b) 품질 분산, (c) latency 폭주, (d) 사후 측정 불가능 — 네 가지 문제를 동시에 만든다.

구체적 evidence:

- helm은 *생성적/탐색적* 작업(요구를 ticket으로 분해). 비용 vs. 품질 trade-off에서 품질을 사야 한다 → Opus급/`xhigh` effort/`personality: interrogative`.
- forge는 *수렴적/실행적* 작업(spec → patch). 비용 효율이 우선 → Sonnet/Haiku급/`high` effort/`personality: terse`.
- lens는 *판단/검증* 작업. 결정의 일관성이 우선 → personality fixed, effort medium, fast_mode 금지.
- status는 *순수 조회*. → fast_mode pin, low effort, 가능한 가장 싼 모델.
- reconciler는 *결정론적*. → 이상적으론 LLM 없이 bash. 현재 그렇다(유지).

지금은 이 모든 차이가 *암묵적*이고, role MD의 영문 prompt에 흩어져 있다. 측정도 안 된다.

#### 4.1.2 가설

각 role에 대해 *contract* — `(model, effort, personality, budget_per_ticket_usd, latency_slo_seconds, fast_mode, request_compression)` — 를 명시적으로 선언하면, (a) $/ticket이 측정 가능해지고, (b) 위반 시 자동 차단/escalation이 가능해지고, (c) 변경이 PR로 추적 가능해진다.

#### 4.1.3 형상

`harness.yaml`에 신규 `role_contracts` 블록:

```yaml
role_contracts:
  ct2-helm:
    model: opus
    effort: xhigh
    personality: interrogative   # codex; for claude this maps to skill prompt preamble
    budget_per_session_usd: 2.50
    latency_slo_seconds: 120
    request_compression: false
    fast_mode: false
    on_budget_exceeded: hard_deny  # block further LLM calls; require manual /unblock
  ct2-forge:
    model: sonnet
    effort: high
    personality: terse
    budget_per_ticket_usd: 1.50
    latency_slo_seconds: 600
    request_compression: true       # large thread tolerance
    fast_mode: false
    on_budget_exceeded: bounce      # send budget-exceeded inbox; ticket → backlog
  ct2-lens-cc:
    model: opus                     # judgment over speed
    effort: high
    personality: skeptical-short
    budget_per_review_usd: 0.40
    latency_slo_seconds: 90
    fast_mode: false                 # never on review
    request_compression: true
  ct2-lens-cx:
    model: gpt-5.4-default
    effort: high
    personality: skeptical-short
    budget_per_review_usd: 0.40
    latency_slo_seconds: 90
    fast_mode: false
  ct2-status:
    model: haiku
    effort: low
    personality: terse
    budget_per_run_usd: 0.05
    latency_slo_seconds: 8
    fast_mode: true
    request_compression: false
```

CLI 통합 (예시 — Claude 측):

```bash
# claude-plugin/skills/ct2-forge/SKILL.md 가 호출하는 wrapper
claude \
  --agent ct2-forge \
  --model "${CT2_FORGE_MODEL:-sonnet}" \
  --effort "${CT2_FORGE_EFFORT:-high}" \
  --max-budget-usd "${CT2_FORGE_BUDGET:-1.50}" \
  --include-hook-events \
  -p "$(cat .ct2/in-progress/${TICKET}.md)"
```

Codex 측은 profile per role:

```toml
# ~/.codex/profiles/ct2-forge.toml
model = "gpt-5-codex"
effort = "high"
personality = "terse"
fast_mode = false
enable_request_compression = true
```

신규 도구: `bin/ct2-cost` — `.ct2/telemetry/cost.jsonl`을 읽고 (a) role × ticket 별 누적 비용, (b) SLO violation event, (c) budget remaining을 출력. `ct2-status`에 한 줄로 합류.

#### 4.1.4 성공 지표

- **$/ticket(p50)**가 baseline 대비 30% 감소(forge가 sonnet/haiku로 적절히 강등될 때)
- **lens latency p95**가 90초 이하
- 한 분기 동안 budget hard_deny 발동 횟수 ≥ 0회 (즉, budget이 SLO 게이트로 *작동했고* 미수렴 작업을 차단했다)
- Trust ratio가 떨어지지 *않은* 채로 위 cost 효과 달성

#### 4.1.5 Scope-out

- LLM router(자동 모델 선택)는 이번 베팅에 *포함하지 않는다*. 결정은 정적 contract로 시작. router는 6개월 뒤 재고.
- 사용자별 cap, organization 단위 limit는 out-of-scope (single-user 제품).

#### 4.1.6 의존성

- Feature Radar의 P0 Capability Registry — 어떤 role에서 `--max-budget-usd`/effort가 실제로 가용한지 알아야 contract enforce 가능.
- Codex 측 `personality`, `fast_mode`, `enable_request_compression`의 정확한 config surface 확정 — `codex` 0.130.0에서 stable 표시이지만 본 문서 작성 시점에 spec 페이지에 명시적으로 문서화돼 있지 않으므로, **spike (1일)**로 실측 후 contract 형상 확정.

#### 4.1.7 위험

| 위험 | 완화 |
|---|---|
| Sonnet으로 forge 강등 시 trust ratio 하락 | A/B: 신규 contract로 50 ticket 처리 후 trust ratio 비교; 회귀 시 model upgrade 옵션 |
| `--max-budget-usd`가 작업 *중간*에 끊겨 부분 완료 ticket 양산 | budget이 끊기면 forge가 `bounce` (in-progress → backlog)하도록; *부분 patch는 절대 commit 안 함* |
| Codex personality preset이 lens의 reviewer-independence에 영향 | personality은 *스타일* layer로만 사용, 결정 logic은 spec/role MD에 그대로 |

---

### Bet 2: Plan-Mode-First Forge

#### 4.2.1 문제

현재 forge는 ticket을 받으면 *즉시 코드 작업*에 들어간다. 그 결과:

- ticket의 ambiguity가 forge의 첫 patch에서 드러남 → lens rejection → rework
- forge의 plan(어떤 함수를 어떻게 수정할지)은 *작업 후*에 commit message나 sidecar 응답으로만 남는다. 사후 검증 불가.
- 이것은 "plan은 무료, code는 비싸다"라는 LLM 비용 곡선과 정확히 반대로 가는 patten.

#### 4.2.2 가설

forge가 *항상* `EnterPlanMode`로 시작하고, plan을 sealing한 뒤에만 `ExitPlanMode`로 진입하도록 구조를 강제하면, (a) ambiguity가 코드 작성 *전*에 드러나고 (b) plan 자체가 ticket sidecar(`.ct2/plans/{id}-r{n}.md`)로 보존되어 lens가 plan과 patch를 *함께* 검토할 수 있다.

#### 4.2.3 형상

ticket lifecycle 확장:

```
backlog → in-progress(planning) → in-progress(executing) → in-review
              │                          ▲
              │ EnterPlanMode →          │ ExitPlanMode (plan approved)
              │ plan written to          │ + plan saved to .ct2/plans/{id}-r{n}.md
              │ .ct2/.tmp/plan-...md     │
              ▼                          │
          plan-stale?  ──No──────────────┘
              │ Yes
              ▼
         abort, bounce to backlog
```

신규 spec 룰 (review-protocol.md addition):

> **Plan-evidence rule.** lens의 sidecar는 다음 중 하나를 만족해야 한다:
> (a) `.ct2/plans/{id}-r{n}.md`가 존재하고, sidecar의 "Plan adherence" 섹션이 plan 대비 patch의 일치도를 평가했다.
> (b) ticket이 `plan-exempt: true`이고 Acceptance Criteria가 3개 이하인 단순 ticket이다.

Codex 측 매핑: `goals` + `tool_search`. forge는 ticket 진입 시 `/goal` 생성 → `tool_search`로 후보 surface 탐색 → goal 노트가 plan으로 변환되어 `.ct2/plans/`에 저장.

#### 4.2.4 성공 지표

- review-round=1 first-pass approval rate 가 +15pp 이상 상승
- p50 ticket 완료 시간이 baseline 대비 *증가하지 않음* (plan 단계가 코드 rework 시간을 갈음)
- lens sidecar에서 "scope creep" 지적 빈도 -50%

#### 4.2.5 Scope-out

- plan-mode를 helm/lens에 강요하지 않는다(이들은 본디 plan-shaped 작업).
- "plan을 LLM이 자동 검증" 기능은 out-of-scope. plan은 ticket의 일부로 lens 인간/모델이 검토.

#### 4.2.6 의존성

- Claude 2.1.136의 plan mode write-block 수정(이전 버전에는 plan 모드에서 file write가 누수되는 버그가 있었다 — local 2.1.138은 OK).
- Codex `goals` 안정화 (현재 experimental); `goals` 가 GA되면 매핑이 더 견고해진다.

#### 4.2.7 위험

| 위험 | 완화 |
|---|---|
| plan-mode 강제가 너무 무거워 단순 ticket에 마찰 | `plan-exempt: true` flag in ticket frontmatter |
| plan과 patch가 어긋날 때 lens가 plan을 *진리*로 잘못 사용 | spec에 명시: "Acceptance Criteria가 진리, plan은 trace" |
| Codex `goals`의 experimental 상태 | Claude 측 plan-mode를 우선 도입; Codex는 fallback (goal-less plan note) 허용 |

---

### Bet 3: Ambient CT2 — Async Agents over Channels

#### 4.3.1 문제

CT2는 사용자가 *터미널을 열어야* 시작된다. 결과:

- 자정에 도착한 PR comment를 다음날 아침까지 forge가 모름.
- 동료(혹은 미래 다인 사용)가 Slack으로 "이 ticket 우선순위 올려줘"라고 해도 들어오지 못함.
- helm이 "이 클라리피케이션이 필요해"라고 inbox에 적어도, 사용자가 안 보면 그대로 멈춤.

이것은 "협업 도구"라기보다 "command-line 비서"의 한계다.

#### 4.3.2 가설

CT2 inbox와 외부 채널(Discord/Slack/Gmail/Notion) 사이에 *얇은 양방향 bridge*를 두면, CT2는 *터미널 밖에서도* 일하기 시작한다. 핵심은 "외부에서 ticket을 *수정*하지 않는다 — `.ct2/`는 여전히 single source of truth — 하지만 메시지/알림/위임 요청은 자유로이 흐른다"이다.

#### 4.3.3 형상

```
                ┌──────────────────────────────────┐
                │       External channels          │
                │ Discord / Slack / Gmail / Notion │
                └──────────────────────────────────┘
                          ▲              │
                  (notify)│              │(command)
                          │              ▼
                ┌──────────────────────────────────┐
                │       ct2-bridge                 │
                │  - PushNotification on inbox new │
                │  - RemoteTrigger on /ct2 command │
                │  - SendMessage→inbox             │
                │  - filter: never modifies tickets│
                └──────────────────────────────────┘
                          ▲              │
                          │              ▼
                ┌──────────────────────────────────┐
                │        .ct2/inbox/{role}/        │
                │   (single source of truth)       │
                └──────────────────────────────────┘
```

지원하는 외부 동작 (whitelist):

| 외부 명령 | 효과 | 권한 |
|---|---|---|
| `/ct2 status` | `ct2-status` 한 줄 요약을 채널에 붙임 | 모두 |
| `/ct2 priority {id} {p0|p1|p2}` | helm inbox에 priority-override 메시지 작성 | 명시 ALLOW 사용자 |
| `/ct2 unblock {id}` | inbox blocked 처리 후 forge 재개 | 명시 ALLOW |
| `/ct2 clarify {id}: <text>` | helm → forge clarification 메시지 | 명시 ALLOW |
| (그 외) | 거절. ticket 직접 편집은 *영구히* 외부에서 불가능 | — |

알림 시점 (PushNotification):

- escalated 도달 (사람 개입 필요)
- helm inbox에 blocked 메시지 도착 → 일정 시간(예: 30분) 미해결
- ultrareview 결과 critical issue 발견
- budget hard_deny 발동
- nightly summary (옵션)

#### 4.3.4 성공 지표

- p95 "blocked → unblocked" wallclock 시간이 baseline 대비 -70%
- 외부 채널을 통한 ticket 변경(직접 수정) 시도 *0회* (= invariant 유지)
- 사용자 설문: "잠자기 전에 forge에게 일을 맡기고 자고 일어나도 정상"이라는 응답 ≥ 4/5

#### 4.3.5 Scope-out

- 멀티 사용자 ticket 편집/소유권 분리는 out-of-scope (single-user 가정 유지).
- bridge 본체를 Claude/Codex 어느 한쪽에 묶지 않는다 — 별도 bash daemon으로 구현(외부 의존 0 룰을 위해 `gh`, `discord`/`slack` MCP만 사용).

#### 4.3.6 의존성

- Discord MCP / Slack MCP의 안정성 (현 환경에 connected).
- `PushNotification`/`RemoteTrigger` 권한 — Claude `--remote-control` 세션에서.

#### 4.3.7 위험

| 위험 | 완화 |
|---|---|
| "외부에서 ticket 수정" 유혹 → invariant 붕괴 | bridge 내부에 strict whitelist; ticket file 직접 쓰기는 코드상 *불가능*하게 |
| 알림 폭주(noise) | per-channel 일/시간당 cap; 동일 종류 알림 dedup window |
| Slack/Discord에 secret 누출 | bridge가 ticket 본문/sidecar 본문은 *절대* 외부로 보내지 않음 — id/제목/상태만 |

---

### Bet 4: Eval Harness for Roles

#### 4.4.1 문제

CT2 role 정의(`config/ct2-lens-cc-role.md`, `config/ct2-lens-cx-role.md`, plugin SKILL.md)는 *코드*인데 *테스트가 없다*. Role MD를 한 줄 고치면:

- forge가 더 보수적/공격적으로 변할 수 있고
- lens가 같은 patch를 어제와 다르게 평가할 수 있고
- helm이 ambiguity 처리 방식을 바꿀 수 있다

그러나 우리는 그것을 *measure*할 방법이 없다. 결과적으로 role MD 수정은 "느낌"으로 진행되고, 회귀를 잡을 수 없다.

#### 4.4.2 가설

`skill-creator`의 evals 패턴 + `claude --json-schema` + `claude --bare`를 활용해, 각 role마다 *fixed-input regression suite*를 만들면 role MD/skill MD/role config 변경의 영향을 *수치로* 잡아낼 수 있다.

#### 4.4.3 형상

```
.ct2/evals/
├── ct2-helm/
│   ├── case-001-vague-feature-request/
│   │   ├── input.md         # 사용자가 helm에 던지는 요청 raw
│   │   ├── expected.json    # 기대 ticket frontmatter (subset match)
│   │   └── rubric.md        # 사람이 읽고 채점 가능한 정성 기준
│   └── case-002-...
├── ct2-forge/
│   ├── case-001-clear-spec/
│   │   ├── repo-snapshot.tar  # forge가 작업할 미니 repo
│   │   ├── ticket.md
│   │   ├── expected-files/    # 기대 patch 결과
│   │   └── rubric.md
│   └── ...
├── ct2-lens-cc/
│   └── case-001-buggy-patch/
│       ├── ticket.md
│       ├── patch.diff
│       └── expected-sidecar.json  # 기대 verdict, 기대 issue 키워드
└── runner.sh
```

`runner.sh`는 매 케이스에 대해:

1. 깨끗한 임시 디렉터리에 case 자료 펼침.
2. `claude --bare --agent ct2-{role} --json-schema <schema> -p <input>` 실행 — `--bare`로 외부 변수(auto-memory, hook, plugin sync) 제거.
3. 결과를 `expected-*.json` 대비 deep-subset 비교 + LLM-as-judge로 정성 채점 (`/ultrareview`?? — 아니, 지나친 의존; 단순 별도 claude 호출로 채점).
4. role × case × commit 별 score 행을 `.ct2/evals/results.jsonl`에 누적.

신규 ticket type: `eval-regression` — role MD 수정 PR이 들어오면 자동으로 이 ticket이 생성되어 baseline 대비 회귀를 보고.

#### 4.4.4 성공 지표

- role MD 변경 PR 중 eval 회귀로 차단된 비율 ≥ 1건/분기 (= harness가 실제 회귀를 잡고 있다)
- 각 role 당 ≥ 5개 eval case 가 6주 안에 자리잡음
- runner 1회 실행 비용 ≤ $0.50 / role (Bet 1과 결합)

#### 4.4.5 Scope-out

- "role을 LLM이 자동 최적화" — out-of-scope. eval은 *방어적*이다, 진화는 사람이.
- helm/forge eval은 작은 fixture repo로만 — 실 repo 회귀는 너무 비싸고 비결정론적.

#### 4.4.6 의존성

- `--bare` 모드의 stable 동작.
- `--json-schema` (현 stable).
- (옵션) `skill-creator` skill — 우리가 만드는 게 아니라 fold-in.

#### 4.4.7 위험

| 위험 | 완화 |
|---|---|
| LLM-as-judge 비결정론 → noisy eval | rubric 기반 정량 metric을 우선; LLM 채점은 보조 metric |
| eval suite가 prompt를 *과적합*하게 만든다 | case 추가는 특정 PR 회귀 잡기보단 *실 ticket 표본*에서 추출 |
| eval 비용이 contract budget 초과 | runner는 별도 budget envelope; ticket budget과 분리 |

---

### Bet 5: Native Task Graph Mirror (Advisory)

#### 4.5.1 문제

CT2 ticket은 파일이고, runtime(Claude `TaskList`, Codex `multi_agent`)은 별도의 task 표현을 가진다. 이 둘이 *완전히 분리*되어 있어:

- Claude 세션 안에서 "지금 CT2가 뭘 하고 있나"가 안 보임 — `TaskList`에 안 뜸.
- runtime이 background에서 task를 진행해도 ticket 진행률에 반영되지 않음.
- 사용자는 runtime UI에서 task 봤다가 `ct2-status`에서 또 ticket 봐야 — 인지 부하 ↑.

Claude `TaskCreate`는 `blockedBy` 의존성을 native 지원한다. CT2의 ticket dependency(현재는 없음)와 자연스럽게 매핑된다.

#### 4.5.2 가설

ticket 상태 변화 시 native task를 *advisory*로 mirror하면 — 그러나 native task로는 ticket state를 *바꾸지 못하게* 하면 — 인지 통일성은 얻고 권위는 잃지 않는다.

이 가설을 *마지막* bet으로 둔 이유: 거꾸로 흐를 위험이 가장 크다. 네이티브 task가 보기에 편리해서 사용자가 그 위에서 작업하다가 ticket과 동기화가 깨질 수 있다.

#### 4.5.3 형상

방향성: **CT2 → native = OK, native → CT2 = 차단**.

```
ct2-status / ticket transition:
  → for each ticket in {backlog, in-progress, in-review}:
       TaskCreate (if not present) with metadata:
         {ct2_ticket_id: "001", ct2_state: "in-progress", ct2_round: 0}
       TaskUpdate (if present) status to mirror ticket state:
         backlog → pending
         in-progress → in_progress
         in-review → in_progress (with note "in review")
         done → completed
         rejected → pending (with note)
         escalated → completed (with note "escalated, needs human")

native TaskUpdate hook (PreToolUse):
  → if task has ct2_ticket_id metadata and update is from non-CT2 source:
       block with message "CT2 tickets are authoritative; edit .ct2/{id}.md"
```

CT2 ticket frontmatter 확장(optional):

```yaml
depends_on: ["003-refactor-pool", "008-migration"]
```

→ `TaskCreate(addBlockedBy=[task_id_of_003, task_id_of_008])`로 매핑.

#### 4.5.4 성공 지표

- 사용자 설문: "ticket과 native task가 일치하는가" → ≥ 4/5
- "native task 통해 ticket 상태가 잘못 바뀐 사례" → 0건
- mirror 동기화 latency p95 < 5초

#### 4.5.5 Scope-out

- 양방향 동기화 — 영구히 out-of-scope. 권위 분기는 CT2 정체성을 깬다.
- TeamCreate/SendMessage 통합 — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 게이트 뒤에 있고 본 분기 진행에 의존하지 않는다. 모니터링.

#### 4.5.6 의존성

- Claude `TaskCreate/TaskUpdate` (stable).
- PreToolUse hook이 metadata 검사 가능한지 spike 필요(Bet 4의 eval 같은 환경에서 점검 가능).

#### 4.5.7 위험

| 위험 | 완화 |
|---|---|
| native task와 ticket 동기화 깨짐 | reconciler가 매 loop에서 mismatch 검출하면 ticket *우선*으로 강제 sync; mismatch event 로깅 |
| 사용자가 native task를 직접 편집해 의존성 그래프 변경 | hook으로 차단; 차단 시 친절한 안내 메시지 |
| TaskCreate API 변경 | Claude version pin (Capability Registry — Feature Radar P0와 자연스럽게 합류) |

---

## 5. 우선순위와 sequencing

### 5.1 왜 이 순서인가

**Phase 0 (Registry+Baseline) 먼저** — 어떤 runtime 기능이 실제로 가용한지, 현재 trust/evidence/autonomy/cost baseline이 얼마인지 모르면 어떤 베팅도 제품 효과로 판정할 수 없다. Capability Registry와 empirical baseline은 bet이 아니라 admission gate다.

**Bet 1 (Cost contracts) 두 번째** — 비용/지연을 *측정*할 수 있어야 다른 베팅의 효과를 평가할 수 있다. 다른 모든 베팅의 ROI 분모.

**Bet 2 (Plan-mode-first) 세 번째** — Trust ratio와 Evidence coverage에 직접 영향. forge rework가 줄어들면 lens latency도, $/ticket도, p50 latency도 동시에 좋아짐.

**Bet 4 (Eval) 네 번째** — Bet 1, 2가 만든 변화가 *회귀하지 않도록* 잠금. Bet 3, 5에 들어가기 전에 안전망.

**Bet 3 (Ambient) 다섯 번째** — UX 개선이지만 invariant 위험이 있다. eval/contract가 자리잡은 뒤에 도입.

**Bet 5 (Task mirror) 마지막** — *가장 매혹적이고 가장 위험*하다. 네이티브 task가 보기에 좋다는 이유로 권위 분기를 만들 유혹. 다른 4개가 안정된 후에야 실험.

### 5.2 6-week sprint plan

| 주차 | 베팅 | 산출물 | exit criteria |
|---|---|---|---|
| 0-1 | Phase 0 Registry+Baseline | `ct2-runtime-doctor`, `bin/ct2-baseline`, `.ct2/telemetry/baseline-2026-05.json` | Codex/Claude capability와 balanced scorecard baseline이 기록됨; state mutation 없음 |
| 1 | Bet 1 spike | Codex `personality`/`fast_mode`/`enable_request_compression` 실측 보고서; `harness.yaml` `role_contracts` 초안 | 5개 role 모두 contract 안에 있음; CLI 명령으로 dry-run 검증 |
| 2 | Bet 1 impl | role wrapper 스크립트, `bin/ct2-cost`, telemetry sink | 1주간 실 ticket 처리 시 cost.jsonl이 기록되고 `ct2-status`에 표출 |
| 3 | Bet 2 spike + impl | plan-mode integration, `.ct2/plans/` 디렉터리, spec 업데이트 PR | 5개 ticket을 plan-mode-first로 처리; first-pass approval 비교 |
| 4 | Bet 4 baseline | helm/forge/lens 각 3 case eval suite, runner.sh, baseline 측정 | role MD 한 줄 의도적 변경 시 eval에서 잡혀나옴 |
| 5 | Bet 3 phase-1 | `ct2-bridge` daemon, Discord/Slack notify only(읽기전용), 알림 정책 | 5개 PushNotification 발송 로그; ticket modification 시도 0건 |
| 6 | Buffer + retro | postmortem, balanced scorecard 1차 측정, Bet 5 spike (실 mirror 시도 X) | Trust/Evidence/Autonomy/Cost scorecard 보고; 다음 6주 plan |

### 5.2.1 Empirical baseline plan — "측정 없이 베팅하지 말라"

본 문서의 모든 metric은 *baseline 대비*로 표현된다. 그러나 현재 CT2에는 cost/latency/trust/evidence/autonomy 측정 인프라가 없다. 베팅을 시작하려면 *최소한* 다음 baseline이 필요하다. Phase 0에서 먼저 수행하고, Bet 1 spike와 병행 가능한 항목만 병행한다.

| Baseline | 수집 방법 | 기간 | 목표 표본 |
|---|---|---|---|
| Trust ratio (현재) | `git log --grep "ct2-revise"` + `done/` 디렉터리 회귀 분석. ticket이 done 도달 후 revise/revert/reopen 됐는지 시점별로 카운트. | 직전 90일 git history 회고 | ≥ 20 done ticket |
| First-pass approval rate | `.ct2/reviews/`에서 `*-r0` sidecar의 verdict 분포(존재 시) | 직전 90일 | ≥ 20 review event |
| Evidence coverage | `done/` 전이 ticket 중 sidecar, command evidence, verifier result가 연결된 비율 | 직전 90일 | ≥ 20 done ticket |
| $/ticket | **수집 인프라 없음** — Bet 1 spike 산출물에 포함. baseline은 0주차 사후 구성. | 1주차 ~ 2주차 병행 | 이번 sprint 처리되는 ticket 전수 |
| ticket latency (sealed → done) | ticket frontmatter `sealed` 와 `updated` (verdict=approved 시) 차이 | 직전 90일 | ≥ 20 |
| review latency (in-review entry → reconciler verdict) | `.ct2/reviews/` mtime + ticket mtime cross | 직전 90일 | ≥ 20 |
| blocked → unblocked latency | `.ct2/inbox/{role}/done/` 의 blocked 메시지 mtime → 다음 helm 응답 메시지 mtime | 직전 90일 | ≥ 5 (rare event) |

**산출물**: `bin/ct2-baseline` (1회용 파이썬 스크립트, stdlib만), `.ct2/telemetry/baseline-2026-05.json`. 본 문서 §9 success metric의 "baseline 대비" 수치는 모두 이 파일을 reference. baseline이 아예 안 잡히는 metric(특히 $/ticket)은 본 sprint 내 *측정 시작* 자체가 deliverable이다 — "baseline 0에서 시작" 기록.

**중요한 솔직함.** 실 데이터가 적으면(예: done이 5건뿐), p50/p95 통계는 무의미하다. 그 경우엔 metric을 *비율*(승률 같은)로 단순화하고, 6주 후 sprint 종료 시점에 신규 sprint 데이터로 대체. 통계가 의미를 갖기 전에 "trust ratio 0.92"를 주장하지 않는다.

### 5.3 90-day vision

- Bet 3 phase-2 (외부 명령 whitelist 활성화)
- Bet 5 mirror 활성화(advisory만)
- eval suite 30+ cases per role
- 모든 PR에 자동 eval CI
- multi-machine 사용을 위한 `.ct2/runtime/sessions.json` registry

### 5.4 12-month vision

- Cloud delegation pilot (Feature Radar의 P2와 합류) — *advisory only, ticket 권위 유지*
- Multi-tenant 실험 — single-user 룰을 *깨지 않은 채* 같은 repo에서 두 사람이 ticket 분담하는 방법
- Multimodal evidence (Feature Radar P2)
- "CT2 as plugin marketplace" — 다른 팀이 자기 role을 만들고 공유

## 6. Anti-bets — 매혹적이지만 거절

다음 6개는 의식적으로 *하지 않는다*. 각각 거절 이유를 명시한다 — 미래의 PR/제안이 들어오면 이 섹션을 인용해 거절하기 위해서.

| Anti-bet | 매혹 | 거절 이유 |
|---|---|---|
| **vendor scheduler가 ticket을 done으로 보낸다** | 자동화 끝판왕 | dual-review 권위가 vendor cron으로 분기됨. CT2 정체성 붕괴. |
| **이미지가 단독 evidence가 된다** | UI ticket이 빠르게 닫힘 | 검증 가능한 텍스트 trace가 없으면 "왜 approved 됐는지"를 사후 재구성 불가 |
| **클라우드(Codex Cloud, Claude Routines)에 ticket 라이프사이클 위임** | 백그라운드로 계속 도는 자동화 | `.ct2/`가 권위라는 룰 깨짐. cloud는 *executor*만, *판정*은 못 함. |
| **TeamCreate/SendMessage가 inbox를 대체** | runtime native primitives | 1) experimental flag 게이트, 2) 메시지의 *인스턴스 단위 영속*이 inbox의 단순함보다 약함 |
| **자동 LLM router** | role마다 비용/품질 자동 최적화 | 정적 contract도 안 굳혀진 상태에서 router는 디버깅 불가능한 변동성 추가 |
| **role을 LLM이 자동 진화** | "self-improving CT2" | 사람이 role을 *읽을 수 있어야* 한다는 디자인 룰 깨짐. eval은 회귀 *방어*, 진화는 사람이. |

## 6.5 Kill criteria — 베팅을 *언제 끄는가*

성공 지표만 박는 것은 위험하다. "잘 안 되어도 매몰비용 때문에 계속 가는" 함정. 베팅별 *kill criteria* — 3주차 mid-point에서 다음 trigger가 발생하면 그 베팅을 중단/재형상.

| Bet | 3-week kill trigger | 6-week kill trigger |
|---|---|---|
| **1 Cost contracts** | spike에서 `personality`/`fast_mode`/`request_compression` 중 ≥ 2 표면이 실제로 작동 안 함 (문서엔 stable이지만 실측 불일치) | $/ticket 30% 감소 미달 *그리고* trust ratio도 함께 하락 — 양쪽 모두 실패 시 contract 자체 폐기 |
| **2 Plan-mode-first** | 처음 3 ticket에서 plan→patch 흐름이 사용자 마찰 폭증(즉, helm/forge가 plan mode에서 빠져나오지 못함) | first-pass approval rate +15pp 미달 *그리고* p50 ticket latency +20% 이상 — 비용만 늘었다 |
| **3 Ambient bridge** | 첫 알림 5건 중 ≥ 1건이 false alarm 또는 중복 noise | 외부에서 ticket 수정 시도 발생 (단 1회라도) — invariant 깨짐 |
| **4 Eval harness** | runner 1회 실행이 $5+ (개별 case 비용 폭주) | 4주 누적 회귀 검출 0건 — eval suite가 noise만 잡고 있다 |
| **5 Task mirror** | spike에서 PreToolUse hook이 metadata 검사 불가 — 차단 메커니즘 없음 | mismatch event(ticket과 native task 어긋남)이 일/회 이상 발생 — 동기화 비용이 가시성 ROI 초과 |

Kill 결정 시 다음 trail을 남긴다: `.ct2/postmortems/bet-{n}-kill-{date}.md` — 사유, 측정값, 대안. 죽인 베팅을 *3개월 안에* 다시 동일 형상으로 시도하지 않는다(다른 형상은 OK).

### 6.6 Per-bet spec PR list — 무엇을 spec에 박는가

각 베팅이 만들어낼 spec 변경. 코드 PR은 별개; 여기는 *권위 문서* PR만.

| Bet | 신규 spec 파일 | 기존 spec 수정 |
|---|---|---|
| 1 Cost contracts | `spec/role-contracts.md` (신규) | `spec/state-machine.md`에 budget-bounce transition; `config/harness.yaml` 템플릿에 `role_contracts` 블록 |
| 2 Plan-mode-first | `spec/plan-evidence.md` (신규) | `spec/review-protocol.md`에 plan-evidence rule; `spec/ticket-format.md`에 `plan-exempt` field; `spec/state-machine.md`의 in-progress 분할 |
| 3 Ambient bridge | `spec/external-channels.md` (신규) | `spec/review-protocol.md`의 inbox 섹션에 외부 origin 메시지 처리 |
| 4 Eval harness | `spec/role-evals.md` (신규) | `config/ct2-lens-*-role.md`에 eval 적용 의무; `AGENTS.md`에 role MD 변경 시 eval 통과 요구 |
| 5 Task mirror | `spec/runtime-mirror.md` (신규) | `spec/state-machine.md`에 mirror sync 규칙; `spec/directory-structure.md`에 `.ct2/runtime/mirror/` |

CT2 정신("spec is authoritative")의 일관성을 유지하기 위해, **코드 PR은 spec PR이 머지된 후에만** 진행. spec PR이 의도된 형상을 통과하지 못하면 베팅 자체를 재형상.

## 7. Hidden primitives — 어디에 묻혀있나

본 섹션은 Feature Radar에 *없거나 가볍게* 다뤄졌고 본 베팅들에 직접 안 쓰지만, 후속 베팅의 재료가 될 수 있는 표면들. 인덱스로만.

- **Codex `tool_call_mcp_elicitation` (stable).** MCP tool이 user에게 elicitation 가능 — Bet 3의 외부 채널 명령 검증에 활용 후보.
- **Codex `enable_request_compression` (stable).** Bet 1에 일부 활용. helm-auto-cx 같은 long-thread role에 강제하면 token 절감 큼.
- **Codex `image_generation` + `image_input` + `view_image` (stable).** UI ticket의 *비주얼 spec*에 사용. Feature Radar P2 다중모달과 합류.
- **Claude `--exclude-dynamic-system-prompt-sections` (CLI).** prompt cache hit rate 개선 — Bet 1의 cost lever 보조.
- **Claude `--include-hook-events` (CLI).** Bet 4 eval 시 hook 작동 trace 검증에 사용.
- **Claude `--fork-session` (CLI).** lens가 같은 ticket을 두 가지 angle로 검토할 때(예: security 관점 + perf 관점) — 후속 베팅 후보.
- **Claude `LSP` tool.** forge가 patch 후 type error를 *자동* 인지. lens sidecar의 "AC: tests pass" 검증 보조.
- **Codex `child_agents_md` (under development).** subagent 별 AGENTS.md 분리 — 안정화되면 lens-cc/lens-cx의 *완전 격리*에 강력. 6개월 후 재고.
- **Claude `claude project purge` (2.1.126+).** 임시 ticket workspace 클린업.
- **Claude `--from-pr`.** lens가 PR 컨텍스트를 함께 로드해 review.

## 8. Risk Register

| ID | 위험 | 영향 | 가능성 | 완화 |
|---|---|---|---|---|
| R-01 | Bet 1 contract가 trust ratio를 떨어뜨림 | 高 | 中 | A/B with 50-ticket window; 회귀 시 model 한 단계 upgrade |
| R-02 | plan-mode 강제가 사용자 마찰 만듦 | 中 | 中 | `plan-exempt` flag; 6주 후 사용자 NPS 측정 |
| R-03 | Discord/Slack bridge에서 secret 누출 | 高 | 低 | 본문은 절대 외부로; id/title/state만 |
| R-04 | eval 비용이 cost contract 깨뜨림 | 中 | 中 | 별도 budget envelope; 하루 cap |
| R-05 | native task mirror 권위 분기 | 高 | 中 | Bet 5를 마지막에; advisory-only; 차단 hook |
| R-06 | Codex experimental feature(`goals`)에 깊게 의존 | 中 | 中 | Claude plan-mode를 우선; Codex는 fallback |
| R-07 | vendor 버전 drift | 中 | 高 | Capability Registry(Feature Radar P0)와 합류; min-version 게이트 |
| R-08 | "always-on" Bet 3가 인지부하 폭증(알림 지옥) | 中 | 中 | per-channel cap, dedup, snooze |
| R-09 | role MD 변경 PR이 eval 통과를 *과적합* | 低 | 中 | case 모집을 실 ticket sample에서; 분기별 case 회전 |
| R-10 | single-user 가정이 실 사용 시 깨짐(공유 repo, 2인 사용) | 中 | 低 | 12개월 vision으로 미루고, 그 전엔 명시적 거절 |

## 9. Success Metrics — 어떻게 "잘 된 것"을 알 것인가

90일 후 다음 balanced scorecard로 self-grade:

1. **Trust:** Trust ratio (90d) ≥ 0.92; first-pass approval rate baseline +15pp
2. **Evidence:** Evidence coverage ≥ 0.90; `done/` transition 중 uncited verifier 0건
3. **Autonomy:** lens latency p95 ≤ 90초; blocked → unblocked p95 wallclock baseline -70%; stale runtime twin 0건
4. **Cost/Latency:** $/ticket p50 baseline -30%; p50 ticket latency가 baseline보다 증가하지 않음
5. **Safety:** eval suite size ≥ 5 cases × 4 roles = 20+; ticket 외부 수정 0건; dual-review 우회 0건; vendor scheduler가 done 발행 0건

한 축의 개선이 다른 축의 붕괴를 만들면 성공으로 판정하지 않는다. 예를 들어 cost가 30% 줄어도 Trust나 Evidence가 하락하면 Bet 1은 재형상한다.

## 10. Feature Radar와의 관계 — 정확히 어떻게 합류하는가

| Feature Radar 항목 | 본 문서에서의 처리 |
|---|---|
| P0 Capability Registry | **그대로 채택**. Bet 1 contract enforcement의 전제. |
| P0 Decision Bridge | **그대로 채택**. Bet 3 외부 명령이 internal decision으로 변환되는 경로. |
| P0 Hook Guardrails | **그대로 채택**. Bet 5 mirror에서 PreToolUse 차단 hook 재사용. |
| P1 Watch/Monitor Plane | **재정의**. "wakeup 인프라"로 자리매김 — Bet 3의 *알림 정책 엔진*과 합류. |
| P1 Runtime Driver Hardening | **그대로 채택**. Bet 1이 driver의 cost 측정 path 의존. |
| P1 Dual Plugin Distribution | **연기**. 6주 sprint 후, 90일 vision 안에. Plugin 안정성보단 protocol 안정성이 먼저. |
| P1 Observability Ledger | **그대로 채택**. Bet 1의 telemetry sink와 동일 인프라. |
| P2 Multimodal Evidence | **유지**. 90일 이후. UI 작업이 늘어나기 전엔 우선순위 낮음. |
| P2 Cloud Delegation | **회의적 유지**. Anti-bet 3과 가까움 — *executor* 한정. |

요약: Feature Radar의 P0 셋은 Verified Autonomy OS의 *kernel admission layer*, P1 한 두 개는 본 문서 베팅의 *직접 의존*, P1 나머지와 P2는 *6주 후 재평가*다. 최종 통합 문서에서는 이 관계를 OS primitive와 release train으로 다시 묶는다.

## 10.5 Competitive landscape — 비슷한 문제를 푸는 다른 시스템들

CT2가 *어디에 머물 것인지*를 정의하기 위해, 인접 제품군과 명시적으로 대조. 본 비교는 frontier-tech PRD의 표준이다("우리는 X와 다르다, 그래서 우리만의 자리가 있다"). 본 표는 일반 평가가 아니라 *CT2 프레임에서의 비교*다.

| 시스템 | 주된 자리 | 우리와의 가장 큰 공통점 | 우리와의 가장 큰 차이 | CT2가 차용할 만한 것 |
|---|---|---|---|---|
| **Cursor** | IDE-내장 single-agent assistant | 코드 옆에 ticket-like context | review independence 없음, dual-LLM 아님 | 없음 — 다른 자리 |
| **Aider** | git-aware single-agent CLI | git workflow 통합, file-system-first | dual-review 없음, plan-mode-first 아님 | 부분 commit 흐름은 ct2-git-* 와 호환 |
| **AutoGen** (MS) | multi-agent conversation framework | multi-agent | "대화"가 권위 — file 권위 아님; 검증가능성 약함 | role definition pattern (다른 형상) |
| **CrewAI** | task graph orchestration | task graph | python-bound (외부 의존성), 사용자 룰 위반 | 그래프 의존성 시각화 정도 |
| **Smol Developer / GPT-Engineer** | 처음부터-끝까지 자동 생성 | LLM 작업 위임 | review/iteration 없음, 1-shot | Bet 4 eval에서 1-shot baseline로 비교용 |
| **Devin (Cognition)** | autonomous SWE | autonomous | dual-review 없음, 검증 불투명, SaaS only | Bet 3 ambient — async 스타일 |
| **OpenHands (구 OpenDevin)** | open-source SWE agent | open, file-based | 단일 agent 중심, dual-review 없음 | sandboxing 모델 (Codex `unified_exec`와 비교) |
| **Claude Projects / OpenAI Projects** | vendor-internal context store | 같은 vendor 내 reuse | 권위가 vendor cloud, file 아님 | 사용자 메모리 통합 (§3.5.2) |
| **Linear / Jira + Copilot** | PM tool + AI helper | ticket 개념 | spec/code 분리, dev workflow에서 멀음 | 없음 — 다른 자리 |
| **Anthropic Computer Use / OpenAI Operator** | OS-level automation | 검증 가능 trail 시도 | code review가 아닌 GUI task | screenshot evidence (Feature Radar P2) |

CT2의 **차별점 한 줄**: "두 개의 *서로 모르는* LLM이 같은 patch를 *각자* 검증하고 그 trace가 immutable file로 남는, 단일 사용자용 file-system-first harness." 이 자리는 위 어느 것도 정확히 차지하지 않는다. "differential testing for LLM patches" — 즉 *dual-LLM regression validation* — 이 우리가 본격적으로 점유할 시장 segment.

본 차별화가 흔들리지 않는 한, 본 문서의 베팅은 "Cursor 같이 만들자/Devin 같이 만들자"는 방향으로 끌려가서는 안 된다. §6 anti-bet 들이 그 방어선이다.

## 11. Decision Log — 문서 작성 중 채택/기각된 큰 갈래

| 갈래 | 채택? | 이유 |
|---|---|---|
| "Verified Autonomy OS를 canonical 이름으로 채택" | 채택 | Feature Radar의 강한 protocol framing을 제품 정체성으로 올림 |
| "OS를 보편적 agent OS로 확장" | 거절 | 범위는 file-first dual-review protocol kernel로 제한 |
| "CT2를 SaaS화" | 거절 | local file authority가 정체성. SaaS는 다른 제품. |
| "CT2를 풀-multi-tenant" | 12개월 후 | 지금 풀어주면 invariant 다섯 개 동시에 깨짐. |
| "Reliability Platform 비유 채택" | 하위 framing으로 채택 | OS가 제공하는 운영 가치로 유지하되 canonical 이름은 아님 |
| "TeamCreate/SendMessage 즉시 채택" | 거절 | experimental flag, 인스턴스 결합 비용 |
| "Native task mirror를 1번 베팅으로" | 거절 | 가장 매혹적, 가장 위험. 마지막. |
| "외부 의존성 추가(예: redis)" | 거절 | 외부 0 룰 유지. file system + bash + python stdlib. |
| "/ultrareview를 lens 대체로 사용" | 거절 | dual-review independence가 lens의 본질. ultrareview는 *제3 의견*만. |
| "LLM router 도입" | 12개월 후 | 정적 contract 안 정착 상태에선 router는 noise multiplier |

## 11.5 Stakeholder map — 누구를 위한 문서인가

본 문서는 다음 4 stakeholder를 동시에 만족시켜야 한다. 각자에게 무엇을 약속하는지를 명시.

| Stakeholder | 본 sprint에서 무엇이 좋아지나 | 어떻게 측정하나 |
|---|---|---|
| **Solo dev (현재 사용자)** | $/ticket 30% 감소; first-pass approval +15pp; "자고 일어나도 정상" UX | §9 balanced scorecard |
| **얼리 어답터(다른 multi-agent 사용자)** | role-contract 패턴이 spec에 박혀, 자기 환경에서 vendor 갈아끼우기 가능 | spec PR 머지 이후 fork 수, plugin install 수 |
| **CT2 plugin author / spec 기여자** | spec PR-driven 변경 절차; eval로 회귀 잡힘; PR 부담 ↓ | §6.6 spec PR list, eval suite case 수 |
| **(미래) enterprise 사용자** | budget hard_deny, OTel 통합, audit trail 강화 | §9 metric 7 (invariant 위반 0) + Feature Radar P0 Capability Registry |

각자에 대한 **거절**:

- Solo dev에게: "더 빠른 ticket 처리"는 약속하지 않는다 — *신뢰 가능한* ticket 처리.
- Plugin author에게: "내 plugin이 ct2-status에 자동 노출"은 약속하지 않는다 — Capability Registry에 *등록되어야* 노출.
- Enterprise에게: "SaaS multi-tenant"은 약속하지 않는다 — local file authority 유지.

## 12. Open questions — spike로 풀어야 하는 것들

각각 1–2일 spike, 주차 1에 병렬 진행:

1. **Codex `personality` config surface.** 문서엔 stable로 표시되지만 실제 CLI/profile 손잡이가 어디인지. `~/.codex/config.toml` 실측 + 0.130.0 release notes 재독.
2. **`enable_request_compression` 관측.** 실 ticket을 두 번 처리(on/off)하고 token 비교.
3. **`--max-budget-usd` 작동 모드.** 작업 *중간*에 끊기는지, *시작 전* 추정으로 거절하는지. Test ticket으로 검증.
4. **`--bare` 모드의 skill 가용성.** SKILL 파일이 fully resolve 되는지, plugin sync 없이 작동하는지.
5. **`PreToolUse` hook이 `TaskUpdate` metadata를 검사 가능한지.** 검사 불가하면 Bet 5 형상 수정 필요.
6. **`Monitor` 도구 cap (Bedrock/Vertex/Foundry 미지원).** CT2 사용자가 그 환경을 쓰면 fallback 필요.
7. **`AskUserQuestion` multi-select가 inbox로 fallback 되는 path.** Feature Radar P0 Decision Bridge와 직접 결합.

## 13. Anti-pattern catalog — 6주 안에 보일 수 있는 함정

문서로 박아두는 이유: 6주 후 회고 때 함정에 빠진 채 베팅을 "성공"으로 잘못 판정하지 않기 위해.

- **Cost가 30% 줄었지만 trust ratio도 함께 줄었다.** → forge model을 너무 강등. roll back.
- **first-pass rate가 올랐지만 plan-mode가 helm boilerplate를 만들기만 한다.** → plan-exempt threshold를 낮춤; eval에 "plan signal-to-noise" rubric 추가.
- **Discord ping이 inbox 대체로 사용된다.** → bridge 정책에 "외부 채널이 ticket lifecycle의 권위가 될 수 없다" 명시; 위반 metric 측정.
- **eval suite가 minor wording 변경에서 거짓 회귀 발생.** → judge 결정론성 점검; rubric 단순화.
- **Native task mirror에서 사용자가 native에서 직접 작업.** → hook으로 차단; mismatch event 카운트.

## 14. Closing — 한 문단

CT2의 다음 라운드는 *기능 추가*가 아니라 *정체성 명확화*다. Vendor가 stable로 풀어둔 다섯 표면(`personality`, `fast_mode`, `enable_request_compression`, `--max-budget-usd`, `EnterPlanMode`)을 OS primitive, role contract, plan evidence, eval, ambient advisory bridge로 묶으면, CT2는 "atomic mv + dual review"라는 단순한 protocol harness에서 **Verified Autonomy OS**로 업그레이드된다. 그 단계에서 가장 중요한 결정은 *무엇을 추가할지*가 아니라 *무엇을 끝내 안 할지*다. 본 문서 §6의 여섯 anti-bet은 그 거절을 미리 박아두기 위한 글이다. CT2가 보편적 agent OS로 범람하지 않고 file-first dual-review protocol kernel로 남을 수 있도록.

---

## Appendix A — 본 문서가 *원본* 데이터로 활용한 표면 인덱스

다음은 작성 중 직접 확인한 항목과 확인 방법. 추후 검증 시 본 인덱스를 starting point로.

| 항목 | 확인 방법 | 결과 |
|---|---|---|
| `codex --version` | local CLI | `codex-cli 0.130.0` |
| `claude --version` | local CLI | `2.1.138 (Claude Code)` |
| Codex stable feature flags | `codex features list` | `apps`, `browser_use`, `browser_use_external`, `computer_use`, `enable_request_compression`, `fast_mode`, `guardian_approval`, `hooks`, `image_generation`, `in_app_browser`, `multi_agent`, `personality`, `plugins`, `tool_call_mcp_elicitation`, `tool_search`, `tool_suggest`, `unified_exec` |
| Codex experimental flags | `codex features list` | `goals`, `external_migration`, `prevent_idle_sleep` |
| Claude CLI surface | `claude --help` | `--agent`, `--agents`, `--bare`, `--brief`, `--effort`, `--fork-session`, `--from-pr`, `--include-hook-events`, `--include-partial-messages`, `--input-format`, `--json-schema`, `--max-budget-usd`, `--no-session-persistence`, `--plugin-dir`, `--plugin-url`, `--remote-control`, `--resume`, `--session-id`, `--system-prompt`, `--tmux`, `--tools`, `--worktree` |
| Claude built-in tools | docs (tools-reference) | Agent, AskUserQuestion, Bash, CronCreate/List/Delete, Edit, EnterPlanMode/ExitPlanMode, EnterWorktree/ExitWorktree, Glob, Grep, ListMcpResourcesTool, LSP, Monitor, NotebookEdit, PowerShell, Read, ReadMcpResourceTool, SendMessage, ShareOnboardingGuide, Skill, TaskCreate/Get/List/Update/Stop/Output, TeamCreate/Delete, TodoWrite, ToolSearch, WebFetch, WebSearch, Write |
| Claude 2.1.136 변경 | docs changelog | OTel feedback survey, autoMode hard_deny, plan mode write block 수정, AskUserQuestion multi-select, CronList output |
| Claude 2.1.133 변경 | docs changelog | `worktree.baseRef`, hook effort metadata, subagent skill discovery 수정, sandbox bwrap/socat path |
| Claude 2.1.129 변경 | docs changelog | `--plugin-url`, `skillOverrides`, `claude_code.pull_request.count` OTel, `experimental` plugin manifest |
| Claude 2.1.128 변경 | docs changelog | EnterWorktree from local HEAD, `--channels` console auth, MCP tool counts |
| Claude 2.1.126 변경 | docs changelog | `claude project purge`, `--dangerously-skip-permissions` 확장, OAuth code paste |
| Codex 0.130 변경 | docs changelog | `codex remote-control`, app-server thread paging, plugin sharing metadata, multi-env `view_image` |
| Codex 0.129 변경 | docs changelog | TUI vim, `/goal` discovery/pause/resume, plugin workspace sharing, hook pre/post-compaction |
| Codex 0.128 변경 | docs changelog | `/goal` 첫 구현, plugin marketplace install, multi-agent v2 caps |

## Appendix B — Feature Radar와 일관성 점검 (diff 요약)

| 사실 | Feature Radar | 본 문서 | 격차 원인 |
|---|---|---|---|
| 로컬 Claude 버전 | 2.1.138 | 2.1.138 | 현재 두 문서 모두 최신 실측 기준으로 정합 |
| Claude 2.1.138 ~ 2.1.132 gap | 사라짐 | 사라짐 | 과거 draft의 stale diff를 제거 |
| `--bare` 모드 | 다루지 않음 | Bet 4의 핵심 의존 | 본 문서가 추가 |
| `personality`, `fast_mode`, `enable_request_compression` | 가볍게 표면만 | Bet 1의 직접 손잡이 | 본 문서가 추가 |
| `--max-budget-usd`, `--effort` | 가볍게 표면만 | Bet 1의 핵심 | 본 문서가 추가 |
| EnterPlanMode | 다루지 않음 | Bet 2의 핵심 | 본 문서가 추가 |
| Balanced scorecard | 후보 인프라만 제안 | Trust/Evidence/Autonomy/Cost로 채택 | 사용자 인터뷰 결과 반영 |
| Verified Autonomy OS framing | North Star로 제안 | canonical 제품 정체성으로 채택 | 사용자 인터뷰 결과 반영 |
| Anti-bets | "non-goals" 6개 | 별도 §6에서 6개 anti-bet | 강조 차이 |

본 문서는 Feature Radar를 *대체*하지 않는다. Feature Radar의 카탈로그/protocol 흡수 작업은 그대로 유효하고 P0 셋은 본 문서 베팅의 기반이다. 두 문서를 한 묶음으로 stakeholder review.

## Appendix C — Bet 1 implementation sketch (실 wrapper)

다음은 Bet 1을 *구체적*으로 어떻게 시작할지 보여주는 sketch. 본 문서가 "추상적 strategy일 뿐"이 되지 않도록 박아둔다. 실제 코드는 spec PR 후에 `bin/ct2-forge-run`(Claude 측 wrapper) 형태로 머지.

`bin/ct2-role-run` (provider-agnostic, 새 스크립트):

```bash
#!/usr/bin/env bash
set -euo pipefail
# ct2-role-run <role> <provider> <ticket-id>
# Loads role contract from .ct2/config/harness.yaml, invokes provider,
# emits cost telemetry to .ct2/telemetry/cost.jsonl.

role="$1"; provider="$2"; ticket_id="$3"
contract_yaml=".ct2/config/harness.yaml"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Parse contract via python stdlib (yaml-free regex; consistent with CT2 conventions).
contract=$(python3 - "$role" "$contract_yaml" <<'PY'
import re, sys
role, path = sys.argv[1], sys.argv[2]
content = open(path).read()
# Locate role_contracts: <role>: block (regex-only)
block = re.search(rf'role_contracts:.*?{re.escape(role)}:(.*?)(?=^\S|\Z)',
                  content, re.S | re.M)
if not block:
    print("MISSING"); sys.exit(0)
out = {}
for k in ("model", "effort", "personality",
         "budget_per_ticket_usd", "budget_per_session_usd",
         "budget_per_review_usd", "budget_per_run_usd",
         "latency_slo_seconds", "request_compression",
         "fast_mode", "on_budget_exceeded"):
    m = re.search(rf'^\s*{k}:\s*(.+?)\s*$', block.group(1), re.M)
    if m: out[k] = m.group(1).strip()
import json; print(json.dumps(out))
PY
)
[[ "$contract" == "MISSING" ]] && { echo "no contract for $role" >&2; exit 2; }

model=$(echo "$contract" | python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('model',''))")
effort=$(echo "$contract" | python3 -c "import json,sys;print(json.loads(sys.stdin.read()).get('effort','medium'))")
budget=$(echo "$contract" | python3 -c "
import json,sys; c=json.loads(sys.stdin.read())
for k in ('budget_per_ticket_usd','budget_per_session_usd','budget_per_review_usd','budget_per_run_usd'):
  if k in c: print(c[k]); break")

case "$provider" in
  claude)
    # Claude wrapper. --include-hook-events keeps hook trace for eval correlation.
    exec claude \
      --agent "$role" \
      --model "${model:-sonnet}" \
      --effort "${effort}" \
      ${budget:+--max-budget-usd "$budget"} \
      --include-hook-events \
      -p "$(cat .ct2/in-progress/${ticket_id}-*.md 2>/dev/null || cat .ct2/in-review/${ticket_id}-*.md)"
    ;;
  codex)
    # Codex profile is the primary surface for personality/fast_mode/compression.
    # Profile name convention: ct2-<role> in ~/.codex/config.toml
    profile="ct2-${role#ct2-}"
    exec codex --profile "$profile" exec "$(cat .ct2/in-progress/${ticket_id}-*.md 2>/dev/null || cat .ct2/in-review/${ticket_id}-*.md)"
    ;;
  *)
    echo "unknown provider: $provider" >&2; exit 2 ;;
esac
```

Codex side `~/.codex/config.toml` profile per role:

```toml
[profiles.ct2-forge]
model = "gpt-5-codex"
effort = "high"
personality = "terse"
fast_mode = false
enable_request_compression = true
# budget는 codex 측에서 별도 surface — 0.130.0 기준 직접적 cap은 없음.
# CT2는 wrapper에서 `tool_call_mcp_elicitation` event count로 간접 측정 후
# .ct2/telemetry/cost.jsonl에 기록한다.

[profiles.ct2-lens-cx]
model = "gpt-5-codex"
effort = "high"
personality = "skeptical-short"
fast_mode = false
enable_request_compression = true

[profiles.ct2-status]
model = "gpt-5-codex-fast"
effort = "low"
personality = "terse"
fast_mode = true
```

Telemetry sink (post-run, hook으로 호출되는 `bin/ct2-cost-record`):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Reads $CLAUDE_TOOL_LOG / Codex stdout, parses cost summary, appends jsonl.
role="$1"; ticket_id="$2"; provider="$3"; outcome="$4"; duration_s="$5"; cost_usd="$6"
mkdir -p .ct2/telemetry
python3 - <<PY
import json, time
rec = {
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "role": "$role",
  "ticket": "$ticket_id",
  "provider": "$provider",
  "outcome": "$outcome",
  "duration_s": float("$duration_s"),
  "cost_usd": float("$cost_usd") if "$cost_usd" else None,
}
with open(".ct2/telemetry/cost.jsonl", "a") as f:
    f.write(json.dumps(rec) + "\n")
PY
```

`bin/ct2-cost` (status integration):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Aggregates .ct2/telemetry/cost.jsonl into a one-screen summary.
python3 - <<'PY'
import json, sys, os
from collections import defaultdict
path = ".ct2/telemetry/cost.jsonl"
if not os.path.exists(path):
    print("(no telemetry yet)"); sys.exit(0)
by_role = defaultdict(lambda: {"n": 0, "cost": 0.0, "violations": 0})
with open(path) as f:
    for line in f:
        r = json.loads(line)
        b = by_role[r["role"]]
        b["n"] += 1
        if r.get("cost_usd"): b["cost"] += r["cost_usd"]
        if r["outcome"] == "budget_exceeded": b["violations"] += 1
print(f"{'role':24} {'runs':>6} {'$total':>10} {'budget violations':>20}")
for role, b in sorted(by_role.items()):
    print(f"{role:24} {b['n']:>6} {b['cost']:>10.2f} {b['violations']:>20}")
PY
```

`ct2-status` 통합: 마지막 줄에 `bin/ct2-cost --brief` 한 줄. 기존 status 출력의 모양을 깨지 않는 *부가* 정보로.

## Appendix D — Bet 4 eval case example (full)

다음은 lens-cc 역할에 대한 eval case 하나의 *완전한* 모습. 본 문서가 Bet 4를 *구상*만 한 것이 아님을 박아두는 부록.

`.ct2/evals/ct2-lens-cc/case-001-missing-test/` 디렉터리:

`ticket.md`:

```markdown
---
id: "001"
title: "Add user authentication endpoint"
status: in-review
priority: high
review-round: 0
review-status:
  lens-claude:
    status: pending
    sidecar: null
  lens-codex:
    status: pending
    sidecar: null
verdict: pending
---

## Requirements
- [x] POST /auth/login endpoint accepts email + password
- [x] Returns JWT on success, 401 on failure
- [x] Password hashing with bcrypt

## Constraints
- No new dependencies beyond bcrypt
- Must follow existing FastAPI patterns

## Acceptance Criteria
- [ ] Endpoint added with correct request/response shape
- [ ] Unit tests cover success and 401 cases
- [ ] Existing test suite passes
```

`patch.diff`:

```diff
diff --git a/app/auth.py b/app/auth.py
new file mode 100644
--- /dev/null
+++ b/app/auth.py
@@ -0,0 +1,28 @@
+from fastapi import APIRouter, HTTPException
+from pydantic import BaseModel
+import bcrypt, jwt, os
+
+router = APIRouter()
+
+class LoginRequest(BaseModel):
+    email: str
+    password: str
+
+@router.post("/auth/login")
+async def login(req: LoginRequest):
+    user = await get_user(req.email)
+    if not user:
+        raise HTTPException(401, "Invalid credentials")
+    if not bcrypt.checkpw(req.password.encode(), user.password_hash):
+        raise HTTPException(401, "Invalid credentials")
+    token = jwt.encode({"sub": user.id}, os.environ["JWT_SECRET"])
+    return {"token": token}
```

`expected-sidecar.json` (subset matcher; lens-cc의 sidecar가 *최소* 다음을 만족해야):

```json
{
  "verdict": "rejected",
  "issues_must_contain_keywords": [
    "test",                   // AC 2가 unchecked인데 패치에 테스트 없음
    "unit test",
    "missing"
  ],
  "blocking_issues_count_min": 1,
  "ac_check_must_have_failed": ["Unit tests cover success and 401 cases", "Existing test suite passes"],
  "must_not_contain_phrases": [
    "approved",            // verdict가 rejected여야 한다
    "looks good"
  ]
}
```

`rubric.md` (정성 채점 기준; LLM-as-judge 시 사용):

```markdown
## Rubric — case-001 (lens-cc rejecting an obvious AC miss)

### Must (binary, 0/1 each)
1. verdict == "rejected"
2. sidecar identifies missing tests as a blocking issue
3. sidecar references AC 2 ("Unit tests cover success and 401 cases") explicitly
4. sidecar does NOT recommend approval despite the patch shape

### Should (graded 0–2)
5. sidecar suggests specific test cases (success path, wrong password, missing user)
6. sidecar notes JWT_SECRET env var lookup is brittle (no fallback / no validation)
7. sidecar tone is "skeptical-short" per role-contract personality

### Nice-to-have (0–1)
8. sidecar flags `get_user` is called but not defined/imported in this patch — incomplete
9. sidecar suggests using FastAPI's HTTPException with `WWW-Authenticate` header

### Pass condition
- All Must items = 1
- Should sum ≥ 4/6
```

`runner.sh` invocation (간소화):

```bash
case_dir="$1"
out=$(claude --bare \
  --agent ct2-lens-cc \
  --model "${CT2_LENS_CC_MODEL:-opus}" \
  --effort high \
  --max-budget-usd 0.50 \
  --json-schema '{"type":"object","properties":{"verdict":{"type":"string"},"summary":{"type":"string"},"issues":{"type":"array"}}}' \
  -p "$(cat "$case_dir/ticket.md" "$case_dir/patch.diff")")

# Subset match against expected-sidecar.json
python3 bin/_eval_subset_match.py "$case_dir/expected-sidecar.json" <<<"$out"

# Rubric judge (separate cheaper claude call)
judge_out=$(claude --bare --model haiku --max-budget-usd 0.10 \
  -p "$(cat "$case_dir/rubric.md")\n\nReview:\n$out\n\nReturn JSON: {must:[0|1,...], should:[0..2,...], nice:[0|1,...], pass:true|false}")
echo "$judge_out" | tee -a "$case_dir/results-$(date +%s).json"
```

해석:

- `--bare`로 hook/auto-memory를 끊어 *해당 role MD*만의 결과를 얻는다(외부 변수 격리).
- `--max-budget-usd 0.50`은 Bet 1 contract와 다른 envelope (eval 별도).
- `--json-schema`로 결과 구조를 fix해 subset matcher가 작동.
- judge LLM은 더 싼 모델(haiku) — 결정의 *합리성*만 채점.
- 결과는 case 디렉터리에 누적되어 시간에 따른 회귀 추적.

## Appendix E — 구체적 다음 7일

본 문서를 *읽은 직후* 무엇을 시작하나.

| Day | 작업 | 결과물 |
|---|---|---|
| 1 | Bet 1 spike: `personality`/`fast_mode`/`enable_request_compression` 실측 | `.ct2/runtime/codex-flags-actual.md` (실측 보고) |
| 1 | `bin/ct2-baseline` 1회용 스크립트 작성 | `.ct2/telemetry/baseline-2026-05.json` |
| 2 | `harness.yaml`에 `role_contracts` 블록 1차 초안 | spec PR draft (`spec/role-contracts.md`) |
| 3 | `bin/ct2-role-run` 첫 구현(Claude only) | 실 ticket 1건 처리; cost.jsonl 기록 확인 |
| 4 | Codex profile 작성, `bin/ct2-role-run` codex 분기 | 동일 ticket을 양 provider로 처리 비교 |
| 5 | Bet 4 baseline: lens-cc/lens-cx 각 1 case 작성 | `.ct2/evals/ct2-lens-{cc,cx}/case-001-...` |
| 6 | runner.sh 1차 작동, baseline 측정 | `.ct2/evals/results-2026-05-XX.jsonl` |
| 7 | retro + spec PR 머지 의사결정 | spec/role-contracts.md PR open or revise |

7일 후 stakeholder review에 가져갈 것: (a) baseline 숫자, (b) cost.jsonl 표본 ≥ 5건, (c) eval case ≥ 4건, (d) Codex flag 실측 보고. 이 4개가 없으면 6주 sprint 진입을 미룬다.

---

*작성: 2026-05-10. v3 — 3-turn 반복 iteration:*
*  v1: 5개 bet + 6개 anti-bet + framing + roadmap (turn 1)*
*  v2: empirical baseline, kill criteria, spec PR list, subagent/memory, 경쟁비교, stakeholder, Bet 1 wrapper, Bet 4 eval case, 7-day plan (turn 2)*
*  v3: Feature Radar diff 한눈에 (§0.1), Layered architecture diagram (§2.1) (turn 3)*
*다음 갱신: Bet 1 spike 완료 후(예상 1주 차).*
