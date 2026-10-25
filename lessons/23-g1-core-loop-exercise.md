# 第 23 次动手：自己组织 Agent 的核心循环

日期：2026-10-23。当前状态：学习者有提示尝试后，AI 按请求修复实现，8 项验收通过；下文保留原始练习契约。控制流解释及独立迁移检查待完成，G1 尚未正式通过。

前面的工具、策略和真实模型入口已经能运行。这次由你实现核心控制流程，检查是否能把“理解运行结果”迁移到“组织运行过程”。这是 G1 的代码部分；测试通过后还要解释控制流并完成一次小修改，才讨论正式通过 G1。

## 本次写哪里

补全 `exercises/g1_agent_loop.py` 中的 `run_agent`。不要改验收测试，也不要调用 `experiment_agent/loop.py` 或 `ollama_loop.py` 中的完整循环代替实现。先依据下面的契约自己写；卡住时再逐步索取提示。

可以直接复用已学的两个函数：

- `call_tool(tools, name, arguments)`：查工具、验证参数、执行并转换已知异常。
- `decide_tool_result(result, corrections_used)`：返回包含 `action`、`reason` 的策略字典。默认整个任务只允许一次参数修正。

本次不请求 Ollama、不执行子进程。测试用可预测的模型替身及真实临时文件。这样可以把注意力放在循环和消息上，不受推理耗时影响。

## 输入和消息契约

函数签名：

```python
run_agent(task, model, tools, tool_descriptions, max_steps=5)
```

每轮调用 `model(messages, tool_descriptions)`，获得一个动作：

```python
{"type": "tool_call", "name": "read_text_file",
 "arguments": {"relative_path": "data/notes.txt"}}
# 或
{"type": "final", "content": "回答正文"}
```

这里沿用 l06 的教学协议，消息的 `content` 可以直接保存字典；它不是 l11/l18 的 Ollama 原生 HTTP 消息格式。

| 消息来源 | 保存格式 |
| --- | --- |
| 用户 | `{"role": "user", "content": task}` |
| 模型动作 | `{"role": "assistant", "content": action}` |
| 工具结果 | `{"role": "tool", "name": name, "content": result}` |

开始时只有用户消息。每轮先请求模型，再记录本轮动作；即使动作非法，也记录原值后返回诊断。工具结果必须先保存，再执行策略分支。`append` 只保存消息，下一次调用 `model(...)` 时模型才收到更新后的列表。

有效 `final` 必须有非空白字符串 `content`，回答保留原字符串。有效 `tool_call` 必须有非空白字符串 `name` 和 `arguments` 字段；参数内容交给分发器验证。其余动作是 `invalid_model_response`。模型回调自身抛出异常的恢复、本次教学协议以外的原生消息解析，不属于这道练习。

## 返回值契约

所有正常返回的字典都包含 `status`、`steps`、`messages`。`steps` 表示已经请求模型的次数，第一个动作是第 1 步。骨架已提供 `max_steps < 1` 的检查；本题假定调用方提供整数步数。

| 情况 | 必须返回的其他字段 |
| --- | --- |
| 有效 final | `status="completed"`，`answer=回答原文` |
| 非法模型动作 | `status="failed"`，`error_type="invalid_model_response"` |
| 策略要求停止 | `status="failed"`，`error_type="tool_policy_stopped"`，`tool_error_type=result.get("error_type")`，`stop_reason=decision["reason"]` |
| 决策次数耗尽，仍无 final | `status="failed"`，`error_type="max_steps_exceeded"` |

工具成功不等于循环完成，仍需要模型下一次给出 final。达到最后一轮时也要执行该轮请求的工具并保存结果，然后才能报告步数耗尽。

策略的三种动作：

- `continue`：工具成功，进入下一轮。
- `correct`：累计消耗一次修正机会，再进入下一轮；之后工具成功也不能重置这个计数。
- `stop`：立即返回，保留刚保存的工具结果，不再请求模型。

策略停止与步数限制是两种退出原因。即使还有剩余步数，缺失文件等错误也应立即停止。

## 八项验收

1. 模型直接 final：只请求一次，不执行工具。
2. 列目录 → 按观察到的路径读取 → final：后续模型确实收到前面的工具结果。
3. 参数名错误 → 正确参数 → final：允许一次修正。
4. 错误 → 成功 → 再错误：修正预算不因成功而重置。
5. 文件缺失：结果已保存，但策略停止后不再请求模型。
6. 未知工具：停止，不替换成别的已注册工具执行。
7. 两次工具成功但没有 final：决策预算耗尽，最后结果仍保留。
8. 非法动作：记录诊断，不执行工具；包含多个子案例。

在已激活的 Anaconda 环境运行：

```bat
cd /d E:\study\agent
conda activate agent-study
python -X utf8 -m unittest discover -s exercises -p test_g1_agent_loop.py -v
```

初始骨架会因 `NotImplementedError` 报错，这是待实现的练习状态。先不要用是否全绿衡量第一小步；全部补完后，目标是 `Ran 8 tests ... OK`。这些测试位于 `exercises/`，不改变产品回归测试 `tests/` 的范围。

## 第一小步

先写初始化：`messages` 里只放用户任务，`corrections_used` 从 0 开始。再写最多 `max_steps` 次的循环，每轮取得模型动作并保存 assistant 消息。然后考虑 final 分支应该返回什么，为什么这里的 return 会结束整个函数。

先完成这一小段即可继续讨论。工具执行、策略判断和超限退出留待后续逐步补上；不要为了让不完整的中间版本过测试而修改测试。

代码完成后，复述一次“保存观察”和“发送观察”的区别，并在临时案例中说明最后一次工具成功但没有 final 时如何退出。这两项检查尚未发生，不计为已掌握。
