# 确定性模型替身闭环首次运行

日期：2026-10-21。环境：agent-study，Python 3.11.17。

AI 新增 experiment_agent/loop.py、labs/l06_mock_agent_loop.py 和 tests/test_loop.py。先保存接口桩并实际观察新增五项测试因 NotImplementedError 失败，再实现循环。

本次模型替身是有明确条件分支的 Python 函数。它的参数修正逻辑由人预写，不调用 LLM，不应作为真实模型理解 Schema 或自主推理能力的证据。工具读取和错误结果是真实执行产生的。

实际演示：初始用户消息；第一次模型动作把字段写成 path；工具返回 invalid_arguments；第二次动作改为 relative_path；工具返回文件内容；第三次动作返回 final。共六条消息、三次模型决策，循环状态 completed。

运行命令：

```bat
python -X utf8 -m labs.l06_mock_agent_loop
python -X utf8 -m unittest discover -s tests -v
```

AI 实测全部 20 项通过，耗时 0.038 秒。新增五项验证：最终响应停止、错误观察参与修正、未知工具错误回传、步数上限停止重复调用、非法模型响应返回可诊断状态。保留原文件工具和注册表十五项行为。

completed 仅代表循环协议正常结束，任务是否成功仍依赖工具产物和验收条件。真实模型 API、费用、持久化和更完整故障恢复尚未实现。

学习者随后提供完整独立运行轨迹和 20 项测试全部通过的输出（0.039 秒）。正确回答 mock_model 根据错误结果重新提出请求，并问 run_loop 是否只是执行循环。反馈将补充它还持有消息历史、通过 call_tool 校验执行、记录观察、检查模型响应并控制停止。

学习者随后独立将演示调用的 max_steps 改成 2，贴出五条消息、failed、Model decisions:2、max_steps_exceeded 的实际输出，并正确解释两次工具请求后没有 final 决策。只读检查当前演示参数确为 2。该配置实测由学习者完成，AI 未代改；正常演示前恢复为 5。
