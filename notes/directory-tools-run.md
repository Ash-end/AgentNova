# 查看目录与双工具选择实测

日期：2026-10-21。代码与本次实测由 AI 完成，学习者本轮独立运行、解释和修改待验收。

## 实现

新增 directory_tools.list_directory，解析路径并检查项目范围，列出直接子项的 name、type、relative_path，排序后最多返回 50 项，truncated 标记是否截断。不会读取文件正文或递归枚举目录；50 项限制仅约束返回条目数。

注册表新增绑定可信根目录的 list_directory 函数，两项工具复用 validate_relative_path_arguments。新增目录参数 Schema。沿用已有异常转换、修正预算与停止策略，保留学习者的工具超时分类实现。原生模型循环未增加按任务选择工具的分支。

新增 labs/l14_multi_tool_agent.py，每个任务都发送相同的两个工具定义；--case 仅选择用户任务，EXPECTED 只在运行后比较本题预期工具序列，不参与调度。每种任务独立保存完整报告。

## 测试与回归

新增 9 项目录测试，先观察未注册工具导致行为断言失败，再实现功能。覆盖根目录与子目录、空目录、非递归、参数校验、路径越界、结构化错误、50 项截断、根目录绑定，以及预设模型依靠实际目录结果选择读取。

首次回归中项目 50 项通过，超时练习 2 项失败。重新读取文件发现 TimeoutError 已排到 OSError 后面，与此前读取的顺序不同；原因未确定。恢复此前已验收的子类优先顺序并统一缩进，再运行两组测试，项目 50 项与练习 4 项全部通过。未更改练习预期或弱化测试。

真实服务实验结束后最终读取时，又观察到相同顺序变化，原因仍未确定；再次恢复后核验两组测试及磁盘分支顺序。后续若在编辑器保存该文件，需保留 TimeoutError 在 OSError 之前的已验收顺序。

## 真实服务观察

命令：

```bat
python -X utf8 -m labs.l14_multi_tool_agent --case all
```

模型 qwen3.5:9b-q4_K_M，temperature=0，stream=false，think=false，keep_alive=10m，num_predict=512，每次 socket timeout=180 秒。使用项目真实 fixtures，没有把文件正文或目录观察预先提供给模型。

AI 完成的三个独立会话任务：

| 任务 | 实际工具序列 | 模型决策 | 总耗时 | 结果 |
| --- | --- | --- | --- | --- |
| list | list_directory | 2 | 144.908 秒 | completed，正确列出 hello.txt 为文件 |
| read | read_text_file | 2 | 193.107 秒 | completed，正确给出实际两行正文 |
| discover | list_directory → read_text_file | 3 | 294.652 秒 | completed，根据目录结果选择文件并正确给出正文 |

组合任务第一轮 list_directory，真实目录结果含 hello.txt 的项目相对路径；第二轮模型根据结果提出 read_text_file，工具成功读取。第二轮同时包含“现在我将读取”的文字与 tool_calls，运行时正确优先执行工具并进入第三轮，而不是将这句话当作最终回答。第三轮没有新工具请求，正确给出两行实际正文。

三个报告已读取核对：全部 completed，简单工具序列与预期一致，两个读取任务回答包含实际正文。组合任务三次请求的消息条数为 2、4、6，说明目录观察和读取观察依次进入后续请求。

本次多轮均出现较长加载时间，部分响应 load_duration 约 75–79 秒且缓存命中为零，不能按前几课的热启动速度预计耗时。没有更改或重启模型服务；性能原因尚未诊断。

报告位置：reports/l14_multi_tool_agent_list.json、reports/l14_multi_tool_agent_read.json、reports/l14_multi_tool_agent_discover.json。

## 学习者独立运行

学习者随后提供三个完整终端记录：list 耗时 51.419 秒、read 0.856 秒、discover 1.413 秒，分别为 2、2、3 次模型决策，实际工具序列与上表相同，读取正文正确。当前同名报告已对应新的独立运行。list 首轮加载约 31.748 秒、后续加载约 0.003 秒；read/discover 为已加载模型，多轮命中输入缓存。与 AI 此前较慢运行条件不同，不据此宣称优化效果。

学习者正确回答：目录结果没有正文，只有名称、类型和路径；下一步将 relative_path 传给 read_text_file。本次附件没有新一轮 tests/ 50 项输出，因此只记录三项模型任务独立完成，保留测试由 AI 已验收的来源标记。

最终回归时还观察到注册表回到单工具版本，导致目录测试失败（unknown_tool）；新工具文件和已有真实运行报告仍存在。依据当时磁盘内容补回目录导入、绑定函数、注册项和共用校验，保留已验收的 TimeoutError 顺序。最终实际运行结果：项目 50 项、练习 4 项全部通过，并打印确认注册表包含 read_text_file 和 list_directory。文件内容变化来源未确定，不归因于学习者；未重启服务或重复已完成的真实模型任务。
