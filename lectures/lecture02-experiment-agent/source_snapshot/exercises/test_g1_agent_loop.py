"""G1 行为验收：模型替身 + 真实临时文件，无 HTTP、无脚本执行。"""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from exercises.g1_agent_loop import run_agent
from experiment_agent.tools.registry import build_tool_registry


def request(name="read_text_file", **arguments):
    return {"type": "tool_call", "name": name, "arguments": arguments}


def final(content="已完成"):
    return {"type": "final", "content": content}


class ScriptedModel:
    """记录每次调用当时的消息快照，防止后续 append 改写历史证据。"""

    def __init__(self, *actions):
        self.actions = actions
        self.calls = []

    def __call__(self, messages, tool_descriptions):
        index = len(self.calls)
        self.calls.append({
            "messages": deepcopy(messages),
            "tool_descriptions": deepcopy(tool_descriptions),
        })
        if index >= len(self.actions):
            raise AssertionError("不应再次请求模型：预定动作已用完")
        return deepcopy(self.actions[index])


class G1AgentLoopTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="g1-agent-loop-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "notes.txt").write_text("真实内容：17\n", encoding="utf-8")
        self.tools = build_tool_registry(str(self.root))
        self.descriptions = [{"name": "read_text_file"}, {"name": "list_directory"}]

    def run_case(self, model, max_steps=5, tools=None):
        return run_agent(
            "查看并读取文件", model, self.tools if tools is None else tools,
            self.descriptions, max_steps=max_steps,
        )

    def assert_common(self, result, model, status, steps):
        self.assertEqual(result["status"], status)
        self.assertEqual(result["steps"], steps)
        self.assertEqual(len(model.calls), steps)
        self.assertEqual(model.calls[0]["messages"], [
            {"role": "user", "content": "查看并读取文件"},
        ])
        for call in model.calls:
            self.assertEqual(call["tool_descriptions"], self.descriptions)

    def test_final_stops_immediately_without_executing_a_tool(self):
        read = Mock(side_effect=AssertionError("final 后不应执行工具"))
        model = ScriptedModel(final("无需读取"), request(relative_path="data/notes.txt"))
        result = self.run_case(model, tools={"read_text_file": read})
        self.assert_common(result, model, "completed", 1)
        self.assertEqual(result["answer"], "无需读取")
        self.assertEqual(result["messages"], [
            {"role": "user", "content": "查看并读取文件"},
            {"role": "assistant", "content": final("无需读取")},
        ])
        read.assert_not_called()

    def test_directory_observation_reaches_next_decision_then_actual_file_is_read(self):
        snapshots = []

        def model(messages, descriptions):
            self.assertEqual(descriptions, self.descriptions)
            snapshots.append(deepcopy(messages))
            if len(snapshots) == 1:
                self.assertEqual(messages, [{"role": "user", "content": "查看并读取文件"}])
                return request("list_directory", relative_path="data")
            if len(snapshots) == 2:
                observation = messages[-1]
                self.assertEqual(observation["role"], "tool")
                self.assertEqual(observation["name"], "list_directory")
                self.assertEqual(observation["content"]["status"], "success")
                path = observation["content"]["entries"][0]["relative_path"]
                return request(relative_path=path)
            if len(snapshots) == 3:
                self.assertEqual(messages[-1], {
                    "role": "tool", "name": "read_text_file",
                    "content": {"status": "success", "content": "真实内容：17\n"},
                })
                return final(messages[-1]["content"]["content"])
            raise AssertionError("final 后不应请求模型")

        result = self.run_case(model)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"], 3)
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(result["answer"], "真实内容：17\n")
        self.assertEqual([m["role"] for m in result["messages"]], [
            "user", "assistant", "tool", "assistant", "tool", "assistant",
        ])

    def test_argument_error_is_observed_and_can_be_corrected_once(self):
        bad = request(path="data/notes.txt")
        good = request(relative_path="data/notes.txt")
        model = ScriptedModel(bad, good, final("读取成功"))
        result = self.run_case(model)
        self.assert_common(result, model, "completed", 3)
        observation = model.calls[1]["messages"][-1]
        self.assertEqual(observation["role"], "tool")
        self.assertEqual(observation["content"]["error_type"], "invalid_arguments")
        self.assertEqual(model.calls[2]["messages"][-1]["content"]["content"], "真实内容：17\n")
        self.assertEqual([m["content"] for m in result["messages"] if m["role"] == "assistant"], [
            bad, good, final("读取成功"),
        ])

    def test_correction_budget_is_not_reset_by_a_successful_tool(self):
        model = ScriptedModel(
            request(path="data/notes.txt"),
            request(relative_path="data/notes.txt"),
            request(path="data/notes.txt"),
        )
        result = self.run_case(model)
        self.assert_common(result, model, "failed", 3)
        self.assertEqual(result["error_type"], "tool_policy_stopped")
        self.assertEqual(result["tool_error_type"], "invalid_arguments")
        self.assertEqual(result["stop_reason"], "correction_limit_exceeded")
        self.assertEqual(result["messages"][-1]["content"]["error_type"], "invalid_arguments")

    def test_missing_file_is_recorded_then_stopped_without_another_model_call(self):
        model = ScriptedModel(request(relative_path="data/missing.txt"))
        result = self.run_case(model)
        self.assert_common(result, model, "failed", 1)
        self.assertEqual(result["error_type"], "tool_policy_stopped")
        self.assertEqual(result["tool_error_type"], "file_not_found")
        self.assertEqual(result["stop_reason"], "required_file_missing")
        self.assertEqual([m["role"] for m in result["messages"]], ["user", "assistant", "tool"])
        self.assertEqual(result["messages"][-1]["content"]["error_type"], "file_not_found")
        self.assertEqual(len(model.calls[0]["messages"]), 1)

    def test_unknown_tool_stops_and_does_not_execute_a_registered_tool(self):
        read = Mock(side_effect=AssertionError("不能把未知工具替换为已注册工具"))
        model = ScriptedModel(request("delete_file", relative_path="data/notes.txt"))
        result = self.run_case(model, tools={"read_text_file": read})
        self.assert_common(result, model, "failed", 1)
        self.assertEqual(result["error_type"], "tool_policy_stopped")
        self.assertEqual(result["tool_error_type"], "unknown_tool")
        self.assertEqual(result["stop_reason"], "tool_unavailable")
        self.assertEqual(result["messages"][-1]["name"], "delete_file")
        read.assert_not_called()

    def test_step_limit_counts_model_decisions_and_preserves_last_tool_result(self):
        model = ScriptedModel(
            request(relative_path="data/notes.txt"),
            request(relative_path="data/notes.txt"),
        )
        result = self.run_case(model, max_steps=2)
        self.assert_common(result, model, "failed", 2)
        self.assertEqual(result["error_type"], "max_steps_exceeded")
        self.assertEqual(len(result["messages"]), 5)
        self.assertEqual(result["messages"][-1]["content"], {
            "status": "success", "content": "真实内容：17\n",
        })

    def test_invalid_model_actions_stop_without_executing_a_tool(self):
        cases = [
            None, [], {"type": "other"}, final(123), final("   "),
            {"type": "tool_call", "name": "read_text_file"},
            {"type": "tool_call", "name": 123, "arguments": {}},
            {"type": "tool_call", "name": "", "arguments": {}},
        ]
        for action in cases:
            with self.subTest(action=action):
                read = Mock(side_effect=AssertionError("非法动作不应执行工具"))
                model = ScriptedModel(action)
                result = self.run_case(model, tools={"read_text_file": read})
                self.assert_common(result, model, "failed", 1)
                self.assertEqual(result["error_type"], "invalid_model_response")
                self.assertEqual(result["messages"][-1], {"role": "assistant", "content": action})
                read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
