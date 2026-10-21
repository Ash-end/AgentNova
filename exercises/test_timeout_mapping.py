"""独立练习验收：实现工具 TimeoutError 的分类与停止理由。无等待、无模型 API。"""

import json
import unittest

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import call_tool


def timeout_read(relative_path):
    raise TimeoutError("Simulated tool timeout.")


class TimeoutMappingExerciseTests(unittest.TestCase):
    def test_timeout_has_its_own_error_type_and_keeps_exception_details(self):
        result = call_tool(
            {"read_text_file": timeout_read}, "read_text_file", {"relative_path": "hello.txt"},
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "tool_timeout")
        self.assertEqual(result["exception_type"], "TimeoutError")
        self.assertEqual(result["tool_name"], "read_text_file")
        self.assertEqual(result["message"], "Simulated tool timeout.")

    def test_timeout_policy_stops_with_a_specific_reason(self):
        decision = decide_tool_result({"status": "failed", "error_type": "tool_timeout"}, 0)
        self.assertEqual(decision["action"], "stop")
        self.assertEqual(decision["reason"], "tool_timeout_needs_review")

    def test_loop_records_timeout_and_stops_without_another_model_request(self):
        requests = []

        def chat(messages, descriptions):
            requests.append(True)
            return {"done": True, "done_reason": "stop", "message": {
                "role": "assistant", "content": "", "tool_calls": [{"function": {
                    "name": "read_text_file", "arguments": {"relative_path": "hello.txt"},
                }}],
            }}

        result = run_ollama_loop(
            "read hello.txt", chat, {"read_text_file": timeout_read}, [], tool_policy=decide_tool_result,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "tool_policy_stopped")
        self.assertEqual(result["tool_error_type"], "tool_timeout")
        self.assertEqual(result["stop_reason"], "tool_timeout_needs_review")
        self.assertEqual(len(requests), 1)
        observed = json.loads(result["messages"][-1]["content"])
        self.assertEqual(observed["error_type"], "tool_timeout")

    def test_generic_os_error_keeps_its_existing_classification(self):
        def io_failure(relative_path):
            raise OSError("A generic I/O error.")

        result = call_tool({"read_text_file": io_failure}, "read_text_file", {"relative_path": "hello.txt"})
        self.assertEqual(result["error_type"], "io_error")
        self.assertEqual(result["exception_type"], "OSError")
        decision = decide_tool_result(result, 0)
        self.assertEqual(decision, {"action": "stop", "reason": "io_failure"})


if __name__ == "__main__":
    unittest.main()
