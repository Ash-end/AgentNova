# 第 16 次动手：第二个工具与模型选择

前置：你已经独立完成超时异常分类与策略映射。练习 4 项、原有 41 项均通过，能解释为什么子类异常要先于父类捕获。

## 两个工具分别解决什么问题

| 工具 | 输入 | 返回的信息 |
| --- | --- | --- |
| list_directory | relative_path，目录路径；根目录用 . | 下一层文件/目录的名称、类型、项目相对路径 |
| read_text_file | relative_path，文件路径 | UTF-8 文件正文 |

列目录不等于读取里面的文件。看见 hello.txt 的名称以后，还需要调用读取工具才获得正文。

## 先看普通 Python 实现

新文件 experiment_agent/tools/directory_tools.py：

```python
root = Path(project_root).resolve()
path = (root / relative_path).resolve()
if not path.is_relative_to(root):
    return {"status": "failed", "error_type": "path_outside_project", ...}

children = sorted(path.iterdir(), key=lambda child: child.name.casefold())
```

先解析并检查项目范围，再访问目录。iterdir 获取直接子项，不递归进入子目录；程序排序后返回稳定顺序。[Python Path.iterdir 文档](https://docs.python.org/3.11/library/pathlib.html#pathlib.Path.iterdir)

输出示例：

```json
{
  "status": "success",
  "entries": [
    {"name": "hello.txt", "type": "file", "relative_path": "labs/fixtures/hello.txt"}
  ],
  "truncated": false
}
```

entries 是列表，每个元素是一个条目字典。返回项目相对路径后，模型可以把这个路径放进下一次 read_text_file 的参数，不用猜当前工作目录。

本课最多返回排序后的 50 项；超过时 truncated=true。此限制减少返回给模型的内容，不是对目录枚举总耗时或内存的硬限制。truncated=true 时不能把已显示的条目当成整个目录。

空目录返回 success 和空 entries。目录不存在或目标是普通文件时，iterdir 的异常进入上一课的统一转换与策略。符号链接条目标为 symlink；后续实际访问路径仍需要 resolve 和范围检查。本工具没有完整文件系统沙箱的保证。

## 加进注册表，还要告诉模型

注册表新增绑定根目录的函数：

```python
def list_project_directory(relative_path):
    return list_directory(root, relative_path)

return {
    "read_text_file": read_project_file,
    "list_directory": list_project_directory,
}
```

两项的键是名称字符串，值是函数对象。固定根目录仍由 Python 管理，不能让模型通过参数覆盖。

两个工具都只允许一个非空字符串 relative_path，所以参数校验函数改名为 validate_relative_path_arguments 并复用。新增 list_directory.schema.json，将目录参数说明发送给模型；用 . 表示项目根目录。

只把函数放进 Python 注册表，模型还不知道存在这个工具。新实验将两份 description + Schema 一起放进请求 tools 中。旧实验的工具说明保持原样，本课入口使用新的双工具说明。[Ollama 工具调用格式](https://docs.ollama.com/capabilities/tool-calling)

## 谁根据任务选工具

模型看到任务和两个工具的说明，返回工具名与参数。运行时仍然执行熟悉的一行：

```python
result = call_tool(tools, function["name"], function["arguments"])
```

这里没有按照任务中是否出现“目录”写 if/else 来选择工具。原生循环逻辑没有改动；它依然保存模型请求，校验与执行工具，把结果带入下一轮。

新实验的 --case 只是选择用户任务；EXPECTED 只是运行后对照本题的简单工具序列，不参与选择或强制模型执行工具。序列相符仅是这几个演示的观察指标，不能代替对全部回答内容的评估，也不是广泛能力评测。

## 三个对照任务

```bat
python -X utf8 -m labs.l14_multi_tool_agent --case list
python -X utf8 -m labs.l14_multi_tool_agent --case read
python -X utf8 -m labs.l14_multi_tool_agent --case discover
```

| case | 用户任务 | 本题预期简单工具序列 |
| --- | --- | --- |
| list | 查看 labs/fixtures 的名称与类型 | list_directory |
| read | 读取指定 hello.txt 的实际内容 | read_text_file |
| discover | 先看目录，再找到其中的 .txt 文件并读取 | list_directory → read_text_file |

每个任务都是独立新会话，请求中都提供相同的两个工具。任务没有直接给出工具名称。discover 中第二次读取的路径应来自第一轮目录观察，读取结果再进入第三次模型请求，最终得到回答。

不带参数默认执行 discover；--case all 会依次运行三种任务。每次模型请求的 socket timeout 为 180 秒，最多 5 次模型请求，启用现有失败策略。实际模型选择与决策次数以输出为准，程序不会偷偷替模型补上缺失调用。

报告分别保存在 reports/l14_multi_tool_agent_list.json、_read.json、_discover.json，保留实际请求快照、完整响应、工具序列与消息历史。

AI 首次实测三种任务全部完成，耗时分别为 144.908、193.107、294.652 秒，多轮出现较长加载。随后学习者已独立完成三项，耗时 51.419、0.856、1.413 秒；实际工具序列均与上表一致，决策数为 2、2、3，正文正确。学习者正确解释目录元信息和读取路径；两轮加载与缓存条件不同，不把耗时差异归因于代码优化。

运行测试：

```bat
python -X utf8 -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s exercises -p test_timeout_mapping.py -v
```

本轮新增 9 项目录工具测试，tests/ 共 50 项；加上 exercises/ 的 4 项，两组都需要通过。新测试覆盖参数、路径、空目录、相对路径、结果截断、根目录绑定、异常，以及预设模型根据真实目录观察继续读取文件。

## 理解检查

list_directory 返回 hello.txt 这个条目的 name、type、relative_path 后，模型知道了哪些信息？它是否已经知道文件正文？下一步应拿哪个字段构造读取请求？
