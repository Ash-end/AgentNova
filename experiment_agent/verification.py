"""根据可信运行时的原生消息记录验收目录发现与文件读取；不执行工具。"""

from collections import deque
import json
from pathlib import PurePosixPath

from exercises.select_text_file import select_unique_text_file


def _relative_path(value):
    """比较项目相对路径，接受 Windows 分隔符和 ./，拒绝越级或绝对路径。"""
    if not isinstance(value, str) or not value.strip() or ":" in value:
        return None
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _tool_events(messages):
    """按现有运行时的串行顺序，将请求与真实 tool 结果配对。"""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    pending = deque()
    events = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError("invalid message")
        role = message.get("role")
        if role == "assistant":
            if pending:
                raise ValueError("tool results missing before next assistant message")
            calls = message.get("tool_calls", [])
            if calls is None:
                calls = []
            if not isinstance(calls, list):
                raise ValueError("invalid tool_calls")
            for call in calls:
                function = call.get("function") if isinstance(call, dict) else None
                if (not isinstance(function, dict)
                        or not isinstance(function.get("name"), str)
                        or not isinstance(function.get("arguments"), dict)):
                    raise ValueError("invalid tool request")
                pending.append(function)
        elif role == "tool":
            if not pending:
                raise ValueError("tool result has no matching request")
            function = pending.popleft()
            if message.get("tool_name") != function["name"]:
                raise ValueError("tool result does not match request order")
            if not isinstance(message.get("content"), str):
                raise ValueError("tool content must be serialized JSON")
            observation = json.loads(message["content"])
            if not isinstance(observation, dict) or observation.get("status") not in ("success", "failed"):
                raise ValueError("tool result must be an object with a known status")
            events.append({"name": function["name"], "arguments": function["arguments"],
                           "result": observation, "message_index": index})
        elif role not in {"system", "user"} or pending:
            raise ValueError("invalid message order")
    if pending:
        raise ValueError("tool request has no execution result")
    return events


def verify_unique_text_read(run_result: dict, expected_directory: str) -> dict:
    """验收完成的运行是否有完整目录观察和正确读取证据；不评价最终回答语义。"""
    def fail(reason, **details):
        return {"status": "failed", "reason": reason, **details}

    expected_directory = _relative_path(expected_directory)
    if expected_directory is None:
        raise ValueError("expected_directory must be a project-relative path")
    if not isinstance(run_result, dict):
        return fail("invalid_execution_trace")
    if run_result.get("status") != "completed":
        return fail("loop_not_completed")
    try:
        events = _tool_events(run_result.get("messages"))
    except ValueError:
        return fail("invalid_execution_trace")

    directories = [e for e in events if e["name"] == "list_directory"
                   and _relative_path(e["arguments"].get("relative_path")) == expected_directory]
    if not directories:
        return fail("missing_directory_evidence")
    reads = [e for e in events if e["name"] == "read_text_file"]
    if not reads:
        return fail("missing_read_evidence")
    before_read = [e for e in directories if e["message_index"] < reads[0]["message_index"]]
    if not before_read:
        return fail("read_before_directory")

    observation = before_read[-1]["result"]
    if observation.get("status") == "success":
        entries = observation.get("entries")
        if (not isinstance(entries, list) or not isinstance(observation.get("truncated"), bool)
                or not all(isinstance(e, dict) and all(isinstance(e.get(k), str)
                           for k in ("name", "type", "relative_path")) for e in entries)):
            return fail("invalid_directory_evidence")
    selection = select_unique_text_file(observation)
    if selection["status"] != "success":
        return fail("directory_selection_failed", selection_error=selection.get("error_type"))
    target = _relative_path(selection["relative_path"])
    if target is None or PurePosixPath(target).parent.as_posix() != expected_directory:
        return fail("invalid_directory_evidence")

    for event in reads:
        actual = _relative_path(event["arguments"].get("relative_path"))
        if actual != target:
            return fail("wrong_file_read", expected_path=target, actual_path=actual)
        if event["result"].get("status") != "success":
            return fail("read_failed", tool_error=event["result"].get("error_type"))
        if not isinstance(event["result"].get("content"), str):
            return fail("missing_file_content")
    return {"status": "passed", "reason": "verified_read", "relative_path": target}
