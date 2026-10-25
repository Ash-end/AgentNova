# 第 12 次动手：真实模型的自动循环

前置：学习者已独立运行 l10（72.302 秒），实际读取成功、模型给出正确内容且无新工具请求；能解释 tool 消息来自工具执行，而不是用户输入。

## 本次变化

之前需要分别运行 l09、l10，通过报告文件接续。现在运行一个脚本：从新任务出发，每轮自动判断是否执行工具并继续。不读取旧报告，模型的请求和最终回答都来自这次运行。

```bat
conda activate agent-study
python -X utf8 -m labs.l11_real_agent_loop
```

文件分工：

- experiment_agent/ollama_loop.py：保存消息历史、判断响应、执行工具、限制步数。
- labs/l11_real_agent_loop.py：准备任务与工具说明，使用标准库发送 HTTP 请求，打印过程并保存报告。
- experiment_agent/tools/registry.py：继续负责按名称找到函数、校验参数。

l06 的内部教学协议继续保留供对照。原生 Ollama 响应含 message.tool_calls，不直接符合旧 run_loop 使用的 type=tool_call/final 格式，因此本课使用独立的 run_ollama_loop，不强行把两种消息格式混在一起。

## 先读核心流程

以下是便于理解的简化版；实际实现还会检查响应结构、生成是否完整，以及网络错误：

```python
for step in range(1, max_steps + 1):
    response = chat(messages, tool_descriptions)
    message = response["message"]
    messages.append(message)

    calls = message.get("tool_calls") or []
    if calls:
        for call in calls:
            function = call["function"]
            result = call_tool(tools, function["name"], function["arguments"])
            messages.append({
                "role": "tool",
                "tool_name": function["name"],
                "content": json.dumps(result, ensure_ascii=False),
            })
        continue

    if message.get("content", "").strip():
        return completed_result

return step_limit_result
```

chat 是一个函数对象，作用类似之前注册表里的函数对象：循环负责在合适的时机调用它。本实验的 chat 发送真实 HTTP 请求；单元测试用预设 API 响应替代网络，但文件读取仍使用真实工具。

三处控制流程需要理解：

1. messages 在 for 外创建，所以新的一轮能看到之前的请求和工具结果。
2. continue 结束本轮 for，带着已经追加的消息进入下一轮；它不会清空历史。
3. return 直接结束 run_ollama_loop；模型没有新工具请求、有完整非空回答时才返回 completed。

有 tool_calls 时优先执行工具，即使 content 同时含文字也不能提前结束。一条响应中的全部请求处理完后，再发送下一轮模型请求。本课按顺序执行这批工具，没有并发执行工具。

官方消息格式依据：[Ollama 工具调用](https://docs.ollama.com/capabilities/tool-calling)；请求与完成字段依据：[Chat API](https://docs.ollama.com/api/chat)。访问日期：2026-10-21。

## 预测输出

简单读取任务通常需要两次模型决策，但实际次数取决于这次模型的输出：

```text
Step 1：模型提出 read_text_file 请求
        Python 执行，追加 role=tool 的结果
Step 2：模型看到结果并回答

Loop status: completed
Model decisions: 2
Tools executed: 1
```

max_steps 计算模型请求次数，不是工具调用数量。一轮提出两个工具请求，也只消耗一次模型决策。生成最终回答同样消耗一次决策。

报告保存为 reports/l11_real_agent_loop_steps5.json，包含每次请求快照、全部响应和最终消息历史。保存快照是为了避免后续追加 messages 后，报告里的旧请求也跟着变化。

AI 已在本机实际运行：completed，模型决策 2 次、读取 1 次、回答内容正确，总耗时 51.963 秒。max_steps=1 对照也已实测：读取成功后按预期返回 max_steps_exceeded。随后学习者已独立运行成功（0.858 秒）并通过全部 29 项测试，能解释本地保存消息与下一轮发送的区别。

## 停止行为

本课将“模型已给出结束回答”记为 completed；这不等于任务内容已被独立验证正确。查看实际工具结果与回答是否相符。

工具返回 invalid_arguments、unknown_tool、file_not_found 等错误时，错误也会进入消息历史，下一步由模型根据观察决定。循环本身不改写参数、不伪造成功。本课没有专门制定所有错误的重试策略，max_steps 提供最终停止上限。

网络失败会返回 model_request_failed，保留已有历史；不自动重试 HTTP 请求。空回答、格式错误或生成未完整结束都会报告失败，不把它们当成最终答案。180 秒是每次请求的 socket timeout，不是整个循环的总耗时上限。

本课初始版本只提供项目内 UTF-8 文件读取，尚未统一转换目录、编码等工具异常。后续 [工具异常转换](14-tool-exceptions.md) 在分发器增加了具体异常处理；本课仍是最小循环，任务评估等能力另行学习。

## 运行与理解检查

先运行默认实验，再运行：

```bat
python -X utf8 -m unittest discover -s tests -v
```

本轮新增 9 项测试，结合原有 20 项，共 29 项。测试验证真实工具结果进入下一次请求、多调用完整回传、工具错误可被观察、步数上限、空响应、异常格式、截断生成以及网络失败。

先回答：如果从 if calls 分支中删掉 continue，紧接着走到 content 判断，而模型这一轮又同时说了“我先读取文件”，循环会发生什么？

可选对照：

```bat
python -X utf8 -m labs.l11_real_agent_loop --max-steps 1
```

如果第一轮提出工具调用，即使读取成功，也会因没有下一次决策机会而返回 max_steps_exceeded；这是预期结果，进程会以退出码 1 结束。对照报告另存为 reports/l11_real_agent_loop_steps1.json，不覆盖默认实验报告。

下一步：[工具失败的处理策略](13-tool-failure-policy.md)，在总步数之外增加错误分类与参数修正预算。
