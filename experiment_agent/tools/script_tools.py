"""只执行固定名单中的可信教学脚本；这不是任意代码执行沙箱。"""

import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter


ALLOWED_SCRIPTS = {
    "normal": "labs/fixtures/process_scripts/normal.py",
    "error": "labs/fixtures/process_scripts/error.py",
    "timeout": "labs/fixtures/process_scripts/timeout.py",
}
DEFAULT_TIMEOUT_SECONDS = 2.0


def _output_text(value):
    """TimeoutExpired 的捕获输出可能仍是 bytes，统一转成可保存的文本。"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").replace("\r\n", "\n")
    return value


def run_python_script(project_root: str, script_id: str, *, timeout_seconds=DEFAULT_TIMEOUT_SECONDS) -> dict:
    """超时参数由可信 Python 调用方控制，不属于模型可提交的工具参数。"""
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ValueError("timeout_seconds must be a finite positive number")
    started = perf_counter()

    def finish(status, *, exit_code=None, stdout="", stderr="", timed_out=False, **details):
        return {"status": status, "script_id": script_id, "exit_code": exit_code,
                "stdout": _output_text(stdout), "stderr": _output_text(stderr),
                "timed_out": timed_out, "duration_seconds": perf_counter() - started,
                **details}

    if not isinstance(script_id, str) or script_id not in ALLOWED_SCRIPTS:
        return finish("failed", error_type="script_not_allowed")
    root = Path(project_root).resolve()
    script = (root / ALLOWED_SCRIPTS[script_id]).resolve()
    if not script.is_relative_to(root):
        return finish("failed", error_type="path_outside_project")
    if not script.exists():
        return finish("failed", error_type="file_not_found")
    if not script.is_file():
        return finish("failed", error_type="script_not_file")

    command = [sys.executable, "-I", "-X", "utf8", "-u", str(script)]
    try:
        completed = subprocess.run(
            command, cwd=root, shell=False, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        return finish("failed", error_type="tool_timeout", exception_type="TimeoutExpired",
                      timed_out=True, stdout=error.stdout, stderr=error.stderr)
    except OSError as error:
        return finish("failed", error_type="process_start_failed",
                      exception_type=type(error).__name__, message=str(error))

    if completed.returncode != 0:
        return finish("failed", error_type="process_failed", exit_code=completed.returncode,
                      stdout=completed.stdout, stderr=completed.stderr)
    return finish("success", exit_code=completed.returncode,
                  stdout=completed.stdout, stderr=completed.stderr)
