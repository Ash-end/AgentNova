# 工具注册表首次示范与运行

日期：2026-10-21。学习者已独立通过原文件工具 5 项测试，并明确请求学习根据工具名称调用函数。

最初由 AI 保存实现与示范。学习者随后已提供独立运行输出和回答；过程中发现文件工具范围检查回归，详见下方追加记录。

## 实现

- experiment_agent/tools/registry.py：build_tool_registry 构造字典，包装函数通过闭包记住可信根目录；call_tool 根据 name 查找函数，再通过 **arguments 传入业务参数。
- labs/l03_tool_registry.py：手工构造三条请求，不调用模型。名称 read_text_file 对应包装函数 read_project_file。
- tests/test_tool_registry.py：真实文件读取、未知名称、两个注册表根目录隔离、调用后保留路径边界。

先保存接口桩并运行新增 4 项测试，均因 NotImplementedError 失败；补充实现后与原文件工具用例一起执行，全部 9 项通过，耗时 0.025 秒。未更改原文件工具行为。

## 实测

环境：E:/Anaconda3/envs/agent-study/python.exe，Python 3.11.17。

```bat
python -X utf8 -m labs.l03_tool_registry
python -X utf8 -m unittest discover -s tests -v
```

三种演示结果依次为：read_text_file 正常读取返回 success；delete_file 未注册返回 unknown_tool；read_text_file 请求外部路径返回 path_outside_project。没有注册或执行删除能力。

本次只实现名称分发和绑定根目录。参数缺失、额外参数、类型错误等尚未统一处理；下一课增加参数契约与错误返回，不能将当前示例视作完整模型调用运行时。

## 下一轮

学习者已复跑修复后的 9 项测试并正确区分函数引用与调用，开始参数契约小节。

## 学习者运行发现回归与修复

学习者输出：正常读取和 unknown_tool 正确，但项目外路径返回 file_not_found；全部 9 项测试中 4 项失败。学习者对注册时不加括号的解释为“注册表里面只写工具的 name，就是字符串”。后半句尚未区分函数引用与函数调用。

AI 实际检查当前文件，发现 file_tools.py 内容是没有 resolve / is_relative_to 检查的早期实现。通过 sys.executable、模块 __file__、inspect.getsource 以及 registry.read_text_file is file_tools.read_text_file，确认当前 agent-study 导入的就是该项目文件，注册表引用同一函数。随后复现 4 项失败。

失败机制：底层工具先直接读取项目外路径；外部文件存在则返回 success，不存在则返回 file_not_found。注册表只是调用该底层工具，所以相关集成测试也失败。现有证据不能确定范围检查为何缺失，不能推断由谁或哪次保存覆盖。

AI 仅恢复 read_text 之前的路径解析与范围检查，未改测试判据。修复后全部 9 项通过，耗时 0.022 秒；演示恢复为 success、unknown_tool、path_outside_project。学习者随后提供独立复跑 9 项全部通过的输出（0.022 秒），并正确回答“第一行是取出函数，第二行才是开始读取文件”。
