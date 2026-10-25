# 第 11 次动手：执行工具并回传结果

前置：学习者已独立运行 l09，真实模型返回一条 read_text_file 请求。content 为空，工具执行数为零，说明只完成了提出请求。

本课只补齐这一条请求的后半段，不接入通用循环。

## 一次完整的往返

```text
用户提出任务
  → 模型返回 assistant + tool_calls（l09 已完成）
  → Python 按名称找到函数，校验参数并执行
  → Python 把真实结果记为 tool 消息
  → 模型看到新增消息，生成回答
```

运行：

```bat
conda activate agent-study
python -X utf8 -m labs.l10_tool_result_reply
```

脚本读取已有 reports/l09_first_tool_call.json，所以不需要再运行 l09。每次重跑 l10 都会重新读取文件、重新请求一次模型，文件内容来自本次实际读取，不复用旧的工具结果。

## 看懂三处代码

先保留模型原来的完整响应：

```python
messages = list(saved["request"]["messages"])
messages.append(assistant_message)
```

assistant_message 就是上一步响应里的 message，包含 role、content、tool_calls。即使 content 为空，也不能只把空文本记入历史；模型提出的工具名称与参数需要留在上下文中。

然后通过已经学过的注册表执行：

```python
result = call_tool(tools, name, function["arguments"])
```

name 和 arguments 来自真实模型的请求；项目根目录由本地程序固定。call_tool 继续做名称和参数校验，文件工具继续做路径范围检查。提供 Schema 不会替代这些运行时检查。

最后新增工具消息：

```python
messages.append({
    "role": "tool",
    "tool_name": name,
    "content": json.dumps(result, ensure_ascii=False),
})
```

result 是 Python 字典，json.dumps 将它变成字符串，满足本课 Ollama 工具消息 content 的格式。ensure_ascii=False 让中文保持可读。JSON 输出里出现转义字符是字符串的表示形式，不代表文件被改写。

role=tool 表示这是一条程序执行得到的观察结果；tool_name 指明来自哪个工具。本课按 [Ollama 官方工具调用示例](https://docs.ollama.com/capabilities/tool-calling) 构造消息，保留原生 assistant 消息及其调用字段，不套用旧 mock 循环的内部格式。访问日期：2026-10-21。

## 第二次模型请求有什么变化

仍然调用 /api/chat，仍然提供工具说明；messages 从原来的两条变成四条：system、user、assistant（请求工具）、tool（真实结果）。模型据此生成新的 assistant 响应。

脚本会处理保存响应中的全部工具请求，不假定列表永远只有一个。本次实验预期只有一个读取请求。

观察：

- Executed tool 后的 status 和 content：Python 实际读取的结果。
- Tools executed by this script：本次实际执行数量。
- New tool calls：第二次响应是否还要求调用工具。
- Answer：模型结合工具观察给出的回答。

如果又出现工具请求，本脚本会保存响应并明确停止，不自动继续。这是一次往返演示；后续才把相同过程接进有步数限制的循环。done=True 仍只表示这次生成结束；工具结果和回答内容都需要检查，不能只凭 stop 认定任务正确。

完整记录保存到 reports/l10_tool_result_reply.json，包含执行参数、真实工具结果、第二次请求和响应。

AI 已在 agent-study 实测成功（66.243 秒）。随后学习者独立运行成功（72.302 秒）：执行 1 次读取，工具返回 success；后续响应没有新工具请求，模型正确回答两行文件内容。学习者正确解释了 role=tool 来自工具执行。下一步见 [真实模型自动循环](12-real-agent-loop.md)。

## 理解检查

为什么要先保存 assistant 的工具请求，再追加 role=tool 的执行结果？如果只把工具结果放进一个全新的 messages 列表，会丢失哪些上下文？
