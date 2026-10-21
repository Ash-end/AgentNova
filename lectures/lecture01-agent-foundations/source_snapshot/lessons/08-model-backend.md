# 第 8 次动手：选择真实模型接口

## 已完成的循环实验

学习者独立将 max_steps 从 5 改为 2，实际运行得到五条消息，最终为 failed / max_steps_exceeded / 两次决策。正确解释两次工具请求后尚未进行生成 final 的第三次决策。

因此，要区分工具操作完成与运行循环正常结束。读取成功已经有真实结果，但模型尚未输出最终响应。步数上限限制模型决策次数。学习者随后已恢复 max_steps=5，并独立运行本地服务预检。

## 用户提出的两个候选

用户询问能否直接用 Codex，或 E:/AI 中的本地模型。2026-10-21 只读检查结果：

| 项目 | 已观察到的信息 |
| --- | --- |
| Codex CLI | 本机可调用，版本 0.163.0-alpha.11；exec --help 可读，未发起 Codex 模型任务 |
| Ollama 可执行文件 | E:/AI/Ollama/ollama.exe |
| 模型存放位置 | E:/AI/Models/Ollama，启动脚本中设置 OLLAMA_MODELS 指向此处 |
| Ollama 服务 | http://127.0.0.1:11434，元数据接口已返回成功，版本 0.40.6 |
| 已安装模型 | qwen3.5:9b-q4_K_M（列表大小 6.6GB）；qwen3.5:2b（2.7GB） |
| 9B 模型能力声明 | /api/show 返回 completion、vision、tools、thinking；不等于工具调用质量已通过实验 |
| GPU | NVIDIA GeForce RTX 5080，16303 MiB 总显存 |

上述是本机实际查询结果，不是对其他设备或服务版本的保证。查询时 9B 模型已在 GPU 运行，没有下载模型、重启服务或更改 Ollama 配置。

## 为什么建议当前先用本地 Ollama

当前学习目标是掌握自己的模型—工具循环。直接调用 Ollama 聊天接口，可以保留 run_loop、工具注册表、校验器和消息记录，由我们明确执行工具。

Codex 官方支持 codex exec 和 SDK 等程序化集成，但它提供现成 Agent 运行时。可在后续作为工具或对照系统，比较它与自己实现的 Agent。也可采用 Codex，但那是另一层集成：不把 Codex 应用直接等同于一个只返回模型动作的普通函数。

官方来源：[Codex 非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)、[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)。

本地候选先用已安装并已运行的 qwen3.5:9b-q4_K_M，之后再比较 2B 的任务成功率和速度。本次没有推理测量，不依据参数量宣布结果更好。

Ollama 支持聊天 API 和工具调用，参考 [工具调用](https://docs.ollama.com/capabilities/tool-calling)、[聊天接口](https://docs.ollama.com/api/chat)。

## 第一步：从 Python 查询本地服务

```bat
python -X utf8 -m labs.l07_local_model_info
```

脚本使用标准库 urllib 和 json，向 /api/version 和 /api/tags 发起元数据查询。没有发起推理，也没有把资料发送到云端模型。成功返回说明 Python 能连上本机服务并读取模型列表，不等于模型推理或工具调用已验证。

## 接下来的顺序

1. Python 连通本地 API，看到现有模型列表。
2. 对选定模型发起一次最小聊天请求，理解 HTTP 输入和 JSON 返回。
3. 携带工具说明请求一次原生工具调用，检查实际响应。
4. 编写适配器，把内部消息协议与 Ollama 协议互相转换，再接入 run_loop。

实际模型的工具选择和错误修正不再由我们写好的 if 分支保证，需要通过真实运行观察。接入时记录返回值、耗时和终止原因。

本小节预检已由学习者独立完成。下一小节的 [首次真实聊天](09-first-local-chat.md) 已由 AI 实测成功；工具调用和循环适配器仍未实现。
