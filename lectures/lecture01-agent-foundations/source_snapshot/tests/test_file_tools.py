"""验证文件读取结果与项目路径范围。"""

import tempfile
import unittest
from pathlib import Path

from experiment_agent.tools.file_tools import read_text_file


class ReadTextFileTests(unittest.TestCase):
    def test_existing_utf8_file_returns_exact_content(self):
        with tempfile.TemporaryDirectory() as directory:
            expected_content = "你好，Agent！\n这是一次真实的文件读取。\n"
            (Path(directory) / "hello.txt").write_text(
                expected_content, encoding="utf-8"
            )

            result = read_text_file(directory, "hello.txt")

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["content"], expected_content)

    def test_missing_file_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = read_text_file(directory, "missing.txt")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "file_not_found")
            self.assertEqual(result["path"], str(Path(directory) / "missing.txt"))

    def test_parent_traversal_to_existing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            outside = Path(directory) / "outside.txt"
            outside.write_text("outside test fixture", encoding="utf-8")

            result = read_text_file(str(root), "../outside.txt")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "path_outside_project")
            self.assertEqual(result["path"], str(outside.resolve()))
            self.assertNotIn("content", result)

    def test_absolute_path_to_sibling_with_shared_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            sibling = Path(directory) / "project-copy"
            sibling.mkdir()
            outside = sibling / "outside.txt"
            outside.write_text("outside test fixture", encoding="utf-8")

            result = read_text_file(str(root), str(outside.resolve()))

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "path_outside_project")
            self.assertNotIn("content", result)

    def test_missing_file_outside_project_is_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()

            result = read_text_file(str(root), "../missing.txt")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_type"], "path_outside_project")


if __name__ == "__main__":
    unittest.main()
