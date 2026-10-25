"""给真实模型两个工具，由任务与工具观察决定调用哪个工具。"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry
from experiment_agent.verification import verify_unique_text_read


TASKS = {
    "list": "请查看 labs/fixtures 目录下有哪些直接子项，只列出名称和类型。",
    "read": "请告诉我 labs/fixtures/hello.txt 的实际文本内容。",
    "discover": (
        "请先查看 labs/fixtures 目录，拿到目录结果后找到其中的 .txt 文件，"
        "再读取该文件的真实内容并告诉我。如果没有或不止一个 .txt 文件，请说明情况并停止。"
    ),
}
EXPECTED = {"list": ["list_directory"], "read": ["read_text_file"],
            "discover": ["list_directory", "read_text_file"]}


def run_case(root, case, descriptions, max_steps):
    requests = []
    seen_messages = 0

    def chat(messages, tool_descriptions):
        nonlocal seen_messages
        for message in messages[seen_messages:]:
            if message["role"] == "tool":
                print(f"Tool result [{message['tool_name']}]: {message['content']}", flush=True)
        seen_messages = len(messages)
        payload = {
            "model": "qwen3.5:9b-q4_K_M", "messages": messages, "tools": tool_descriptions,
            "stream": False, "think": False, "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": 512},
        }
        requests.append(json.loads(json.dumps(payload, ensure_ascii=False)))
        print(f"\nStep {len(requests)}/{max_steps}: requesting model (socket timeout: 180s)...", flush=True)
        request = Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        started = perf_counter()
        with urlopen(request, timeout=180) as response:
            data = json.load(response)
        print(f"Model response ({perf_counter() - started:.3f}s):", flush=True)
        print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
        return data

    print(f"\nCase: {case}\nTask: {TASKS[case]}", flush=True)
    started = perf_counter()
    result = run_ollama_loop(
        TASKS[case], chat, build_tool_registry(str(root)), descriptions,
        max_steps=max_steps, tool_policy=decide_tool_result,
    )
    elapsed = perf_counter() - started
    if case == "discover":
        verification = verify_unique_text_read(result, "labs/fixtures")
    else:
        verification = {"status": "not_applicable", "reason": "discover_only"}
    observations = [m for m in result["messages"] if m["role"] == "tool"]
    observed_tools = [m["tool_name"] for m in observations]
    for message in result["messages"][seen_messages:]:
        if message["role"] == "tool":
            print(f"Tool result [{message['tool_name']}]: {message['content']}")
    trace_matches = observed_tools == EXPECTED[case]
    print(f"\nLoop status: {result['status']}")
    print(f"Task verification: {verification['status']}")
    print(f"Verification reason: {verification['reason']}")
    if "relative_path" in verification:
        print(f"Verified path: {verification['relative_path']}")
    if "expected_path" in verification:
        print(f"Expected path: {verification['expected_path']}")
        print(f"Actual path: {verification['actual_path']}")
    print(f"Model decisions: {result['steps']}")
    print(f"Observed tools: {observed_tools}")
    print(f"Expected simple tool sequence matched: {trace_matches}")
    print(f"Final response: {result.get('answer', '')}")
    if result["status"] != "completed":
        print(f"Error: {result.get('error_type')} / {result.get('stop_reason')}")
    print(f"Elapsed seconds: {elapsed:.3f}")
    path = root / "reports" / f"l14_multi_tool_agent_{case}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "task": TASKS[case], "requests": requests, "result": result,
        "verification": verification,
        "observed_tools": observed_tools, "expected_sequence_matched": trace_matches,
        "elapsed_seconds": elapsed,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved report: {path}")
    accepted = verification["status"] == "passed" if case == "discover" else trace_matches
    return result["status"] == "completed" and accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[*TASKS, "all"], default="discover")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")
    root = Path(__file__).resolve().parents[1]
    descriptions = []
    for name, description in [
        ("read_text_file", "读取项目内指定 UTF-8 文件的文本内容。"),
        ("list_directory", "查看项目目录下一层的文件和子目录名称、类型及路径。最多返回50项；truncated表示未完整列出。"),
    ]:
        schema = json.loads((root / f"experiment_agent/tools/{name}.schema.json").read_text(encoding="utf-8"))
        descriptions.append({"type": "function", "function": {
            "name": name, "description": description, "parameters": schema,
        }})
    print(f"Available tools: {[d['function']['name'] for d in descriptions]}", flush=True)
    passed = True
    for case in TASKS if args.case == "all" else [args.case]:
        if not run_case(root, case, descriptions, args.max_steps):
            passed = False
    if not passed:
        raise SystemExit("A task did not meet its acceptance checks. Inspect the saved report.")


if __name__ == "__main__":
    main()
