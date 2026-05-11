# CT2 VAO Completion Audit

Date: 2026-05-11
Objective: complete the plan in
`docs/ct2-verified-autonomy-os-strategy-2026-05.md` with test-driven
verification.

## Success Criteria

- Phase 0 Registry + Baseline mechanics exist and are tested.
- Bet 1 role contract/cost telemetry mechanics exist and are tested.
- Bet 2 plan evidence requirements exist in spec and forge role workflows.
- Bet 4 role eval baseline layout exists.
- Bet 3 advisory bridge is notify-only and tested against state mutation.
- Bet 5 native mirror remains advisory-only and has a spike report.
- Every new state plane is documented as advisory/evidentiary, not ticket-state
  authority.
- Every new operator-facing command is documented in `README.md`.
- Every new behavior surface has either a dedicated spec or an update to an
  existing authoritative spec.

## Prompt-to-Artifact Checklist

| Requirement | Evidence |
|---|---|
| `ct2-runtime-doctor` | `bin/ct2-runtime-doctor`; tests in `tests/test_vao_strategy.py` |
| `.ct2/runtime/capabilities.json` and degradations | `ct2-runtime-doctor`; `spec/runtime-capabilities.md`; status `--doctor` test |
| `.ct2/runtime/codex-flags-actual.md` | `ct2-runtime-doctor`; runtime doctor test |
| `ct2-baseline` and `.ct2/telemetry/baseline-2026-05.json` | `bin/ct2-baseline`; baseline/status test |
| Balanced scorecard status output | `bin/ct2-status`; `spec/balanced-scorecard.md`; status test |
| Role contracts | `config/harness.yaml` `role_contracts`; `spec/role-contracts.md`; init/config test |
| `ct2-role-run`, `ct2-cost`, cost JSONL | `bin/ct2-role-run`, `bin/ct2-cost`; success and failure telemetry tests |
| Plan evidence | `spec/plan-evidence.md`; `.ct2/plans/`; Claude and Codex forge skill updates; role-doc test |
| Five plan-first tickets gate | `ct2-plan-audit`; regression fixture with 5 in-review tickets and plan files |
| Role eval baseline layout | `.ct2/evals/{ct2-helm,ct2-forge,ct2-lens-cc,ct2-lens-cx}/`; `spec/role-evals.md`; init test |
| Role eval runner and regression catch | `bin/ct2-role-eval`; `config/evals/*/*.json`; `ct2-vao-pilot` intentional regression step |
| Decision bridge | `bin/ct2-decision`; `spec/decision-bridge.md`; `.ct2/decisions/*`; Codex app-server pending decision records; tests |
| Hook guardrails and policy compiler | existing hook scripts; `bin/ct2-policy-compile`; hook and compiler tests |
| Evidence graph | `bin/ct2-evidence`; `spec/evidence-graph.md`; command, artifact, screenshot, verifier, and hook-event evidence tests |
| Advisory runtime bridge | `bin/ct2-bridge`; `config/watchers/advisory-local.json`; `spec/external-channels.md`; 5-notification/no-state-mutation test |
| Full phase pilot | `bin/ct2-vao-pilot`; `docs/ct2-vao-phase-completion-report-2026-05-11.md` |
| Native mirror advisory spike | `spec/runtime-mirror.md`; `docs/ct2-native-task-mirror-spike-2026-05.md` |
| Phase 0 / Bet 1 readiness | `docs/ct2-phase0-bet1-readiness-2026-05.md` |
| Directory authority | `bin/ct2-init`; `spec/directory-structure.md`; init directory test |
| Self-verification standard | `docs/ct2-vao-self-verification-criteria-2026-05-11.md` |
| Documentation coverage | `README.md` command table; `tests/test_vao_strategy.py` documentation coverage test |
| Self-verification executable | `bin/ct2-vao-self-verify`; static and executed gate reports |
| Self-verification report | `docs/ct2-vao-self-verification-report-2026-05-11.md` |

## Verification Evidence

Commands run:

```bash
python3 -m unittest discover -s tests
python3 -c 'import pathlib, sys; [compile(pathlib.Path(p).read_text(encoding="utf-8"), p, "exec") for p in sys.argv[1:]]' bin/ct2-codex-goal bin/ct2-codex-doctor bin/ct2-codex-app-driver bin/_ct2_validate_review_sidecar.py bin/ct2-status bin/ct2-runtime-doctor bin/ct2-baseline bin/ct2-role-run bin/ct2-cost bin/ct2-evidence bin/ct2-decision bin/ct2-policy-compile bin/ct2-bridge bin/ct2-plan-audit bin/ct2-role-eval bin/ct2-vao-pilot bin/ct2-vao-self-verify bin/_ct2_vao.py
bash -n install.sh bin/ct2-init bin/ct2-lens-cx-daemon bin/ct2-lens-cx-tui bin/ct2-revise bin/ct2-seal claude-plugin/hooks/enforce-write-access.sh claude-plugin/hooks/enforce-review-independence.sh
python3 -m json.tool codex-plugin/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool claude-plugin/hooks/hooks.json >/dev/null
git diff --check
```

Latest full test result: 29 tests passed.

## Documentation Quality Gate

The documentation standard is defined in
`docs/ct2-vao-self-verification-criteria-2026-05-11.md`.

Required documentation coverage:

- README command row for every new user/operator-facing command.
- Spec coverage for every behavior-changing surface.
- Directory structure coverage for every new `.ct2/` plane.
- Safety-boundary language for advisory-only and evidence-only planes.
- Completion audit row mapping each strategy requirement to concrete evidence.

## Measurement Caveat

The strategy forbids claiming metric success without baseline samples. This
implementation records insufficient samples as `measurement_started` and the
Phase 0 readiness report explicitly blocks public trust/cost claims until real
project data reaches the configured thresholds.

For the stricter question "are all strategy phases fully complete with local
runtime and pilot evidence?", see
`docs/ct2-verified-autonomy-os-full-phase-audit-2026-05-11.md`. That audit
concludes that local phase-exit mechanics are complete after
`ct2-vao-pilot`, while production metric claims remain separate.
