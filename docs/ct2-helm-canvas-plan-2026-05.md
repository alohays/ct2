# CT2 발전방향 계획서 — Helm Canvas: HTML 기반 계획 GUI

작성일: 2026-05-18 KST
작성자: ct2 (goal 모드)
대상 역할: `ct2-helm`
기준 main: `78d52f0` — **protocol-adapter-reframe(PR #13, 2026-05-13) 반영**
관련 문서:
- `spec/PROTOCOL.md` — CT2 프로토콜의 정본 진입점. 본 계획의 모든 결정은 이 프로토콜 법칙(특히 "Atomic mv Is Commit", "Agent Owns the Loop")에 종속된다
- `spec/adapter-format.md` — CT2 "어댑터"의 엄밀한 정의(`adapters/{agent}/{role}.md`). **용어 주의는 §4.1 참조**
- `spec/decision-bridge.md` — 본 계획의 데이터 기반 (`ct2-decision` + `.ct2/decisions/`)
- `spec/plan-evidence.md` — 캔버스 산출물의 저장 위치
- `claude-plugin/skills/ct2-helm/SKILL.md` — 변경 대상 스킬 정의
- `docs/ct2-product-strategy-2026-05.md` — Bet 2 "Plan-mode-first forge"의 사용자 인터페이스 짝

참고 기법:
- <https://news.hada.io/topic?id=29347> — "Claude Code가 Markdown 대신 HTML로 산출하면 표현력·공유성·양방향 상호작용이 올라간다"
- <https://x.com/trq212/status/2052809885763747935> — 동일 기법의 원전 (요약은 hada 글 기준)

---

## 0. 한 페이지 요약

### 0.1 결심

`ct2-helm`의 **기본 계획 인터페이스를 텍스트 대화에서 "Helm Canvas"라는 HTML 페이지로 전환**한다. helm은 계획 국면마다 자기완결형(self-contained) HTML 한 장을 `.ct2/plans/`에 생성하고, 사용자는 브라우저에서 그 페이지를 보며 범위·티켓 분할·우선순위·인수 기준을 **위젯으로 직접 조작**한다. 조작 결과는 CT2가 이미 보유한 **Decision Bridge(`.ct2/decisions/`)** 를 통해 helm으로 되돌아온다.

핵심은 새 시스템을 짓는 게 아니다. **Decision Bridge에 세 번째 provider format("html")을 추가**하는 것이다. Codex `requestUserInput`, Claude `AskUserQuestion`에 이어 HTML이 같은 결정 레코드를 렌더하는 또 하나의 provider format이 된다. 단일 진실원천은 여전히 `.ct2/decisions/` JSON이다.

이때 helm 워크플로는 **5단계**(대화 → 캔버스 생성 → 캔버스 결정·복사 → 토큰 회수·티켓 작성 → seal)로 정형화되고(§3.4), 캔버스 HTML 파일은 md 티켓과 *동일 등급*의 관리 대상이 된다 — `open/answered/sealed/expired/` 4-상태를 디렉터리 간 atomic `mv`로 거치며, 어떤 캔버스가 결정 대기인지 끝났는지 항상 한눈에 정리된다(§4.4).

### 0.2 왜 지금

| 신호 | 의미 |
|---|---|
| helm SKILL.md의 "Clarification-First Mandate" | helm은 이미 *모든 모호함을 사용자에게 묻도록* 설계됨 — 단지 그 묻는 채널이 빈약하다 |
| `AskUserQuestion`은 질문 4개·선택지 4개 한계 | 범위·분할·AC·우선순위·의존성을 *한 화면에* 못 보여줌 → 결정이 파편화 |
| Decision Bridge가 이미 존재 | provider-neutral 결정 스키마가 깔려 있어 HTML은 "렌더러" 하나만 더 얹으면 됨 |
| Product Strategy Bet 2 (Plan-mode-first) | 계획을 sidecar로 남기는 흐름 — 캔버스는 그 계획의 *사람 쪽 표면* |
| HTML-for-agentic-AI 기법 성숙 | 표/색/SVG/슬라이더로 "읽히는 계획"을 만들고, 값을 되돌려받는 양방향 루프가 검증된 패턴 |

### 0.3 이 문서가 제안하지 *않는* 것 (anti-scope)

- ❌ Electron·React·번들러·npm 도입 — CT2는 bash + Python stdlib만. 캔버스도 의존성 0.
- ❌ 상시 웹 서버·SaaS 대시보드 — 캔버스는 티켓 1건 계획 동안만 사는 일회용 페이지.
- ❌ `ct2-status` 칸반의 HTML화 — 본 계획은 *계획 수립* 국면에 한정. 모니터링은 별건.
- ❌ HTML을 git에 추적 — 캔버스는 `.ct2/` 런타임 산출물. 노이즈 diff 회피(hada 글이 지적한 트레이드오프).
- ❌ HTML이 결정의 진실원천이 되는 것 — 진실원천은 `.ct2/decisions/` JSON. HTML은 읽기 전용 렌더.

---

## 1. 배경: 현재 helm의 계획 인터페이스와 한계

helm은 현재 두 채널로만 사용자와 계획을 합의한다.

1. **자유 텍스트 대화** — 요구사항 청취, 티켓 미리보기를 코드펜스로 제시.
2. **`AskUserQuestion`** — 모호한 지점을 객관식으로 질의.

이 방식의 구조적 한계:

| 한계 | 설명 |
|---|---|
| **파편화된 결정** | 범위·우선순위·AC·의존성이 질문 N개로 쪼개져 순차 노출. 사용자는 *전체 그림*을 한 번도 못 봄 |
| **위젯 빈곤** | `AskUserQuestion`은 객관식뿐. 슬라이더(우선순위 가중치), 드래그(티켓 분할), 체크리스트(AC 토글)가 없음 |
| **비교 불가** | "티켓을 2개로 vs 3개로 쪼갤 때" 두 안을 나란히 못 봄 — 텍스트로 번갈아 묘사할 뿐 |
| **맥락 휘발** | 결정 근거가 대화 스크롤에 묻힘. 나중에 "왜 이 범위였지?"를 재구성하기 어려움 |
| **수동성** | 사용자는 helm이 *던지는 질문에 답만* 함. 계획을 능동적으로 *조형*할 표면이 없음 |

helm SKILL.md는 이미 "추측하지 말고 모든 모호함을 사용자에게 물어라"를 의무화한다. 문제는 의지가 아니라 **묻는 도구의 표현력**이다. 본 계획은 그 도구를 교체한다.

---

## 2. 참고 기법: HTML for Agentic AI

hada/trq212 글의 골자를 CT2 맥락으로 옮기면:

| 원전 주장 | CT2 적용 |
|---|---|
| HTML은 표·CSS·SVG·스크립트로 Markdown보다 표현력이 높다 | 범위 매트릭스, 의존성 그래프(SVG), 티켓 분할을 한 화면에 시각화 |
| HTML 문서는 브라우저로 열고 링크로 공유 가능 → 실제로 읽힌다 | `.ct2/plans/canvas/open/{id}-r{n}.canvas.html`을 `file://`로 즉시 열람. 팀 공유 시 그대로 전달 |
| **슬라이더·컨트롤로 값을 조정하고, 바뀐 값을 다시 프롬프트로 복붙** (양방향) | 사용자가 캔버스에서 결정 → "결정 복사" 버튼 → helm에 붙여넣기 (Phase 1 루프의 핵심) |
| 일회성 편집 UI를 작업마다 즉석에서 생성 | 캔버스는 *티켓 1건* 전용. 끝나면 버려짐 |
| 트레이드오프: 생성 2–4배 느림, diff 노이즈 | 캔버스는 `.ct2/`(git 미추적)에만. 생성 비용은 "계획이 실제로 합의된다"로 상쇄 |

**차용 4원칙** (캔버스 설계의 불변 규칙):

1. **한 화면 = 전체 계획** — 스크롤은 허용하되 결정에 필요한 모든 축을 한 페이지에.
2. **양방향** — 보여주기만 하지 않는다. 모든 패널은 조작 가능하고, 조작 결과는 helm으로 회수된다.
3. **자기완결** — 외부 CDN·폰트·스크립트 0. 단일 `.html` 파일. `file://`에서 완전 동작.
4. **결정의 진실원천은 JSON** — HTML은 휘발성 뷰. 합의 결과는 `.ct2/decisions/`에 정규 레코드로 박제.

---

## 3. 핵심 컨셉: Helm Canvas

### 3.1 정의

> **Helm Canvas** — helm이 계획 국면마다 생성하는 자기완결형 HTML 한 장.
> 진행 중인 티켓 초안의 모든 미결 결정을 패널로 펼쳐 보이고, 사용자가 위젯으로
> 조작한 결과를 Decision Bridge를 통해 helm으로 되돌린다.

캔버스는 *새로운 UI 레이어*가 아니다. **결정 레코드(`.ct2/decisions/`)를 조작 가능하게 렌더한 것**이다. 이 한 줄이 설계 전체를 지배한다.

### 3.2 설계 철학 — 다섯 가지 비타협 원칙

이 원칙들은 두 번의 잘못된 시도를 거쳐 나왔다. (1) 1차 데모는 "6개 패널을 쌓은 폼"이었다 — 입력은 받지만 *결정을 돕지 않았다*. (2) 2차 데모는 그 반작용으로 "미해결 항목이 0이 되기 전엔 확정 버튼을 비활성"하는 게이트를 넣었다 — 그런데 이건 더 나빴다. **도구가 해결을 *요구*하면서 해결할 *수단*(텍스트를 직접 고치는 길)은 주지 않은 채 copy만 가둔 것**이다. 사용자를 가두는 도구는 좋은 도구가 아니다.

좋은 캔버스는 다음 다섯 원칙을 지킨다 — 모두 데모(`docs/assets/helm-canvas-demo.html`)에 구현돼 있다.

| # | 원칙 | 안티패턴 | 캔버스의 구현 |
|---|---|---|---|
| **P1** | **캔버스는 결정 레코드를 렌더한 것이다** | UI와 데이터가 따로 논다 | 우측에 실제 `.ct2/decisions/` JSON을 **실시간 미러**. 위젯을 건드리면 JSON이 그 자리에서 바뀌고 잠깐 빛난다 — "이 화면이 곧 그 파일"임을 눈으로 확인 |
| **P2** | **모든 결정은 비용을 보여준다** | 입력의 결과를 숨긴다 | "이 계획 한눈에" — 범위 칩을 켜면 In-scope 수·예상 일수가 즉시 갱신. 각 토글의 *무게*를 느낀다 |
| **P3** | **helm과 다른 선택은 증거다** | 최종값만 남긴다 | helm 원안(baseline) 대비 변경분만 "helm 제안 → 내 결정" delta로 표시 → `overrides` 필드로 박제 |
| **P4** | **캔버스는 안내하되 가두지 않는다** | 미완성이라고 제출을 막는다 | 확정/copy 버튼은 **항상 동작**. 미해결 항목은 비활성이 아니라 *advisory*("helm이 확인을 권하는 항목")로 표시하고, 토큰의 `open_items`에 정직하게 실어 helm이 이어받게 한다 |
| **P5** | **캔버스는 양식이 아니라 제안서다** | helm이 채운 칸은 고정이다 | 모든 셀이 자유 편집(contenteditable) — AC 문구, 범위 라벨, 제약 분류·내용, 티켓 제목·규모·세부 항목까지. *구조*도 자유 — 티켓·AC·범위·제약·세부 항목을 더하고 뺀다. 어디에도 안 맞는 말은 "자유 메모" 패널로 |

P3·P4·P5가 이 계획의 진짜 베팅이다.

- **P3** — Karpathy식으로, 모델(helm)이 제안한 계획과 사람이 실제 결정한 계획의 *차이*야말로 CT2가 한 계획에 대해 포착할 수 있는 가장 신호가 강한 데이터다. lens의 감사 대상이자 helm 역할 정의를 고치는 eval 신호가 된다.
- **P4** — helm SKILL.md의 Clarification-First Mandate는 여전히 유효하다. 단, 그 mandate의 집행 주체는 **사용자를 가두는 게 아니라 helm 자신**이다. 캔버스는 미해결 항목을 *숨기지 않고*(advisory + `open_items`) helm에게 넘긴다 — helm은 그걸 받아 대화로 마저 푼다. 미해결을 가짜로 해소시키는 것보다, *미해결인 채로 정직하게 기록*하는 것이 CT2의 evidence 철학에 맞다.
- **P5** — 캔버스가 폼이면 사용자는 helm의 틀 안에서만 움직인다. 제안서이면 사용자가 틀 자체를 고친다. 예: "로그인 UX가 자연스럽다"라는 모호한 AC를 사용자가 "로그인 후 2초 내 메인 렌더"로 *직접 다시 쓴다* — 이것이 P4가 말하는 진짜 해결 수단이다. P5는 텍스트 편집에 그치지 않는다. **구조 편집** — 티켓을 더 쪼개거나 합치고, AC·범위·제약·세부 항목을 더하거나 빼는 것 — 까지 포함한다. helm의 티켓 분할안조차 *출발점*일 뿐, 모든 패널이 끝까지 사용자 손에 열려 있어야 한다. "helm이 빈칸을 만들고 사용자가 채우는" 게 아니라 "helm이 초안을 그리고 사용자가 자유롭게 덮어쓰는" 것이다. P4(가두지 않음)와 P5(고칠 자유)는 한 쌍이다.

### 3.3 패널 구성

캔버스는 7개 패널로 구성된다. 모든 패널은 *해당 결정이 존재할 때만* 렌더된다(progressive disclosure). 모든 텍스트 셀은 P5에 따라 직접 편집 가능하다.

| 패널 | 보여주는 것 | 위젯 | 회수되는 결정 |
|---|---|---|---|
| **① helm의 해석** | helm이 사용자 의도를 해석한 한 단락 + 원문 인용 | 정확/수정요청 양자택, 수정 시 자유 텍스트 | 해석 정확성 확인 |
| **② 범위** | 항목별 In / Out / 보류 | 상태 배지 클릭(3-상태 순환), 라벨 직접 편집, 항목 추가·삭제 | 범위 경계 |
| **③ 티켓 분할** | 초안을 PR 크기 티켓 N개로 쪼갠 안 | 카드 **제목·규모·세부 항목 모두 직접 편집**, 티켓·항목 추가·삭제, (Phase 3) 드래그 병합/분할 | 티켓 경계 + 개수 |
| **④ 인수 기준(AC)** | 검증 가능한 AC 체크리스트 | 항목 체크, **텍스트 직접 편집**, ⚑모호 플래그, 추가·삭제 | AC 완결성 |
| **⑤ 우선순위 & 의존성** | 백로그 위 위치 + 의존 티켓 SVG 그래프 | 우선순위 슬라이더, **의존성 자유 텍스트 편집**, (Phase 3) 의존선 연결 | 우선순위·의존성 |
| **⑥ 제약 & 엣지케이스** | helm이 추정한 기술/성능 제약, 실패모드 | 분류 라벨·내용 직접 편집, 줄 추가·삭제 | 제약 명확화 |
| **⑦ 자유 메모** | 어느 패널에도 안 맞는 말 | 자유 텍스트 | helm에게 보내는 비정형 맥락 |

①~⑥은 helm SKILL.md의 "Clarification-First Mandate" 6개 항목(해석·범위·AC·우선순위·제약·의존성)과 **1:1로 대응**한다 — 캔버스는 그 명령을 텍스트가 아닌 GUI로 집행한다. ⑦은 mandate가 미처 담지 못한 비정형 의견을 위한 탈출구다. ①②④는 *advisory*("helm 확인 권장")를 만들 수 있는 패널이지만, P4에 따라 그것이 확정을 막지는 않는다.

### 3.4 helm 워크플로 — 5단계

캔버스는 helm의 *대체*가 아니라 helm 워크플로의 한 국면이다. 전체 흐름은 다섯 단계이고, 각 단계는 `.ct2/` 디렉터리에 정확한 흔적을 남긴다.

| 단계 | 무슨 일이 | 누가 | `.ct2/` 상태 변화 |
|---|---|---|---|
| **S1. 대화 계획** | 유저가 helm과 대화하며 요구사항을 좁힌다 | 유저 ↔ helm | (아직 파일 없음 — 대화) |
| **S2. 캔버스 정리** | 유저가 "html로 줘"라고 하면, helm이 그때까지의 결정 후보를 캔버스 HTML로 정리·생성 | helm | `decisions/pending/{dec}.json` 생성<br>`plans/canvas/open/{id}-r{n}.canvas.html` 생성 |
| **S3. 캔버스 결정** | 유저가 브라우저에서 패널을 조작해 결정하고 **copy 버튼**으로 결정 토큰을 복사 | 유저 | (변화 없음 — 브라우저 안에서 결정) |
| **S4. 토큰 회수 → 티켓화** | 유저가 토큰을 helm 대화창에 붙여넣고 "최종 md 티켓으로 만들어줘"라고 요청. helm이 토큰을 검증·회수하고 forge에게 줄 md 티켓을 작성 | 유저 → helm | 캔버스 `open/` → `answered/`<br>`decisions/` `pending/` → `answered/`<br>`draft/{id}-{slug}.md` 작성 |
| **S5. 티켓 생성(seal)** | helm이 `ct2-seal` 실행 → 그 직후 `ct2-helm-canvas seal`로 캔버스 박제 | helm | `ct2-seal`: `draft/` → `backlog/{id}-{slug}.md`<br>`ct2-helm-canvas seal`: 캔버스 `answered/` → `sealed/{id}/` |

```
S1 대화 ──► S2 캔버스 생성 ──► S3 유저 결정·copy ──► S4 토큰 회수+티켓 작성 ──► S5 seal
            canvas/open/         (브라우저)            canvas/answered/         canvas/sealed/
            decisions/pending/                         decisions/answered/      backlog/{id}.md
```

S3에서 유저가 캔버스에서 하는 일 — 텍스트 직접 편집·항목 추가/삭제(P5), 범위 토글 시 "한눈에" 즉시 갱신(P2), helm 제안과 다른 선택은 delta로 누적(P3), 확인 권장 항목은 advisory로 보이되 copy를 막지 않음(P4). copy 버튼은 언제든 동작하고, 토큰에는 `overrides`와 `open_items`가 함께 실린다.

핵심 불변: **캔버스 HTML 파일도 md 티켓처럼 "상태 = 디렉터리"로 관리된다.** 어떤 캔버스가 결정 대기 중(`open/`)인지, 회수됐는지(`answered/`), 티켓이 됐는지(`sealed/`)를 항상 디렉터리만 보면 알 수 있다 — 자세한 생명주기는 §4.4.

---

## 4. 아키텍처: Decision Bridge 위의 세 번째 provider

### 4.1 데이터 흐름

```
                   ┌─────────────────────────────────────┐
   helm 계획 국면 ──┤ ct2-decision new  (결정 레코드 생성)  │
                   └──────────────┬──────────────────────┘
                                  │  .ct2/decisions/pending/{id}.json   ← 단일 진실원천
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
   ct2-decision format     ct2-decision format    ct2-decision format
        --codex                 --claude               --html        ← 본 계획의 신규 provider format
            │                     │                     │
   requestUserInput        AskUserQuestion       canvas.html (자기완결)
        (provider)            (provider)            (provider, 본 계획)
                                                        │
                                                  사용자 브라우저 조작 → 토큰
                                                        │
                                          helm: ct2-helm-canvas recover (nonce 검증)
                                                        ▼
                                         .ct2/decisions/answered/{id}.json
```

핵심: HTML은 **`ct2-decision format --html`이라는 provider format 출력**일 뿐이다. `spec/decision-bridge.md`가 이미 "provider format은 같은 레코드의 한 뷰이지 제2의 진실원천이 아니다"라고 못박았다. 캔버스는 이 규약을 그대로 따른다.

> **용어 주의 — "provider format" ≠ "어댑터".** PR #13의 protocol-adapter-reframe 이후 CT2에서 **"어댑터(adapter)"는 엄밀한 의미**를 갖는다: `spec/adapter-format.md`가 정의하는 `adapters/{agent}/{role}.md` — 즉 *런타임이 CT2 역할을 어떻게 수행하는지* 기술하는 markdown 계약(현재 lens 역할만 필수). 본 계획서가 다루는 HTML은 그것이 **아니다**. HTML은 `ct2-decision`이 결정 레코드를 렌더한 **provider format**(Codex/Claude/HTML 세 가지 중 하나)이다. 두 개념은 다른 층위이므로, 본 계획서는 혼동을 피해 일관되게 **"provider format"** 으로 칭한다. (참고: `decision-bridge.md`는 PR #13 전 작성되어 "adapter view"라는 표현을 쓰는데, Phase 0에서 이 표현도 PROTOCOL.md 용어에 맞춰 정리한다.)

### 4.2 저장 위치

| 산출물 | 경로 | 근거 |
|---|---|---|
| 결정 레코드 | `.ct2/decisions/{pending,answered,expired}/{dec}.json` | 기존 Decision Bridge |
| 캔버스 HTML | `.ct2/plans/canvas/{open,answered,sealed,expired}/...` | §4.4 캔버스 생명주기 — 상태=디렉터리 |
| 계획 증거(JSON) | `.ct2/plans/{ticket-id}-r{round}.json` | 기존 plan-evidence |

캔버스 HTML을 `plan-evidence`에 편입하면 부수 효과가 좋다 — **lens가 나중에 "어떤 계획이 사용자와 합의됐는지"를 그 HTML로 재구성**할 수 있다. 계획 캔버스가 곧 감사 증거가 된다.

### 4.3 PROTOCOL.md 법칙 준수 체크리스트

PR #13 이후 CT2의 불변식은 `spec/PROTOCOL.md`의 "Protocol Laws"로 정본화됐다. 캔버스는 그 법칙 하나하나에 종속된다.

| 법칙 / 불변식 | 캔버스의 준수 방식 |
|---|---|
| bash + Python stdlib만 | HTML 생성·회수는 Python stdlib만 — 문자열 템플릿, `json`, `argparse`. 외부 패키지·CDN·번들러 0 |
| **Filesystem Is the Database** | 진실원천은 `.ct2/decisions/`·`.ct2/plans/`. HTML은 advisory 렌더, runtime 메타 |
| **Atomic mv Is Commit** | 캔버스 생성·상태전이·결정 write-back 모두 `.ct2/.tmp/`→`mv` |
| **Agent Owns the Loop** | `ct2-helm-canvas`의 `generate`/`recover`/`seal` 모두 one-shot — bounded work 후 즉시 종료. 지속 프로세스·서버·daemon 없음 |
| **Adapter Boundary** | `ct2-seal`·`ct2-reconcile` 등 Required Reference Tool 미수정. 캔버스 로직은 `ct2-helm-canvas`에 격리 |
| `.ct2/` git 미추적 | 캔버스는 `.ct2/plans/` 아래 — 자동으로 미추적 |
| spec-first | 신규 `spec/helm-canvas.md` 선행, PROTOCOL.md Reading Order에 등재, 구현 후행 |
| 역할 경계 | 캔버스는 helm 전용 도구. forge/lens 미사용. helm의 쓰기 권한(`draft/`) 안에서만 동작 |

### 4.4 캔버스 생명주기 — md 티켓처럼 상태로 관리한다

CT2의 제1원칙은 **"상태 전이는 디렉터리 간 atomic `mv`"** 다. 칸반 티켓이 `draft/ → backlog/ → in-progress/ …` 를 거치듯, 캔버스 HTML도 같은 규율을 따른다. 캔버스가 그냥 `.ct2/plans/` 아무 데나 쌓이면 — 어떤 게 살아 있는 결정 대기이고 어떤 게 끝난 것인지 알 수 없는 — 잡동사니가 된다. 그래서 캔버스에 **고유한 4-상태 머신**을 둔다.

```
.ct2/plans/canvas/
├── open/        S2 직후 — helm이 생성, 유저 결정 대기 (= "인박스")
│                  {id}-r{round}.canvas.html
├── answered/    S4 — copy 토큰이 helm에 회수됨, 티켓 작성 대기
├── sealed/      S5 — md 티켓이 backlog에 생성됨, 계획 증거로 박제
│                  {id}/r{round}.canvas.html  (티켓별 폴더에 라운드 누적)
└── expired/     유저가 끝내 결정하지 않은 채 방치되거나, 개정으로 대체된 캔버스
```

**상태 전이** (모두 atomic `mv`, tmpfile-then-`mv` 패턴):

| 전이 | 트리거 | 동시에 일어나는 일 |
|---|---|---|
| (생성) → `open/` | helm이 `ct2-helm-canvas` 실행 (S2) | `decisions/pending/{dec}.json` 동반 생성 |
| `open/` → `answered/` | helm이 copy 토큰을 회수 (S4) | `decisions/` `pending/`→`answered/` |
| `answered/` → `sealed/{id}/` | `ct2-seal` 성공 직후 helm이 `ct2-helm-canvas seal` 호출 (S5) | (앞서 `ct2-seal`이 티켓 `draft/`→`backlog/`) |
| `open/`·`answered/` → `expired/` | 같은 티켓에 새 라운드 캔버스 생성, 또는 TTL 경과 | 짝이 된 결정 레코드도 `decisions/expired/`로 |

**불변식.** (1) 캔버스의 상태 = 그것이 든 디렉터리. HTML 내부에 status 필드를 박지 않는다 (P1 — HTML은 읽기 전용 렌더). (2) 캔버스 1개 ↔ 결정 레코드 1개는 항상 짝지어 같은 상태로 움직인다 — 한쪽만 `answered`이고 다른 쪽은 `pending`인 상태는 금지. (3) `open/`에 있는 캔버스는 "유저가 아직 결정하지 않은 것" — `ct2-status`가 이를 **inbox처럼 카운트해서 보여준다**("결정 대기 캔버스 2건"). (4) 한 티켓이 `ct2-revise`로 개정되면 그 round의 캔버스는 `expired/`로, 새 round 캔버스가 `open/`에 생성된다 — 칸반의 sidecar 아카이브 규율과 동형.

이렇게 하면 캔버스가 md 티켓과 *완전히 같은 등급의 관리 대상*이 된다 — 생성·대기·완료·만료가 항상 한눈에 정리되어 쌓이지 않는다.

---

## 5. 피드백 루프: 캔버스 → helm

캔버스의 결정을 helm으로 되돌리는 경로. hada 글의 "값을 다시 프롬프트로 복붙" 패턴을 그대로 MVP로 삼는다. **두 방식 모두 CT2 도구는 one-shot으로 실행되고 끝난다** — PROTOCOL.md의 "Agent Owns the Loop" 법칙을 지킨다.

| 방식 | 동작 | 인프라 | 채택 단계 |
|---|---|---|---|
| **A. 복사-붙여넣기 토큰** | "확정" 클릭 → JS가 압축 토큰(JSON 한 줄) 생성 → 사용자가 helm 대화창에 붙여넣기 → helm이 `ct2-helm-canvas recover`로 회수 | 없음. `file://`로 동작 | **Phase 1 (기본)** |
| **B. 파일 드롭** | "확정" 클릭 → JS가 `decision-{id}.json`을 브라우저 다운로드 → helm이 `ct2-helm-canvas recover <file>`로 회수 | 없음(브라우저 기본 다운로드). 서버 없음 | **Phase 2 (선택)** |

**왜 A가 기본인가.** 인프라 0, `file://`만으로 완결, hada 글에서 검증된 패턴. 계획 결정 JSON은 수 KB라 클립보드로 충분하다. 방식 B(파일 드롭)는 토큰이 비대하거나 클립보드를 못 쓰는 환경의 *선택지*일 뿐 A보다 단계가 많다(파일 경로 조율 필요). 둘 다 helm이 `recover`라는 **one-shot 도구**를 한 번 실행해 끝낸다.

> **기각된 방식 — 지속 실행 로컬 서버.** 초안에서는 `ct2-helm-canvas --serve`(Python `http.server`로 `/answer` POST를 받아 자동 write-back)를 Phase 2로 검토했다. **기각한다.** PROTOCOL.md의 *"Agent Owns the Loop"* — "CT2는 polling·continuation을 소유하지 않는다. CT2 도구는 bounded work를 하고 종료한다" — 와 *"Filesystem Is the Database"* — "어떤 daemon·socket·network service도 ticket state의 권위가 되어선 안 된다" — 에 정면으로 어긋난다. PR #13이 정확히 이 이유로 `ct2-lens-cx-daemon`·`ct2-lens-cx-tui`를 retire했다. 캔버스 write-back의 매끄러움은 daemon을 다시 들일 만한 가치가 없다 — 복사-붙여넣기/파일 드롭이 정답이다.

**회수 검증** (방식 A·B 공통, Phase 0 spec에 명시):
- 토큰/파일은 결정 `id`와 1회용 `nonce`를 포함 — helm은 진행 중 `decisions/pending/` 레코드와 대조해 위·변조·혼선을 차단.
- `ct2-helm-canvas recover`는 `nonce` 불일치 시 거부하고 비-0으로 종료.
- 검증 통과 시에만 `.ct2/.tmp/`→`mv`로 `decisions/answered/`에 기록하고 캔버스를 `answered/`로 이동 — 임의 명령 실행 표면 없이 파일 파싱만 한다.

---

## 6. 단계별 로드맵

### Phase 0 — Spec 정착 (1일, 티켓 1건)

- `spec/helm-canvas.md` 신규 작성: 캔버스 정의, 7패널 스키마, 다섯 설계 원칙(P1–P5), 자기완결 제약, **캔버스 4-상태 생명주기(`open/answered/sealed/expired/`)와 전이 규칙**, 피드백 루프 A·B, 회수 검증(`nonce`).
- `spec/PROTOCOL.md`의 "Reading Order"에 `spec/helm-canvas.md` 등재 — 본 spec이 PROTOCOL.md에 종속됨을 명시(하위 spec은 PROTOCOL.md와 충돌 시 정렬 대상).
- `spec/decision-bridge.md`에 `--html` provider format 추가 + PR #13 이전 표현인 "adapter view"를 PROTOCOL.md 용어에 맞춰 "provider format"으로 정리(§4.1 용어 주의 참조) + "캔버스 ↔ 결정 레코드 1:1 동반 전이" 규칙 추가.
- `spec/plan-evidence.md`에 `plans/canvas/` 경로·상태 편입 한 문단 추가.
- `AGENTS.md` Specs 표에 행 추가.

### Phase 1 — MVP: 복사-붙여넣기 캔버스 + 생명주기 (3일, 티켓 3건)

- `bin/ct2-helm-canvas` 신규: 결정 레코드 + 티켓 초안을 받아 자기완결 HTML 생성(Python stdlib 템플릿) → `plans/canvas/open/{id}-r{n}.canvas.html`에 atomic 배치. `decisions/pending/`도 동반 생성.
- `bin/ct2-helm-canvas recover`(또는 helm이 호출): copy 토큰을 검증·회수 → 캔버스 `open/`→`answered/`, 결정 레코드 `pending/`→`answered/` (S4).
- `bin/ct2-helm-canvas seal` 서브커맨드: helm이 `ct2-seal` 성공 *직후* 호출 → 짝지어진 캔버스를 `answered/`→`sealed/{id}/`로 이동 (S5). **`ct2-seal` 자체는 수정하지 않는다** — `ct2-seal`은 PROTOCOL.md의 Required Reference Tool이고, 그 계약("draft 검증 후 backlog로 이동")에 캔버스 부수효과를 끼워 넣으면 핵심 스크립트가 helm 전용 동작을 떠안게 된다(PROTOCOL.md "Adapter Boundary" 위반). 캔버스 생명주기는 전부 `ct2-helm-canvas` 안에 가둔다.
- `ct2-decision format`에 `--html` 분기 추가.
- 캔버스 HTML: 7패널 + 우측 결정 레코드 미러. 다섯 원칙(P1 JSON 미러 / P2 비용 요약 / P3 override delta / P4 advisory·비차단 / P5 자유 편집) 모두 구현. 인라인 CSS/JS, "결정 확정" 버튼 → 토큰 생성.
- `ct2-status`에 "결정 대기 캔버스 N건"(= `canvas/open/` 카운트) 표시 — 인박스처럼.
- helm SKILL.md에 `<workflow id="plan-canvas">` 추가 — §3.4의 5단계를 *기본* 동선으로. `AskUserQuestion`은 단발성 질의용 fallback으로 강등.
  - *전망*: protocol-reframe 문서(`docs/ct2-protocol-reframe-2026-05-13.md` §13.7)는 helm을 "가장 단순한 어댑터 형태"로 보고 향후 `adapters/{agent}/helm.md` 도입을 예고한다. 본 계획은 helm 어댑터가 아직 없는 시점 기준이므로 SKILL.md에 워크플로를 넣는다 — helm 어댑터가 생기면 `plan-canvas`의 런타임별 invocation 절은 그쪽으로 이관한다(결정 스키마·생명주기는 그대로 유지).
- `tests/test_canvas_lifecycle.py` 신규 — S1~S5 디렉터리 전이를 자동 assert (아래 "완료 게이트" 참조). 브라우저 수동 탐색은 이를 *보완*할 뿐 대체하지 않는다.

### Phase 2 — 파일 드롭 회수 (1일, 티켓 1건, 선택)

- 캔버스 HTML에 "결정 다운로드" 버튼 추가 — `decision-{id}.json`을 브라우저 기본 다운로드(서버 없음).
- `ct2-helm-canvas recover <file>`: 파일 경로를 받는 회수 경로. Phase 1의 토큰 회수와 검증 로직을 공유.
- **지속 서버는 도입하지 않는다** (§5 기각 사유). Phase 1의 복사-붙여넣기로 충분하면 이 Phase는 통째로 건너뛸 수 있다.

### Phase 3 — 표현력 강화 (점진적, 후속)

- 티켓 분할 패널: 카드 드래그-병합/분할, 2안 나란히 비교 뷰.
- 의존성 패널: 백로그 티켓과의 의존선을 SVG 그래프로 연결.
- 우선순위 슬라이더: 칸반 백로그 내 위치를 실시간 미리보기.
- (선택) 캔버스를 `ct2-status`의 읽기전용 칸반 뷰와 링크.

### 완료 게이트 — `/goal`이 직접 확인할 수 있는 조건

이 계획을 `/goal`로 개발할 때, 각 단계의 "완료"는 사람의 수동 확인이 아니라 **종료 코드로 판정 가능한 검사**여야 한다. `/goal`의 stop-hook은 조건 충족을 객관적으로 판별해야 멈춘다 — 수동 검증은 그 신호가 될 수 없다. CT2엔 이미 `tests/test_*.py`(stdlib only) 체계가 있고, 특히 `test_state_lifecycle.py`·`test_script_syntax.py`가 직접적인 선례이므로, 캔버스도 같은 자리에 검사를 추가한다.

| 단계 | 완료 게이트 (machine-checkable, 종료 코드 0 = done) |
|---|---|
| **Phase 0** | `spec/helm-canvas.md` 존재 + `PROTOCOL.md` Reading Order·`AGENTS.md` Specs 표에서 참조됨 + `ct2-verify`가 green(신규 spec이 conformance 위반 0) + `test_repository_hygiene.py`류 검사로 spec 링크 끊김 0 |
| **Phase 1** | `tests/test_canvas_lifecycle.py` 통과 — scratch `.ct2/`에서 ① `ct2-helm-canvas`가 `canvas/open/`에 파일 생성 + `decisions/pending/` 동반 ② `recover`가 `open/→answered/`·`pending/→answered/` 원자 전이 ③ `ct2-helm-canvas seal`이 `answered/→sealed/{id}/` 전이 ④ 모든 전이 후 캔버스↔레코드 상태 일치·고아 0 — 을 assert. `test_script_syntax.py`가 신규 bin 스크립트 자동 검사. `ct2-verify`가 green(신규 spec·tool이 conformance 위반 0). 캔버스 HTML은 `python3 -m html.parser` 파싱 무오류 + JS `node --check`(있을 때) |
| **Phase 2** | `tests/test_canvas_lifecycle.py`에 케이스 추가 — `ct2-helm-canvas recover <file>`가 nonce 불일치 파일을 거부(비-0 종료)하고, 정상 파일은 `decisions/answered/`에 atomic 기록 + 캔버스 `open/→answered/` 이동 |
| **Phase 3** | 패널별 기능에 대응하는 검사를 티켓별로 추가 (분할 가능) |

**원칙: 티켓의 AC는 "이 게이트가 green"으로 환원될 수 있어야 한다.** helm이 이 계획에서 티켓을 끊을 때 각 AC를 위 게이트의 한 줄에 매핑한다 — 그래야 `/goal`이 "구현 → 게이트 실행 → green이면 done"을 자율적으로 돌릴 수 있다. §9의 성공 지표는 *운영 성과*(기능이 만들어진 *뒤* 시간을 두고 측정)이지 dev-done 조건이 아니다 — 둘을 혼동하면 `/goal`이 영원히 멈추지 못한다.

산출물별 변경 요약:

| 구분 | 신규/변경 |
|---|---|
| spec | `spec/helm-canvas.md` 신규(7패널·P1–P5·4-상태 생명주기), `decision-bridge.md`·`plan-evidence.md` 보강 |
| bin | `bin/ct2-helm-canvas` 신규(서브커맨드 `generate`/`recover`/`seal`, 전부 one-shot), `bin/ct2-decision` `--html` 분기, `bin/ct2-status`에 `open/` 카운트. **`ct2-seal`·`ct2-reconcile` 등 Required Reference Tool은 미수정** |
| dir | `.ct2/plans/canvas/{open,answered,sealed,expired}/` — `ct2-init`이 생성 |
| tests | `tests/test_canvas_lifecycle.py` 신규(Phase 1) — 완료 게이트. Phase 2는 같은 파일에 파일-드롭 회수 케이스 추가 |
| skill | `claude-plugin/skills/ct2-helm/SKILL.md`에 `plan-canvas` 워크플로 추가 (codex 측 `codex-plugin/skills/ct2-helm/` 동기화) |
| docs | 본 문서, `AGENTS.md` Specs 표 |

---

## 7. HTML 생성 사양 (요약)

`spec/helm-canvas.md`에서 상술하되, 핵심 제약:

- **단일 파일** — 하나의 `.html`. 외부 리소스 참조 0. SVG는 인라인.
- **렌더 예산** — 생성 토큰은 Markdown 대비 2–4배(hada 글). 따라서 캔버스는 *결정이 실재할 때만* 생성. 단순 단발 질의는 여전히 `AskUserQuestion`.
- **결정 레코드 미러 (P1)** — 우측에 `.ct2/decisions/` 페이로드를 실시간 렌더. 위젯 조작 시 해당 필드를 갱신·하이라이트. HTML은 별도 상태를 갖지 않는다 — 위젯 = 레코드 필드.
- **비용 요약 (P2)** — 티켓 수·예상 작업량·In-scope 수·미해결 건수를 패널 조작에 따라 즉시 재계산.
- **override delta (P3)** — `ct2-helm-canvas`는 helm의 원안을 baseline으로 HTML에 임베드. 캔버스는 baseline 대비 변경분을 표시하고, 회수 토큰의 `overrides` 필드에 그 delta를 포함.
- **advisory·비차단 (P4)** — 확정/copy 버튼은 어떤 상태에서도 비활성화하지 않는다. 미해결 항목은 advisory 목록으로 표시하고, 토큰의 `open_items` 배열에 그대로 실어 helm에 전달. helm은 `open_items`가 비어 있지 않으면 seal 전에 대화로 마저 확인한다.
- **자유 편집 (P5)** — AC·범위·제약·티켓 제목은 `contenteditable` 텍스트. 항목 추가·삭제 가능. 캔버스는 helm의 제안값을 *초기값*으로만 쓴다 — 사용자가 그 위에 자유롭게 덮어쓴다.
- **상태 보존** — 새로고침해도 잃지 않도록 `localStorage`에 작업 상태 저장(서버 불필요).
- **접근성** — 키보드 조작 가능, 명도 대비 준수, 색만으로 정보 전달 금지(범위 칩은 색+텍스트+모양).
- **결정성** — 같은 결정 레코드 → 같은 HTML. `ct2-helm-canvas`는 순수 함수처럼 동작(타임스탬프 외).
- **회수 토큰 검증** — 붙여넣은 토큰은 결정 `id`와 nonce를 포함. helm은 진행 중 레코드와 대조해 위·변조/혼선 차단.

---

## 8. 리스크와 anti-bet

| 리스크 | 완화 |
|---|---|
| 캔버스 생성이 느려 계획 흐름이 끊김 | 결정이 실재할 때만 생성. 단발 질의는 `AskUserQuestion` 유지. 생성을 background로 |
| 사용자가 브라우저를 안 열고 텍스트를 선호 | 캔버스는 *기본*이되, helm은 항상 텍스트 fallback 제공. 강제하지 않음 |
| HTML이 사실상 제2의 진실원천이 됨 | 구조적 차단 — HTML은 `ct2-decision format --html` 출력. 합의 결과는 반드시 `ct2-helm-canvas recover`를 거쳐 `.ct2/decisions/answered/` JSON에 박제 |
| 사용자가 advisory를 무시하고 확정 → 불완전한 계획이 seal됨 | P4의 핵심 — 가두는 대신 *추적*한다. 미해결은 토큰의 `open_items`로 helm에 전달되고, helm은 이를 인지한 채 seal 전 대화로 확인한다. 그대로 진행하더라도 `open_items` 기록이 plan-evidence에 남아 lens가 감사할 수 있다. "막힌 적 없음"과 "추적 안 됨"은 다르다 |
| 위·변조된 토큰/파일이 회수됨 | `ct2-helm-canvas recover`가 결정 `id`·`nonce`를 진행 중 `decisions/pending/` 레코드와 대조, 불일치 시 비-0 종료. 회수 경로는 파일 파싱만 — 임의 명령 실행 표면 없음 |
| 지속 서버를 들이고 싶은 유혹 | §5에서 명시적으로 기각 — PROTOCOL.md "Agent Owns the Loop" 위반. 회수는 항상 one-shot `recover`로만 |
| 캔버스 HTML이 git diff를 오염 | `.ct2/plans/` 아래 — 이미 git 미추적 |
| forge/lens가 캔버스를 흉내내 권한 경계 침범 | 캔버스는 helm 전용으로 spec에 명시. forge/lens는 미사용 |

**명시적 anti-bet** (Product Strategy의 anti-bet 정신을 계승):
- 캔버스를 `ct2-status` 모니터링 대시보드로 키우지 않는다 — 계획 국면 한정.
- 캔버스에 상시 SaaS·인증·멀티유저를 붙이지 않는다 — 일회용 로컬 페이지.
- HTML을 evidence의 *단독* 근거로 삼지 않는다 — 결정 JSON이 정본.

---

## 9. 성공 지표

| 축 | 지표 | 초기 목표 |
|---|---|---|
| 합의 품질 | 캔버스 사용 티켓의 seal 후 helm-재방문(범위 재논의) 비율 | baseline 대비 −40% |
| 결정 가시성 | 계획 결정이 `.ct2/decisions/answered/`에 정규 레코드로 남는 비율 | ≥ 0.95 |
| 속도 | 캔버스 생성 → 사용자 확정 → seal 까지의 helm 왕복 횟수 | baseline 대비 −30% |
| 채택 | 계획 국면에서 캔버스가 기본 채널로 쓰인 비율 | ≥ 0.80 (텍스트 fallback 제외) |
| 감사성 | done 티켓 중 `canvas-r*.html` 계획 증거를 가진 비율 | ≥ 0.90 |
| 개입 신호 (P3) | seal된 티켓 중 `overrides`(helm 제안↔사용자 결정 delta)가 레코드에 포착된 비율 | ≥ 0.99 (delta 0건도 "동일"로 명시 기록) |

Product Strategy의 balanced scorecard에 매핑하면: **Evidence**(결정 레코드율·감사성·override 포착)와 **Trust**(재방문율 감소)를 직접 끌어올리며, **Cost/Latency**(왕복 횟수)를 해치지 않는 선에서 움직인다. 특히 `overrides` 신호는 Product Strategy Bet 4(역할 eval harness)의 입력이 된다 — helm이 *어디서 자주 빗나가는지*를 데이터로 보여주므로, 역할 정의 회귀 테스트의 직접 재료다.

---

## 10. 즉시 착수 항목 (티켓 후보)

helm이 본 계획을 채택하면 아래 순서로 티켓을 끊는다 (1티켓=1PR=1일):

1. `spec/helm-canvas.md` 작성(7패널·P1–P5·4-상태 생명주기) + `decision-bridge.md`/`plan-evidence.md`/`AGENTS.md` 보강. *(Phase 0)*
2. `bin/ct2-helm-canvas` MVP(생성→`open/`) + `ct2-decision format --html` 분기. *(Phase 1)*
3. 캔버스 생명주기: `ct2-helm-canvas recover`(`open/`→`answered/`) + `ct2-helm-canvas seal`(`answered/`→`sealed/`) + `ct2-init`의 디렉터리 생성 + `ct2-status` `open/` 카운트 + **`tests/test_canvas_lifecycle.py`**(이 티켓의 완료 게이트). *(Phase 1)*
4. helm `SKILL.md`에 `plan-canvas` 워크플로(§3.4 5단계) 추가 + codex 측 동기화. *(Phase 1)*
5. (선택) 파일 드롭 회수: 캔버스 "결정 다운로드" 버튼 + `ct2-helm-canvas recover <file>` + `test_canvas_lifecycle.py` 케이스 추가. *(Phase 2)*
6. 티켓 분할/의존성/우선순위 패널 표현력 강화. *(Phase 3, 분할 가능)*

각 티켓의 모든 AC는 §6 "완료 게이트" 표의 검사 한 줄로 환원되어야 한다 — 이것이 `/goal` 자율 개발의 종료 조건이다. 검사 없이 끊는 티켓은 `/goal`이 "done"을 판정할 수 없으므로 받지 않는다.

---

## 11. 구현 현황 (2026-05-19, `feat/helm-canvas`)

Phase 0–2를 구현 완료했다. Phase 3은 본 계획이 처음부터 "점진적·후속"으로 둔 표현력 강화이므로 후속 작업으로 남긴다.

| 항목 | 산출물 | 상태 |
|---|---|---|
| Phase 0 spec | `spec/helm-canvas.md`(신규), `PROTOCOL.md`·`decision-bridge.md`·`plan-evidence.md`·`AGENTS.md` 보강 | ✅ |
| 디렉터리 | `ct2-init`·`ensure_ct2`가 `plans/canvas/{open,answered,sealed,expired}/` 생성 | ✅ |
| 캔버스 렌더러 | `bin/_ct2_canvas.py` — 7패널·P1–P5·자기완결 HTML + 토큰 파서 | ✅ |
| CLI | `bin/ct2-helm-canvas` — `generate`/`recover`/`seal`/`expire` one-shot 서브커맨드 | ✅ |
| provider format | `ct2-decision format --html` | ✅ |
| 인박스 표시 | `ct2-status`의 "open canvases" 카운트 | ✅ |
| 워크플로 | claude·codex helm SKILL.md의 `plan-canvas` | ✅ |
| Phase 2 파일 드롭 | 캔버스 "다운로드" 버튼 + `ct2-helm-canvas recover --file` | ✅ |
| 완료 게이트 | `tests/test_canvas_lifecycle.py`(9 케이스), `ct2-verify` green, 전체 95 테스트 통과 | ✅ |
| Phase 3 | 드래그 병합/분할, 의존선 SVG 연결 — 후속 | ⏸ 의도적 후속 |

재검증(2026-05-19): §7 항목을 다시 대조해 누락분을 닫았다 — localStorage **복원**(저장만 있고 복원이 없었음), `role=button` 컨트롤의 **키보드 조작**, 패널 ⑤의 **의존성 그래프 SVG**(데이터 기반·실시간). 전체 96 테스트 + `ct2-verify` green.

---

## 부록 A. Helm Canvas 데모

본 계획의 컨셉을 글이 아니라 화면으로 확인할 수 있도록, 동작하는 데모 캔버스를 함께 제공한다:

```
docs/assets/helm-canvas-demo.html
```

브라우저에서 그대로 열면 (`file://`) 가상의 티켓 #42(OAuth 로그인)에 대한 캔버스가 뜬다. 처음 상태는 helm 확인 권장 3건(미확인 해석 + 보류 범위 1건 + ⚑모호 AC 1건)이지만 **확정 버튼은 처음부터 동작한다**. 패널을 조작하며 §3.2의 다섯 원칙을 직접 확인할 수 있다:

- **P1** — 위젯을 건드릴 때마다 우측 "결정 레코드" JSON이 그 자리에서 바뀌고 잠깐 빛난다.
- **P2** — 범위 칩을 토글하면 "이 계획 한눈에"의 In-scope 수가 즉시 갱신된다.
- **P3** — helm 제안과 다른 선택(예: '계정 연결'을 보류→제외)을 하면 "helm 제안 → 내 결정" delta에 누적된다.
- **P4** — 확인 권장 항목이 남아 있어도 "결정 확정" 버튼은 언제든 눌린다. 누르면 `open_items`에 그 항목들이 실린 채 토큰이 복사된다 — helm이 이어서 확인한다. 사용자를 가두지 않는다.
- **P5** — ⚑모호로 표시된 AC("로그인 UX가 자연스럽다")의 텍스트를 클릭해 "로그인 후 2초 내 메인 렌더"처럼 *직접 다시 쓸 수 있다*. 범위 항목·제약·인수 기준을 추가/삭제할 수도 있다.

데모는 자기완결(인라인 CSS/JS, 외부 의존성 0)이므로 캔버스가 따라야 할 기술 제약의 참조 구현이기도 하다.

## 부록 B. 결정 레코드 ↔ 캔버스 매핑 예시

```
.ct2/decisions/pending/dec-0007.json   (요약)
  question:  "티켓 #42 'OAuth 로그인'의 계획을 확정해주세요"
  questions: [해석, 범위, 티켓분할, AC, 우선순위, 제약]   ← 7패널의 소스
        │
        │  ct2-helm-canvas generate  (= ct2-decision format --html)
        ▼
.ct2/plans/canvas/open/42-oauth-login-r0.canvas.html
        │
        │  사용자 조작 → "결정 확정" → 토큰 복사 → helm에 붙여넣기
        ▼
helm: ct2-helm-canvas recover '<token>'   (nonce 검증)
        ▼
.ct2/decisions/answered/dec-0007.json     ← helm이 이걸 읽고 티켓 초안 확정
.ct2/plans/canvas/answered/42-oauth-login-r0.canvas.html  ← 캔버스 동반 이동
```

---

*본 계획서는 helm이 사용자와 검토 후 Phase 0 티켓부터 끊어 진행한다. spec-first 원칙에 따라 `spec/helm-canvas.md`가 구현보다 먼저다.*
