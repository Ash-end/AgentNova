# 第 20 次动手：真实模型入口同时显示循环与验收状态

日期：2026-10-22。前置：学习者独立运行 l16 三个案例及 13 项验收器测试，正确指出目标路径与实际读取路径不同导致验收失败。

## 连接位置

本课直接更新已有 labs/l14_multi_tool_agent.py 的 discover 入口。原 run_ollama_loop 负责与本地 Ollama 交互、执行工具和结束；返回后，Python 再验收记录：

```python
result = run_ollama_loop(...)

if case == "discover":
    verification = verify_unique_text_read(result, "labs/fixtures")
else:
    verification = {"status": "not_applicable", "reason": "discover_only"}
```

验收放在循环结束后。它不向模型发新请求、不重新执行文件工具、不替模型补调用，也不将原来的 result["status"] 改成 passed/failed。

## 运行

```bat
conda activate agent-study
python -X utf8 -m labs.l14_multi_tool_agent --case discover
```

本命令会实际调用本机 Ollama 的 qwen3.5:9b-q4_K_M；每次 HTTP 请求的 socket timeout 仍为 180 秒，最多 5 次模型请求。真实输出以模型实际行为为准，不保证每次相同。

如果模型正常完成且证据通过，可看到：

```text
Loop status: completed
Task verification: passed
Verification reason: verified_read
Verified path: labs/fixtures/hello.txt
```

如果模型直接声称读取却没有实际读取，则可能是：

```text
Loop status: completed
Task verification: failed
Verification reason: missing_read_evidence
```

后一种情况下，原循环仍然是 completed，但实验入口不接受本题结果，保存报告后以非零退出码结束。失败不会自动启动重试。

## 报告里的两个结果

reports/l14_multi_tool_agent_discover.json 同时保存：

```json
{
  "result": {"status": "completed", "messages": []},
  "verification": {
    "status": "passed",
    "reason": "verified_read",
    "relative_path": "labs/fixtures/hello.txt"
  }
}
```

这是字段示意，省略了实际消息内容；真正报告保留全部请求、响应和工具结果。`result.status` 是循环状态，`verification.status` 是独立验收状态。

旧的 expected_sequence_matched 仍显示工具名称序列是否恰好等于 list_directory → read_text_file，但对于 discover 它只是诊断信息。模型多做一次合理的目录查看可能使序列不相等，却仍满足读取证据规则；反之名称序列相等也可能读取错文件。因此 discover 的最终接受条件改为循环 completed 且验收 passed。

## 验收器适用范围

本验收器要求先发现目录再读取目标，不适用于只列目录的 list 或直接读取指定文件的 read。这两个模式显示 not_applicable / discover_only，仍使用原有循环结束与简单序列检查；不能把 not_applicable 当作已通过任务级验收。

当前检查的是“完整目录中有唯一普通 .txt，并成功读取”的执行证据。无候选或多候选时正确停止、最终回答是否忠实于正文等其他任务结果，尚未定义通过规则；不能据此声称完整语义评分已经完成。

## 连接验收测试

```bat
python -X utf8 -m unittest discover -s tests -p test_real_entry_verification.py -v
```

6 项测试使用确定 HTTP 响应和真实临时文件，覆盖通过、没读取、读错文件、非适用任务、步数耗尽，以及多一次目录调用但证据合格。它们不请求真实模型。

AI 备课检查：新增 6 项通过，项目 tests/ 全部 75 项及选择练习 8 项通过。真实模型运行结果及来源记录见 notes/real-entry-verification-run.md。学习者尚未提供本课独立输出。

AI 已实际运行 discover：3 次模型请求，依次列目录和读取文件，正确返回两行正文；Loop status=completed、Task verification=passed、reason=verified_read，路径 labs/fixtures/hello.txt，循环耗时约 15.592 秒。该数值不是学习者独立测量；不与昨日不同运行条件直接比较性能。

## 理解检查

真实运行后，报告中 result["status"] 和 verification["status"] 分别回答什么问题？如果一个是 completed、另一个是 failed，能否把本题记作读取验收通过？

## 学习者验收记录

2026-10-22 学习者独立运行真实 discover 任务，3 次模型请求、两次实际工具调用，总耗时 4.993 秒，循环 completed 且验收 passed，目标路径和正文正确。正确解释前者说明循环正常结束、后者说明实际读取证据通过。本课运行与状态区分通过，尚不代表独立实现验收器或已独立运行全部 75 项测试。
