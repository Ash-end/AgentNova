# 第 5 次动手：调用工具前检查参数

## 已验证的前置能力

学习者已提供修复后 9 项测试通过的输出，并正确说明：第 1 行从注册表取出函数，第 2 行调用函数并开始读取。接下来处理参数契约。

## 为什么还需要检查参数

加校验前，call_tool 能检查名称是否注册，但随后直接执行 tool(**arguments)。请求里名称正确，也可能缺字段、字段名拼错或类型错误。

```python
{"relative_path": "labs/fixtures/hello.txt"}  # 正常
{}                                           # 缺少字段
{"path": "labs/fixtures/hello.txt"}           # 字段名不匹配
{"relative_path": 123}                       # 类型不匹配
```

函数签名中的 relative_path: str 是类型标注，不会自动拒绝整数；错误可能直到函数体里执行 Path 操作时才发生。缺参数和多参数则可能在 Python 绑定函数参数时直接报 TypeError。这是不同的失败位置。

## 运行观察

```bat
python -X utf8 -m labs.l04_tool_arguments
```

学习者已运行初版演示：第一种返回 success，后面三种产生 TypeError。当前代码已加入校验，演示扩充为六种输入；除正常输入外，其余返回 invalid_arguments，不再出现这些 TypeError。

## 我们要定义的规则

对 read_text_file 的业务参数，暂定如下契约：

1. arguments 必须是字典。
2. 只允许 relative_path 一个字段，必须提供；不接受调用方提供 project_root。
3. relative_path 必须是非空字符串；本项目也拒绝只包含空白字符的输入。
4. 参数契约通过后，才实际调用工具；路径是否越界仍由文件工具检查。

不符合契约时，希望分发层返回结构化结果，例如：

```json
{
  "status": "failed",
  "error_type": "invalid_arguments",
  "message": "relative_path must be a non-empty string"
}
```

参数是否正确、路径是否允许、文件能否读取，是三个不同的判断。只有前一步通过，才进入后一步。

## 练习

学习者正确提出先排除非字符串，再判断空内容；将 strip 理解为删除所有空格的部分需要修正：strip 只移除两端空白，不改中间的空格。

```python
valid = isinstance(value, str) and bool(value.strip())
```

and 使用短路求值：当类型不符时，右边不会执行，避免对整数或 None 调用 strip。实际校验器用等价的拒绝条件：

```python
if not isinstance(value, str) or not value.strip():
    return "relative_path must be a non-empty string"
```

这里 strip 仅用于判断；调用文件工具时保留原始路径，不擅自删除或替换文件名中的空格。

## 当前实现与复跑

registry.py 已新增 validate_read_text_arguments：先判断字典，再检查必需/额外字段，最后检查字符串。当前只有一个工具，call_tool 根据 read_text_file 名称调用这个校验器；新增工具时需定义其自己的参数契约。

校验器合法时返回 None，非法时返回错误说明；分发器把说明包装成 invalid_arguments，然后立即返回，不执行工具。不使用捕获全部异常的方式把真正的工具 bug 伪装成参数错误。

```bat
python -X utf8 -m labs.l04_tool_arguments
python -X utf8 -m unittest discover -s tests -v
```

AI 已实测 15 项通过，其中包含文件名 my notes.txt 正常读取的测试。学习者独立复跑及 strip / 短路求值的解释待验证。

下一小步是描述工具接口的 JSON Schema，再把已验证的名称、参数、结果接到模拟模型的循环。
