"""验证真实子进程和拒绝执行边界；异常注入用例明确标注。"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiment_agent.tools.registry import build_tool_registry, call_tool
from experiment_agent.tools.script_tools import ALLOWED_SCRIPTS, run_python_script


class ScriptToolTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        source = Path(__file__).resolve().parents[1]
        for relative in ALLOWED_SCRIPTS.values():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        self.tools = build_tool_registry(str(self.root), enable_python_scripts=True)

    def test_normal_process_uses_current_python_and_succeeds_despite_stderr(self):
        with patch("experiment_agent.tools.script_tools.subprocess.run", wraps=subprocess.run) as launch:
            result = call_tool(self.tools, "run_python_script", {"script_id": "normal"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("2 + 3 = 5", result["stdout"])
        self.assertIn("诊断信息", result["stderr"])
        self.assertFalse(result["timed_out"])
        command = launch.call_args.args[0]
        settings = launch.call_args.kwargs
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[-1]), (self.root / ALLOWED_SCRIPTS["normal"]).resolve())
        self.assertIn("-I", command)
        self.assertFalse(settings["shell"])
        self.assertFalse(settings["check"])
        self.assertEqual(settings["cwd"], self.root.resolve())
        self.assertEqual(settings["stdin"], subprocess.DEVNULL)

    def test_real_child_exception_produces_nonzero_exit_and_preserves_both_streams(self):
        result = call_tool(self.tools, "run_python_script", {"script_id": "error"})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "process_failed")
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("准备触发", result["stdout"])
        self.assertIn("RuntimeError", result["stderr"])
        self.assertFalse(result["timed_out"])

    def test_real_timeout_returns_partial_text_and_no_invented_exit_code(self):
        result = call_tool(self.tools, "run_python_script", {"script_id": "timeout"})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "tool_timeout")
        self.assertEqual(result["exception_type"], "TimeoutExpired")
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("开始等待", result["stdout"])
        self.assertNotIn("等待结束", result["stdout"])
        json.dumps(result, ensure_ascii=False)

    def test_execution_capability_is_absent_from_default_registry(self):
        result = call_tool(build_tool_registry(str(self.root)), "run_python_script", {"script_id": "normal"})
        self.assertEqual(result["error_type"], "unknown_tool")

    def test_unknown_ids_paths_and_shell_fragments_never_start_a_process(self):
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            for script_id in ("../outside.py", "normal; echo unexpected", "normal.py", "unknown"):
                with self.subTest(script_id=script_id):
                    result = call_tool(self.tools, "run_python_script", {"script_id": script_id})
                    self.assertEqual(result["error_type"], "script_not_allowed")
            launch.assert_not_called()

    def test_invalid_arguments_cannot_override_execution_settings(self):
        bad_arguments = [None, [], {}, {"script_id": ""}, {"script_id": 1}, {"script_id": "   "}]
        bad_arguments += [{"script_id": "normal", key: "untrusted"}
                          for key in ("project_root", "timeout_seconds", "command", "args", "python_path")]
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            for arguments in bad_arguments:
                with self.subTest(arguments=arguments):
                    result = call_tool(self.tools, "run_python_script", arguments)
                    self.assertEqual(result["error_type"], "invalid_arguments")
            launch.assert_not_called()

    def test_missing_allowed_script_is_rejected_before_process_creation(self):
        (self.root / ALLOWED_SCRIPTS["normal"]).unlink()
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            result = run_python_script(str(self.root), "normal")
            self.assertEqual(result["error_type"], "file_not_found")
            launch.assert_not_called()

    def test_directory_at_allowed_script_path_is_rejected(self):
        path = self.root / ALLOWED_SCRIPTS["normal"]
        path.unlink()
        path.mkdir()
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            result = run_python_script(str(self.root), "normal")
            self.assertEqual(result["error_type"], "script_not_file")
            launch.assert_not_called()

    def test_allowlist_target_outside_project_is_rejected_after_resolution(self):
        (self.base / "outside.py").write_text("raise RuntimeError('must not run')", encoding="utf-8")
        with patch.dict(ALLOWED_SCRIPTS, {"normal": "../outside.py"}), \
                patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            result = run_python_script(str(self.root), "normal")
            self.assertEqual(result["error_type"], "path_outside_project")
            launch.assert_not_called()

    def test_injected_spawn_failure_is_structured_without_a_child_exit_code(self):
        with patch("experiment_agent.tools.script_tools.subprocess.run",
                   side_effect=OSError("Injected process creation failure.")):
            result = run_python_script(str(self.root), "normal")
        self.assertEqual(result["error_type"], "process_start_failed")
        self.assertIsNone(result["exit_code"])
        self.assertFalse(result["timed_out"])

    def test_injected_timeout_bytes_are_decoded_for_json_reports(self):
        error = subprocess.TimeoutExpired("injected", 2, output=b"partial\r\n", stderr=b"diagnostic")
        with patch("experiment_agent.tools.script_tools.subprocess.run", side_effect=error):
            result = run_python_script(str(self.root), "normal")
        self.assertEqual(result["stdout"], "partial\n")
        self.assertEqual(result["stderr"], "diagnostic")
        json.dumps(result, ensure_ascii=False)

    def test_invalid_trusted_timeout_configuration_is_rejected_before_launch(self):
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            for timeout in (0, -1, True, float("inf"), float("nan"), "2"):
                with self.subTest(timeout=timeout):
                    with self.assertRaises(ValueError):
                        run_python_script(str(self.root), "normal", timeout_seconds=timeout)
            launch.assert_not_called()
