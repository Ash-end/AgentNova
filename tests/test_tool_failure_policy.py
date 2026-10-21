"""检查失败后的控制流，不依赖真实模型是否愿意产生某类错误。"""

import json
import tempfile
import unittest
from pathlib import Path

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry


def tool_response(arguments, name="read_text_file", extra_calls=None):
    calls = [{"function": {"name": name, "arguments": arguments}}]
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": "", "tool_calls": calls + (extra_calls or []),
    }}


def final_response():
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": "模型已结束。",
    }}


class ToolFailurePolicyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "hello.txt").write_text("真实读取结果", encoding="utf-8")
        self.tools = build_tool_registry(str(self.root))

    def run_script(self, responses):
        self.requests = []

        def chat(messages, descriptions):
            self.requests.append(json.loads(json.dumps(messages)))
            index = len(self.requests) - 1
            return responses[index] if index < len(responses) else final_response()

        return run_ollama_loop("读取指定文件", chat, self.tools, [], tool_policy=decide_tool_result)

    def test_invalid_arguments_can_be_corrected_once_using_real_observation(self):
        result = self.run_script([
            tool_response({"path": "hello.txt"}),
            tool_response({"relative_path": "hello.txt"}),
            final_response(),
        ])
        self.assertEqual(result["status"], "completed")
        first_observation = json.loads(self.requests[1][-1]["content"])
        self.assertEqual(first_observation["error_type"], "invalid_arguments")
        self.assertEqual(json.loads(self.requests[2][-1]["content"])["content"], "真实读取结果")
        self.assertIn("tool_decisions", result)
        self.assertEqual([d["action"] for d in result["tool_decisions"]], ["correct", "continue"])

    def test_second_invalid_request_stops_before_third_model_request(self):
        bad = tool_response({"path": "hello.txt"})
        result = self.run_script([bad, bad])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stop_reason"], "correction_limit_exceeded")
        self.assertEqual(result["tool_error_type"], "invalid_arguments")
        self.assertEqual(len(self.requests), 2)

    def test_missing_file_stops_and_preserves_the_actual_tool_error(self):
        result = self.run_script([tool_response({"relative_path": "missing.txt"})])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "tool_policy_stopped")
        self.assertEqual(result["tool_error_type"], "file_not_found")
        self.assertEqual(len(self.requests), 1)
        observation = json.loads(result["messages"][-1]["content"])
        self.assertEqual(observation["error_type"], "file_not_found")

    def test_outside_path_and_unregistered_tool_stop_without_another_model_request(self):
        for response, error_type in [
            (tool_response({"relative_path": "../outside.txt"}), "path_outside_project"),
            (tool_response({}, name="delete_file"), "unknown_tool"),
        ]:
            with self.subTest(error_type=error_type):
                result = self.run_script([response])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["tool_error_type"], error_type)
                self.assertEqual(len(self.requests), 1)

    def test_stop_skips_remaining_tools_in_the_same_batch(self):
        executions = []
        original = self.tools["read_text_file"]

        def recorded_read(relative_path):
            executions.append(relative_path)
            return original(relative_path)

        self.tools["read_text_file"] = recorded_read
        later_call = {"function": {"name": "read_text_file", "arguments": {"relative_path": "hello.txt"}}}
        result = self.run_script([tool_response({"relative_path": "missing.txt"}, extra_calls=[later_call])])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(executions, ["missing.txt"])
        self.assertEqual(result["pending_tool_calls"], 1)

    def test_unrecognized_failures_do_not_trigger_blind_retry(self):
        decision = decide_tool_result({"status": "failed", "error_type": "new_unhandled_error"}, 0)
        self.assertEqual(decision["action"], "stop")


if __name__ == "__main__":
    unittest.main()
