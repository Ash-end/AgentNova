"""验证第二个只读工具、参数与路径边界，以及目录观察驱动文件读取。"""

import json
import tempfile
import unittest
from pathlib import Path

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry, call_tool


class DirectoryToolTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.root = self.base / "project"
        self.root.mkdir()
        (self.root / "data").mkdir()
        (self.root / "data/nested.txt").write_text("not listed recursively", encoding="utf-8")
        (self.root / "hello.txt").write_text("目录发现后的真实内容", encoding="utf-8")
        (self.root / "empty").mkdir()
        self.tools = build_tool_registry(str(self.root))

    def list_path(self, path):
        return call_tool(self.tools, "list_directory", {"relative_path": path})

    def test_project_root_listing_returns_sorted_direct_children_without_contents(self):
        result = self.list_path(".")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["entries"], [
            {"name": "data", "type": "directory", "relative_path": "data"},
            {"name": "empty", "type": "directory", "relative_path": "empty"},
            {"name": "hello.txt", "type": "file", "relative_path": "hello.txt"},
        ])
        self.assertFalse(result["truncated"])
        self.assertNotIn("content", result)

    def test_subdirectory_entries_use_paths_relative_to_project_root(self):
        result = self.list_path("data")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["entries"], [
            {"name": "nested.txt", "type": "file", "relative_path": "data/nested.txt"},
        ])

    def test_empty_directory_is_a_success(self):
        result = self.list_path("empty")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["entries"], [])
        self.assertFalse(result["truncated"])

    def test_argument_rules_apply_to_the_new_tool_before_execution(self):
        for arguments in [None, [], {}, {"path": "."}, {"relative_path": 123},
                          {"relative_path": "  "}, {"relative_path": ".", "project_root": "elsewhere"}]:
            with self.subTest(arguments=arguments):
                result = call_tool(self.tools, "list_directory", arguments)
                self.assertEqual(result["error_type"], "invalid_arguments")

    def test_relative_and_absolute_outside_paths_are_rejected_before_listing(self):
        sibling = self.base / "project-copy"
        sibling.mkdir()
        for path in ["../project-copy", str(sibling.resolve()), "../missing"]:
            with self.subTest(path=path):
                result = self.list_path(path)
                self.assertEqual(result["error_type"], "path_outside_project")
                self.assertNotIn("entries", result)

    def test_missing_directory_and_file_input_have_structured_errors(self):
        self.assertEqual(self.list_path("missing")["error_type"], "file_not_found")
        self.assertEqual(self.list_path("hello.txt")["error_type"], "not_a_directory")

    def test_large_directory_result_is_explicitly_truncated(self):
        large = self.root / "large"
        large.mkdir()
        for index in range(51):
            (large / f"item{index:02d}.txt").write_text("", encoding="utf-8")
        result = self.list_path("large")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["entries"]), 50)
        self.assertTrue(result["truncated"])

    def test_each_directory_registry_uses_its_bound_project_root(self):
        second_root = self.base / "other"
        second_root.mkdir()
        (second_root / "second.txt").write_text("second", encoding="utf-8")
        other_tools = build_tool_registry(str(second_root))
        result = call_tool(other_tools, "list_directory", {"relative_path": "."})
        self.assertEqual(result["status"], "success")
        self.assertEqual([e["name"] for e in result["entries"]], ["second.txt"])
        self.assertEqual([e["name"] for e in self.list_path(".")["entries"]], ["data", "empty", "hello.txt"])

    def test_model_can_choose_read_tool_after_observing_directory_result(self):
        def chat(messages, descriptions):
            last = messages[-1]
            if last["role"] == "user":
                name, arguments = "list_directory", {"relative_path": "data"}
            else:
                observed = json.loads(last["content"])
                if last["tool_name"] == "list_directory":
                    self.assertEqual(observed["status"], "success")
                    self.assertEqual(observed["entries"][0]["name"], "nested.txt")
                    name = "read_text_file"
                    arguments = {"relative_path": observed["entries"][0]["relative_path"]}
                else:
                    return {"done": True, "done_reason": "stop", "message": {
                        "role": "assistant", "content": observed["content"],
                    }}
            return {"done": True, "done_reason": "stop", "message": {
                "role": "assistant", "content": "", "tool_calls": [{"function": {
                    "name": name, "arguments": arguments,
                }}],
            }}

        result = run_ollama_loop("find then read", chat, self.tools, [], tool_policy=decide_tool_result)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "not listed recursively")
        self.assertEqual(result["steps"], 3)
        self.assertEqual([m["tool_name"] for m in result["messages"] if m["role"] == "tool"],
                         ["list_directory", "read_text_file"])


if __name__ == "__main__":
    unittest.main()
