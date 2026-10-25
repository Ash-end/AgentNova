"""文件读取与受控脚本执行任务的工具结果策略。"""


def decide_tool_result(result, corrections_used, max_corrections=1):
    """返回 continue、correct 或 stop；修正预算按整个任务累计。"""
    if not isinstance(result, dict) or result.get("status") not in {"success", "failed"}:
        return {"action": "stop", "reason": "invalid_tool_result"}
    if result["status"] == "success":
        return {"action": "continue", "reason": "tool_succeeded"}

    error_type = result.get("error_type")
    if error_type == "invalid_arguments":
        if corrections_used < max_corrections:
            return {"action": "correct", "reason": "ask_model_to_fix_arguments"}
        return {"action": "stop", "reason": "correction_limit_exceeded"}

    reasons = {
        "file_not_found": "required_file_missing",
        "path_outside_project": "permission_boundary",
        "unknown_tool": "tool_unavailable",
        "permission_denied": "file_access_denied",
        "is_a_directory": "expected_file",
        "not_a_directory": "invalid_parent_directory",
        "invalid_encoding": "utf8_required",
        "tool_timeout": "tool_timeout_needs_review",
        "io_error": "io_failure",
        "script_not_allowed": "script_not_authorized",
        "script_not_file": "expected_script_file",
        "process_failed": "script_process_failed",
        "process_start_failed": "script_start_failed",
        "execution_limit_exceeded": "script_execution_budget_exceeded",
    }
    return {"action": "stop", "reason": reasons.get(error_type, "unclassified_tool_failure")}
