"""通过工具名称和参数调用已经注册的文件工具。"""

import json
import sys
from pathlib import Path

from experiment_agent.tools.registry import build_tool_registry, call_tool


def main():
    project_root = Path(__file__).resolve().parents[1]
    tools = build_tool_registry(str(project_root))

    print(f"Python: {sys.executable}")
    print(f"Project root: {project_root}")
    print(f"Registered tools: {list(tools)}")

    requests = [
        {
            "name": "read_text_file",
            "arguments": {"relative_path": "labs/fixtures/hello.txt"},
        },
        {
            "name": "delete_file",
            "arguments": {"relative_path": "labs/fixtures/hello.txt"},
        },
        {
            "name": "read_text_file",
            "arguments": {"relative_path": "../outside-demo.txt"},
        },
    ]

    for request in requests:
        print("\nRequest:")
        print(json.dumps(request, ensure_ascii=False, indent=2))
        result = call_tool(tools, request["name"], request["arguments"])
        print("Result:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
