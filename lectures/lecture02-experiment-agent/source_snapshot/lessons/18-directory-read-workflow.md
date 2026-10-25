# 第 18 次动手：将选择函数接到真实读取步骤

日期：2026-10-22。前置：学习者依据提示完成 select_unique_text_file，并自行修正循环缩进；AI 复验 8 项测试通过。

## 本次只学一个连接点

```text
list_directory 的真实结果
  → select_unique_text_file 判断能否确定唯一文件
    → 失败：立即返回，不调用读取
    → 成功：把 selection["relative_path"] 交给 read_text_file
      → 返回真实读取结果，可能成功，也可能失败
```

新入口是 labs/l15_directory_read_workflow.py。它直接导入 exercises/select_text_file.py 中学习者已完成的函数，不复制另一份实现。本课为教学连接实验，尚未将练习函数迁入正式工具模块；原有真实模型循环不变。

## 先看核心代码

```python
directory_result = call_tool(
    tools, "list_directory", {"relative_path": relative_directory},
)
selection = select_unique_text_file(directory_result)

if selection["status"] != "success":
    return ...  # 返回失败和已执行轨迹，下面的读取不会运行

read_result = call_tool(
    tools, "read_text_file", {"relative_path": selection["relative_path"]},
)
```

selection 的路径来自刚获得的目录观察，不从用户任务猜文件名，也不用在这里拼接项目根目录。注册表仍绑定可信根目录，call_tool 仍负责参数校验、已知异常转换；读取工具仍负责解析路径并检查范围。

如果目录工具失败，选择函数会原样传递失败，随后流程提前返回。这里采用固定停止规则，不调用全局 decide_tool_result，也没有参数修正或重试预算；不能将这个教学流程的停止行为与原生 Agent 策略混为一谈。

## 为什么还要检查读取结果

选择成功只说明目录观察完整，且满足唯一普通 .txt 的规则；扩展名不保证文件内容是 UTF-8，也不保证列出后文件仍然存在或权限没变。因此最终 status 取自 read_result，而不是把 selection 的 success 当作读取成功。

返回值包含三个部分：

| 字段 | 用途 |
| --- | --- |
| status | 整个固定流程成功或失败 |
| result | 最后决定结果的原始选择/工具字典，保留 content 或 error_type |
| trace | 实际经历的步骤及各自结果；不是模型消息或模型决策 |

例如读取成功后，正文位于 result["result"]["content"]。最外层 result 是你接收整个流程返回值的变量；里面的 "result" 键保存最后一步结果。

## 运行三个真实案例

```bat
conda activate agent-study
python -X utf8 -m labs.l15_directory_read_workflow
```

| 案例 | 文件来源 | 应观察到的步骤 | 最终结果 |
| --- | --- | --- | --- |
| unique_text_file | 项目 labs/fixtures | 列目录、选择、读取 | success，两行真实正文 |
| multiple_text_files | 自动创建的临时目录，两份 .txt | 列目录、选择 | failed / multiple_text_files，没有读取 |
| invalid_utf8_file | 自动创建的临时目录，真实非法 UTF-8 字节 | 列目录、选择、读取 | failed / invalid_encoding，选择曾成功 |

临时案例结束后自动清理，不修改已有 hello.txt。最后两个 failed 是预期演示结果，不是脚本意外崩溃。报告保存到 reports/l15_directory_read_workflow.json；报告中的三个步骤不代表三次模型请求，本实验没有请求模型。

```bat
python -X utf8 -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s exercises -p test_text_file_selection.py -v
```

新增 6 项连接验收，使用真实临时文件，并观察读取函数是否实际被调用。它们覆盖唯一文件、多个文件、没有文本、真实截断、列目录失败、读取解码失败；不是只检查打印的步骤名称。

AI 备课实测：三个演示符合上表，tests/ 56 项全部通过，第 17 课 8 项也通过。学习者尚未提供本课独立运行结果或解释；原始报告保留为 AI 验证证据。

## 与 l14 真实 Agent 对照

l15 的执行顺序和分支由 Python 预先写好，属于固定 workflow；没有模型参与选择。l14 则是模型根据任务和观察提出下一步工具请求。二者都调用真实工具，但决定下一步动作的位置不同。本课是把学习者函数连接到读取的验证基线，还不是把它塞进模型循环或注册成第三个工具。

## 本次理解检查

运行后解释：multiple_text_files 案例为什么只有两个 trace 步骤？是哪一个 return 让 read_text_file 没有执行？

再观察 invalid_utf8_file：选择成功后为什么整个流程仍然失败？先把这两个问题解释清楚，再进入下一步。

## 学习者运行验收

2026-10-22 学习者独立执行 l15，提供三个案例的完整终端输出，结果均与预期相符；正确解释 selection 失败后的 return 结束整个函数，阻止读取步骤。非法编码案例的独立解释仍待确认。本次输出不包含独立测试运行，不混记为已独立通过 56+8 项测试。

随后学习者正确解释：非法编码时失败来自读取结果，最外层 status 取自 read_result["status"]，选择成功不代表读取成功。该理解检查通过；AI 补充了读取工具抛出异常、call_tool 将其转换为 invalid_encoding 的精确分工。
