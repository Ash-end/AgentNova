# 第 13 次动手：工具失败后，修正还是停止

前置：学习者已经独立完成真实循环与 29 项测试，并正确说明 append 只是本地保存消息，要等下一轮 chat 才发送给模型。

## 先问三个问题

1. 失败原因是什么？先看 status，再看 error_type 和错误细节。
2. 原样再执行，条件会改变吗？参数名拼错、文件确实不存在时，重复同一请求通常无助于解决问题。
3. 继续是否在本次任务许可和预算内？模型可以建议下一步，运行时负责执行边界和次数上限。

本课任务限定为读取项目内已经指定的文件；不搜索替代文件、不创建数据、不改变权限。策略如下，这是本项目当前的选择，不是所有 Agent 的通用规则：

| 结果 | 动作 | 原因 |
| --- | --- | --- |
| success | continue | 工具成功，继续让模型处理结果 |
| invalid_arguments，尚有修正预算 | correct | 把真实错误发给模型，让它重新提出合法请求 |
| invalid_arguments，修正预算用完 | stop | 避免无限修正循环 |
| file_not_found | stop | 本次任务要求的文件缺失，需要外部补齐输入 |
| path_outside_project | stop | 本次路径超出授权范围 |
| unknown_tool | stop | 本次程序未注册该能力 |
| 未分类的失败 | stop | 尚无证据支持自动重试 |

例如其他任务允许搜索项目目录时，file_not_found 也可以触发受控搜索；本课还没有搜索工具，因此不假定具备这个恢复能力。工具名拼错也可能设计为可修正，本课先采用遇到 unknown_tool 停止的简单规则。

## 区分两种“再试”

参数修正：

```text
path="..." → invalid_arguments
把错误发给模型
模型改成 relative_path="..." → 重新校验并执行
```

这是换了请求内容之后再尝试，不是 Python 自动修补参数，也不是把同一组错误参数重复执行。

临时故障重试：远程服务短暂不可用时，在确认允许重复执行、且预算足够的前提下，可以等待后重试相同请求。需要限制次数、控制等待，避免把压力放大；带写入副作用的操作还需要确认重复执行是否安全。依据：[AWS 关于超时、重试与退避的工程说明](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)，2026-10-21 已访问。

本课代码只实现参数修正与明确停止。当前文件工具没有远程服务调用；模型 HTTP 失败也仍然停止，不新增网络重试或等待逻辑。

## 代码分工

experiment_agent/tool_policy.py 中的 decide_tool_result 是一个普通函数：输入工具结果和已使用的修正次数，返回 action 与 reason。

```python
if error_type == "invalid_arguments":
    if corrections_used < max_corrections:
        return {"action": "correct", "reason": "ask_model_to_fix_arguments"}
    return {"action": "stop", "reason": "correction_limit_exceeded"}
```

注意比较的是 corrections_used < max_corrections。默认最多给一次修正机会，这个预算按整个任务累计，成功后也不会重新补满。一次机会并不保证模型能修正成功，max_steps 也仍然有效。

ollama_loop.py 在保存真实工具结果之后执行策略：

```python
decision = tool_policy(result, corrections_used)
if decision["action"] == "correct":
    corrections_used += 1
if decision["action"] == "stop":
    return finish(...)
```

correct：允许通过原有 continue 进入下一轮模型请求，结果字典原样保留；模型看到其中 invalid_arguments 的说明后再决策。策略函数本身不调用模型或工具。

stop：立刻返回运行时诊断，不再发起模型请求，也不再执行同一批里尚未处理的工具；pending_tool_calls 记录被跳过的数量。这次是终止任务，不是暂停后可直接接续的状态。结果消息已经保存在本地，但不会为了润色解释额外请求模型。

新实验显式传入 tool_policy=decide_tool_result 来启用策略。l11 没有传入策略，仍保留上一课“反馈错误，由模型继续决定，最终受 max_steps 限制”的行为，便于对照；不是所有旧实验自动切换到新规则。

## 运行实验

```bat
python -X utf8 -m labs.l12_tool_failure_policy
python -X utf8 -m unittest discover -s tests -v
```

本课使用预设模型响应来稳定制造错误，不访问真实模型 API；文件读取、参数校验和路径范围检查仍使用真实代码。演示中的修正是我们写好的逻辑，不算再次验证真实模型的纠错能力。

五个案例的预期结果：

| 案例 | 关键动作 | 模型决策数 | 循环状态 |
| --- | --- | --- | --- |
| 错参数后正确修正 | correct → continue → 最终回答 | 3 | completed |
| 文件不存在 | stop | 1 | failed |
| 路径越界 | stop | 1 | failed |
| 工具未注册 | stop | 1 | failed |
| 修正机会后仍给出错参数 | correct → stop | 2 | failed |

这里 failed 是我们按规则结束任务的状态，不代表实验程序有 bug。报告保存为 reports/l12_tool_failure_policy.json，包含真实错误、策略理由与消息历史。新增 6 项测试，连同原有测试共 35 项。

诊断字段区分：

- error_type=tool_policy_stopped：循环为何停止。
- tool_error_type：实际工具失败类型，比如 file_not_found。
- stop_reason：策略解释，比如 required_file_missing 或 correction_limit_exceeded。
- tool_decisions：每次工具结果对应的 action、reason 和已用修正机会数。

本课策略处理的是工具已返回的结构化结果。工具直接抛出异常时，如何转换后再交给策略，见下一课 [工具异常转换](14-tool-exceptions.md)。

## 理解检查

第一次参数错，已给模型一次修正机会。第二次参数仍错，此时 max_steps=5 还有剩余：应该继续，还是停止？你认为应该依据哪个限制判断？
