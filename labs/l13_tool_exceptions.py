"""比较原始 Python 异常、结构化工具结果和策略判断；不调用模型 API。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry


def denied_read(relative_path):
    """明确注入权限异常，不修改任何真实文件的 ACL。"""
    raise PermissionError("Injected permission failure for this lesson.")


def make_chat(path):
    def chat(messages, descriptions):
        if messages[-1]["role"] == "user":
            return {"done": True, "done_reason": "stop", "message": {
                "role": "assistant", "content": "", "tool_calls": [{"function": {
                    "name": "read_text_file", "arguments": {"relative_path": path},
                }}],
            }}
        observation = json.loads(messages[-1]["content"])
        return {"done": True, "done_reason": "stop", "message": {
            "role": "assistant", "content": observation.get("content", "已收到工具失败结果。"),
        }}
    return chat


def main():
    project_root = Path(__file__).resolve().parents[1]
    reports = []
    print("Deterministic model responses; no model API called.")
    print("Real UTF-8/directory/decoding cases; permission case explicitly injected.")
    print("Fixtures are created in a temporary demo project and cleaned up afterward.")
    with TemporaryDirectory(prefix="agent-exceptions-") as directory:
        root = Path(directory)
        (root / "hello.txt").write_text("你好，异常处理！", encoding="utf-8")
        (root / "invalid.bin").write_bytes(b"\xff\xfe\x80")
        (root / "folder").mkdir()
        tools = build_tool_registry(str(root))
        cases = [
            ("valid UTF-8 file", tools, "hello.txt"),
            ("directory read (real OS exception)", tools, "folder"),
            ("invalid UTF-8 bytes (real decoding exception)", tools, "invalid.bin"),
            ("permission error (injected; ACL unchanged)", {"read_text_file": denied_read}, "hello.txt"),
        ]
        for label, case_tools, path in cases:
            print(f"\nCase: {label}")
            # 仅为教学对照：绕过分发器执行一次，以展示原本会向上传播的异常。
            raw_exception_type = None
            try:
                raw = case_tools["read_text_file"](relative_path=path)
                print(f"Direct call: returned status={raw['status']}")
            except (OSError, UnicodeDecodeError) as error:
                raw_exception_type = type(error).__name__
                print(f"Direct call raised: {raw_exception_type}: {error}")

            # 再走一次正式调用链：循环 → call_tool → 工具 → 错误字典 → 策略。
            result = run_ollama_loop(
                task=f"读取 {path} 的 UTF-8 内容。",
                chat=make_chat(path),
                tools=case_tools,
                tool_descriptions=[],
                tool_policy=decide_tool_result,
            )
            observation = next(m for m in result["messages"] if m["role"] == "tool")
            print("Through dispatcher:")
            print(json.dumps(json.loads(observation["content"]), ensure_ascii=False, indent=2))
            decision = result["tool_decisions"][0]
            print(f"Policy: {decision['action']} / {decision['reason']}")
            print(f"Loop status: {result['status']}")
            print(f"Model decisions: {result['steps']}")
            if result["status"] == "completed":
                print(f"Final response: {result['answer']}")
            else:
                print(f"Stopped because: {result['tool_error_type']} / {result['stop_reason']}")
            reports.append({"case": label, "direct_exception_type": raw_exception_type, "result": result})

    report_path = project_root / "reports/l13_tool_exceptions.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
