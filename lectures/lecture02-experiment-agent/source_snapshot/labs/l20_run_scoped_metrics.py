"""真实子进程 → 本次目录指标 → run_id 核对 → 指标验收；无模型和训练。"""

import json
from pathlib import Path
import sys

from experiment_agent.experiment_workflow import EXPERIMENT_CASES, run_experiment_workflow
from labs.l19_metrics_file_workflow import redact_demo_root


EXPECTED = {
    "normal": ("passed", "verified_metrics"),
    "missing_metrics": ("failed", "file_not_found"),
    "wrong_run_id": ("failed", "run_id_mismatch"),
    "error": ("failed", "process_failed"),
    "timeout": ("failed", "tool_timeout"),
}


def main():
    root = Path(__file__).resolve().parents[1]
    print(f"Python: {sys.executable}")
    print("Real child processes and run-specific files; no model API called; no training executed.")
    print("Metrics are fixed teaching values. Run artifacts remain under runs/ (Git ignored).")
    reports = []
    previous_metrics_path = None
    matched_all = True
    for case in EXPERIMENT_CASES:
        result = run_experiment_workflow(root, case)
        reason = result["result"].get("reason", result["result"].get("error_type"))
        matched = (result["status"], reason) == EXPECTED[case]
        record = {"case": case, **result, "expected_behavior_matched": matched}
        if case == "normal" and result["status"] == "passed":
            previous_metrics_path = result["metrics_path"]
        if case == "missing_metrics":
            old_exists = previous_metrics_path is not None and (root / previous_metrics_path).is_file()
            new_exists = (root / result["metrics_path"]).exists()
            record.update({
                "previous_metrics_path": previous_metrics_path,
                "previous_metrics_exists": old_exists,
                "current_metrics_exists": new_exists,
            })
            matched = matched and old_exists and not new_exists
            record["expected_behavior_matched"] = matched
        matched_all = matched_all and matched
        record = redact_demo_root(record, root)
        reports.append(record)
        print(f"\nCase: {case}")
        print(f"Run ID: {record.get('run_id')}")
        print(f"Expected metrics: {record.get('metrics_path')}")
        if "execution" in record:
            execution = record["execution"]
            print(f"Execution: {execution['status']} / exit_code={execution['exit_code']} / timed_out={execution['timed_out']}")
        for event in record["trace"]:
            print(f"Step: {event['step']}")
            print(json.dumps(event["result"], ensure_ascii=False, indent=2))
        if case == "missing_metrics":
            print(f"Previous metrics exists: {record['previous_metrics_exists']}")
            print(f"Current metrics exists: {record['current_metrics_exists']}")
        print(f"Workflow status: {record['status']}")
        print(f"Reason: {reason}")
        print(f"Expected behavior matched: {matched}")

    path = root / "reports" / "l20_run_scoped_metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {path}")
    if not matched_all:
        raise SystemExit("A run-scoped artifact case did not match its expected result.")


if __name__ == "__main__":
    main()
