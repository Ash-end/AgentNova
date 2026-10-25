# 任务验收器备课运行记录

日期：2026-10-22。下文先记录 AI 备课执行；学习者独立运行与解释单独记在末尾。

实现 experiment_agent/verification.py，新增入口 labs/l16_agent_task_verifier.py。保持原生模型循环和工具实现不变，完成后调用独立验收函数。选择规则复用学习者已通过验收的函数。

本次三个案例使用确定性模型替身，文件工具实际访问自动创建的临时文件；没有模型 API 调用。报告 reports/l16_agent_task_verifier.json 中 run 保存真实运行时产生的消息，verification 保存单独判定。

| 案例 | 循环状态 | 工具执行与验收结果 |
| --- | --- | --- |
| correct_completion | completed | 列目标目录并读取正确文件，passed / verified_read |
| claimed_without_reading | completed | 只有目录调用，没有读取，failed / missing_read_evidence |
| wrong_file_read | completed | 实际成功读取另一文件，failed / wrong_file_read；期望 data/hello.txt，实际 other/other.txt |

新增 13 项验收器测试全部通过；tests/ 全部 69 项通过，第 17 课 8 项练习通过。此处为 AI 测试证据，不写作学习者独立执行。

兼容性复核：将已有 reports/l14_multi_tool_agent_discover.json 的 result 和目标 labs/fixtures 交给验收器，得到 passed / verified_read，路径 labs/fixtures/hello.txt。没有重新请求真实模型，也没有覆盖旧报告。

本版本只检验正确文件读取的执行证据，不评分回答语义；输入须来自可信运行时，暂不涵盖日志防篡改或恢复重试。后续待学习者运行三例并解释为什么工具 success 不等于本题验收通过。

## 学习者独立运行与解释

学习者提供 l16 三个案例的完整终端输出，全部符合上表：循环均 completed，仅正确文件读取通过；另外两例分别为 missing_read_evidence 和 wrong_file_read。同时提供指定验收器测试结果：13 项，0.011 秒，OK。

学习者正确解释第三例失败原因：读取的不是期望文件，expected_path 为 data/hello.txt，actual_path 为 other/other.txt。本项路径证据理解与指定测试独立运行已验收；不将此记录写为学习者独立实现了验收器，或已独立运行全部 69 项回归测试。
