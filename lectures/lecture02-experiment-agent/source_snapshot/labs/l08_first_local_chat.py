"""通过本机 Ollama API 发起一次真实聊天请求，保存请求与响应。"""

import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    url = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": "qwen3.5:9b-q4_K_M",
        "messages": [{
            "role": "user",
            "content": "请用一句中文解释：什么是大模型的工具调用？",
        }],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 128},
    }

    print(f"POST {url}", flush=True)
    print("Request:", flush=True)
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = perf_counter()
    try:
        with urlopen(request, timeout=60) as response:
            data = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Ollama HTTP {error.code}: {detail}")
    except (URLError, TimeoutError) as error:
        raise SystemExit(f"Cannot complete local chat request: {error}")
    elapsed = perf_counter() - started

    print("\nResponse:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nAnswer: {data.get('message', {}).get('content', '')}")
    print(f"Done: {data.get('done')}")
    print(f"Done reason: {data.get('done_reason')}")
    print(f"Elapsed seconds: {elapsed:.3f}")

    report_path = Path(__file__).resolve().parents[1] / "reports/l08_first_local_chat.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"request": payload, "response": data, "elapsed_seconds": elapsed}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
