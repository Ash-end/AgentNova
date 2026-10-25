"""真实模型选择固定脚本；Python 根据执行观察决定继续或停止。"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import build_tool_registry


TASKS = {
    "normal": "请实际运行一次正常计算演示脚本，根据工具返回的退出码和输出，说明是否执行成功。不要仅口头声称已运行。",
    "error": "请实际运行一次会触发演示异常的脚本，检查真实退出码和错误输出；失败后停止，不要换脚本或再次执行。",
    "timeout": "请实际运行一次长时间等待的演示脚本；超过工具时限后停止，不要重试，也不要改成其他脚本。",
}
EXPECTED_SCRIPT = {"normal": "normal", "error": "error", "timeout": "timeout"}


def expected_behavior_matched(case, result):
    """运行后核对实际脚本和控制流；不替模型选择参数，不评价回答语义。"""
    observations = [json.loads(m["content"]) for m in result["messages"]
                    if m["role"] == "tool" and m["tool_name"] == "run_python_script"]
    executions = [o for o in observations if "exit_code" in o]
    if len(executions) != 1 or executions[0].get("script_id") != EXPECTED_SCRIPT[case]:
        return False
    execution = executions[0]
    if case == "normal":
        return (result["status"] == "completed" and execution["status"] == "success"
                and execution["exit_code"] == 0 and not execution["timed_out"])
    error_type = "process_failed" if case == "error" else "tool_timeout"
    reason = "script_process_failed" if case == "error" else "tool_timeout_needs_review"
    stopped = (result["status"] == "failed" and result.get("error_type") == "tool_policy_stopped"
               and result.get("tool_error_type") == error_type and result.get("stop_reason") == reason
               and execution["status"] == "failed" and execution.get("error_type") == error_type)
    if case == "error":
        return stopped and execution["exit_code"] not in (None, 0) and not execution["timed_out"]
    return stopped and execution["timed_out"] and execution["exit_code"] is None


def run_case(root, case, descriptions, max_steps=4):
    requests = []
    seen_messages = 0
    execution_calls = 0
    registered = build_tool_registry(str(root), enable_python_scripts=True)

    def run_once(script_id):
        nonlocal execution_calls
        if execution_calls >= 1:
            return {"status": "failed", "error_type": "execution_limit_exceeded"}
        execution_calls += 1
        return registered["run_python_script"](script_id=script_id)

    tools = {"run_python_script": run_once}

    def show_new_observations(messages):
        nonlocal seen_messages
        for message in messages[seen_messages:]:
            if message["role"] == "tool":
                print(f"Tool result [{message['tool_name']}]:", flush=True)
                print(json.dumps(json.loads(message["content"]), ensure_ascii=False, indent=2), flush=True)
        seen_messages = len(messages)

    def chat(messages, tool_descriptions):
        show_new_observations(messages)
        payload = {
            "model": "qwen3.5:9b-q4_K_M", "messages": messages, "tools": tool_descriptions,
            "stream": False, "think": False, "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": 512},
        }
        requests.append(json.loads(json.dumps(payload, ensure_ascii=False)))
        print(f"\nModel request {len(requests)}/{max_steps} (HTTP timeout: 180s)...", flush=True)
        request = Request("http://127.0.0.1:11434/api/chat",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=180) as response:
            data = json.load(response)
        print("Model response:", flush=True)
        print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
        return data

    print(f"\nCase: {case}\nTask: {TASKS[case]}", flush=True)
    started = perf_counter()
    result = run_ollama_loop(TASKS[case], chat, tools, descriptions,
                             max_steps=max_steps, tool_policy=decide_tool_result)
    elapsed = perf_counter() - started
    show_new_observations(result["messages"])
    matched = expected_behavior_matched(case, result)
    print(f"\nLoop status: {result['status']}")
    print(f"Model decisions: {result['steps']}")
    print(f"Execution function calls: {execution_calls}")
    for decision in result["tool_decisions"]:
        print(f"Policy: {decision['action']} / {decision['reason']}")
    if "answer" in result:
        print(f"Final model reply: {result['answer']}")
    else:
        print("No final model reply: loop stopped before requesting another reply.")
    if result["status"] == "failed":
        print(f"Stopped because: {result.get('tool_error_type', result.get('error_type'))} / {result.get('stop_reason')}")
    print(f"Expected behavior matched: {matched}")
    print(f"Elapsed seconds: {elapsed:.3f}")
    path = root / "reports" / f"l18_real_script_agent_{case}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "task": TASKS[case], "requests": requests, "result": result,
        "execution_function_calls": execution_calls, "expected_behavior_matched": matched,
        "elapsed_seconds": elapsed,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved report: {path}")
    return matched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[*TASKS, "all"], default="normal")
    parser.add_argument("--max-steps", type=int, default=4)
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "experiment_agent/tools/run_python_script.schema.json").read_text(encoding="utf-8"))
    descriptions = [{"type": "function", "function": {
        "name": "run_python_script",
        "description": "实际运行一个固定允许的教学脚本。normal 正常计算；error 触发演示异常；timeout 长时间等待。每任务最多调用一次执行函数，脚本超时2秒；结果含退出码、stdout、stderr。",
        "parameters": schema,
    }}]
    print("Real local model; only run_python_script is exposed; one execution call per task.", flush=True)
    accepted = True
    for case in TASKS if args.case == "all" else [args.case]:
        if not run_case(root, case, descriptions, args.max_steps):
            accepted = False
    if not accepted:
        raise SystemExit("A case did not match its expected execution and stopping behavior. Inspect its report.")


if __name__ == "__main__":
    main()
