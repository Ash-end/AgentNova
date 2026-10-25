"""目录观察筛选练习：只验证输入/输出契约，无文件访问、无模型请求。"""

from copy import deepcopy
import unittest

from exercises.select_text_file import select_unique_text_file


def entry(name, kind="file"):
    return {"name": name, "type": kind, "relative_path": f"labs/fixtures/{name}"}


def listing(entries, truncated=False):
    return {"status": "success", "entries": entries, "truncated": truncated}


class TextFileSelectionExerciseTests(unittest.TestCase):
    def test_unique_regular_text_file_returns_observed_path_without_mutating_input(self):
        observation = listing([
            entry("README.md"), entry("hello.txt"),
            entry("archive.txt", "directory"), entry("shortcut.txt", "symlink"),
        ])
        original = deepcopy(observation)
        result = select_unique_text_file(observation)
        self.assertEqual(result, {
            "status": "success", "relative_path": "labs/fixtures/hello.txt",
        })
        self.assertEqual(observation, original)

    def test_uppercase_extension_and_spaces_in_observed_path_are_preserved(self):
        result = select_unique_text_file(listing([entry("my notes.TXT")]))
        self.assertEqual(result, {
            "status": "success", "relative_path": "labs/fixtures/my notes.TXT",
        })

    def test_empty_complete_directory_has_no_text_file(self):
        self.assertEqual(select_unique_text_file(listing([])), {
            "status": "failed", "error_type": "no_text_file",
        })

    def test_directories_and_symlinks_are_not_regular_text_files(self):
        observation = listing([
            entry("README.md"), entry("archive.txt", "directory"),
            entry("shortcut.txt", "symlink"),
        ])
        self.assertEqual(select_unique_text_file(observation), {
            "status": "failed", "error_type": "no_text_file",
        })

    def test_multiple_text_files_are_not_selected_arbitrarily(self):
        self.assertEqual(select_unique_text_file(listing([entry("a.txt"), entry("b.txt")])), {
            "status": "failed", "error_type": "multiple_text_files",
        })

    def test_truncated_listing_with_one_visible_match_cannot_prove_uniqueness(self):
        self.assertEqual(select_unique_text_file(listing([entry("hello.txt")], truncated=True)), {
            "status": "failed", "error_type": "incomplete_directory_listing",
        })

    def test_truncated_listing_without_visible_matches_cannot_prove_absence(self):
        self.assertEqual(select_unique_text_file(listing([], truncated=True)), {
            "status": "failed", "error_type": "incomplete_directory_listing",
        })

    def test_failed_listing_preserves_original_failure_without_requiring_entries(self):
        observation = {"status": "failed", "error_type": "path_outside_project", "path": "../outside"}
        self.assertEqual(select_unique_text_file(observation), observation)


if __name__ == "__main__":
    unittest.main()
