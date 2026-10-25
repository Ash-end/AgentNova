"""只替换模型 HTTP 响应，真实执行固定脚本，验证策略与执行次数上限。"""

from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiment_agent.tools.script_tools import ALLOWED_SCRIPTS
from labs.l16_agent_task_verifier import final_reply
from labs.l18_real_script_agent import run_case


def script_reply(arguments, extra_calls=None, name="run_python_script"):
    calls = [{"function": {"name": name, "arguments": arguments}}]
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": "", "tool_calls": calls + (extra_calls or []),
    }}


class RealScriptAgentTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = Path(__file__).resolve().parents[1]
        for relative in ALLOWED_SCRIPTS.values():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)

    def run_entry(self, case, replies, max_steps=4):
        responses = [BytesIO(json.dumps(reply, ensure_ascii=False).encode("utf-8")) for reply in replies]
        output = StringIO()
        with patch("labs.l18_real_script_agent.urlopen", side_effect=responses), redirect_stdout(output):
            matched = run_case(self.root, case, [], max_steps)
        report = json.loads((self.root / f"reports/l18_real_script_agent_{case}.json").read_text(encoding="utf-8"))
        return matched, output.getvalue(), report

    def test_normal_result_reaches_next_model_request_before_final_reply(self):
        matched, output, report = self.run_entry("normal", [
            script_reply({"script_id": "normal"}), final_reply("退出码0，执行成功。"),
        ])
        self.assertTrue(matched)
        self.assertEqual(report["result"]["status"], "completed")
        self.assertEqual(report["execution_function_calls"], 1)
        self.assertEqual(len(report["requests"]), 2)
        observation = json.loads(report["requests"][1]["messages"][-1]["content"])
        self.assertEqual(observation["exit_code"], 0)
        self.assertIn("诊断信息", observation["stderr"])
        self.assertEqual(report["result"]["tool_decisions"][-1]["action"], "continue")

    def test_real_child_error_stops_before_another_model_request(self):
        matched, output, report = self.run_entry("error", [script_reply({"script_id": "error"})])
        self.assertTrue(matched)
        self.assertEqual(len(report["requests"]), 1)
        self.assertEqual(report["result"]["status"], "failed")
        self.assertEqual(report["result"]["stop_reason"], "script_process_failed")
        self.assertIn("No final model reply", output)
        observation = json.loads(report["result"]["messages"][-1]["content"])
        self.assertEqual(observation["exit_code"], 1)
        self.assertIn("RuntimeError", observation["stderr"])

    def test_real_child_timeout_stops_without_retry(self):
        matched, output, report = self.run_entry("timeout", [script_reply({"script_id": "timeout"})])
        self.assertTrue(matched)
        self.assertEqual(len(report["requests"]), 1)
        self.assertEqual(report["execution_function_calls"], 1)
        self.assertEqual(report["result"]["stop_reason"], "tool_timeout_needs_review")
        observation = json.loads(report["result"]["messages"][-1]["content"])
        self.assertTrue(observation["timed_out"])
        self.assertIsNone(observation["exit_code"])

    def test_wrong_allowlisted_script_is_not_misreported_as_correct_selection(self):
        matched, output, report = self.run_entry("normal", [script_reply({"script_id": "error"})])
        self.assertFalse(matched)
        self.assertEqual(report["result"]["tool_error_type"], "process_failed")

    def test_bad_arguments_can_be_corrected_without_consuming_execution_call(self):
        matched, output, report = self.run_entry("normal", [
            script_reply({"script": "normal"}), script_reply({"script_id": "normal"}),
            final_reply("执行成功。"),
        ])
        self.assertTrue(matched)
        self.assertEqual(report["execution_function_calls"], 1)
        self.assertEqual(len(report["requests"]), 3)
        self.assertEqual([d["action"] for d in report["result"]["tool_decisions"]], ["correct", "continue"])

    def test_repeated_execution_in_same_batch_starts_only_one_child_process(self):
        later = {"function": {"name": "run_python_script", "arguments": {"script_id": "normal"}}}
        with patch("experiment_agent.tools.script_tools.subprocess.run", wraps=subprocess.run) as launch:
            matched, output, report = self.run_entry("normal", [
                script_reply({"script_id": "normal"}, extra_calls=[later]),
            ])
        self.assertFalse(matched)
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(report["execution_function_calls"], 1)
        self.assertEqual(report["result"]["stop_reason"], "script_execution_budget_exceeded")

    def test_read_tool_is_not_exposed_by_execution_only_entry(self):
        with patch("experiment_agent.tools.script_tools.subprocess.run") as launch:
            matched, output, report = self.run_entry("normal", [
                script_reply({"relative_path": "secret.txt"}, name="read_text_file"),
            ])
            launch.assert_not_called()
        self.assertFalse(matched)
        self.assertEqual(report["result"]["tool_error_type"], "unknown_tool")

    def test_successful_process_without_final_reply_can_still_exceed_model_step_limit(self):
        matched, output, report = self.run_entry("normal", [script_reply({"script_id": "normal"})], max_steps=1)
        self.assertFalse(matched)
        self.assertEqual(report["result"]["error_type"], "max_steps_exceeded")
        observation = json.loads(report["result"]["messages"][-1]["content"])
        self.assertEqual(observation["status"], "success")
