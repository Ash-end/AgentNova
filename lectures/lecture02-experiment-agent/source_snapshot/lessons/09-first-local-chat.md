# 第 9 次动手：第一次真实模型请求

## 已确认的前置状态

学习者已将模型替身演示的 max_steps 恢复为 5，并独立运行 labs.l07_local_model_info。Python 成功访问本机 Ollama 0.40.6，列出 qwen3.5:9b-q4_K_M 和 qwen3.5:2b。

本课只完成一次真实聊天请求。工具调用和自己的 run_loop 接入放在后续小节。

## 请求长什么样

```python
payload = {
    "model": "qwen3.5:9b-q4_K_M",
    "messages": [{
        "role": "user",
        "content": "请用一句中文解释：什么是大模型的工具调用？",
    }],
    "stream": False,
    "think": False,
    "keep_alive": "10m",
    "options": {"temperature": 0, "num_predict": 128},
}
```

- model 指定本机已经安装的模型名称。
- messages 是消息历史；本次只有一条 user 消息。
- stream=False 请求一次返回完整结果，便于用 json.load 解析。
- think=False 请求不输出思考内容；本机 /api/show 已确认该模型支持 false/true，默认 true。
- keep_alive="10m" 请求在本次调用后保留模型 10 分钟，减少学习过程中重新加载；不改变 Ollama 的全局配置。
- num_predict=128 限制本次生成 token 的上限；与运行时 max_steps 的“决策次数上限”不同。

这里是 Python 字典，所以布尔值用 False；序列化成 JSON 后显示为 false。

## 从 Python 到 HTTP 再回来

```python
body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
request = Request(
    "http://127.0.0.1:11434/api/chat",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=180) as response:
    data = json.load(response)
```

json.dumps 把字典转成 JSON 文本；encode 转为 HTTP 请求体的字节。Ollama 返回 JSON 后，json.load 把它解析回 Python 字典。

本次 messages 中没有工具执行结果，payload 没有 tools 字段，也没有调用本项目的文件读取工具。

## 运行

```bat
python -X utf8 -m labs.l08_first_local_chat
```

脚本打印请求、完整响应、答案、done、done_reason 和耗时，并保存到 reports/l08_first_local_chat.json。每次重新运行会覆盖该演示的最近一次报告。首次调用可能包含模型加载时间；单次请求不能作为稳定性能结论。

初版 socket timeout 为 60 秒，学习者实际遇到 timed out。现默认 180 秒，可通过命令行调整：

```bat
python -X utf8 -m labs.l08_first_local_chat --timeout 180
```

这是一次请求的 socket 超时设置，与 run_loop 的模型决策次数限制 max_steps 不同。脚本不自动重试。失败时会显示实际等待时间，不覆盖最近一次成功响应报告，因此不能用旧报告证明新的失败请求已完成。

如果本机服务尚未就绪或请求失败，脚本会报告连接或 HTTP 错误；不要把连接失败当成模型能力不足。

## 读取返回值

```python
answer = data["message"]["content"]
done = data["done"]
done_reason = data.get("done_reason")
```

done=True 表示这次生成已经结束。done_reason 提供结束原因，例如 stop 或 length；生成结束不代表回答正确。若为 length，可能是生成上限截断，应结合 content 判断，不能直接视为完整答案。

返回里的 eval_count 是本次生成 token 数；total_duration 以纳秒计。脚本另用 perf_counter 记录 Python 观察到的整次 HTTP 调用耗时，二者不必完全相等。

官方来源（2026-10-21 已核验）：[聊天 API](https://docs.ollama.com/api/chat)、[thinking 控制](https://docs.ollama.com/capabilities/thinking)。

## 已遇到的超时与诊断

学习者提供 60 秒版本的 timed out 输出。AI 检查服务在线、模型在 GPU 运行，未见显存耗尽迹象；当前手动 serve 进程没有找到可读取的日志文件，未重启服务。

保持原模型和问题不变，诊断请求使用 180 秒 socket 超时，实际 45.028 秒成功返回：加载约 25.982 秒、输入处理约 17.698 秒、生成约 1.341 秒。

随后对保留在内存中的模型运行修改后脚本，实际 0.713 秒成功返回：加载约 0.003 秒、输入处理约 0.268 秒、生成约 0.405 秒；命中 19 个输入缓存 token。

这支持“冷启动开销很大，需要留足等待余量”的判断；由于未取得学习者失败请求的服务端轨迹，不能确定其超出的时间具体来自加载、排队还是其他等待。两次测量也不能说明增加 timeout 会让推理加速，缓存状态不同是关键条件。

原始首次成功报告已另存 reports/l08_initial_success.json；诊断结果为 reports/l08_timeout_diagnostic.json；最近成功结果为 reports/l08_first_local_chat.json。

## 本轮练习

独立运行后贴出 Answer、Done、Done reason 三项。解释 data["message"]["content"] 为什么先取 message 再取 content。随后再添加工具说明，观察真实模型提出的工具调用。
