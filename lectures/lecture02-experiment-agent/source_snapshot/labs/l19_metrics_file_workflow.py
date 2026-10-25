"""真实 UTF-8 指标文件读取与 JSON 解析演示；数据为人工构造，不运行训练。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from experiment_agent.metrics_workflow import run_metrics_file_workflow
from experiment_agent.tools.registry import build_tool_registry


CASES = {
    "valid_metrics": ('{"mse": 0.04}', "passed", "verified_metrics"),
    "missing_file": (None, "failed", "file_not_found"),
    "invalid_json": ('{"mse": 0.04,}', "failed", "invalid_json"),
    "invalid_metric_type": ('{"mse": "0.04"}', "failed", "invalid_metrics"),
    "above_threshold": ('{"mse": 1.2}', "failed", "mse_above_threshold"),
}


def redact_demo_root(value, root):
    """仅处理演示输出，避免临时目录中的本机用户名进入学习报告。"""
    if isinstance(value, dict):
        return {key: redact_demo_root(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_demo_root(item, root) for item in value]
    if isinstance(value, str):
        return value.replace(str(root), "<demo_project>")
    return value


def main():
    project_root = Path(__file__).resolve().parents[1]
    print("Fixed Python workflow; no model API called; no training executed.")
    print("Real temporary files; metric values are manually constructed examples.")
    reports = []
    matched_all = True
    with TemporaryDirectory(prefix="metrics-file-lesson-") as directory:
        root = Path(directory)
        data = root / "data"
        data.mkdir()
        tools = build_tool_registry(str(root))
        for name, (content, expected_status, expected_reason) in CASES.items():
            relative_path = f"data/{name}.json"
            if content is not None:
                (root / relative_path).write_text(content, encoding="utf-8")
            result = run_metrics_file_workflow(tools, relative_path)
            reason = result["result"].get("reason", result["result"].get("error_type"))
            matched = result["status"] == expected_status and reason == expected_reason
            matched_all = matched_all and matched
            record = redact_demo_root({
                "case": name, "relative_path": relative_path,
                **result, "expected_behavior_matched": matched,
            }, root)
            reports.append(record)
            print(f"\nCase: {name}")
            for event in record["trace"]:
                print(f"Step: {event['step']}")
                print(json.dumps(event["result"], ensure_ascii=False, indent=2))
            print(f"Workflow status: {record['status']}")
            print(f"Reason: {reason}")
            print(f"Expected behavior matched: {matched}")

    path = project_root / "reports" / "l19_metrics_file_workflow.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {path}")
    if not matched_all:
        raise SystemExit("A workflow case did not match its expected result.")


if __name__ == "__main__":
    main()
