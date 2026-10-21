# 第 15 次动手：由你完成工具超时分类

预计 10–20 分钟。目标是独立修改两个很小的分支，不需要新增工具、等待超时或调用模型 API。AI 只准备需求与验收测试，没有实现答案。

## 问题

假设工具执行中抛出 TimeoutError。目前它会被现有的 OSError 分支接住，统一归类为 io_error。本次要求将工具超时单独分类，便于记录与后续分析。

本课仍然采用停止策略，不新增自动重试。这里是工具函数抛出的 TimeoutError，不是 chat 请求超时；不修改 Ollama 地址、模型 HTTP timeout 或循环的模型请求异常处理。

## 验收目标

工具抛出 TimeoutError("Simulated tool timeout.") 后，分发器应返回：

```json
{
  "status": "failed",
  "error_type": "tool_timeout",
  "tool_name": "read_text_file",
  "exception_type": "TimeoutError",
  "message": "Simulated tool timeout."
}
```

策略收到 error_type=tool_timeout 时应返回：

```json
{"action": "stop", "reason": "tool_timeout_needs_review"}
```

循环应记录真实工具结果，返回 tool_policy_stopped，保留上述工具错误与停止原因；模型只被请求一次，不继续下一轮。不需要修改循环来实现这些已有行为。

普通 OSError 必须仍然得到 io_error / io_failure，其他已有异常分类也保持有效。

## 你需要修改的地方

1. experiment_agent/tools/registry.py：在 call_tool 的异常分支中添加工具超时的独立分类。可以复用现有 _exception_result，不必手写新的错误字典辅助函数。
2. experiment_agent/tool_policy.py：让 reasons 能识别新错误类别并给出指定停止原因。

只需要少量代码。不要修改验收测试，不需要改 run_ollama_loop 或文件工具。

提示：TimeoutError 属于 OSError 的子类。考虑捕获分支顺序；若放错位置，代码可能不会进入你新写的分支。先自己判断应放在哪里。

## 动手顺序

第一步，先运行本题验收，观察当前结果与目标的差异：

```bat
python -X utf8 -m unittest discover -s exercises -p test_timeout_mapping.py -v
```

练习发布时 AI 检查的基线为：4 项中 3 项失败、1 项通过。失败是因为题目要求的新分类和理由尚未实现，是本题的起点；当时现有功能的 41 项测试仍通过。

练习测试放在 exercises/，以便将待完成练习与现有 tests/ 分开运行。测试工具主动抛出 TimeoutError，不读取 hello.txt、不等待、不访问模型 API。

第二步，完成两个文件的修改，重新运行上述 4 项练习测试，直到全部通过。

第三步，运行已有回归测试：

```bat
python -X utf8 -m unittest discover -s tests -v
```

最终验收是：练习 4 项通过，加上原有 41 项通过。两个命令都需要运行；只运行 tests/ 不会验收这道练习。

## 提交给我检查

贴出你新增的异常分支、策略映射，以及两次测试结果。再用一句话解释：如果把 TimeoutError 的捕获分支写在 OSError 分支之后，会发生什么？

## 本次完成记录

学习者已独立完成两个文件的功能修改，正确解释 TimeoutError 与 OSError 的捕获顺序；AI 读取代码并在 agent-study 中验收：练习 4 项、原有 41 项全部通过。独立修改能力在这一小范围内已验证，下一步可进入第二个工具的设计。
