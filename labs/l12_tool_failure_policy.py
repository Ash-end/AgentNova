"""预设模型请求 + 真实文件工具：观察修正预算与停止策略，不调用模型 API。"""

import json
from pathlib import Path

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry


def make_demo_chat(name, arguments, repeat_invalid=False):
    """用确定的请求制造失败；这是手写演示逻辑，不是模型推理。"""
    def chat(messages, descriptions):
        if messages[-1]["role"] == "user":
            next_name, next_arguments = name, arguments
        else:
            observation = json.loads(messages[-1]["content"])
            if observation.get("error_type") == "invalid_arguments":
                next_name = "read_text_file"
                next_arguments = arguments if repeat_invalid else {"relative_path": "labs/fixtures/hello.txt"}
            else:
                return {"done": True, "done_reason": "stop", "message": {
                    "role": "assistant", "content": observation.get("content", "工具失败，无法完成读取。"),
                }}
        return {"done": True, "done_reason": "stop", "message": {
            "role": "assistant", "content": "", "tool_calls": [{"function": {
                "name": next_name, "arguments": next_arguments,
            }}],
        }}
    return chat


def main():
    root = Path(__file__).resolve().parents[1]
    if (root / "labs/fixtures/missing.txt").exists():
        raise SystemExit("The missing-file demo requires labs/fixtures/missing.txt to be absent; no file was changed.")
    scenarios = [
        ("invalid arguments, then correction", "read_text_file", {"path": "labs/fixtures/hello.txt"}, False),
        ("required file missing", "read_text_file", {"relative_path": "labs/fixtures/missing.txt"}, False),
        ("path outside project", "read_text_file", {"relative_path": "../outside.txt"}, False),
        ("unregistered tool", "delete_file", {"relative_path": "labs/fixtures/hello.txt"}, False),
        ("invalid arguments repeated", "read_text_file", {"path": "labs/fixtures/hello.txt"}, True),
    ]
    reports = []
    print("Deterministic model responses; real file tools; no model API called.")
    print("Correction budget: 1 opportunity for the whole task; max_steps: 5.")
    for label, name, arguments, repeat in scenarios:
        print(f"\nCase: {label}")
        result = run_ollama_loop(
            task="读取指定文件；文件确实不存在时停止，不猜测内容。",
            chat=make_demo_chat(name, arguments, repeat),
            tools=build_tool_registry(str(root)),
            tool_descriptions=[],
            max_steps=5,
            tool_policy=decide_tool_result,
        )
        observations = [m for m in result["messages"] if m["role"] == "tool"]
        for observation, decision in zip(observations, result["tool_decisions"]):
            print(f"  Step {decision['step']} tool result: {observation['content']}")
            print(f"  Decision: {decision['action']} / {decision['reason']}")
            print(f"  Correction opportunities used: {decision['corrections_used']}")
        print(f"Loop status: {result['status']}")
        print(f"Model decisions: {result['steps']}")
        if result["status"] == "completed":
            print(f"Final response: {result['answer']}")
        else:
            print(f"Stopped because: {result['tool_error_type']} / {result['stop_reason']}")
        reports.append({"case": label, "result": result})

    path = root / "reports/l12_tool_failure_policy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {path}")


if __name__ == "__main__":
    main()
