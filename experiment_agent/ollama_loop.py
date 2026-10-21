"""使用 Ollama 原生消息格式的模型—工具循环。"""

import json

from experiment_agent.tools.registry import call_tool


def run_ollama_loop(task, chat, tools, tool_descriptions, max_steps=5, tool_policy=None):
    """chat 返回原生响应；可选 tool_policy 决定工具结果出现后继续、修正或停止。"""
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    messages = [
        {"role": "system", "content": "你是代码实验助手。读取项目文件必须通过提供的工具获得实际内容。"},
        {"role": "user", "content": task},
    ]
    responses = []
    tool_decisions = []
    corrections_used = 0

    def finish(status, steps, **fields):
        return {
            "status": status, "steps": steps, "messages": messages,
            "responses": responses, "tool_decisions": tool_decisions, **fields,
        }

    # 一步是一次模型请求；一条响应里的多个工具调用仍属于这一步。
    for step in range(1, max_steps + 1):
        try:
            response = chat(messages, tool_descriptions)
        except (OSError, json.JSONDecodeError) as error:
            return finish("failed", step, error_type="model_request_failed", message=str(error))
        responses.append(response)

        if not isinstance(response, dict):
            return finish("failed", step, error_type="invalid_model_response")
        if response.get("done") is not True or response.get("done_reason") != "stop":
            return finish("failed", step, error_type="incomplete_model_response")
        message = response.get("message")
        if (
            not isinstance(message, dict)
            or message.get("role") != "assistant"
            or not isinstance(message.get("content", ""), str)
        ):
            return finish("failed", step, error_type="invalid_model_response")
        calls = message.get("tool_calls")
        if calls is None:
            calls = []
        if not isinstance(calls, list):
            return finish("failed", step, error_type="invalid_model_response")
        # 先检查整批调用结构，避免处理到一半才发现后一条结构不完整。
        for call in calls:
            function = call.get("function") if isinstance(call, dict) else None
            if (
                not isinstance(function, dict)
                or not isinstance(function.get("name"), str)
                or "arguments" not in function
            ):
                return finish("failed", step, error_type="invalid_model_response")

        # 保留原生 assistant 消息，包括调用 id、名称和参数。
        messages.append(message)
        if calls:
            for index, call in enumerate(calls):
                function = call["function"]
                result = call_tool(tools, function["name"], function["arguments"])
                messages.append({
                    "role": "tool",
                    "tool_name": function["name"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
                if tool_policy is not None:
                    decision = tool_policy(result, corrections_used)
                    if decision["action"] == "correct":
                        corrections_used += 1
                    tool_decisions.append({
                        "step": step,
                        "tool_name": function["name"],
                        **decision,
                        "corrections_used": corrections_used,
                    })
                    if decision["action"] == "stop":
                        return finish(
                            "failed", step,
                            error_type="tool_policy_stopped",
                            tool_error_type=result.get("error_type"),
                            stop_reason=decision["reason"],
                            pending_tool_calls=len(calls) - index - 1,
                        )
            continue  # 带上真实工具结果，进入下一次模型请求。

        content = message.get("content", "")
        if content.strip():
            return finish("completed", step, answer=content)
        return finish("failed", step, error_type="empty_model_response")

    return finish("failed", max_steps, error_type="max_steps_exceeded")
