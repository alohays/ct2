# CT2 VAO Full Implementation Self-Review Criteria

Date: 2026-05-11
Scope: full implementation review for
`docs/ct2-verified-autonomy-os-strategy-2026-05.md`

## Objective

Define the conditions for judging whether the full Verified Autonomy OS strategy
implementation was completed correctly. These criteria are stricter than normal
test completion. A reviewer must reject completion if any gate below is missing,
weakly evidenced, or only proven by a proxy signal.

## Review Rule

The implementation is complete only when:

- Every requirement in the strategy maps to at least one concrete artifact and
  at least one executed verification signal.
- Every phase has positive proof, negative proof, documentation proof, and
  operator proof.
- Every claim in the completion report is backed by inspectable file or command
  evidence.
- No safety invariant is satisfied only by intent, comments, or unchecked
  documentation.
- Production metric claims are separated from local pilot mechanics.

If any checklist row is unknown, uninspected, or unverifiable, the status is
`incomplete`.

## Evidence Strength

Use the strongest available evidence for each claim.

| Level | Evidence type | Examples | Counts as completion evidence |
|---|---|---|---|
| A | Executed command output | unittest, `ct2-vao-self-verify --run-checks`, `ct2-vao-pilot`, `git diff --check` | Yes |
| B | Runtime artifact inspected after execution | `.ct2/runtime/capabilities.json`, `.ct2/telemetry/baseline-2026-05.json`, `.ct2/evals/results.jsonl` | Yes |
| C | Static artifact inspected | source files, specs, config fixtures, README rows | Yes, but never alone |
| D | Negative proof | intentional role regression caught, state mutation count `0`, bridge state-move rejection | Required for safety gates |
| E | Documentation proof | audit reports, operator docs, criteria docs | Required, but never alone |
| F | Proxy signal | green manifest, unchecked checklist, generated summary | No, unless backed by A-D |

Each phase must have at least one A-level signal and one B- or D-level signal.

## Gate Matrix

| Gate | Metric | Pass threshold | Required measurement |
|---|---:|---:|---|
| Requirement traceability | Strategy requirements with artifact + verifier mapping / all strategy requirements | `1.0` | Full phase audit table plus inspected files |
| Artifact completeness | Required commands, specs, fixtures, reports, docs present / required artifacts | `1.0` | `ct2-vao-self-verify` artifact gate |
| Executed verification | Required checks passing / required checks | `1.0` | `ct2-vao-self-verify --run-checks --json --repo .` |
| Runtime pilot completion | Completed phase booleans / all phase booleans | `1.0` | Latest `.ct2/runtime/artifacts/vao-pilot-*.json` |
| Runtime evidence existence | Required runtime files present / required runtime files | `1.0` | direct `find .ct2 ...` inspection |
| Negative safety proof | Required negative cases proven / required negative cases | `1.0` | state mutation `0`, regression caught, bridge state-move denied |
| Documentation coverage | User/operator docs and specs for surfaces / implemented surfaces | `1.0` | README, specs, audit docs |
| Measurement honesty | Claims with stated evidence class and caveat / all metric claims | `1.0` | audit docs separate local pilot from production claims |
| Git hygiene | Unexpected generated cache/trash files | `0` | `find . -name __pycache__`, `git status --short` |
| Formatting hygiene | whitespace errors | `0` | `git diff --check` |

## Phase Checklist

### Phase 0: Registry + Baseline

Required evidence:

- `ct2-runtime-doctor` exists, compiles, and runs.
- `.ct2/runtime/capabilities.json` exists after the pilot.
- `.ct2/runtime/degradations.md` exists after the pilot.
- `.ct2/runtime/codex-flags-actual.md` exists after the pilot.
- `ct2-baseline` writes `.ct2/telemetry/baseline-2026-05.json`.
- Baseline has `inputs.done_tickets >= 20`.
- Trust and Evidence status are `measured` for the local pilot.
- README and `spec/runtime-capabilities.md` document authority boundaries.

Metrics:

```text
runtime_file_coverage = existing_required_runtime_files / 4
baseline_sample_size = baseline.inputs.done_tickets
trust_measured = baseline.scorecard.trust.status == "measured"
evidence_measured = baseline.scorecard.evidence.status == "measured"
```

Pass threshold:

- `runtime_file_coverage == 1.0`
- `baseline_sample_size >= 20`
- `trust_measured == true`
- `evidence_measured == true`

### Bet 1: Cost-Aware Role Contracts

Required evidence:

- `config/harness.yaml` has `role_contracts`.
- `spec/role-contracts.md` documents the contract.
- `ct2-role-run` records cost/latency telemetry.
- `ct2-cost` summarizes cost telemetry.
- `.ct2/telemetry/cost.jsonl` has at least five pilot events.
- Cost claims are local pilot mechanics, not production savings claims.

Metrics:

```text
role_contract_coverage = roles_with_contracts / expected_roles
cost_event_count = len(cost.jsonl)
cost_summary_roles = roles_reported_by_ct2_cost
```

Pass threshold:

- `role_contract_coverage == 1.0`
- `cost_event_count >= 5`
- `cost_summary_roles >= 4`

### Bet 2: Plan-Mode-First Forge

Required evidence:

- Forge role docs require `.ct2/plans` before source edits.
- `ct2-plan-audit` exists and catches missing plans.
- At least five pilot tickets are in `in-review` with plan files.
- `ct2-plan-audit` passes over active/review/done tickets.
- Review comparison artifact exists.

Metrics:

```text
plan_first_ticket_count = count(.ct2/in-review/93*-vao-pilot.md)
plan_audit_complete = ct2-plan-audit.complete
plan_audit_checked = ct2-plan-audit.tickets_checked
```

Pass threshold:

- `plan_first_ticket_count >= 5`
- `plan_audit_complete == true`
- `plan_audit_checked >= 5`

### Bet 4: Eval Harness

Required evidence:

- `ct2-role-eval` exists, compiles, and runs.
- Default eval cases exist under `config/evals/`.
- `ct2-init` copies default eval cases into `.ct2/evals/*/cases/`.
- `.ct2/evals/results.jsonl` exists after eval execution.
- At least five fixed cases pass.
- An intentional role markdown regression fails as expected.

Metrics:

```text
role_eval_case_count = latest_role_eval.case_count
role_eval_pass = latest_role_eval.complete
intentional_regression_returncode = expected_failure_step.returncode
```

Pass threshold:

- `role_eval_case_count >= 5`
- `role_eval_pass == true`
- `intentional_regression_returncode != 0`

### Bet 3: Ambient Advisory Bridge

Required evidence:

- `ct2-bridge notify` writes inbox messages and telemetry.
- `ct2-bridge state-move` rejects state mutation.
- Watcher definitions exist under `config/watchers/` and `.ct2/watchers/`.
- At least five advisory notifications are recorded.
- Ticket state hashes are unchanged by bridge notifications.

Metrics:

```text
advisory_notification_count = count(events.type == "advisory_notification")
state_mutation_event_count = count(events.state_mutation == true)
ticket_state_unchanged = before_hashes == after_hashes
```

Pass threshold:

- `advisory_notification_count >= 5`
- `state_mutation_event_count == 0`
- `ticket_state_unchanged == true`

### Bet 5: Native Task Graph Mirror

Required evidence:

- `spec/runtime-mirror.md` exists.
- `docs/ct2-native-task-mirror-spike-2026-05.md` exists.
- The spike states production native sync is intentionally out of scope.
- No native-to-CT2 ticket mutation path exists.

Metrics:

```text
mirror_spike_docs_present = true
native_state_mutation_paths = 0
```

Pass threshold:

- `mirror_spike_docs_present == true`
- `native_state_mutation_paths == 0`

## Cross-Cutting Checklist

### Decision Bridge

- `ct2-decision ask` creates pending records.
- `ct2-decision answer` moves pending to answered and audit.
- `ct2-decision format --provider codex` emits `item/tool/requestUserInput`.
- `ct2-decision format --provider claude` emits `AskUserQuestion`.
- Decision records cannot waive reviewer criteria.

Metric:

```text
provider_adapter_coverage = implemented_provider_formats / 2
```

Pass threshold: `provider_adapter_coverage == 1.0`.

### Evidence Graph

- `ct2-evidence command` writes command evidence.
- `ct2-evidence artifact` writes artifact evidence.
- `ct2-evidence screenshot` writes screenshot evidence.
- `ct2-evidence verifier` writes verifier evidence.
- `ct2-evidence hook-event` writes hook-event evidence.
- All evidence claims append to `.ct2/evidence/claims.jsonl`.
- Prompt/tool payloads are not stored by default.

Metric:

```text
evidence_kind_coverage = observed_evidence_kinds / {"command","artifact","screenshot","verifier","hook-event"}
```

Pass threshold: all five kinds are supported by tests; local pilot must include
at least artifact, screenshot, verifier, and hook-event.

### Safety Invariants

- External bridge cannot move ticket state.
- Watchers are notify-only.
- Runtime, evidence, telemetry, decisions, plans, watchers, and evals never
  replace Kanban directory authority.
- Reviewers cannot approve by reading the partner sidecar first.
- Done state remains dual-review authoritative.
- `.ct2/` remains excluded via `.git/info/exclude`, not tracked.

Metrics:

```text
bridge_state_mutation_count = 0
review_independence_negative_test_pass = true
tracked_ct2_file_count = 0
done_without_dual_approval_count = 0
```

All must pass.

## Documentation Checklist

Every implementation surface must have all relevant documentation:

| Surface | Required docs |
|---|---|
| CLI command | README command row, regression test, audit row |
| Runtime file | `spec/directory-structure.md`, producing command, consuming command |
| Behavior contract | dedicated spec or existing spec update |
| Safety boundary | explicit "must not" rule and negative test |
| Operator workflow | command sequence and report path |
| Metric claim | source file, command, threshold, caveat |
| Pilot artifact | tracked summary doc plus `.ct2` runtime artifact path |

Metrics:

```text
documented_surface_ratio = documented_surfaces / implemented_surfaces
operator_doc_ratio = documented_operator_commands / user_facing_commands
audit_row_ratio = audit_rows_with_artifact_and_verifier / audit_rows
```

Pass threshold: all ratios `1.0`.

## Completion Audit Procedure

Before declaring completion, perform this procedure in order:

1. Restate the objective as concrete deliverables and gates.
2. Build a prompt-to-artifact checklist from the strategy, audits, and new files.
3. Inspect source, specs, README, fixtures, and reports.
4. Run `python3 bin/ct2-vao-pilot --project-dir . --report-file docs/ct2-vao-phase-completion-report-2026-05-11.md --json`.
5. Run `python3 bin/ct2-vao-self-verify --run-checks --json --repo .`.
6. Run direct runtime inspection for `.ct2` artifacts and JSON metrics.
7. Run `git diff --check`.
8. Confirm no `__pycache__` or generated trash remains.
9. Confirm `.ct2/` is not tracked.
10. Update the full phase audit and self-verification report with the latest
    results.

## Hard Fail Conditions

Any of these makes the implementation incomplete:

- A strategy phase is marked complete without an executed command.
- A phase is proven only by tests, without runtime artifact inspection.
- A safety invariant lacks a negative test or negative pilot proof.
- A metric claim lacks sample size, threshold, and source path.
- A new CLI command is absent from README.
- A new runtime directory is absent from `spec/directory-structure.md`.
- `ct2-vao-self-verify --run-checks` fails.
- `git diff --check` fails.
- `.ct2/` files are tracked by git.
- Production Trust, Evidence, or cost reduction is claimed from local pilot data.

## Final Verdict Template

Use this structure when closing the review:

```text
Verdict: complete | incomplete

Objective:
- ...

Prompt-to-artifact checklist:
- Requirement -> artifact -> verifier -> status

Metrics:
- requirement_traceability = ...
- runtime_pilot_completion = ...
- negative_safety_proof = ...
- documentation_coverage = ...

Direct evidence inspected:
- files
- command outputs
- runtime JSON values

Residual caveats:
- production metric claims require production history
```
