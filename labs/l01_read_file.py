"""显示文件存在与不存在时的返回结果。"""

import json
import sys
from pathlib import Path

from experiment_agent.tools.file_tools import read_text_file


def main():
    project_root = Path(__file__).resolve().parents[1]
    print(f"Python: {sys.executable}")
    print(f"Project root: {project_root}")

    cases = [
        ("Case 1: existing file", "labs/fixtures/hello.txt"),
        ("Case 2: missing file", "labs/fixtures/missing.txt"),
    ]
    for label, relative_path in cases:
        print(f"\n{label}")
        result = read_text_file(str(project_root), relative_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
