"""通过消息历史连接模型决策和工具执行。"""

from experiment_agent.tools.registry import call_tool


def run_loop(task: str, model, tools: dict, tool_descriptions: list, max_steps: int = 5) -> dict:
    """运行内部教学协议的模型—工具循环。"""
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    messages = [{"role": "user", "content": task}]

    for step in range(1, max_steps + 1):
        action = model(messages, tool_descriptions)
        messages.append({"role": "assistant", "content": action})

        if isinstance(action, dict):
            if action.get("type") == "final" and isinstance(action.get("content"), str):
                return {
                    "status": "completed",
                    "answer": action["content"],
                    "steps": step,
                    "messages": messages,
                }

            if (
                action.get("type") == "tool_call"
                and isinstance(action.get("name"), str)
                and "arguments" in action
            ):
                result = call_tool(tools, action["name"], action["arguments"])
                messages.append({
                    "role": "tool",
                    "name": action["name"],
                    "content": result,
                })
                continue

        return {
            "status": "failed",
            "error_type": "invalid_model_response",
            "steps": step,
            "messages": messages,
        }

    return {
        "status": "failed",
        "error_type": "max_steps_exceeded",
        "steps": max_steps,
        "messages": messages,
    }
