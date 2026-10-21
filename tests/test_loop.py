"""验证反馈进入下一轮、最终响应停止循环，以及步数上限。"""

import tempfile
import unittest
from pathlib import Path

from experiment_agent.loop import run_loop
from experiment_agent.tools.registry import build_tool_registry


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "hello.txt").write_text("Hello, loop!", encoding="utf-8")
        self.tools = build_tool_registry(str(self.root))
        self.descriptions = [{"name": "read_text_file"}]

    def test_final_response_stops_without_another_model_call(self):
        calls = []

        def model(messages, descriptions):
            calls.append(True)
            self.assertEqual(messages[-1]["role"], "user")
            return {"type": "final", "content": "done"}

        result = run_loop("finish immediately", model, self.tools, self.descriptions)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "done")
        self.assertEqual(len(calls), 1)
        self.assertFalse(any(message["role"] == "tool" for message in result["messages"]))

    def test_model_can_correct_arguments_using_tool_observation(self):
        def model(messages, descriptions):
            self.assertEqual(descriptions, self.descriptions)
            last = messages[-1]
            if last["role"] == "user":
                return {"type": "tool_call", "name": "read_text_file", "arguments": {"path": "hello.txt"}}
            observation = last["content"]
            if observation.get("error_type") == "invalid_arguments":
                return {"type": "tool_call", "name": "read_text_file", "arguments": {"relative_path": "hello.txt"}}
            self.assertEqual(observation["status"], "success")
            return {"type": "final", "content": observation["content"]}

        result = run_loop("read hello.txt", model, self.tools, self.descriptions)

        self.assertEqual(result["answer"], "Hello, loop!")
        self.assertEqual(result["steps"], 3)
        observations = [message["content"] for message in result["messages"] if message["role"] == "tool"]
        self.assertEqual(observations[0]["error_type"], "invalid_arguments")
        self.assertEqual(observations[1]["status"], "success")

    def test_unknown_tool_error_is_returned_to_model(self):
        def model(messages, descriptions):
            if messages[-1]["role"] == "user":
                return {"type": "tool_call", "name": "not_registered", "arguments": {}}
            self.assertEqual(messages[-1]["role"], "tool")
            self.assertEqual(messages[-1]["content"]["error_type"], "unknown_tool")
            return {"type": "final", "content": "requested tool is unavailable"}

        result = run_loop("use an unavailable tool", model, self.tools, self.descriptions)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"], 2)

    def test_step_limit_stops_endless_tool_requests(self):
        calls = []

        def model(messages, descriptions):
            calls.append(True)
            return {"type": "tool_call", "name": "read_text_file", "arguments": {"relative_path": "hello.txt"}}

        result = run_loop("keep reading", model, self.tools, self.descriptions, max_steps=2)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "max_steps_exceeded")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len([message for message in result["messages"] if message["role"] == "tool"]), 2)

    def test_invalid_model_response_ends_with_a_diagnostic(self):
        def model(messages, descriptions):
            return {"type": "not_a_supported_action"}

        result = run_loop("bad model output", model, self.tools, self.descriptions)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "invalid_model_response")


if __name__ == "__main__":
    unittest.main()
