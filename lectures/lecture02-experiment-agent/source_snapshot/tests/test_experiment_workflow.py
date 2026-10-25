"""真实固定脚本验证运行隔离、产物编号和失败后禁止验收。"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiment_agent.experiment_workflow import EXPERIMENT_SCRIPT, run_experiment_workflow


class ExperimentWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="run-scoped-test-")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.root = self.parent / "project"
        self.script = self.root / EXPERIMENT_SCRIPT
        self.script.parent.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / EXPERIMENT_SCRIPT
        shutil.copyfile(source, self.script)

    def run_case(self, case="normal", **settings):
        return run_experiment_workflow(self.root, case, **settings)

    def steps(self, result):
        return [event["step"] for event in result["trace"]]

    def test_real_process_writes_current_id_and_is_launched_in_its_fresh_directory(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run", wraps=subprocess.run) as launch:
            result = self.run_case()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertFalse(result["execution"]["timed_out"])
        self.assertEqual(self.steps(result), [
            "prepare_run", "run_python_script", "read_text_file", "parse_json", "check_run_id", "verify_metrics",
        ])
        metrics = json.loads((self.root / result["metrics_path"]).read_text(encoding="utf-8"))
        self.assertEqual(metrics, {"run_id": result["run_id"], "mse": 0.04})
        command = launch.call_args.args[0]
        settings = launch.call_args.kwargs
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[command.index("--run-id") + 1], result["run_id"])
        self.assertEqual(settings["cwd"], (self.root / result["run_directory"]).resolve())
        self.assertFalse(settings["shell"])
        self.assertEqual(settings["stdin"], subprocess.DEVNULL)

    def test_two_runs_do_not_reuse_paths_or_modify_the_first_artifact(self):
        first = self.run_case()
        first_path = self.root / first["metrics_path"]
        original = first_path.read_bytes()
        second = self.run_case()
        self.assertEqual(second["status"], "passed")
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertNotEqual(first["metrics_path"], second["metrics_path"])
        self.assertEqual(first_path.read_bytes(), original)

    def test_old_valid_metrics_cannot_rescue_a_new_run_without_output(self):
        old = self.run_case()
        old_path = self.root / old["metrics_path"]
        original = old_path.read_bytes()
        result = self.run_case("missing_metrics")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "file_not_found")
        self.assertEqual(self.steps(result), ["prepare_run", "run_python_script", "read_text_file"])
        self.assertFalse((self.root / result["metrics_path"]).exists())
        self.assertEqual(old_path.read_bytes(), original)
        self.assertNotEqual(old["metrics_path"], result["metrics_path"])
        self.assertEqual(Path(result["result"]["path"]), (self.root / result["metrics_path"]).resolve())

    def test_wrong_id_stops_before_metric_verification_even_with_a_good_mse(self):
        with patch("experiment_agent.metrics_workflow.verify_metrics") as verifier:
            result = self.run_case("wrong_run_id")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["reason"], "run_id_mismatch")
        self.assertEqual(result["result"]["expected_run_id"], result["run_id"])
        self.assertEqual(result["result"]["actual_run_id"], "previous_run")
        self.assertEqual(self.steps(result)[-1], "check_run_id")
        verifier.assert_not_called()

    def test_failed_process_does_not_read_metrics_even_if_it_wrote_a_valid_file(self):
        with patch("experiment_agent.experiment_workflow.run_metrics_file_workflow") as checker:
            result = self.run_case("error")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "process_failed")
        self.assertNotEqual(result["execution"]["exit_code"], 0)
        self.assertTrue((self.root / result["metrics_path"]).is_file())
        self.assertEqual(self.steps(result), ["prepare_run", "run_python_script"])
        checker.assert_not_called()

    def test_real_timeout_stops_without_reading_or_verification(self):
        with patch("experiment_agent.experiment_workflow.run_metrics_file_workflow") as checker:
            result = self.run_case("timeout", timeout_seconds=0.3)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "tool_timeout")
        self.assertTrue(result["execution"]["timed_out"])
        self.assertIsNone(result["execution"]["exit_code"])
        self.assertEqual(self.steps(result), ["prepare_run", "run_python_script"])
        checker.assert_not_called()

    def test_matching_identity_still_requires_task_threshold(self):
        result = self.run_case(max_mse=0.01)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["trace"][-2]["result"]["reason"], "run_id_matched")
        self.assertEqual(result["result"], {
            "status": "failed", "reason": "mse_above_threshold", "mse": 0.04, "max_mse": 0.01,
        })

    def test_unsupported_cases_cannot_supply_arbitrary_scripts_or_shell_commands(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run") as launch:
            for case in ("../outside.py", "normal; echo injected", [], None):
                with self.subTest(case=case):
                    result = self.run_case(case)
                    self.assertEqual(result["result"]["error_type"], "script_not_allowed")
            launch.assert_not_called()
        self.assertFalse((self.root / "runs").exists())

    def test_collision_is_rejected_without_overwriting_or_executing(self):
        previous = self.root / "runs" / "same-id"
        previous.mkdir(parents=True)
        artifact = previous / "metrics.json"
        artifact.write_text('{"run_id":"old","mse":0.01}', encoding="utf-8")
        original = artifact.read_bytes()
        with patch("experiment_agent.experiment_workflow.uuid4", return_value=SimpleNamespace(hex="same-id")), \
                patch("experiment_agent.experiment_workflow.subprocess.run") as launch:
            result = self.run_case()
            launch.assert_not_called()
        self.assertEqual(result["result"]["error_type"], "run_setup_failed")
        self.assertEqual(artifact.read_bytes(), original)

    def test_missing_or_outside_fixed_script_is_rejected_before_launch(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run") as launch:
            with patch("experiment_agent.experiment_workflow.EXPERIMENT_SCRIPT", "missing.py"):
                result = self.run_case()
                self.assertEqual(result["result"]["error_type"], "file_not_found")
            outside = self.parent / "outside.py"
            outside.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
            with patch("experiment_agent.experiment_workflow.EXPERIMENT_SCRIPT", "../outside.py"):
                result = self.run_case()
                self.assertEqual(result["result"]["error_type"], "path_outside_project")
            launch.assert_not_called()

    def test_invalid_trusted_timeout_never_launches(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run") as launch:
            for value in (0, -1, True, float("nan"), float("inf"), "2"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    self.run_case(timeout_seconds=value)
            launch.assert_not_called()

    def test_injected_spawn_failure_is_recorded_and_never_verifies(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run", side_effect=OSError("Injected spawn failure")), \
                patch("experiment_agent.experiment_workflow.run_metrics_file_workflow") as checker:
            result = self.run_case()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "process_start_failed")
        self.assertIsNone(result["execution"]["exit_code"])
        checker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
