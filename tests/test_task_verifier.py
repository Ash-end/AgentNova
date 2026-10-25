"""验证任务证据与循环完成分离；负例检查被拒绝的具体原因。"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiment_agent.verification import verify_unique_text_read
from labs.l16_agent_task_verifier import run_cases


class TaskVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "other").mkdir()
            (root / "data/hello.txt").write_text("你好，验收器！\n", encoding="utf-8")
            (root / "other/other.txt").write_text("这是另一个文件。\n", encoding="utf-8")
            cls.cases = {case["case"]: case for case in run_cases(root)}

    def correct_run(self):
        return deepcopy(self.cases["correct_completion"]["run"])

    def replace_directory_observation(self, run, **fields):
        message = next(m for m in run["messages"] if m.get("tool_name") == "list_directory")
        observation = json.loads(message["content"])
        observation.update(fields)
        message["content"] = json.dumps(observation)

    def test_correct_completion_passes_without_mutating_run(self):
        run = self.correct_run()
        original = deepcopy(run)
        self.assertEqual(verify_unique_text_read(run, "data"), {
            "status": "passed", "reason": "verified_read", "relative_path": "data/hello.txt",
        })
        self.assertEqual(run, original)

    def test_claim_without_reading_completes_loop_but_fails_verification(self):
        case = self.cases["claimed_without_reading"]
        self.assertEqual(case["run"]["status"], "completed")
        self.assertEqual(case["verification"], {"status": "failed", "reason": "missing_read_evidence"})

    def test_successful_read_of_wrong_file_is_rejected(self):
        case = self.cases["wrong_file_read"]
        tool = next(m for m in case["run"]["messages"] if m.get("tool_name") == "read_text_file")
        self.assertEqual(json.loads(tool["content"])["status"], "success")
        self.assertEqual(case["verification"], {
            "status": "failed", "reason": "wrong_file_read",
            "expected_path": "data/hello.txt", "actual_path": "other/other.txt",
        })

    def test_truncated_observation_cannot_prove_uniqueness(self):
        run = self.correct_run()
        self.replace_directory_observation(run, truncated=True)
        self.assertEqual(verify_unique_text_read(run, "data")["selection_error"], "incomplete_directory_listing")

    def test_multiple_candidates_fail_even_if_one_was_read(self):
        run = self.correct_run()
        self.replace_directory_observation(run, entries=[
            {"name": name, "type": "file", "relative_path": "data/" + name}
            for name in ("hello.txt", "second.txt")
        ])
        self.assertEqual(verify_unique_text_read(run, "data")["selection_error"], "multiple_text_files")

    def test_failed_read_cannot_be_overruled_by_final_claim(self):
        run = self.correct_run()
        tool = next(m for m in run["messages"] if m.get("tool_name") == "read_text_file")
        tool["content"] = json.dumps({"status": "failed", "error_type": "invalid_encoding"})
        self.assertEqual(verify_unique_text_read(run, "data"), {
            "status": "failed", "reason": "read_failed", "tool_error": "invalid_encoding",
        })

    def test_successful_read_requires_string_content_but_allows_empty_file(self):
        for observation, expected in [({"status": "success"}, "missing_file_content"),
                                      ({"status": "success", "content": ""}, "verified_read")]:
            with self.subTest(observation=observation):
                run = self.correct_run()
                tool = next(m for m in run["messages"] if m.get("tool_name") == "read_text_file")
                tool["content"] = json.dumps(observation)
                self.assertEqual(verify_unique_text_read(run, "data")["reason"], expected)

    def test_request_without_execution_result_is_not_read_evidence(self):
        run = self.correct_run()
        run["messages"] = [m for m in run["messages"] if m.get("tool_name") != "read_text_file"]
        self.assertEqual(verify_unique_text_read(run, "data")["reason"], "invalid_execution_trace")

    def test_orphan_or_mismatched_tool_observation_is_rejected(self):
        for name in ("unexpected_tool", "read_text_file"):
            with self.subTest(name=name):
                run = self.correct_run()
                if name == "unexpected_tool":
                    run["messages"][3]["tool_name"] = name
                else:
                    run["messages"].insert(2, {"role": "tool", "tool_name": name,
                                             "content": '{"status": "success", "content": "fake"}'})
                self.assertEqual(verify_unique_text_read(run, "data")["reason"], "invalid_execution_trace")

    def test_wrong_directory_is_not_accepted_as_target_directory_evidence(self):
        self.assertEqual(verify_unique_text_read(self.correct_run(), "other")["reason"], "missing_directory_evidence")

    def test_read_before_directory_observation_is_rejected(self):
        run = self.correct_run()
        messages = run["messages"]
        messages[2:6] = messages[4:6] + messages[2:4]
        self.assertEqual(verify_unique_text_read(run, "data")["reason"], "read_before_directory")

    def test_malformed_directory_or_json_evidence_fails_closed(self):
        run = self.correct_run()
        self.replace_directory_observation(run, entries="not a list")
        self.assertEqual(verify_unique_text_read(run, "data")["reason"], "invalid_directory_evidence")
        run["messages"][3]["content"] = "not JSON"
        self.assertEqual(verify_unique_text_read(run, "data")["reason"], "invalid_execution_trace")

    def test_incomplete_loop_is_not_successful_task_completion(self):
        run = self.correct_run()
        run["status"] = "failed"
        self.assertEqual(verify_unique_text_read(run, "data")["reason"], "loop_not_completed")
