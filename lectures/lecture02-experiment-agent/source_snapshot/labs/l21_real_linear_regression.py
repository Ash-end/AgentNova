"""两组固定学习率的真实 CPU 线性回归；复用本次运行产物验收，无模型请求。"""

import json
from pathlib import Path
import sys

from experiment_agent.experiment_workflow import TRAINING_CASES, run_experiment_workflow
from labs.l19_metrics_file_workflow import redact_demo_root


def main():
    root = Path(__file__).resolve().parents[1]
    print(f"Python: {sys.executable}")
    print("Real CPU gradient descent on synthetic data; standard library only; no model API called.")
    print("Same data seeds, initialization, steps and threshold; only learning rate differs.")
    reports = []
    for case in TRAINING_CASES:
        result = run_experiment_workflow(root, case, max_mse=0.1)
        execution = result.get("execution", {})
        parsed = next((event["result"]["data"] for event in result["trace"]
                       if event["step"] == "parse_json" and event["result"]["status"] == "success"), None)
        identity = next((event["result"] for event in result["trace"] if event["step"] == "check_run_id"), None)
        record = {"case": case, **result, "training_metrics": parsed}
        print(f"\nCase: {case}")
        print(f"Run ID: {result.get('run_id')}")
        print(f"Metrics path: {result.get('metrics_path')}")
        print(f"Execution: {execution.get('status')} / exit_code={execution.get('exit_code')}")
        print(f"Run identity: {identity['reason'] if identity else 'not_checked'}")
        if parsed is not None:
            print(f"Learning rate: {parsed['config']['learning_rate']}; steps: {parsed['config']['steps']}")
            print(f"Initial train MSE: {parsed['initial_train_mse']:.8f}")
            print(f"Final train MSE: {parsed['train_mse']:.8f}")
            print(f"Initial validation MSE: {parsed['initial_validation_mse']:.8f}")
            print(f"Mean baseline validation MSE: {parsed['baseline_validation_mse']:.8f}")
            print(f"Final validation MSE (mse): {parsed['mse']:.8f}")
            print(f"Learned model: {parsed['model']}")
            print(f"Training seconds: {parsed['training_seconds']:.6f}")
        print(f"Workflow status: {result['status']}")
        print(f"Reason: {result['result'].get('reason', result['result'].get('error_type'))}")
        reports.append(redact_demo_root(record, root))

    same_conditions = False
    if all(record["training_metrics"] is not None for record in reports):
        first, second = [record["training_metrics"] for record in reports]
        same_conditions = (
            first["data_split_id"] == second["data_split_id"]
            and {k: v for k, v in first["config"].items() if k != "learning_rate"}
            == {k: v for k, v in second["config"].items() if k != "learning_rate"}
        )
    print(f"\nSame data and non-learning-rate configuration: {same_conditions}")
    path = root / "reports" / "l21_real_linear_regression.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"runs": reports, "same_conditions": same_conditions},
                               ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved report: {path}")
    # 指标未达标仍是有效实验；只有执行、来源关联或对照条件出错时命令失败。
    if not same_conditions or any(
        record.get("execution", {}).get("status") != "success"
        or not any(event["step"] == "check_run_id" and event["result"]["status"] == "passed"
                   for event in record["trace"])
        or record["result"].get("reason") not in {"verified_metrics", "mse_above_threshold"}
        for record in reports
    ):
        raise SystemExit("A training execution, run identity, or comparison condition failed. Inspect the report.")


if __name__ == "__main__":
    main()
