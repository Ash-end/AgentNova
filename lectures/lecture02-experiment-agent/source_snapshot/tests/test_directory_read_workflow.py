"""验证工具串接确实受选择结果约束；使用真实临时文件与读取调用观察。"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from experiment_agent.tools.registry import build_tool_registry
from labs.l15_directory_read_workflow import run_directory_read_workflow


class DirectoryReadWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / "data"
        self.folder.mkdir()
        self.tools = build_tool_registry(str(self.root))
        self.reader = Mock(wraps=self.tools["read_text_file"])
        self.tools["read_text_file"] = self.reader

    def test_unique_file_is_read_using_observed_relative_path(self):
        (self.folder / "my notes.TXT").write_text("真实正文\n", encoding="utf-8")
        (self.folder / "README.md").write_text("ignore", encoding="utf-8")
        result = run_directory_read_workflow(self.tools, "data")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], {"status": "success", "content": "真实正文\n"})
        self.reader.assert_called_once_with(relative_path="data/my notes.TXT")
        self.assertEqual([e["step"] for e in result["trace"]], [
            "list_directory", "select_unique_text_file", "read_text_file",
        ])

    def test_multiple_files_stop_without_reading_any_file(self):
        for name in ("a.txt", "b.txt"):
            (self.folder / name).write_text(name, encoding="utf-8")
        result = run_directory_read_workflow(self.tools, "data")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "multiple_text_files")
        self.reader.assert_not_called()

    def test_no_text_file_stops_without_reading(self):
        result = run_directory_read_workflow(self.tools, "data")
        self.assertEqual(result["result"]["error_type"], "no_text_file")
        self.reader.assert_not_called()

    def test_real_truncated_listing_does_not_read_the_one_visible_candidate(self):
        (self.folder / "000.txt").write_text("visible", encoding="utf-8")
        for index in range(50):
            (self.folder / f"note-{index:02d}.md").write_text("note", encoding="utf-8")
        result = run_directory_read_workflow(self.tools, "data")
        self.assertTrue(result["trace"][0]["result"]["truncated"])
        self.assertEqual(result["result"]["error_type"], "incomplete_directory_listing")
        self.reader.assert_not_called()

    def test_listing_failure_is_preserved_and_does_not_start_reading(self):
        result = run_directory_read_workflow(self.tools, "missing")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "file_not_found")
        self.assertEqual(result["result"], result["trace"][0]["result"])
        self.reader.assert_not_called()

    def test_read_failure_is_not_reported_as_successful_selection(self):
        (self.folder / "bad.txt").write_bytes(b"\xff\xfe")
        result = run_directory_read_workflow(self.tools, "data")
        self.assertEqual(result["trace"][1]["result"]["status"], "success")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["error_type"], "invalid_encoding")
        self.reader.assert_called_once_with(relative_path="data/bad.txt")


if __name__ == "__main__":
    unittest.main()
