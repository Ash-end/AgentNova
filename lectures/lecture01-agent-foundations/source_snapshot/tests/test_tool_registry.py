"""通过工具名称调用真实文件工具，验证根目录绑定和未知工具行为。"""

import tempfile
import unittest
from pathlib import Path

from experiment_agent.tools.registry import build_tool_registry, call_tool


class ToolRegistryTests(unittest.TestCase):
    def test_registered_name_reads_file(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "hello.txt").write_text("你好，注册表！", encoding="utf-8")
            tools = build_tool_registry(directory)

            result = call_tool(tools, "read_text_file", {"relative_path": "hello.txt"})

            self.assertEqual(result, {"status": "success", "content": "你好，注册表！"})

    def test_unknown_name_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)

            result = call_tool(tools, "delete_file", {"relative_path": "hello.txt"})

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "unknown_tool")
            self.assertEqual(result["tool_name"], "delete_file")

    def test_each_registry_uses_its_own_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            first_root = Path(directory) / "first"
            second_root = Path(directory) / "second"
            first_root.mkdir()
            second_root.mkdir()
            (first_root / "hello.txt").write_text("first project", encoding="utf-8")
            (second_root / "hello.txt").write_text("second project", encoding="utf-8")
            first_tools = build_tool_registry(str(first_root))
            second_tools = build_tool_registry(str(second_root))

            first_result = call_tool(first_tools, "read_text_file", {"relative_path": "hello.txt"})
            second_result = call_tool(second_tools, "read_text_file", {"relative_path": "hello.txt"})

            self.assertEqual(first_result["content"], "first project")
            self.assertEqual(second_result["content"], "second project")

    def test_dispatch_preserves_file_path_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (Path(directory) / "outside.txt").write_text("outside fixture", encoding="utf-8")
            tools = build_tool_registry(str(root))

            result = call_tool(tools, "read_text_file", {"relative_path": "../outside.txt"})

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "path_outside_project")
            self.assertNotIn("content", result)

    def test_arguments_must_be_a_dictionary(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)
            for arguments in (None, [], "hello.txt", 123):
                with self.subTest(arguments=arguments):
                    result = call_tool(tools, "read_text_file", arguments)

                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["error_type"], "invalid_arguments")

    def test_missing_required_argument_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)

            result = call_tool(tools, "read_text_file", {})

            self.assertEqual(result["error_type"], "invalid_arguments")
            self.assertIn("relative_path", result["message"])

    def test_misspelled_argument_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)

            result = call_tool(tools, "read_text_file", {"path": "hello.txt"})

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "invalid_arguments")

    def test_caller_cannot_supply_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)

            result = call_tool(
                tools,
                "read_text_file",
                {"relative_path": "hello.txt", "project_root": directory},
            )

            self.assertEqual(result["error_type"], "invalid_arguments")

    def test_path_value_must_be_a_non_empty_string(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = build_tool_registry(directory)
            for value in (123, None, "", "   ", "\t\n"):
                with self.subTest(value=value):
                    result = call_tool(tools, "read_text_file", {"relative_path": value})

                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["error_type"], "invalid_arguments")

    def test_spaces_inside_valid_file_name_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "my notes.txt").write_text("spaces preserved", encoding="utf-8")
            tools = build_tool_registry(directory)

            result = call_tool(tools, "read_text_file", {"relative_path": "my notes.txt"})

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["content"], "spaces preserved")


if __name__ == "__main__":
    unittest.main()
