import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args, cwd=None, env=None):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def write_fanout_record(ct2_dir, name="fanout-001-20260610T120000Z.json", **overrides):
    record = {
        "schema_version": "1",
        "ticket": "001",
        "fanout_width": 8,
        "agent_count": 6,
        "source_directive": None,
        "recorded_at": "2026-06-10T12:00:00Z",
    }
    record.update(overrides)
    fanout_dir = ct2_dir / "runtime" / "fanout"
    fanout_dir.mkdir(parents=True, exist_ok=True)
    path = fanout_dir / name
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


class CostFanoutTest(unittest.TestCase):
    maxDiff = None

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project])
        self.assertEqual(init.returncode, 0, init.stderr)
        return project

    def baseline_report(self, project):
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-baseline", "--json", project])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def cost_report(self, project):
        proc = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-cost", "--json", project])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_absent_records_leave_baseline_and_cost_output_unchanged(self):
        project = self.make_project()

        report = self.baseline_report(project)
        self.assertNotIn("fanout", report["scorecard"]["cost_latency"])

        summary = self.cost_report(project)
        self.assertNotIn("fanout", summary)

        baseline_text = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-baseline", project])
        self.assertEqual(baseline_text.returncode, 0, baseline_text.stderr)
        self.assertNotIn("fanout", baseline_text.stdout)

        cost_text = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-cost", project])
        self.assertEqual(cost_text.returncode, 0, cost_text.stderr)
        self.assertNotIn("fanout", cost_text.stdout)

    def test_empty_fanout_directory_changes_nothing(self):
        project = self.make_project()
        (project / ".ct2" / "runtime" / "fanout").mkdir(parents=True, exist_ok=True)

        report = self.baseline_report(project)
        self.assertNotIn("fanout", report["scorecard"]["cost_latency"])

        summary = self.cost_report(project)
        self.assertNotIn("fanout", summary)

    def test_present_record_surfaces_agent_count_and_width(self):
        project = self.make_project()
        write_fanout_record(project / ".ct2")

        report = self.baseline_report(project)
        fanout = report["scorecard"]["cost_latency"]["fanout"]
        self.assertTrue(fanout["advisory"])
        self.assertEqual(1, fanout["runs"])
        self.assertEqual(6, fanout["agent_count_p50"])
        self.assertEqual(6, fanout["agent_count_max"])
        self.assertEqual(8, fanout["fanout_width_max"])
        self.assertIsNone(fanout["speedup_vs_serial_p50"])

        summary = self.cost_report(project)
        self.assertTrue(summary["fanout"]["advisory"])
        self.assertEqual(1, summary["fanout"]["runs"])
        self.assertEqual(6, summary["fanout"]["agent_count_total"])
        self.assertEqual(8, summary["fanout"]["fanout_width_max"])

    def test_record_with_durations_yields_speedup_signal(self):
        project = self.make_project()
        write_fanout_record(
            project / ".ct2",
            wall_ms=1000,
            agent_ms_total=4000,
        )

        report = self.baseline_report(project)
        fanout = report["scorecard"]["cost_latency"]["fanout"]
        self.assertEqual(4.0, fanout["speedup_vs_serial_p50"])

    def test_multiple_records_aggregate_and_malformed_records_are_skipped(self):
        project = self.make_project()
        ct2 = project / ".ct2"
        write_fanout_record(ct2, name="fanout-001-20260610T120000Z.json", agent_count=4, fanout_width=4)
        write_fanout_record(
            ct2,
            name="fanout-002-20260610T130000Z.json",
            ticket="002",
            agent_count=12,
            fanout_width=16,
        )
        broken = ct2 / "runtime" / "fanout" / "fanout-003-20260610T140000Z.json"
        broken.write_text("{not json", encoding="utf-8")

        report = self.baseline_report(project)
        fanout = report["scorecard"]["cost_latency"]["fanout"]
        self.assertEqual(2, fanout["runs"])
        self.assertEqual(8, fanout["agent_count_p50"])
        self.assertEqual(12, fanout["agent_count_max"])
        self.assertEqual(16, fanout["fanout_width_max"])

        summary = self.cost_report(project)
        self.assertEqual(2, summary["fanout"]["runs"])
        self.assertEqual(16, summary["fanout"]["agent_count_total"])
        self.assertEqual(16, summary["fanout"]["fanout_width_max"])

    def test_text_output_renders_fanout_line_when_records_exist(self):
        project = self.make_project()
        write_fanout_record(project / ".ct2")

        baseline_text = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-baseline", project])
        self.assertEqual(baseline_text.returncode, 0, baseline_text.stderr)
        self.assertIn("fanout (advisory): runs=1", baseline_text.stdout)

        cost_text = run_cmd([PYTHON, REPO_ROOT / "bin" / "ct2-cost", project])
        self.assertEqual(cost_text.returncode, 0, cost_text.stderr)
        self.assertIn("fanout (advisory): runs=1 agents=6 width_max=8", cost_text.stdout)


if __name__ == "__main__":
    unittest.main()
