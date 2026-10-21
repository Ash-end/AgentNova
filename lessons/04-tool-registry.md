# 第 4 次动手：根据工具名称调用函数

## 已有能力与本次目标

学习者已独立复跑文件工具 5 项测试并提供输出。本次学习把“普通函数”变成“可按名称调用的工具”，使用标准库和字典，无需新增依赖。

这层映射由程序构造；模型接入后只提供工具名称和业务参数。今天的请求由演示脚本手工构造，尚未调用模型。

## 先理解函数可以作为字典的值

```python
tools = {"read_text_file": read_project_file}
tool = tools["read_text_file"]
result = tool(relative_path="labs/fixtures/hello.txt")
```

read_project_file 是下面说明的包装函数。注册时存函数对象，不加括号。加括号会立刻执行函数，并将返回值存入表中；如果缺少必需参数还会直接报错。

## 固定项目根目录

registry.py 的 build_tool_registry 接收可信项目根目录，构造一个包装函数：

```python
def build_tool_registry(project_root: str) -> dict:
    root = str(Path(project_root).resolve())

    def read_project_file(relative_path: str) -> dict:
        return read_text_file(root, relative_path)

    return {"read_text_file": read_project_file}
```

内部函数记住创建时的 root，这称为闭包。调用包装函数只需要 relative_path；不同注册表可以记住不同项目根目录。模型请求中没有 project_root 参数。

## 用名称查找，再传入参数

演示中的工具请求形如：

```json
{
  "name": "read_text_file",
  "arguments": {"relative_path": "labs/fixtures/hello.txt"}
}
```

调用过程：

```python
tool = tools.get(request["name"])
result = tool(**request["arguments"])
```

字典 get 找不到名字时返回 None；实际实现先返回 unknown_tool，而不会调用任意其他函数。参数前的双星号把字典展开为关键字参数：

```python
tool(**{"relative_path": "labs/fixtures/hello.txt"})
# 等价于
tool(relative_path="labs/fixtures/hello.txt")
```

工具名称是调用接口的名称，不要求等于包装函数的 Python 名称。这里字符串 read_text_file 对应的是 read_project_file 包装函数，底层读取仍由原函数实现。

## 运行

在项目根目录且已激活 agent-study 时执行：

```bat
python -X utf8 -m labs.l03_tool_registry
python -X utf8 -m unittest discover -s tests -v
```

三种请求依次为：注册工具正常读取、未注册的 delete_file、注册工具尝试越界。预期返回 success、unknown_tool、path_outside_project。脚本不注册删除能力，第二个请求只用于验证名称查找失败。

新增 4 项测试：按名称读取、未知工具、不同注册表绑定不同目录、调用后仍遵守原文件工具范围检查。与原有 5 项合计 9 项。

## 本轮练习

先运行演示，然后用自己的话解释：为什么 `tools` 字典中存的是 `read_project_file`，而不是 `read_project_file(...)`？

本小节初始版本聚焦名称查找、函数对象和参数展开。当时参数缺失、多传或名称拼错会触发 TypeError；现已在 [参数契约小节](05-tool-arguments.md) 加入 invalid_arguments 返回。

## 首次反馈：区分字典的键和值

学习者把注册表理解为只保存工具名称。实际映射如下：

```python
tools = {
    "read_text_file": read_project_file,
    # 字符串名称      函数对象
}
```

带引号的是字符串；read_project_file 没有引号，是已经定义的函数对象。`read_project_file(...)` 是函数调用表达式，会立即运行函数；注册时若这样写，会把返回结果放进字典。`tools["read_text_file"]` 取出函数时不会读取文件，随后 `tool(...)` 才执行读取。

本轮实际运行发现旧版文件工具缺少范围检查，AI 已确认导入位置并复现失败，恢复范围检查后全部 9 项通过。再次复跑检查时应看到项目外路径返回 path_outside_project。
