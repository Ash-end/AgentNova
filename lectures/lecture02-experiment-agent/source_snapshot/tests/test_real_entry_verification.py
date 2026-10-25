"""真实入口的验收连接测试：只替换 HTTP 响应，文件工具仍实际执行。"""

from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from labs.l14_multi_tool_agent import run_case
from labs.l16_agent_task_verifier import tool_reply, final_reply


class RealEntryVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "labs/fixtures").mkdir(parents=True)
        (self.root / "labs/fixtures/hello.txt").write_text("目标正文\n", encoding="utf-8")
        (self.root / "other.txt").write_text("其他正文\n", encoding="utf-8")

    def run_entry(self, replies, case="discover", max_steps=5):
        http_responses = [BytesIO(json.dumps(reply, ensure_ascii=False).encode("utf-8"))
                          for reply in replies]
        output = StringIO()
        with patch("labs.l14_multi_tool_agent.urlopen", side_effect=http_responses), redirect_stdout(output):
            accepted = run_case(self.root, case, [], max_steps)
        path = self.root / "reports" / f"l14_multi_tool_agent_{case}.json"
        return accepted, output.getvalue(), json.loads(path.read_text(encoding="utf-8"))

    def test_success_displays_and_saves_separate_loop_and_verification_results(self):
        accepted, output, report = self.run_entry([
            tool_reply("list_directory", "labs/fixtures"),
            tool_reply("read_text_file", "labs/fixtures/hello.txt"), final_reply("目标正文\n"),
        ])
        self.assertTrue(accepted)
        self.assertIn("Loop status: completed", output)
        self.assertIn("Task verification: passed", output)
        self.assertEqual(report["result"]["status"], "completed")
        self.assertEqual(report["verification"], {
            "status": "passed", "reason": "verified_read", "relative_path": "labs/fixtures/hello.txt",
        })
        self.assertEqual(len(report["requests"]), 3)

    def test_final_claim_without_reading_fails_acceptance_but_preserves_completed_loop(self):
        accepted, output, report = self.run_entry([
            tool_reply("list_directory", "labs/fixtures"), final_reply("已读取，任务完成。"),
        ])
        self.assertFalse(accepted)
        self.assertIn("Loop status: completed", output)
        self.assertIn("Task verification: failed", output)
        self.assertEqual(report["result"]["status"], "completed")
        self.assertEqual(report["verification"]["reason"], "missing_read_evidence")

    def test_wrong_file_reports_expected_and_actual_paths(self):
        accepted, output, report = self.run_entry([
            tool_reply("list_directory", "labs/fixtures"),
            tool_reply("read_text_file", "other.txt"), final_reply("完成。"),
        ])
        self.assertFalse(accepted)
        self.assertIn("Expected path: labs/fixtures/hello.txt", output)
        self.assertIn("Actual path: other.txt", output)
        self.assertEqual(report["result"]["status"], "completed")
        self.assertEqual(report["verification"]["reason"], "wrong_file_read")

    def test_list_and_read_cases_do_not_use_discovery_only_verifier(self):
        cases = {
            "list": [tool_reply("list_directory", "labs/fixtures"), final_reply("hello.txt file")],
            "read": [tool_reply("read_text_file", "labs/fixtures/hello.txt"), final_reply("目标正文\n")],
        }
        with patch("labs.l14_multi_tool_agent.verify_unique_text_read") as verifier:
            for case, replies in cases.items():
                with self.subTest(case=case):
                    accepted, output, report = self.run_entry(replies, case=case)
                    self.assertTrue(accepted)
                    self.assertIn("Task verification: not_applicable", output)
                    self.assertEqual(report["verification"]["reason"], "discover_only")
            verifier.assert_not_called()

    def test_step_limit_failure_still_saves_verification_and_observations(self):
        accepted, output, report = self.run_entry([
            tool_reply("list_directory", "labs/fixtures"),
        ], max_steps=1)
        self.assertFalse(accepted)
        self.assertIn("Loop status: failed", output)
        self.assertEqual(report["verification"]["reason"], "loop_not_completed")
        self.assertEqual(report["result"]["error_type"], "max_steps_exceeded")
        self.assertEqual(report["observed_tools"], ["list_directory"])

    def test_valid_evidence_can_pass_despite_extra_directory_call_in_diagnostic_sequence(self):
        accepted, output, report = self.run_entry([
            tool_reply("list_directory", "labs/fixtures"),
            tool_reply("list_directory", "labs/fixtures"),
            tool_reply("read_text_file", "labs/fixtures/hello.txt"), final_reply("目标正文\n"),
        ])
        self.assertTrue(accepted)
        self.assertFalse(report["expected_sequence_matched"])
        self.assertEqual(report["verification"]["status"], "passed")
