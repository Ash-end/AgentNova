"""为可信固定脚本分配新目录，执行后只验收该目录内的指标。"""

import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from uuid import uuid4

from experiment_agent.metrics_workflow import run_metrics_file_workflow
from experiment_agent.tools.registry import build_tool_registry
from experiment_agent.tools.script_tools import _output_text


EXPERIMENT_SCRIPT = "labs/fixtures/experiment_scripts/write_metrics.py"
EXPERIMENT_CASES = ("normal", "missing_metrics", "wrong_run_id", "error", "timeout")
TRAINING_SCRIPT = "experiments/linear_regression/train.py"
TRAINING_CASES = ("linear_regression", "linear_regression_slow")


def _execute(script, run_directory, run_id, case, timeout_seconds):
    """仅供可信工作流调用，脚本固定，参数来自本程序，不经 shell。"""
    started = perf_counter()

    def finish(status, *, exit_code=None, stdout="", stderr="", timed_out=False, **details):
        return {
            "status": status, "run_id": run_id, "case": case,
            "exit_code": exit_code, "stdout": _output_text(stdout),
            "stderr": _output_text(stderr), "timed_out": timed_out,
            "duration_seconds": perf_counter() - started, **details,
        }

    command = [
        sys.executable, "-I", "-X", "utf8", "-u", str(script),
        "--run-id", run_id, "--case", case,
    ]
    try:
        completed = subprocess.run(
            command, cwd=run_directory, shell=False, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        return finish(
            "failed", error_type="tool_timeout", exception_type="TimeoutExpired",
            timed_out=True, stdout=error.stdout, stderr=error.stderr,
        )
    except OSError as error:
        return finish("failed", error_type="process_start_failed", message=str(error))

    if completed.returncode != 0:
        return finish(
            "failed", error_type="process_failed", exit_code=completed.returncode,
            stdout=completed.stdout, stderr=completed.stderr,
        )
    return finish("success", exit_code=0, stdout=completed.stdout, stderr=completed.stderr)


def run_experiment_workflow(project_root, case="normal", *, max_mse=0.1, timeout_seconds=2.0):
    """固定教学 workflow；不注册为模型工具，也不接受任意脚本或输出路径。

    新目录隔离 + 成功执行 + 文件内 run_id 一致，关联本次可信教学运行。
    原故障案例使用固定指标；TRAINING_CASES 执行真实小型线性回归。
    运行编号不是防伪证明，此执行器也不是完整沙箱。
    """
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ValueError("timeout_seconds must be a finite positive number")
    if not isinstance(case, str) or case not in EXPERIMENT_CASES + TRAINING_CASES:
        return {"status": "failed", "result": {
            "status": "failed", "error_type": "script_not_allowed",
        }, "trace": []}

    root = Path(project_root).resolve()
    script_path = TRAINING_SCRIPT if case in TRAINING_CASES else EXPERIMENT_SCRIPT
    script = (root / script_path).resolve()
    if not script.is_relative_to(root):
        return {"status": "failed", "result": {
            "status": "failed", "error_type": "path_outside_project",
        }, "trace": []}
    if not script.is_file():
        return {"status": "failed", "result": {
            "status": "failed", "error_type": "file_not_found" if not script.exists() else "script_not_file",
        }, "trace": []}

    run_id = uuid4().hex
    relative_directory = f"runs/{run_id}"
    run_directory = (root / relative_directory).resolve()
    context = {
        "run_id": run_id, "run_directory": relative_directory,
        "metrics_path": f"{relative_directory}/metrics.json",
    }
    trace = []

    def finish(result, **details):
        return {**context, "status": result["status"], "result": result, "trace": trace, **details}

    if not run_directory.is_relative_to(root):
        return finish({"status": "failed", "error_type": "path_outside_project"})
    try:
        # 原子地拒绝复用已存在的叶目录；即使编号碰撞，也不覆盖旧结果。
        run_directory.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        return finish({"status": "failed", "error_type": "run_setup_failed", "message": str(error)})
    trace.append({"step": "prepare_run", "result": {"status": "success", **context}})

    execution = _execute(script, run_directory, run_id, case, timeout_seconds)
    trace.append({"step": "run_python_script", "result": execution})
    if execution["status"] != "success":
        return finish(execution, execution=execution)

    # 读取权限缩小到本次目录，固定文件名，不采用 stdout 建议的其他路径。
    tools = build_tool_registry(str(run_directory))
    checked = run_metrics_file_workflow(
        tools, "metrics.json", max_mse=max_mse, expected_run_id=run_id,
    )
    trace.extend(checked["trace"])
    return finish(checked["result"], execution=execution)
