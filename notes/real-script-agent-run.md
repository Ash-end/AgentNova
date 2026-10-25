# 真实模型脚本选择与停止策略备课记录

日期：2026-10-22。先记录 AI 备课实际执行；学习者后续独立运行与解释记在末尾。

新入口 labs/l18_real_script_agent.py 只向模型提供 run_python_script 及三个 ID 的说明。每个任务最多调用一次执行函数，模型请求上限 4 次，保留已有一次参数修正机会。Python 的 EXPECTED_SCRIPT 仅在运行后核对，不替模型填入参数。

原循环不变；策略新增脚本非零退出、启动失败、名单拒绝、非文件和执行次数耗尽的明确停止理由。超时复用原 tool_timeout_needs_review。

## 确定性连接测试

新增 8 项测试替换模型 HTTP 响应，但使用真实临时脚本工具；覆盖正常结果回传、异常停止、超时停止、错误脚本选择、修正参数、同批重复执行上限、其他工具不可用，以及脚本成功后模型步数耗尽。全部 tests/ 95 项、exercises/ 12 项通过。

## 实际本地模型运行

AI 执行 python -X utf8 -m labs.l18_real_script_agent --case all，实际访问本机 Ollama 0.40.6 / qwen3.5:9b-q4_K_M，退出码 0。

| case | 模型实际选择 | 请求次数 | 工具结果与策略 | 循环状态 | 观测耗时 |
| --- | --- | --- | --- | --- | --- |
| normal | normal | 2 | success/0，continue 后模型总结 | completed | 约 50.487 秒 |
| error | error | 1 | process_failed/1，stop / script_process_failed | failed | 约 0.360 秒 |
| timeout | timeout | 1 | tool_timeout/null，stop / tool_timeout_needs_review | failed | 约 2.331 秒 |

每个案例执行函数调用 1 次，Expected behavior matched 均 True。正常子进程约 0.023 秒，异常子进程约 0.024 秒，超时子进程约 2.014 秒；它们与包含模型请求的整轮耗时不是同一指标。首个模型响应记录较长加载，不把后续较短请求解释为代码优化。

失败案例的真实工具结果已追加到运行日志，但 Python 策略随即结束循环，没有再次请求模型，因此没有模型看见失败结果后生成的最终回复。终端的停止原因由程序打印。正常案例则将工具结果送入第二次模型请求，获得实际总结。

报告保存为 reports/l18_real_script_agent_normal.json、_error.json、_timeout.json，包含完整请求、响应、观察与策略决定。Expected behavior matched=True 是故障演示符合预期，不代表异常脚本成功或实验指标通过验收。

尚未给模型任意代码执行能力、没有运行训练、没有独立语义评测。当前只运行可信固定脚本，完整隔离和资源边界沿用第 21 课说明。

## 学习者独立运行与解释

学习者提供 --case all 的完整真实模型终端输出，三个脚本均选择正确，每例执行函数调用 1 次。normal 两次模型请求、continue 后完成总结，循环 completed；error 和 timeout 各一次模型请求，由策略分别按 script_process_failed、tool_timeout_needs_review 停止，循环 failed。三个 Expected behavior matched 均 True。

学习者观测整轮耗时分别为 47.498、0.361、2.348 秒；子进程约 0.025、0.023、2.010 秒，单独记录，不与 AI 数值混用或据此声称优化。另提供本题 8 项连接测试通过结果（2.211 秒），不代表已独立执行全部 95 项回归测试。

学习者正确解释 error 案例：Python 保存工具失败结果后，由策略直接停止，没有再次调用模型，模型尚未看到这次失败结果。本课运行、指定测试和消息保存/发送与策略停止的理解检查通过。实现仍由 AI 编写，独立实现能力尚未据此验收。
