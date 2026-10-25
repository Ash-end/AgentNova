"""真实临时文件验证分阶段停止、参数传递和文件范围边界。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from exercises.verify_metrics import verify_metrics
from experiment_agent.metrics_workflow import run_metrics_file_workflow
from experiment_agent.tools.registry import build_tool_registry


class MetricsFileWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.root = self.parent / "project"
        (self.root / "data").mkdir(parents=True)
        self.tools = build_tool_registry(str(self.root))
        self.reader = Mock(wraps=self.tools["read_text_file"])
        self.tools["read_text_file"] = self.reader
        verifier_patch = patch("experiment_agent.metrics_workflow.verify_metrics", wraps=verify_metrics)
        self.verifier = verifier_patch.start()
        self.addCleanup(verifier_patch.stop)

    def write(self, content):
        (self.root / "data" / "metrics.json").write_text(content, encoding="utf-8")

    def run_case(self, relative_path="data/metrics.json", max_mse=0.1):
        return run_metrics_file_workflow(self.tools, relative_path, max_mse=max_mse)

    def assert_steps(self, result, steps):
        self.assertEqual([event["step"] for event in result["trace"]], steps)

    def test_real_utf8_file_is_parsed_before_verification(self):
        metrics = {"mse": 0.04, "说明": "真实文件"}
        self.write(json.dumps(metrics, ensure_ascii=False))
        result = self.run_case()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["result"], {
            "status": "passed", "reason": "verified_metrics", "mse": 0.04,
        })
        self.assert_steps(result, ["read_text_file", "parse_json", "verify_metrics"])
        self.assertEqual(result["trace"][1]["result"], {"status": "success", "data": metrics})
        self.reader.assert_called_once_with(relative_path="data/metrics.json")
        self.verifier.assert_called_once_with(metrics, max_mse=0.1)

    def test_missing_file_stops_before_parsing_or_verification(self):
        result = self.run_case()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "file_not_found")
        self.assert_steps(result, ["read_text_file"])
        self.verifier.assert_not_called()

    def test_invalid_json_stops_after_reading_without_verification(self):
        self.write('{"mse": 0.04,}')
        result = self.run_case()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["trace"][0]["result"]["status"], "success")
        self.assertEqual(result["result"]["error_type"], "invalid_json")
        self.assertGreaterEqual(result["result"]["line"], 1)
        self.assertGreaterEqual(result["result"]["column"], 1)
        self.assert_steps(result, ["read_text_file", "parse_json"])
        self.verifier.assert_not_called()

    def test_numeric_string_is_valid_json_but_invalid_metric(self):
        self.write('{"mse": "0.04"}')
        result = self.run_case()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["trace"][1]["result"]["status"], "success")
        self.assertEqual(result["result"]["reason"], "invalid_metrics")
        self.assert_steps(result, ["read_text_file", "parse_json", "verify_metrics"])
        self.verifier.assert_called_once_with({"mse": "0.04"}, max_mse=0.1)

    def test_threshold_is_forwarded_and_read_success_does_not_override_verdict(self):
        self.write('{"mse": 0.15}')
        failed = self.run_case(max_mse=0.12)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["trace"][0]["result"]["status"], "success")
        self.assertEqual(failed["result"], {
            "status": "failed", "reason": "mse_above_threshold", "mse": 0.15, "max_mse": 0.12,
        })
        passed = self.run_case(max_mse=0.2)
        self.assertEqual(passed["status"], "passed")
        self.assertEqual(self.verifier.call_count, 2)
        self.verifier.assert_called_with({"mse": 0.15}, max_mse=0.2)

    def test_existing_file_outside_project_is_rejected(self):
        (self.parent / "outside.json").write_text('{"mse": 0.01}', encoding="utf-8")
        result = self.run_case("../outside.json")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "path_outside_project")
        self.assert_steps(result, ["read_text_file"])
        self.verifier.assert_not_called()

    def test_invalid_utf8_stops_at_tool_exception_conversion(self):
        (self.root / "data" / "metrics.json").write_bytes(b"\xff\xfe")
        result = self.run_case()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "invalid_encoding")
        self.assert_steps(result, ["read_text_file"])
        self.verifier.assert_not_called()

    def test_valid_json_with_wrong_top_level_type_reaches_metric_verifier(self):
        for metrics in (None, [], 0, True):
            with self.subTest(metrics=metrics):
                self.verifier.reset_mock()
                self.write(json.dumps(metrics))
                result = self.run_case()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["trace"][1]["result"]["status"], "success")
                self.assertEqual(result["result"]["reason"], "invalid_metrics")
                self.verifier.assert_called_once_with(metrics, max_mse=0.1)


if __name__ == "__main__":
    unittest.main()
