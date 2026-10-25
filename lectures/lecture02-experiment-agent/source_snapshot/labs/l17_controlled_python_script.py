"""通过明确启用的工具表运行正常、异常、超时三个真实子进程。"""

import json
from pathlib import Path
import sys

from experiment_agent.tools.registry import build_tool_registry, call_tool
from experiment_agent.tools.script_tools import DEFAULT_TIMEOUT_SECONDS


def main():
    root = Path(__file__).resolve().parents[1]
    tools = build_tool_registry(str(root), enable_python_scripts=True)
    print(f"Python: {sys.executable}")
    print(f"Fixed script timeout: {DEFAULT_TIMEOUT_SECONDS}s")
    print("Real child processes; no model API called. Only three allowlisted scripts can run.")
    reports = []
    for script_id in ("normal", "error", "timeout"):
        print(f"\nCase: {script_id}", flush=True)
        result = call_tool(tools, "run_python_script", {"script_id": script_id})
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        reports.append({"case": script_id, "result": result})
    path = root / "reports/l17_controlled_python_script.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {path}")


if __name__ == "__main__":
    main()
