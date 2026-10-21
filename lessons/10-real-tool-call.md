# 第 10 次动手：观察真实模型的工具调用请求

## 已确认的前置能力

学习者已独立完成一次真实聊天：收到 message.content、done=True、done_reason=stop；报告显示耗时 51.230 秒，其中模型加载约 31.005 秒。data["message"] 是字典，data["message"]["content"] 是其中的文本。

注意实际版本：本次读取磁盘文件发现 l08_first_local_chat.py 仍是 timeout=60、无 keep_alive 的早期版本。本次因在 60 秒内完成而成功，不能把它记录成 180 秒版本已由学习者验证。原因未确定，本轮不重写这个已完成的练习。新 l09 实验独立使用 180 秒 socket timeout 和 keep_alive=10m。

## 与上次请求相比，多了什么

模型和 /api/chat 地址相同，新增 tools 字段：

```python
"tools": [{
    "type": "function",
    "function": {
        "name": "read_text_file",
        "description": "读取项目内指定 UTF-8 文本文件。",
        "parameters": parameters_schema,
    },
}]
```

parameters_schema 来自已经写好的 read_text_file.schema.json。外层 type/function 是本课采用的 Ollama 原生工具定义包装，里面保留名称、用途和参数说明。

这段 JSON 只描述工具，不把 Python 函数或文件内容传给模型。本次问题明确要求读取指定路径，模型需要提出调用请求。

官方来源：[Ollama 工具调用](https://docs.ollama.com/capabilities/tool-calling)，2026-10-21 已访问。

## 观察工具调用结构

预期在 message 内出现这样的结构；以下是示意，实际内容以运行报告为准：

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [{
    "function": {
      "name": "read_text_file",
      "arguments": {"relative_path": "labs/fixtures/hello.txt"}
    }
  }]
}
```

tool_calls 是列表，因为一轮响应可能提出多个调用。每个调用的 function 包含名称和参数。本课要求单文件读取，也应先观察实际返回数量，后续适配器不能悄悄丢掉多调用。

content 为空并不必然是失败：模型可能正通过 tool_calls 提出下一步操作。判断时要同时查看 content 和 tool_calls。done=True 表示本轮模型生成结束，不表示读取任务已经完成。

## 本次运行

```bat
python -X utf8 -m labs.l09_first_tool_call
```

脚本发送工具说明，打印完整响应和每个调用的名称/参数，保存 reports/l09_first_tool_call.json。脚本不导入文件读取工具，也不调用 call_tool；Tools executed by this script 必须显示 0。

如果模型只回答文字，没有原生 tool_calls，脚本会保存实际响应并明确报告，不能把普通文本里的函数名称当作原生调用成功。

AI 首次实测：返回一条 read_text_file 调用，relative_path 为指定路径，content 为空，耗时 67.555 秒。随后学习者独立运行成功，耗时 74.809 秒；当前报告对应学习者这次运行。两次工具执行数均为零。

## 本轮练习

学习者已贴出实际输出：Content 为空、Tool calls 为 1，名称和参数正确。此时模型只提出了读取请求。下一步见 [执行工具并回传结果](11-tool-result-reply.md)，通过 call_tool 执行后，将真实结果回传给模型。
