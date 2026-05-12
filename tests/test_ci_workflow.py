import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


class CiWorkflowTest(unittest.TestCase):
    """Assert behavioural invariants of the CI workflow.

    These assertions intentionally target the gates that matter — triggers,
    permissions, matrix coverage, the diff-range gate, and the verifier
    invocation — rather than cosmetic formatting that would churn this test on
    every refactor.
    """

    def setUp(self):
        self.workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_triggers_cover_pr_push_and_manual(self):
        for snippet in ("pull_request:", "push:", "workflow_dispatch:"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.workflow)

    def test_permissions_are_minimum_required(self):
        self.assertIn("permissions:", self.workflow)
        self.assertIn("contents: read", self.workflow)

    def test_concurrency_cancels_in_flight_runs(self):
        self.assertIn("concurrency:", self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)

    def test_python_matrix_covers_supported_versions(self):
        self.assertIn(
            'python-version: ["3.10", "3.11", "3.12", "3.13"]',
            self.workflow,
        )
        self.assertIn("fail-fast: false", self.workflow)

    def test_actions_are_pinned_to_major_versions(self):
        for action in ("actions/checkout@v6", "actions/setup-python@v6"):
            with self.subTest(action=action):
                self.assertIn(action, self.workflow)

    def test_checkout_does_not_persist_credentials(self):
        self.assertIn("persist-credentials: false", self.workflow)

    def test_both_jobs_request_full_history(self):
        # Both `unit-tests` and `repository-checks` need fetch-depth: 0 — the
        # whitespace gate cannot resolve commit ranges on a shallow checkout.
        # A single occurrence would mean one of the jobs is silently shallow,
        # which is the exact regression that broke this PR before.
        self.assertGreaterEqual(
            self.workflow.count("fetch-depth: 0"),
            2,
            "both CI jobs must specify fetch-depth: 0",
        )

    def test_both_jobs_bound_runtime(self):
        # Hanging jobs must not consume the 6-hour runner default.
        self.assertGreaterEqual(
            self.workflow.count("timeout-minutes:"),
            2,
            "both CI jobs must specify timeout-minutes",
        )

    def test_unit_tests_run_via_stdlib_unittest(self):
        # No external dependency manager — discovery must use the stdlib.
        self.assertIn("python3 -m unittest discover -s tests", self.workflow)

    def test_vao_self_verifier_is_the_single_source_of_truth(self):
        self.assertIn(
            "python3 bin/ct2-vao-self-verify --run-checks --json --repo .",
            self.workflow,
        )
        # Static bash/JSON gates were intentionally removed in favour of the
        # dynamic self-verifier — guard against re-introduction.
        self.assertNotIn("Check bash syntax", self.workflow)
        self.assertNotIn("Validate plugin JSON", self.workflow)

    def test_whitespace_gate_validates_full_change_range(self):
        # PR events must compare the PR base to the PR head, not the worktree.
        self.assertIn("${{ github.event.pull_request.base.sha }}", self.workflow)
        # Push events must compare the previous tip to the new tip so multi-
        # commit pushes are fully covered — not just the last commit.
        self.assertIn("${{ github.event.before }}", self.workflow)
        # And the runner must dispatch on the event kind.
        self.assertIn("${{ github.event_name }}", self.workflow)
        self.assertIn("git diff --check", self.workflow)


if __name__ == "__main__":
    unittest.main()
