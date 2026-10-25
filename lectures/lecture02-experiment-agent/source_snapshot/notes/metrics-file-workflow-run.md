# 真实指标文件读取流程记录

日期：2026-10-23。来源：AI 备课与运行；学习者随后提供五例和指定 8 项测试输出，并通过本课控制流理解检查。

用户要求将自己的 verify_metrics 接入真实指标文件读取流程。AI 新增 experiment_agent/metrics_workflow.py，依次使用 call_tool 的 read_text_file、json.loads 和学习者函数。原指标函数与工具注册表未修改，不新增执行能力。

## 实测五例

使用 E:/Anaconda3/envs/agent-study/python.exe 执行 `python -X utf8 -m labs.l19_metrics_file_workflow`。全部使用真实临时文件；数值由教学代码构造，不是训练测量。

| 案例 | 结果 | 执行阶段 |
| --- | --- | --- |
| valid_metrics | passed / verified_metrics | 读取、解析、指标验收 |
| missing_file | failed / file_not_found | 只读取 |
| invalid_json | failed / invalid_json，第 1 行第 14 列 | 读取成功，解析失败 |
| invalid_metric_type | failed / invalid_metrics | 读取和解析成功，指标类型错误 |
| above_threshold | failed / mse_above_threshold | 读取和解析成功，指标超过要求 |

五例 expected_behavior_matched 均为 True，报告保存到 reports/l19_metrics_file_workflow.json。报告中的临时项目根目录替换为 <demo_project>，不保留其中的本机用户名。原工具观察在流程执行时未改写，仅演示输出与报告进行脱敏。

## 测试与边界

新增 tests/test_metrics_file_workflow.py 8 项，包括实际 UTF-8 文件、各阶段提前返回、错误类型、路径边界、非法编码、阈值传递与非对象 JSON。AI 运行 tests/ 全部 103 项通过，4.741 秒；exercises/ 全部 28 项通过，0.021 秒。未修改学习者函数及原测试。

流程是固定 Python workflow，无模型参与。只证明指定文件当前内容可读且通过指标规则，不证明它来自本次运行或确实经过训练；尚未将脚本执行、运行标识和产物来源连接起来。本轮未请求模型、未训练、未上传 GitHub，也不据此宣称 G1 独立迁移通过。

## 学习者运行与理解检查

学习者独立提供 l19 五例完整终端输出，均与预期一致，expected_behavior_matched 全部为 True；指定 8 项连接测试通过，0.028 秒。没有提供全部 103 项回归或 28 项练习的本次独立运行输出，故不扩大记录范围。

学习者正确解释：读取成功仅代表取得正文；json.loads 抛出 JSONDecodeError 后进入 except，分支中的 return 结束整个函数，后续 verify_metrics 不会执行。因此 invalid_json 的 trace 只有读取和解析阶段。本课运行与此控制流理解通过，连接流程独立实现尚未验收。

本次提示符显示 (base)，未提供 sys.executable，因此不将此次运行标记为已确认使用 agent-study。学习者版本的解析诊断为 Illegal trailing comma before end of object，第 1 行第 13 列；AI 之前为 Expecting property name enclosed in double quotes，第 1 行第 14 列。二者均正确分类为 invalid_json；未凭诊断文案推断具体 Python 版本，也不要求为文案差异重跑已通过的案例。
