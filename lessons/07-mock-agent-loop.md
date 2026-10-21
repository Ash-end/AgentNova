# 第 7 次动手：把工具接进反馈循环

## 从上次练习接过来

学习者已独立运行工具 Schema 演示，正确判断 "   a   " 满足长度和非空白约束。补充说明：str.strip 返回新字符串，不会修改原字符串；校验器只判断其结果，不替换实际读取路径。

```python
value = "   a   "
checked = value.strip()
# value 仍是 "   a   "，checked 是 "a"
```

## 这次连接的组成部分

- tool_descriptions：工具名称、用途和参数 Schema。
- model(messages, tool_descriptions)：根据已有消息提出下一步动作。
- run_loop：保存消息，执行工具，把实际结果加入消息，再进行下一次决策。
- tools / call_tool：已有注册表、参数校验和文件工具。

本次 model 是确定性 Python 函数，是教学替身，不是 LLM，不验证真实模型能否理解 Schema、选择工具或修复参数。工具执行和文件结果是真实的。

## 内部教学消息协议

模型替身每轮返回一种动作：

```python
{"type": "tool_call", "name": "read_text_file", "arguments": {...}}
{"type": "final", "content": "最终响应"}
```

运行时将过程记入 messages，使用 user、assistant、tool 三种角色。这里 assistant 表示模型动作，tool 表示程序实际执行的结果。这是内部教学协议，不直接等同任何模型提供方的 API 格式；以后用适配器转换。

## 最核心的循环

下面省略输出检查与步数限制，便于先理解主要数据流：

```python
messages = [{"role": "user", "content": task}]

while True:
    action = model(messages, tool_descriptions)
    messages.append({"role": "assistant", "content": action})

    if action["type"] == "final":
        return action["content"]

    result = call_tool(tools, action["name"], action["arguments"])
    messages.append({"role": "tool", "name": action["name"], "content": result})
```

关键是最后的 append：工具执行结果成为下一次模型调用的输入。工具返回失败不一定终止任务，可以作为下一轮决策的依据。

实际 loop.py 使用有上限的 for 循环，检查动作结构，并区分完成、超过步数和无效模型输出。max_steps 计模型决策次数，不是单纯的工具调用次数。

## 本次实际轨迹

| 模型决策 | 模型替身动作 | 运行时观察 / 处理 |
| --- | --- | --- |
| 1 | 用 path 字段请求读取文件 | 参数校验返回 invalid_arguments |
| 2 | 看到该错误，改用 relative_path | 文件工具读取真实内容并返回 success |
| 3 | 用实际读取内容构造 final | 运行时停止 |

修正参数的分支写在 mock_model 中；运行时没有偷偷改写模型参数。运行时的职责是执行、记录和传回结果。

## 文件与运行

- experiment_agent/loop.py：运行循环。
- labs/l06_mock_agent_loop.py：模型替身和完整演示。
- tests/test_loop.py：反馈、停止与步数限制的测试。

```bat
python -X utf8 -m labs.l06_mock_agent_loop
python -X utf8 -m unittest discover -s tests -v
```

AI 已实测轨迹为六条消息、三次模型决策；全部 20 项测试通过。新增测试包括根据错误观察修正、未知工具错误回传、final 后停止、无限请求被步数上限截断、非法模型输出结束。

completed 只表示循环收到了 final 并正常停止，不保证用户任务真的成功。演示的文件内容有真实工具结果支持；更复杂任务的正确性还需要独立验收。

本次尚未加入真实 API、持久化、费用统计和完整异常恢复。学习者已独立运行演示和 20 项测试，并正确区分模型修正参数与运行时执行。后续能力逐步加入。

## 本轮理解检查

运行后说明：第一次调用失败时，是 run_loop 把 path 自动改成了 relative_path，还是 mock_model 看见观察结果后重新提出了请求？指出对应代码位置。

## 独立小改动：限制模型决策次数

运行时管理的不只是重复次数，还包括消息状态、执行入口、结果回传、输出检查和停止条件。call_tool 负责名称/参数校验，文件工具负责范围和实际读取；运行时把它们连接起来。

打开 labs/l06_mock_agent_loop.py，在 main 调用 run_loop 的位置，将 max_steps=5 改为 max_steps=2。先预测循环会在哪个阶段停止，再运行：

```bat
python -X utf8 -m labs.l06_mock_agent_loop
```

贴出最后三行，并解释 Model decisions 统计的是什么。实验后恢复为 5。只需改演示的参数，无需改已有测试或循环实现；先前测试已有“达到步数上限”的用例。

本练习由学习者动手，当前未替学习者修改，也没有把该配置的预测当作实测。
