"""让真实本地模型提出原生工具调用；本脚本不执行提出的工具。"""

import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "experiment_agent/tools/read_text_file.schema.json"
    parameters = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = {
        "model": "qwen3.5:9b-q4_K_M",
        "messages": [
            {"role": "system", "content": "你是代码实验助手。读取项目文件必须通过提供的工具获得实际内容。"},
            {"role": "user", "content": "请调用 read_text_file 读取 labs/fixtures/hello.txt 的真实内容。"},
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "read_text_file",
                "description": "读取项目内指定 UTF-8 文本文件，用于查看代码、配置或日志。",
                "parameters": parameters,
            },
        }],
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "num_predict": 256},
    }

    print("Request (tool definitions included):", flush=True)
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    print("Waiting for model response (socket timeout: 180s)...", flush=True)
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
        raise SystemExit(f"Local tool-call request failed after {perf_counter() - started:.3f}s: {error}")
    elapsed = perf_counter() - started

    print("\nResponse:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    message = data.get("message", {})
    calls = message.get("tool_calls") or []
    print(f"\nContent: {message.get('content', '')!r}")
    print(f"Tool calls: {len(calls)}")
    for index, call in enumerate(calls, start=1):
        function = call.get("function", {})
        print(f"Call {index} name: {function.get('name')}")
        print(f"Call {index} arguments: {json.dumps(function.get('arguments'), ensure_ascii=False)}")
    print("Tools executed by this script: 0")
    print(f"Elapsed seconds: {elapsed:.3f}")

    report_path = root / "reports/l09_first_tool_call.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"request": payload, "response": data, "elapsed_seconds": elapsed}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved report: {report_path}")
    if not calls:
        raise SystemExit("No native tool_calls returned. Inspect the report before proceeding.")


if __name__ == "__main__":
    main()
