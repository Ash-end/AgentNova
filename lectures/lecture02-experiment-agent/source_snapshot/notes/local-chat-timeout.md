# 本地聊天超时诊断与修正

日期：2026-10-21。

## 失败证据

学习者提供完整终端输出：POST /api/chat 请求打印完成，最终 Cannot complete local chat request: timed out。初版 urlopen 使用 timeout=60。失败没有更新成功报告；不能使用先前 AI 成功报告替代学习者本次结果。

## 只读检查

Ollama 0.40.6 服务在线，qwen3.5:9b-q4_K_M 在 GPU 运行，观察时 GPU 总显存 16303 MiB、已用约 9GB，没有显存耗尽迹象。元数据请求及时返回；诊断 Python 的回环地址绕过代理。

服务是 ollama.exe serve 手动进程，未在默认 LOCALAPPDATA/Ollama 或 E:/AI 找到日志文件。未重启服务、更新驱动、卸载模型或更改全局服务参数。未取得学习者失败请求的服务端轨迹，因此其额外等待阶段不可精确还原。

## 控制变量诊断

原模型、问题、stream=False、think=False 和生成参数不变，仅使用 180 秒 socket 超时发起一次有界请求。实际成功返回，done=True、done_reason=stop：

| 指标 | 秒 |
| --- | --- |
| Python 端耗时 | 45.028 |
| 加载 | 25.982 |
| 输入处理 | 17.698 |
| 生成 | 1.341 |

保存原始数据：reports/l08_timeout_diagnostic.json。证据支持冷启动开销占主导、原 60 秒余量偏小；不确定学习者超时中是否另有排队等额外等待。

## 修改与验证

labs/l08_first_local_chat.py 新增 --timeout，默认 180 秒，拒绝非正数；请求增加 keep_alive=10m；显示等待状态、超时实际耗时、加载/输入/生成时间。没有自动重试，也没有改变模型、问题、生成上限或全局 Ollama 配置。

模型已加载时再运行修改后的脚本，实际成功：总耗时 0.713 秒，加载 0.003 秒，输入处理 0.268 秒，生成 0.405 秒，命中输入缓存 19 token。done=True、done_reason=stop。该热模型运行与冷启动条件不同，不能把速度差归因于 timeout 数值改变。

最初 AI 成功报告保存在 reports/l08_initial_success.json；修改后最近成功报告为 reports/l08_first_local_chat.json。

本次对演示脚本做小范围等待与观测修改，以真实请求验证；未新增镜像配置的测试，也未无必要重复不相关的 20 项运行时测试。学习者修复后独立运行仍待确认。

官方参考：[聊天接口](https://docs.ollama.com/api/chat)、[FAQ](https://docs.ollama.com/faq)、[日志排查](https://docs.ollama.com/troubleshooting)，本次已访问 FAQ 与排查页。
