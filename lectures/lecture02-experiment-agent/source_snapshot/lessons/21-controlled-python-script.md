# 第 21 次动手：受控执行 Python 脚本

日期：2026-10-22。前置：学习者已独立跑通真实模型目录发现与读取任务，并正确区分循环 completed 与读取证据 passed。

## 本课目标

实现 run_python_script 工具，运行三个固定、可信的脚本，记录进程退出码、标准输出、标准错误和超时。先完成真实子进程实验，本课不调用模型、不运行训练、不评分实验指标。

实现：experiment_agent/tools/script_tools.py。演示：labs/l17_controlled_python_script.py。

## 工具只能接收 script_id

```python
tools = build_tool_registry(str(root), enable_python_scripts=True)
result = call_tool(tools, "run_python_script", {"script_id": "normal"})
```

允许的 ID 与脚本路径由 Python 固定：

| script_id | 固定脚本 | 行为 |
| --- | --- | --- |
| normal | labs/fixtures/process_scripts/normal.py | 输出计算结果与一条 stderr 诊断，正常结束 |
| error | labs/fixtures/process_scripts/error.py | 先输出一句文本，再触发真实 RuntimeError |
| timeout | labs/fixtures/process_scripts/timeout.py | 刷新启动输出后等待 10 秒，超过工具默认 2 秒时限 |

调用方不能通过工具参数传入路径、命令、解释器、额外参数或时限。Schema 用 enum 描述固定 ID；运行时仍有实际参数校验和名单判断，不能只依赖 Schema。

默认 build_tool_registry(root) 仍只启用原有读取和目录工具。当前 l14 的真实模型没有获得脚本执行能力；本课入口明确启用它，再按预定顺序调用三个脚本。

## 看核心执行代码

```python
command = [sys.executable, "-I", "-X", "utf8", "-u", str(script)]
completed = subprocess.run(
    command,
    cwd=root,
    shell=False,
    stdin=subprocess.DEVNULL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=timeout_seconds,
    check=False,
)
```

- sys.executable 使用启动工具的同一个 Python；在 agent-study 中运行入口，子进程也使用该环境解释器。
- 传递参数列表，shell=False；不把模型字符串当作 shell 命令执行。
- -I 隔离部分 Python 启动路径与配置，-X utf8 指定 Python UTF-8 模式，-u 及时刷新输出；这些选项不是操作系统沙箱。
- cwd 设置子进程工作目录，stdin=DEVNULL 表示不提供交互输入。
- capture_output 分别捕获 stdout 和 stderr；text/encoding 将输出读成文本。errors=replace 避免输出解码失败丢失整份记录，不能声称任意二进制输出都可无损保存。
- check=False 使普通非零退出作为 CompletedProcess 返回，由本工具读取 returncode 并形成结构化失败。

[Python 3.11 subprocess 文档](https://docs.python.org/3.11/library/subprocess.html)

## 四个字段，不能混为一谈

| 字段 | 含义 |
| --- | --- |
| stdout | 子进程标准输出，不保证打印内容正确 |
| stderr | 子进程错误或诊断输出，不保证非空就失败 |
| exit_code | 子进程退出码；正常案例 0，未捕获异常案例 1 |
| status | 本工具按执行结果判断的 success 或 failed，不是模型循环状态或任务验收结果 |

正常脚本故意向 stderr 写一条诊断，但 exit_code=0，所以仍 success。异常脚本在失败前也有 stdout，但 exit_code=1，所以仍 failed / process_failed。不能只看某个输出流是否为空判断成功。

### 子进程里的 RuntimeError 不会直接跳进父工具的 except RuntimeError

异常发生在另一个 Python 进程中。子进程向 stderr 写堆栈并非零退出，父工具得到 CompletedProcess，然后根据 returncode 返回 process_failed。不要把 traceback 字符串当作父进程抛出的异常对象。

### 超时另走异常分支

subprocess.run 超时会抛出 subprocess.TimeoutExpired，由工具转换为 failed / tool_timeout，timed_out=true。这里复用之前工具超时的错误类别，但实际异常类型是 TimeoutExpired，不是内置 TimeoutError。

超时异常没有提供本工具可用的退出码，因此 exit_code 为 Python None，保存到 JSON 后是 null；不编造 1 或 -9。超时异常里的已捕获输出可能是 bytes，所以辅助函数转成 UTF-8 文本，并处理没有输出的 None。

subprocess.run 会终止并等待它启动的直接子进程，再抛出超时异常；进程创建与调度有额外耗时，因此默认 2 秒不是整个工具调用恰好 2.000 秒的保证。[官方超时说明](https://docs.python.org/3.11/library/subprocess.html#subprocess.run)

## 运行三个真实案例

```bat
conda activate agent-study
python -X utf8 -m labs.l17_controlled_python_script
```

| 案例 | status | exit_code | timed_out | 关键观察 |
| --- | --- | --- | --- | --- |
| normal | success | 0 | false | stdout 有计算输出，stderr 有普通诊断 |
| error | failed | 1 | false | process_failed，stderr 含真实 RuntimeError 堆栈 |
| timeout | failed | null | true | tool_timeout，保留“开始等待”，没有“等待结束” |

报告：reports/l17_controlled_python_script.json。后两项 failed 是预期的演示结果，父演示程序正常退出并保存三项记录；不能把父命令的退出码与每个子进程的 exit_code 混用。

```bat
python -X utf8 -m unittest discover -s tests -p test_script_tools.py -v
```

新增 12 项测试包括真实正常/异常/超时、默认不暴露执行能力、拒绝路径或命令片段、拒绝覆盖配置、允许脚本缺失/为目录/越出根目录，以及明确注入的进程创建失败与超时 bytes 输出。

AI 已实测三个子进程，结果符合上表；tests/ 全部 87 项、exercises/ 12 项均通过。学习者独立运行与解释尚待确认。

## 当前控制范围

名单只限制入口，脚本内容仍必须可信。它们用当前用户的操作系统权限运行，并继承普通环境变量；本工具没有阻止脚本访问项目外文件或网络，也没有限制 CPU、内存和输出总量。capture_output 在内存中收集输出，本课仅用于已审查的短输出脚本。

当前三个脚本不创建后代进程；本工具没有实现任意进程树清理或完整沙箱。不要把它改成接收任意模型生成代码的执行器。真正的隔离、资源限制与后代进程控制属于后续课程。

## 本次理解检查

normal 案例的 stderr 明明有内容，为什么 status 仍然 success？error 案例的 stdout 也有内容，为什么 status 仍然 failed？先找出判断依据，再接入模型选择。

## 学习者验收记录

2026-10-22 学习者独立执行三个真实子进程案例，结果均符合预期，指定 12 项工具测试全部通过（2.138 秒）。正确解释 normal 的 stderr 是诊断信息，退出码为 0 且未超时，故工具判定 success。指定运行与该理解检查通过；不将其记为独立实现工具、已独立通过全部 87 项测试或已接入真实模型。
