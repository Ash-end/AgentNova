"""展示工具描述、手工构造的调用，以及真实执行结果。"""

import json
from pathlib import Path

from experiment_agent.tools.registry import build_tool_registry, call_tool


def main():
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "experiment_agent/tools/read_text_file.schema.json"
    parameters = json.loads(schema_path.read_text(encoding="utf-8"))

    # 本项目内部描述格式；接入模型服务时再转换成该服务要求的格式。
    definition = {
        "name": "read_text_file",
        "description": "读取项目内指定 UTF-8 文本文件；用于查看代码、配置或日志。",
        "parameters": parameters,
    }
    print("Tool description prepared for a model (no model API called):")
    print(json.dumps(definition, ensure_ascii=False, indent=2))

    tools = build_tool_registry(str(project_root))
    requests = [
        {
            "name": "read_text_file",
            "arguments": {"relative_path": "labs/fixtures/hello.txt"},
        },
        {
            "name": "read_text_file",
            "arguments": {
                "relative_path": "labs/fixtures/hello.txt",
                "project_root": str(project_root),
            },
        },
    ]

    for request in requests:
        print("\nManually constructed request:")
        print(json.dumps(request, ensure_ascii=False, indent=2))
        result = call_tool(tools, request["name"], request["arguments"])
        print("Result from Python runtime validation and execution:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
