from experiment_agent.tool_policy import decide_tool_result
from experiment_agent.tools.registry import call_tool


def run_agent(task, model, tools, tool_descriptions, max_steps=5):
    """返回包含 status、steps、messages 的字典；详细分支见本课讲义。

    model(messages, tool_descriptions) 每次返回一个动作：
    {"type": "tool_call", "name": "工具名", "arguments": {...}}
    或 {"type": "final", "content": "回答"}。

    消息使用教学格式：assistant.content 是动作字典，tool.content 是结果字典。
    这不是 Ollama HTTP 原生消息格式。
    """
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    # 初始化
    messages = [{"role": "user", "content": task}]
    corrections_used = 0

    for step in range(1, max_steps + 1):
        # 请求并保存动作
        action = model(messages, tool_descriptions)
        messages.append({
            "role": "assistant",
            "content": action,
        })

        # 先检查外层类型，避免对 None、列表等调用 get。
        if not isinstance(action, dict):
            return {
                "status": "failed",
                "error_type": "invalid_model_response",
                "steps": step,
                "messages": messages,
            }

        # and 从左到右短路：确认正文是字符串后，才调用 strip。
        if (
            action.get("type") == "final"
            and isinstance(action.get("content"), str)
            and action["content"].strip()
        ):
            return {
                "status": "completed",
                "answer": action["content"],
                "steps": step,
                "messages": messages,
            }

        # 校验请求结构；具体参数是否合法，仍交给 call_tool 判断。
        valid_tool_call = (
            action.get("type") == "tool_call"
            and isinstance(action.get("name"), str)
            and bool(action["name"].strip())
            and "arguments" in action
        )
        if not valid_tool_call:
            return {
                "status": "failed",
                "error_type": "invalid_model_response",
                "steps": step,
                "messages": messages,
            }

        name = action["name"]
        arguments = action["arguments"]

        # 执行并保存工具结果
        result = call_tool(tools, name, arguments)
        messages.append({
            "role": "tool",
            "name": name,
            "content": result,
        })

        # 策略判断：继续、修正或停止
        decision = decide_tool_result(result, corrections_used)
        if decision["action"] == "correct":
            corrections_used += 1
            continue
        elif decision["action"] == "continue":
            continue
        else:
            return {
                "status": "failed",
                "error_type": "tool_policy_stopped",
                "tool_error_type": result.get("error_type"),
                "stop_reason": decision["reason"],
                "steps": step,
                "messages": messages,
            }

    # 循环外：返回 max_steps_exceeded
    return {
        "status": "failed",
        "error_type": "max_steps_exceeded",
        "steps": max_steps,
        "messages": messages,
    }
