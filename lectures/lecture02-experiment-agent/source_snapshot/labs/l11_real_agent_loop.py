"""从用户任务出发，自动完成真实模型的工具调用循环。"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tools.registry import build_tool_registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")

    root = Path(__file__).resolve().parents[1]
    parameters = json.loads((root / "experiment_agent/tools/read_text_file.schema.json").read_text(encoding="utf-8"))
    descriptions = [{"type": "function", "function": {
        "name": "read_text_file",
        "description": "读取项目内指定 UTF-8 文本文件，用于查看代码、配置或日志。",
        "parameters": parameters,
    }}]
    requests = []
    seen_messages = 0

    def chat(messages, tool_descriptions):
        nonlocal seen_messages
        for message in messages[seen_messages:]:
            if message["role"] == "tool":
                print(f"\nTool result [{message['tool_name']}]:", flush=True)
                print(message["content"], flush=True)
        seen_messages = len(messages)
        payload = {
            "model": "qwen3.5:9b-q4_K_M",
            "messages": messages,
            "tools": tool_descriptions,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_predict": 256},
        }
        # 消息历史后续会继续追加，保存快照才能准确记录每次实际请求。
        requests.append(json.loads(json.dumps(payload, ensure_ascii=False)))
        print(f"\nStep {len(requests)}/{args.max_steps}: requesting model (socket timeout: 180s)...", flush=True)
        request = Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = perf_counter()
        with urlopen(request, timeout=180) as response:
            data = json.load(response)
        print(f"Model response ({perf_counter() - started:.3f}s):", flush=True)
        print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
        return data

    print(f"Python project root: {root}", flush=True)
    print("Starting a new task; no l09/l10 report is loaded.", flush=True)
    started = perf_counter()
    result = run_ollama_loop(
        task="请调用 read_text_file 读取 labs/fixtures/hello.txt 的真实内容。",
        chat=chat,
        tools=build_tool_registry(str(root)),
        tool_descriptions=descriptions,
        max_steps=args.max_steps,
    )
    elapsed = perf_counter() - started
    # 步数耗尽时可能没有下一次 chat，仍要显示最后执行的工具结果。
    for message in result["messages"][seen_messages:]:
        if message["role"] == "tool":
            print(f"\nTool result [{message['tool_name']}]: {message['content']}")
    tool_count = sum(m["role"] == "tool" for m in result["messages"])
    print(f"\nLoop status: {result['status']}")
    print(f"Model decisions: {result['steps']}")
    print(f"Tools executed: {tool_count}")
    print(f"Final response: {result.get('answer', '')}")
    if result["status"] != "completed":
        print(f"Error: {result['error_type']}")
        if "message" in result:
            print(result["message"])
    print(f"Elapsed seconds: {elapsed:.3f}")
    report_path = root / "reports" / f"l11_real_agent_loop_steps{args.max_steps}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({
        "requests": requests,
        "result": result,
        "elapsed_seconds": elapsed,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved report: {report_path}")
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
