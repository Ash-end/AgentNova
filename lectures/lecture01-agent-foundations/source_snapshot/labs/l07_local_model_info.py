"""只读检查本机 Ollama API，不发起模型推理。"""

import json
from urllib.error import URLError
from urllib.request import urlopen


def main():
    base_url = "http://127.0.0.1:11434"
    try:
        with urlopen(base_url + "/api/version", timeout=10) as response:
            version = json.load(response)
        with urlopen(base_url + "/api/tags", timeout=10) as response:
            data = json.load(response)
    except (URLError, TimeoutError) as error:
        raise SystemExit(f"Cannot query local Ollama API: {error}")

    print(f"Local API: {base_url}")
    print(f"Ollama version: {version['version']}")
    print("Installed models:")
    for model in data["models"]:
        print(f"  - {model['name']}")
    print("Metadata queries only; no inference requested.")


if __name__ == "__main__":
    main()
