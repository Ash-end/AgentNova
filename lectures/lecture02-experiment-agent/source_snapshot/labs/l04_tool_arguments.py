"""观察参数校验如何将错误输入转成结构化返回值。"""

import json
from pathlib import Path

from experiment_agent.tools.registry import build_tool_registry, call_tool


def main():
    project_root = Path(__file__).resolve().parents[1]
    tools = build_tool_registry(str(project_root))

    examples = [
        ("valid arguments", {"relative_path": "labs/fixtures/hello.txt"}),
        ("missing required argument", {}),
        ("misspelled argument name", {"path": "labs/fixtures/hello.txt"}),
        ("wrong argument type", {"relative_path": 123}),
        ("whitespace-only path", {"relative_path": "   "}),
        ("caller supplies project root", {
            "relative_path": "labs/fixtures/hello.txt",
            "project_root": str(project_root),
        }),
    ]

    for label, arguments in examples:
        print(f"\nCase: {label}")
        print(f"Arguments: {json.dumps(arguments, ensure_ascii=False)}")
        try:
            result = call_tool(tools, "read_text_file", arguments)
        except TypeError as error:
            # 保留教学诊断；已知错误参数现在应返回 invalid_arguments。
            print(f"Uncaught by dispatcher: {type(error).__name__}: {error}")
        else:
            print(f"Result: {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
