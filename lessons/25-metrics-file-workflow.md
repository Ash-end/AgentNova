# 第 25 次动手：读取真实指标文件并验收

日期：2026-10-23。学习者自己的 verify_metrics 保持不变，AI 新增连接流程；学习者已独立运行五例、指定 8 项测试通过，并正确解释解析失败后的提前返回。独立实现尚未验收。

## 数据流

```text
相对文件路径
  → call_tool 调用 read_text_file
  → 成功时取得 UTF-8 字符串
  → json.loads 转成 Python 数据
  → verify_metrics 检查结构、数值和阈值
  → passed / failed
```

连接函数位于 experiment_agent/metrics_workflow.py：

```python
run_metrics_file_workflow(tools, relative_path, max_mse=0.1)
```

max_mse 是可信调用方设置的任务要求，不由指标文件改变。流程复用原注册表和路径边界，未添加执行能力。

## 第一步：读文件

```python
read_result = call_tool(tools, "read_text_file", {"relative_path": relative_path})
```

读取失败时，立即返回 failed，最后 result 保留原工具错误，不解析 JSON、不验收指标。缺失文件是 file_not_found；非法编码由分发器转换为 invalid_encoding。

## 第二步：把字符串解析成数据

```python
try:
    metrics = json.loads(read_result["content"])
except json.JSONDecodeError as error:
    # 记录 invalid_json 和行列位置，返回失败。
```

read_result["content"] 是文件正文字符串；metrics 才是解析后的 Python 数据。json.loads 接收字符串，json.load 接收已打开的文件对象；这里正文已经由受控工具读出，因此用 loads。

JSON 语法错误与指标不合法分别处理：

- `{"mse": 0.04,}` 尾逗号导致 JSONDecodeError，流程在解析阶段停止。
- `{"mse": "0.04"}` 是可解析的 JSON，但 mse 是字符串，指标验收返回 invalid_metrics。
- `[]`、null 等也可以被解析，随后仍要检查是否满足指标结构。

## 第三步：调用学习者的验收函数

```python
verification = verify_metrics(metrics, max_mse=max_mse)
```

最终流程状态取自 verification["status"]，不能取自读取结果。读取与解析都成功，指标仍可能因为超过阈值而 failed。

trace 保存实际执行过的阶段：

| 情况 | 最后结果 | trace 阶段 |
| --- | --- | --- |
| 合法且达标 | passed / verified_metrics | read_text_file → parse_json → verify_metrics |
| 文件缺失 | failed / file_not_found | read_text_file |
| JSON 语法错误 | failed / invalid_json | read_text_file → parse_json |
| 指标类型错误 | failed / invalid_metrics | 全部三阶段 |
| 指标超阈值 | failed / mse_above_threshold | 全部三阶段 |

工具和解析阶段使用 success/failed，指标及整个验收流程使用 passed/failed。没有模型参与，所以没有 Loop status；这是固定 workflow。

## 在 Anaconda 中运行

```bat
cd /d E:\study\agent
conda activate agent-study
python -X utf8 -m labs.l19_metrics_file_workflow
python -X utf8 -m unittest discover -s tests -p test_metrics_file_workflow.py -v
```

演示创建真实临时文件并清理，包含上表五例。数据是人工构造的教学样例，不是真实训练结果。报告保存到 reports/l19_metrics_file_workflow.json；临时项目绝对路径中的本机信息替换为 <demo_project>。

8 项连接测试还覆盖越界、非法 UTF-8、可信阈值传递及非对象 JSON。此流程只证明指定文件当前可读取且指标满足规则，尚不证明文件来自本次运行、数值由实际训练计算，或完成了训练任务。之后再加入执行与产物来源关联。

## 本次理解检查

invalid_json 案例里，读取已经 success。为什么流程仍然 failed，而且 trace 里没有 verify_metrics？观察提前 return 的位置，再独立解释。
