# 第 22 次动手：真实模型选择脚本，策略控制继续或停止

日期：2026-10-22。前置：学习者独立运行三个真实子进程案例和 12 项工具测试，正确解释 stderr 可以是诊断信息，正常结束的退出码才是工具 status 的判断依据。

## 本次分工

```text
用户任务 + 三个脚本 ID 的说明
  → 模型提出 run_python_script(script_id=...)
  → Python 校验参数与调用次数，启动固定脚本
  → 保存 role=tool 的真实执行结果
  → Python 策略判断
      success：continue → 下一次模型请求 → 模型根据结果总结
      非零退出或超时：stop → 返回失败与原因，不再请求模型
```

模型负责选择脚本并在成功后总结。必须停止的执行错误由程序策略保证，不依赖模型是否愿意停止。失败结果保存在 messages 中，但 stop 后没有下一次 chat，因此失败结果本轮没有再次发送给模型；终端显示的失败原因是 Python 打印，不是模型看完失败后生成的回复。

## 新入口，不改变原只读入口

入口 labs/l18_real_script_agent.py 显式启用执行能力，再仅把 run_python_script 放进本轮工具表和工具说明。l14 默认仍提供原来的两个只读工具，不能把 l18 的能力范围理解为所有入口都能执行脚本。

```python
registered = build_tool_registry(str(root), enable_python_scripts=True)
# 本入口另加一次调用上限，再暴露该包装函数。
tools = {"run_python_script": run_once}
result = run_ollama_loop(task, chat, tools, descriptions,
                         max_steps=4, tool_policy=decide_tool_result)
```

Schema 向模型说明 normal/error/timeout 三个 ID，模型自行填写 script_id。Python 中的 EXPECTED_SCRIPT 只在运行后核对，不参与模型参数生成，也不会把错误选择偷偷替换为正确脚本。

## 三个真实模型任务

```bat
conda activate agent-study
python -X utf8 -m labs.l18_real_script_agent --case normal
python -X utf8 -m labs.l18_real_script_agent --case error
python -X utf8 -m labs.l18_real_script_agent --case timeout
```

不带参数默认 normal；--case all 依次运行三个独立会话。每个任务重新设置执行调用预算，不共享上一个案例的消息。

| case | 模型应选择 | 执行结果 | 策略与循环预期 |
| --- | --- | --- | --- |
| normal | normal | success / exit_code=0 | continue，再请求模型总结，completed |
| error | error | failed / process_failed / exit_code=1 | stop / script_process_failed，循环 failed |
| timeout | timeout | failed / tool_timeout / exit_code=null | stop / tool_timeout_needs_review，循环 failed |

工具失败时不再请求模型，所以 error/timeout 通常各只有一次模型请求；若先修正过错误参数，次数可能更多，以实际记录为准。正常案例通常两次：选择执行、根据结果回答。

## 几种限制分别控制什么

| 限制 | 本课设置 | 控制对象 |
| --- | --- | --- |
| max_steps | 4 | 每个任务最多几次模型请求 |
| max_corrections | 默认 1 | 参数校验失败后允许模型修正的次数 |
| execution_calls | 最多 1 | 每个任务最多调用一次固定脚本执行函数 |
| 脚本 timeout | 2 秒 | 子进程等待时限 |
| HTTP timeout | 180 秒 | 单次本地模型 HTTP 请求等待 |

参数结构错误在分发器处拒绝，不消耗执行函数调用机会；第一次结构合法调用进入执行函数后就消耗机会，即使 ID 不被允许或进程没能启动也不补回。额外执行请求返回 execution_limit_exceeded，策略给出 script_execution_budget_exceeded 并停止。此限制是 Python 代码执行的，不只是提示模型“不要重试”。

原有 run_ollama_loop 无需修改。只给策略补充 process_failed、process_start_failed、script_not_allowed、script_not_file 和 execution_limit_exceeded 的明确停止原因；未知错误仍按原默认停止。

## 怎样读输出

正常案例应有：

```text
Loop status: completed
Model decisions: 2
Execution function calls: 1
Policy: continue / tool_succeeded
Final model reply: ...模型根据真实结果给出的总结...
Expected behavior matched: True
```

异常案例应有：

```text
Loop status: failed
Model decisions: 1
Execution function calls: 1
Policy: stop / script_process_failed
No final model reply: loop stopped before requesting another reply.
Expected behavior matched: True
```

这是典型输出示意，不保证每次模型请求次数相同。Expected behavior matched=True 表示实际脚本选择与控制流符合本案例预期；故障演示正确停止也可以 True。它不表示异常脚本执行成功，也不是实验指标评分或最终回答语义验收。

报告分别保存到 reports/l18_real_script_agent_normal.json、_error.json、_timeout.json，包含完整请求、响应、工具结果、tool_decisions、执行函数调用次数与预期行为核对结果。若选错脚本、缺少执行或不符合预期，入口保存报告后非零退出，不自动重跑模型以隐藏失败。

## 连接测试

```bat
python -X utf8 -m unittest discover -s tests -p test_real_script_agent.py -v
```

新增 8 项测试只替换 HTTP 响应，真实执行教学脚本。覆盖成功结果进入下一次请求、异常/超时立即停止、选错允许脚本、修正参数、同批重复执行被阻止、其他工具不可用，以及脚本已成功但模型步数耗尽。

AI 备课检查：tests/ 全部 95 项、exercises/ 12 项通过。真实模型运行记录与学习者验收来源见 notes/real-script-agent-run.md；本课实际模型输出不能用测试中的确定响应替代。

AI 已实际运行三个模型任务，脚本 ID 均选择正确：normal 两次请求、循环 completed；error 与 timeout 各一次请求并由策略停止、循环 failed。三个 Expected behavior matched 均 True，耗时分别约 50.487、0.360、2.331 秒。这些是 AI 观测，不是学习者独立运行证据，也不把不同加载条件下的时长当作性能优化结论。

## 理解检查

error 案例的工具失败结果是否已经发给模型，再由模型决定停止？还是只有消息保存，随后 Python 策略立即结束循环？结合 Model decisions、tool_decisions 和最后的消息角色回答。

## 学习者验收记录

2026-10-22 学习者独立运行三个真实模型任务，选择和预期行为均正确，请求次数 2/1/1；指定 8 项连接测试通过（2.211 秒）。正确解释失败观察先保存，然后策略停止，没有下一次模型调用，因此模型未看到该失败结果。本课运行与理解检查通过，尚不代表独立实现了该入口或已独立执行全部 95 项回归测试。
