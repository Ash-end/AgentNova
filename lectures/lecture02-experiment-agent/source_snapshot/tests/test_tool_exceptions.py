"""验证真实文件异常的转换、具体异常分类，以及进入策略后的停止行为。"""

import json
import tempfile
import unittest
from pathlib import Path

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry, call_tool


class ToolExceptionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "invalid.bin").write_bytes(b"\xff\xfe\x80")
        (self.root / "folder").mkdir()
        self.tools = build_tool_registry(str(self.root))

    def dispatch(self, tools, path):
        try:
            return call_tool(tools, "read_text_file", {"relative_path": path})
        except (OSError, UnicodeDecodeError) as error:
            self.fail(f"Expected a structured result, but {type(error).__name__} escaped: {error}")

    def test_real_invalid_utf8_returns_encoding_error_without_file_content(self):
        result = self.dispatch(self.tools, "invalid.bin")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "invalid_encoding")
        self.assertEqual(result["exception_type"], "UnicodeDecodeError")
        self.assertEqual(result["tool_name"], "read_text_file")
        self.assertTrue(result["message"])
        self.assertNotIn("content", result)

    def test_real_directory_read_returns_the_actual_platform_exception(self):
        result = self.dispatch(self.tools, "folder")
        self.assertEqual(result["status"], "failed")
        # Windows 通常返回 PermissionError；其他平台通常返回 IsADirectoryError。
        self.assertIn((result["error_type"], result["exception_type"]), {
            ("permission_denied", "PermissionError"),
            ("is_a_directory", "IsADirectoryError"),
        })
        self.assertNotIn("content", result)

    def test_specific_os_errors_remain_distinguishable_from_generic_io_error(self):
        for exception, expected_type in [
            (FileNotFoundError("injected missing file"), "file_not_found"),
            (PermissionError("injected access denial"), "permission_denied"),
            (IsADirectoryError("injected directory"), "is_a_directory"),
            (NotADirectoryError("injected invalid parent"), "not_a_directory"),
            (OSError("injected I/O failure"), "io_error"),
        ]:
            with self.subTest(exception=type(exception).__name__):
                def failing_read(relative_path):
                    raise exception

                result = self.dispatch({"read_text_file": failing_read}, "hello.txt")
                self.assertEqual(result["error_type"], expected_type)
                self.assertEqual(result["exception_type"], type(exception).__name__)
                self.assertEqual(result["message"], str(exception))

    def test_programming_type_error_is_not_disguised_as_invalid_arguments(self):
        def buggy_read(relative_path):
            raise TypeError("a bug inside the tool")

        with self.assertRaisesRegex(TypeError, "a bug inside the tool"):
            call_tool({"read_text_file": buggy_read}, "read_text_file", {"relative_path": "hello.txt"})

    def test_invalid_arguments_are_rejected_before_tool_execution(self):
        executions = []

        def recorded_read(relative_path):
            executions.append(relative_path)
            return {"status": "success", "content": "should not run"}

        result = call_tool({"read_text_file": recorded_read}, "read_text_file", {"path": "hello.txt"})
        self.assertEqual(result["error_type"], "invalid_arguments")
        self.assertEqual(executions, [])
        self.assertNotIn("exception_type", result)

    def test_converted_errors_reach_policy_and_stop_before_another_model_request(self):
        def denied_read(relative_path):
            raise PermissionError("injected access denial")

        for tools, path, error_type, reason in [
            (self.tools, "invalid.bin", "invalid_encoding", "utf8_required"),
            ({"read_text_file": denied_read}, "hello.txt", "permission_denied", "file_access_denied"),
        ]:
            with self.subTest(error_type=error_type):
                requests = []

                def chat(messages, descriptions):
                    requests.append(True)
                    return {"done": True, "done_reason": "stop", "message": {
                        "role": "assistant", "content": "", "tool_calls": [{"function": {
                            "name": "read_text_file", "arguments": {"relative_path": path},
                        }}],
                    }}

                try:
                    result = run_ollama_loop("read file", chat, tools, [], tool_policy=decide_tool_result)
                except (OSError, UnicodeDecodeError) as error:
                    self.fail(f"The tool exception escaped the loop: {error}")
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["error_type"], "tool_policy_stopped")
                self.assertEqual(result["tool_error_type"], error_type)
                self.assertEqual(result["stop_reason"], reason)
                self.assertEqual(len(requests), 1)
                observed = json.loads(result["messages"][-1]["content"])
                self.assertEqual(observed["error_type"], error_type)
                self.assertTrue(observed["exception_type"])


if __name__ == "__main__":
    unittest.main()
