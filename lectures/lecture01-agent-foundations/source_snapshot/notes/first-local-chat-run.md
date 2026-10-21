# 第一次本地模型聊天实测

日期：2026-10-21。学习者已恢复 max_steps=5，并提供 labs.l07_local_model_info 的独立运行输出。

AI 核验 Ollama 官方 /api/chat 与 thinking 文档，使用本机 /api/show 确认 qwen3.5:9b-q4_K_M 的 thinking.values=[false,true]，默认 true。首次简单聊天指定 think=False、stream=False，temperature=0、num_predict=128。

## 实际执行

```bat
python -X utf8 -m labs.l08_first_local_chat
```

模型：qwen3.5:9b-q4_K_M。请求只包含一句通用教学问题，没有项目文件内容或工具定义。访问本机 http://127.0.0.1:11434/api/chat，未调用云端模型 API。

实际返回：

- message.role=assistant，message.content 为非空中文回答。
- done=True，done_reason=stop。
- Python 端实际耗时约 50.340 秒。
- 服务报告 total_duration=50334220900 ns，load_duration=31304136700 ns，约 31.304 秒用于加载。
- prompt_eval_count=23，eval_count=44。
- 原始请求、响应和耗时已保存至 reports/l08_first_local_chat.json。

本次属于一次真实单轮聊天。没有执行文件工具，没有进入 run_loop，不据此宣称模型的工具调用或任务完成能力已验证。单次测量包含加载，不作为稳态性能结论。

示范脚本不改运行时或已有工具，不增加第三方依赖；本次以实际 HTTP 调用作为验证，没有重复已有 20 项无关测试。学习者独立复跑与响应结构理解待验证。

## 学习者独立成功证据

先前发生超时后，学习者提供了一次成功重试的完整输出，报告 created_at=2026-10-21T10:32:50.769728Z，elapsed_seconds=51.22999269992579，done=True、done_reason=stop，生成 44 token，加载约 31.005 秒。

AI 随后读取实际磁盘，l08 文件是 timeout=60、没有 keep_alive/等待提示的早期版本，与学习者输出一致。因此仅确认真实聊天成功，不声称学习者已运行过 180 秒版本。未确定此前配置变更为何未保留；本轮保留该已完成的学习文件，新原生工具调用演示独立使用较长等待。
