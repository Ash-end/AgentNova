"""用确定性模型替身演示：参数错误、根据观察修正、读取并结束。"""

import json
from pathlib import Path

from experiment_agent.loop import run_loop
from experiment_agent.tools.registry import build_tool_registry


def mock_model(messages: list, tool_descriptions: list) -> dict:
    """手写教学策略，不调用大模型，也不具备通用推理能力。"""
    tool_name = tool_descriptions[0]["name"]
    last = messages[-1]

    if last["role"] == "user":
        # 故意先用错误字段，观察运行时返回的校验结果。
        return {
            "type": "tool_call",
            "name": tool_name,
            "arguments": {"path": "labs/fixtures/hello.txt"},
        }

    observation = last["content"]
    if observation.get("error_type") == "invalid_arguments":
        return {
            "type": "tool_call",
            "name": tool_name,
            "arguments": {"relative_path": "labs/fixtures/hello.txt"},
        }

    if observation.get("status") == "success":
        return {
            "type": "final",
            "content": "已读取文件，实际内容为：\n" + observation["content"],
        }

    return {
        "type": "final",
        "content": "未完成读取，工具报告：" + observation.get("error_type", "unknown_error"),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "experiment_agent/tools/read_text_file.schema.json"
    descriptions = [{
        "name": "read_text_file",
        "description": "读取项目内的 UTF-8 文本文件。",
        "parameters": json.loads(schema_path.read_text(encoding="utf-8")),
    }]
    tools = build_tool_registry(str(root))

    result = run_loop(
        task="读取 labs/fixtures/hello.txt，告诉我文件的实际内容。",
        model=mock_model,
        tools=tools,
        tool_descriptions=descriptions,
        max_steps=5,
    )

    print("Deterministic mock model; no model API called.")
    for index, message in enumerate(result["messages"], start=1):
        print(f"\nMessage {index} [{message['role']}]:")
        print(json.dumps(message["content"], ensure_ascii=False, indent=2))

    print(f"\nLoop status: {result['status']}")
    print(f"Model decisions: {result['steps']}")
    print(f"Final response: {result.get('answer', result.get('error_type'))}")


if __name__ == "__main__":
    main()
