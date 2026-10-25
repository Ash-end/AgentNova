# 第 24 次动手：进程成功与实验指标验收

日期：2026-10-23。状态：学习者在提示后补全函数，AI 代码检查及指定 8 项测试通过；新增数值规则的独立解释与实际文件连接待验收。下文保留原始练习任务。

## 新知识点

此前我们区分了循环 completed 与读取任务 passed。现在把任务验收迁移到代码实验：子进程正常退出，只说明没有通过非零退出码或超时报告失败；实验任务还需要检查实际产物和指标。

例如任务要求：生成 metrics.json，其中 mse 必须是有限的非负数值，且不超过 0.1。

下面是概念示例，不是真实训练测量：

| 例子 | 执行观察 | 产物观察 | 任务判断 |
| --- | --- | --- | --- |
| A | exit_code=0，timed_out=false，工具 success | 文件已读取，JSON 为 {"mse": 0.04} | 指标规则可通过 |
| B | exit_code=0，timed_out=false，工具 success | 预期文件没有生成，只有 stdout 声称已保存 | 缺少产物，不能通过 |
| C | exit_code=0，timed_out=false，工具 success | 文件已读取，JSON 为 {"mse": 1.2} | 数值合法，但未达到阈值 |

三个层级的职责：

1. 执行工具：记录进程退出码、超时和输出。
2. 读取与解析：确认指定产物可读取，且是有效 JSON。
3. 指标验收：确认数据结构、数值合法性及是否达到任务阈值。

本课只实现第 3 层，输入已经是解析后的数据，不新增脚本执行权限，不训练模型。下次再连接实际文件读取与执行记录。单独通过指标函数不能证明文件存在、来自本次运行或确实经过训练；这些证据需要由外层验收补齐。

## 小练习：verify_metrics

编辑 exercises/verify_metrics.py，补全：

```python
verify_metrics(metrics, max_mse=0.1)
```

metrics 是 JSON 解析后的值，可能是字典，也可能是列表、字符串或 None。max_mse 来自可信 Python 调用方，本题假定它是有限非负数值，不从模型回答中取阈值。

| 条件 | 返回值 |
| --- | --- |
| 不是字典，或没有 mse | {"status": "failed", "reason": "invalid_metrics"} |
| mse 不是 int/float，或者是 bool | 同上 |
| mse 是 NaN、正负无穷或负数 | 同上 |
| mse 合法，但大于 max_mse | {"status": "failed", "reason": "mse_above_threshold", "mse": 原值, "max_mse": 阈值} |
| mse 合法，且不大于 max_mse | {"status": "passed", "reason": "verified_metrics", "mse": 原值} |

不修改输入，允许额外字段，不自动把字符串 "0.04" 转成数字。0 和恰好等于阈值的值都应通过。

注意两个 Python 细节：

- bool 是 int 的子类，单用 isinstance(value, (int, float)) 会接受 True 和 False，必须显式排除 bool。
- NaN 不能通过普通大小比较可靠地识别；在类型检查后使用 math.isfinite(value) 检查有限性。本练习使用常规范围的 int/float。

## 第一小步

先判断 metrics 是否为字典，再判断是否存在 mse 字段。只有通过这两项检查，才可以取 metrics["mse"]。先不要写执行脚本或解析 JSON 的代码。

完整实现后运行：

```bat
python -X utf8 -m unittest discover -s exercises -p test_metrics_verifier.py -v
```

共有 8 项测试，包含多个边界子案例。初始骨架的 NotImplementedError 是待实现状态，不计为测试通过。测试只检查上述函数契约，不证明实验已实际运行。

G1 的核心循环由 AI 按请求修复并验收，独立迁移检查仍未完成；本课不把此前 G1 自动标记为通过。
