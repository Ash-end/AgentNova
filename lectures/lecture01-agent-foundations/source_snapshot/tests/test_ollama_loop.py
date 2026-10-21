"""用确定的 API 响应检查循环；文件读取使用真实工具，不访问模型服务。"""

import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tools.registry import build_tool_registry


def reply(content="", calls=None, **fields):
    message = {"role": "assistant", "content": content}
    if calls is not None:
        message["tool_calls"] = calls
    return {"done": True, "done_reason": "stop", "message": message, **fields}


def read_call(path="hello.txt", name="read_text_file", arguments=None):
    return {"id": "call_test", "function": {
        "name": name,
        "arguments": {"relative_path": path} if arguments is None else arguments,
    }}


class OllamaLoopTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "hello.txt").write_text("你好，真实工具！\n", encoding="utf-8")
        self.tools = build_tool_registry(str(self.root))
        self.descriptions = [{"type": "function", "function": {"name": "read_text_file"}}]

    def run_agent(self, chat, max_steps=5):
        return run_ollama_loop("read hello.txt", chat, self.tools, self.descriptions, max_steps=max_steps)

    def test_tool_request_takes_priority_over_text_and_result_reaches_next_request(self):
        first = reply("我先读取。", [read_call()])
        requests = []

        def chat(messages, descriptions):
            requests.append(json.loads(json.dumps(messages)))
            self.assertEqual(descriptions, self.descriptions)
            if len(requests) == 1:
                return first
            self.assertEqual(messages[-2], first["message"])
            self.assertEqual(messages[-1]["role"], "tool")
            self.assertEqual(messages[-1]["tool_name"], "read_text_file")
            observed = json.loads(messages[-1]["content"])
            self.assertEqual(observed, {"status": "success", "content": "你好，真实工具！\n"})
            return reply(observed["content"])

        result = self.run_agent(chat)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "你好，真实工具！\n")
        self.assertEqual(result["steps"], 2)
        self.assertEqual(len(requests), 2)

    def test_final_text_stops_without_another_model_call(self):
        requests = []

        def chat(messages, descriptions):
            requests.append(True)
            return reply("No tool needed.")

        result = self.run_agent(chat)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(requests), 1)
        self.assertFalse(any(m["role"] == "tool" for m in result["messages"]))

    def test_step_limit_can_stop_after_reading_but_before_final_answer(self):
        requests = []

        def chat(messages, descriptions):
            requests.append(True)
            return reply(calls=[read_call()])

        result = self.run_agent(chat, max_steps=1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "max_steps_exceeded")
        self.assertEqual(len(requests), 1)
        self.assertEqual(json.loads(result["messages"][-1]["content"])["status"], "success")

    def test_all_tool_calls_in_one_response_are_returned_before_next_model_call(self):
        def chat(messages, descriptions):
            if messages[-1]["role"] == "user":
                return reply(calls=[read_call(), read_call("missing.txt")])
            observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
            self.assertEqual(len(observations), 2)
            self.assertEqual(observations[0]["status"], "success")
            self.assertEqual(observations[1]["error_type"], "file_not_found")
            return reply("One file exists, one does not.")

        result = self.run_agent(chat)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"], 2)

    def test_tool_errors_are_returned_and_model_can_correct_its_request(self):
        for first_call, error_type in [
            (read_call(arguments={"path": "hello.txt"}), "invalid_arguments"),
            (read_call(name="not_registered"), "unknown_tool"),
            (read_call(path="../outside.txt"), "path_outside_project"),
        ]:
            with self.subTest(error_type=error_type):
                requests = []

                def chat(messages, descriptions):
                    requests.append(True)
                    if len(requests) == 1:
                        return reply(calls=[first_call])
                    observed = json.loads(messages[-1]["content"])
                    if len(requests) == 2:
                        self.assertEqual(observed["error_type"], error_type)
                        return reply(calls=[read_call()])
                    return reply(observed["content"])

                result = self.run_agent(chat)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["steps"], 3)

    def test_malformed_responses_stop_before_executing_any_tool(self):
        for response in [
            None,
            reply(content=123),
            reply(calls="not a list"),
            reply(calls=[read_call(), {"function": {"name": "read_text_file"}}]),
            reply(calls=[{"function": {"name": ["bad"], "arguments": {}}}]),
        ]:
            with self.subTest(response=response):
                result = self.run_agent(lambda messages, descriptions: response)
                self.assertEqual(result["error_type"], "invalid_model_response")
                self.assertFalse(any(m["role"] == "tool" for m in result["messages"]))

    def test_empty_text_without_tools_is_not_completed(self):
        result = self.run_agent(lambda messages, descriptions: reply("   "))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "empty_model_response")

    def test_unfinished_generation_does_not_execute_tools(self):
        for fields in [{"done": False}, {"done_reason": "length"}]:
            with self.subTest(fields=fields):
                result = self.run_agent(lambda messages, descriptions: reply(calls=[read_call()], **fields))
                self.assertEqual(result["error_type"], "incomplete_model_response")
                self.assertFalse(any(m["role"] == "tool" for m in result["messages"]))

    def test_network_failure_preserves_observations_and_does_not_retry(self):
        requests = []

        def chat(messages, descriptions):
            requests.append(True)
            if len(requests) == 1:
                return reply(calls=[read_call()])
            raise URLError("offline")

        result = self.run_agent(chat)
        self.assertEqual(result["error_type"], "model_request_failed")
        self.assertEqual(result["steps"], 2)
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["messages"][-1]["role"], "tool")


if __name__ == "__main__":
    unittest.main()
