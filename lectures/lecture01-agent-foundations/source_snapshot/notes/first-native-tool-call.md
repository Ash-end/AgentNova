# 真实模型首次原生工具请求

日期：2026-10-21。前置：学习者已经独立完成一次本地真实聊天。

## 本次变更与请求

AI 新增 labs/l09_first_tool_call.py，保留 qwen3.5:9b-q4_K_M，通过 Ollama 原生 tools/function 包装发送已有参数 Schema。使用 stream=False、think=False、keep_alive=10m、num_predict=256，socket timeout=180 秒。

只要求读取 labs/fixtures/hello.txt，没有将该文件内容提供给模型。脚本只观察请求，未调用 call_tool 或文件读取函数。

## 实测

```bat
python -X utf8 -m labs.l09_first_tool_call
```

AI 实际收到 message.content="" 和一条 message.tool_calls，function.name=read_text_file，function.arguments={"relative_path":"labs/fixtures/hello.txt"}，附带服务生成的调用 id。done=True、done_reason=stop。

AI 首次实际耗时 67.555 秒，其中加载 47.600 秒、输入处理 18.729 秒、生成 1.207 秒；生成 32 token。

学习者随后独立运行成功，并贴出完整输出：一条正确的 read_text_file 请求，content 为空、done=True / stop，工具执行数为零。耗时 74.809 秒，其中加载 54.770 秒、输入处理 18.826 秒、生成 1.204 秒。当前 reports/l09_first_tool_call.json 对应学习者这次运行，后续演示从这条已保存的请求接续。

这验证该模型在这一条简单明确请求上能产生正确原生工具调用，不代表任意工具任务均可靠，也不等于文件读取已经完成。

本次为标准库教学示范与实际 API 调用，未改动已测试的运行时、校验器和文件工具，没有重复不相关的 20 项测试。学习者已独立复跑；请求/执行区别的独立解释待验证。
