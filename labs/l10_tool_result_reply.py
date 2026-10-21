"""执行 l09 保存的工具请求，回传真实结果，再调用一次模型。"""

import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from experiment_agent.tools.registry import build_tool_registry, call_tool


def main():
    root = Path(__file__).resolve().parents[1]
    source_path = root / "reports/l09_first_tool_call.json"
    if not source_path.is_file():
        raise SystemExit("Run python -X utf8 -m labs.l09_first_tool_call first.")
    saved = json.loads(source_path.read_text(encoding="utf-8"))
    assistant_message = saved["response"]["message"]
    calls = assistant_message.get("tool_calls") or []
    if assistant_message.get("role") != "assistant" or not calls:
        raise SystemExit("The saved response must contain assistant tool_calls.")

    # 保留模型提出请求时的完整消息，包括 tool_calls，而不只保留 content。
    messages = list(saved["request"]["messages"])
    messages.append(assistant_message)
    tools = build_tool_registry(str(root))
    executions = []
    for call in calls:
        function = call["function"]
        name = function["name"]
        result = call_tool(tools, name, function["arguments"])
        executions.append({"name": name, "arguments": function["arguments"], "result": result})
        # Ollama 的工具消息 content 是字符串，所以将结果字典编码为 JSON 文本。
        messages.append({
            "role": "tool",
            "tool_name": name,
            "content": json.dumps(result, ensure_ascii=False),
        })
        print(f"Executed tool: {name}", flush=True)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

    payload = {
        **saved["request"],
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
    }
    print("\nMessages sent back to the model:", flush=True)
    print(json.dumps(messages, ensure_ascii=False, indent=2), flush=True)
    print("Waiting for one model response (socket timeout: 180s)...", flush=True)
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=180) as response:
            data = json.load(response)
    except HTTPError as error:
        raise SystemExit(f"Ollama HTTP {error.code}: {error.read().decode('utf-8', errors='replace')}")
    except (URLError, TimeoutError) as error:
        raise SystemExit(f"Tool-result reply failed after {perf_counter() - started:.3f}s: {error}")
    elapsed = perf_counter() - started

    print("\nResponse:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    message = data.get("message", {})
    pending_calls = message.get("tool_calls") or []
    content = message.get("content", "")
    print(f"\nTools executed by this script: {len(executions)}")
    print(f"New tool calls: {len(pending_calls)}")
    print(f"Answer: {content}")
    print(f"Done reason: {data.get('done_reason')}")
    print(f"Elapsed seconds: {elapsed:.3f}")

    report_path = root / "reports/l10_tool_result_reply.json"
    report_path.write_text(
        json.dumps({
            "source_report": str(source_path),
            "executions": executions,
            "request": payload,
            "response": data,
            "elapsed_seconds": elapsed,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved report: {report_path}")
    if pending_calls:
        raise SystemExit("The model requested more tools. This one-response demo stops here; the task is unfinished.")
    if not data.get("done") or data.get("done_reason") != "stop" or not content.strip():
        raise SystemExit("No complete final text received. Inspect the saved response.")


if __name__ == "__main__":
    main()
