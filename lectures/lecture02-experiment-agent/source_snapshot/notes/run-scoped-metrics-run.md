# 本次运行的脚本与指标关联：备课运行记录

日期：2026-10-23。来源：AI 实现与实测；学习者独立运行及解释待验收。

用户要求把脚本执行与指标验收串起来，并确保不读取旧结果。AI 新增固定可信执行 workflow，分配全新 runs/<run_id>/ 目录，使用当前 Python 运行固定脚本，以该目录为 cwd；只有进程成功才读取该目录内的 metrics.json，解析后检查 run_id，一致才调用学习者原指标函数。

metrics_workflow.py 增加可选 expected_run_id。省略时保留 l19 的原有三阶段；传入时新增 check_run_id。未修改学习者 verify_metrics，未修改原脚本工具、注册表及模型参数说明，也未将新执行器提供给模型。新目录拒绝复用，原有结果不删除；runs/ 已加入 Git 忽略。

## 五例真实子进程与文件结果

使用 E:/Anaconda3/envs/agent-study/python.exe 执行 `python -X utf8 -m labs.l20_run_scoped_metrics`，默认每例超时 2 秒。

| 案例 | 执行状态 | 流程结果 |
| --- | --- | --- |
| normal | success / 0 | passed / verified_metrics |
| missing_metrics | success / 0 | failed / file_not_found；上一例文件仍存在，本次文件不存在 |
| wrong_run_id | success / 0 | failed / run_id_mismatch；没有调用 verify_metrics |
| error | failed / 1 | failed / process_failed；已写文件也不读取 |
| timeout | failed / null，timed_out=true | failed / tool_timeout；已写文件也不读取 |

各例 expected_behavior_matched 均为 True。正常、缺失、编号错误、异常进程耗时约 0.052、0.049、0.054、0.054 秒；超时约 2.022 秒。示例指标固定为 mse=0.04，不是训练测量。

报告保存至 reports/l20_run_scoped_metrics.json，项目根路径替换为 <demo_project>，保留运行编号和项目相对产物路径用于复盘。实际生成物保留在 runs/。

## 测试与保证范围

新增 12 项测试覆盖真实进程的解释器/cwd、两次运行隔离、旧文件不可替代本次输出、编号错误、失败与超时后禁止读取、阈值传递、非法 case、目录碰撞、脚本范围、超时配置及注入的启动失败。AI 全量 tests/ 115 项通过（5.521 秒），exercises/ 28 项通过（0.021 秒）。旧 l19 的 8 项连接测试保持兼容。

来源关联依赖固定可信脚本和运行目录未被外部并发篡改；不以 mtime 或 stdout 作为来源证明。run_id 不是防伪签名，也不证明实际训练。尚未提供恶意代码沙箱、进程树资源隔离或训练计算；本轮没有请求模型、上传 GitHub，也不据此标记 G1 独立迁移通过。

## 2026-10-25 学习者运行

学习者提供 l20 五例完整输出，明确打印解释器 E:/Anaconda3/envs/agent-study/python.exe；各例预期行为均为 True。normal 通过；missing_metrics 中旧文件存在、本次文件不存在，读取本次目录时返回 file_not_found；错误编号拒绝；异常和超时不读取产物。指定 12 项测试通过，0.842 秒。未提供全部 115 项回归或 28 项练习的本次独立运行输出，不扩大验收范围。

学习者询问是否因为 Workflow status=failed 才找不到指标。当前需澄清因果：父进程固定读取本次新目录，本次脚本未生成目标文件，因此读取返回 file_not_found，外层流程再汇总为 failed；旧轮文件存在不满足本次路径。运行验证通过，来源关联及原因/结果关系的修正后独立复述仍待检查。本次仅核对提供的运行记录，没有新增执行或模型调用。

补充理解检查：学习者随后正确复述“本次目录里没有生成指标文件，才导致流程失败”。该因果理解通过；运行器独立实现及目录绑定机制的完整独立复述仍未单独验收。用户随后授权进入真实线性回归训练，见 notes/linear-regression-training-run.md。
