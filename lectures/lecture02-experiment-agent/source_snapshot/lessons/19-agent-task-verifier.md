# 第 19 次动手：根据执行证据验收 Agent

日期：2026-10-22。前置：学习者独立运行 l15 三个案例，正确解释提前 return 会阻止读取，并指出最终 status 取自 read_result，选择成功不代表读取成功。

## 本次核心区别

completed 是 run_ollama_loop 的结束状态：模型给出了非空最终回答。本次另做一个验收器，判断可信执行记录里是否有本题需要的目录发现和实际读取证据。

```python
run = run_ollama_loop(...)
verification = verify_unique_text_read(run, "data")
```

这两个结果分别保存。验收器不把原 run["status"] 改掉，也不让模型自己决定 passed。

| 结果 | 解释 |
| --- | --- |
| run["status"] == "completed" | 模型循环正常结束 |
| verification["status"] == "passed" | 本题要求的读取执行证据通过检查 |
| completed + failed | 循环结束了，但执行证据不符合本题要求 |

本课先实现并测试这个独立的结束后检查，不修改原生循环本身，也不增加失败后的自动修复。

## 看什么证据

实现位于 experiment_agent/verification.py，入口 verify_unique_text_read(run_result, expected_directory)。目标目录由调用方明确传入，不从模型声称的“目标”中反推。

1. 先检查循环是否 completed。
2. 将 assistant.tool_calls 与随后 role=tool 的 JSON 结果按现有串行执行顺序配对；只有请求没有执行结果，不算证据。
3. 找到目标目录的观察，确认它先于读取；若读前有多次目标目录观察，采用读前最近的一次。
4. 复用学习者的 select_unique_text_file，要求目录成功、完整，且恰好有一个普通 .txt 文件。
5. 核对读取请求里的 relative_path 是否就是候选路径，再检查对应的真实工具结果是否 success、是否含字符串 content。

项目相对路径会统一斜杠和 ./，但不接受绝对路径或 ..。本题按规范化后的路径字符串比较，不推断操作系统特有的大小写或链接别名等价关系。

## 先看两个决定性的分支

```python
if not reads:
    return fail("missing_read_evidence")
```

模型最终文本“我已读取”不会生成一条真实的 read_text_file 工具结果，所以不能绕过这个检查。

```python
if actual != target:
    return fail("wrong_file_read", expected_path=target, actual_path=actual)
```

读取另一个项目内文件可能完全合法、工具也可能 success，但它没有满足本题的目标。因此“工具有权限执行”和“任务做对了”必须分开判断。

工具读取结果 status 不是 success 时，验收返回 read_failed，并保留工具 error_type。即使模型随后说成功，也不能改变已经记录的读取错误。

## 三个稳定案例

```bat
conda activate agent-study
python -X utf8 -m labs.l16_agent_task_verifier
```

本实验用确定性的模型替身返回原生消息，通过已有 run_ollama_loop 和注册表执行真实临时文件工具。三个案例不调用 Ollama，不代表真实模型本次发生这些错误。

临时项目 data/ 下只有 hello.txt；other/other.txt 是另一个可访问但不符合任务目标的文件。

| 案例 | 实际动作 | 循环状态 | 验收 |
| --- | --- | --- | --- |
| correct_completion | 列 data，读取 data/hello.txt，给出正文 | completed | passed / verified_read |
| claimed_without_reading | 列 data 后直接声称已读取 | completed | failed / missing_read_evidence |
| wrong_file_read | 列 data，成功读取 other/other.txt | completed | failed / wrong_file_read |

报告 reports/l16_agent_task_verifier.json 分别保存 run 和 verification，保留原生消息与真实工具结果。临时文件结束后清理；验收器只读记录，不重新执行文件工具，因此临时项目清理后仍能复核这些记录。

```bat
python -X utf8 -m unittest discover -s tests -p test_task_verifier.py -v
```

13 项测试还覆盖目录截断、多候选、读取失败、空正文、请求缺少结果、工具结果配错或孤立、目录不符、先读后列、记录格式错误和循环未完成。部分负面记录由测试明确修改以验证拒绝分支；不是历史真实模型故障报告。

AI 备课实测：三个演示符合上表；验收器 13 项、全部 tests/ 69 项、第 17 课 8 项练习均通过。另将已保存的 l14 discover 真实模型报告送入验收器，结果 passed；这是旧记录复核，没有新增模型推理。学习者独立运行与解释尚待确认。

## 这版验收的边界

本课验的是“完成正确文件的读取”这部分执行证据，尚不评分最终回答是否忠实呈现正文，也不证明之后磁盘内容没有变化。空文本文件的 content="" 是合法读取，不能仅因正文为空而失败。

该函数依赖可信运行时保存的消息，不是日志防篡改或签名系统；不同供应商的并行调用关联格式不在本课支持范围。当前规则保守：记录中出现其他文件读取或读取失败就不通过，后续若加入恢复与重试，需要另外定义验收契约。

复用学习者选择函数保持任务规则一致，但也意味着验收器共享这部分判断代码；它不是另一套完全独立的目录规则实现。当前选择规则有独立行为测试，后续正式评测还需要可信任务标注和冻结的评测集。

## 理解检查

运行后比较：wrong_file_read 中读取工具返回 success，循环也 completed，为什么验收仍然 failed？是哪两个路径不一致？

先解释这一个问题，再把验收显示接到真实模型实验入口。

## 学习者验收记录

2026-10-22 学习者独立运行三个案例，输出全部符合预期；指定 13 项验收器测试通过，耗时 0.011 秒。正确解释第三例读错文件：期望 data/hello.txt，实际 other/other.txt，工具成功不代表满足任务目标。本课运行与理解检查通过；验收器主体由 AI 编写，独立实现尚未验收，真实模型入口的验收显示尚未接入。
