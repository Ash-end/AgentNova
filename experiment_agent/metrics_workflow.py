"""读取项目内指标文件，解析 JSON，再复用学习者的指标验收函数。"""

import json

from exercises.verify_metrics import verify_metrics
from experiment_agent.tools.registry import call_tool


def run_metrics_file_workflow(tools, relative_path, max_mse=0.1, *, expected_run_id=None):
    """固定流程，无模型请求；max_mse 由可信调用方给定。

    返回 status=passed/failed、最后阶段的 result，以及各阶段 trace。
    expected_run_id 可选，由外层运行器提供；只核对标记，不证明实际训练计算。
    """
    read_result = call_tool(tools, "read_text_file", {"relative_path": relative_path})
    trace = [{"step": "read_text_file", "result": read_result}]
    if read_result["status"] != "success":
        return {"status": "failed", "result": read_result, "trace": trace}

    try:
        metrics = json.loads(read_result["content"])
    except json.JSONDecodeError as error:
        parse_result = {
            "status": "failed",
            "error_type": "invalid_json",
            "message": error.msg,
            "line": error.lineno,
            "column": error.colno,
        }
        trace.append({"step": "parse_json", "result": parse_result})
        return {"status": "failed", "result": parse_result, "trace": trace}

    trace.append({"step": "parse_json", "result": {"status": "success", "data": metrics}})
    if expected_run_id is not None:
        actual_run_id = metrics.get("run_id") if isinstance(metrics, dict) else None
        identity = {
            "status": "passed" if actual_run_id == expected_run_id else "failed",
            "reason": "run_id_matched" if actual_run_id == expected_run_id else "run_id_mismatch",
            "expected_run_id": expected_run_id,
            "actual_run_id": actual_run_id,
        }
        trace.append({"step": "check_run_id", "result": identity})
        if identity["status"] != "passed":
            return {"status": "failed", "result": identity, "trace": trace}

    verification = verify_metrics(metrics, max_mse=max_mse)
    trace.append({"step": "verify_metrics", "result": verification})
    return {"status": verification["status"], "result": verification, "trace": trace}
