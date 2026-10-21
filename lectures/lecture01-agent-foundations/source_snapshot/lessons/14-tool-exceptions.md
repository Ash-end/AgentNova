# 第 14 次动手：把 Python 异常转换成工具结果

前置：学习者独立完成失败策略实验与 35 项测试，能解释修正预算用完就停止，不必等到 max_steps 耗尽。

## 两种不同的失败方式

工具可以正常返回一个错误结果：

```python
return {"status": "failed", "error_type": "file_not_found"}
```

也可能在执行中抛出异常：

```python
content = path.read_text(encoding="utf-8")  # 可能抛出 UnicodeDecodeError
```

前一种情况，调用者拿得到 result；后一种情况，如果没有捕获，函数不会正常返回 result，控制流会沿调用栈向外寻找匹配的 except。原来循环中 result = call_tool(...) 后面的保存结果、判断策略都来不及执行。

本课把调用链接起来：

```text
工具抛出已知异常
    → call_tool 捕获，返回结构化错误
    → 循环保存 role=tool 消息
    → 策略依据 error_type 判断
    → 本课规则停止，并保存诊断
```

## 捕获放在哪里

experiment_agent/tools/registry.py 中：先查工具名、校验参数；确认可以执行之后，只用 try 包住实际函数调用。

```python
try:
    return tool(**arguments)
except UnicodeDecodeError as error:
    return _exception_result(name, "invalid_encoding", error)
```

这是解码分支的简化摘录，实际代码还有其他具体异常分支。except ... as error 将捕获的异常对象绑定到 error；type(error).__name__ 获取 Python 类型名，str(error) 获取说明文本。return 返回普通字典后，调用者就能像处理其他工具结果一样继续处理。

_exception_result 前的下划线表示这是模块内部使用的辅助函数命名约定，不是 Python 的访问权限限制。

```json
{
  "status": "failed",
  "error_type": "invalid_encoding",
  "tool_name": "read_text_file",
  "exception_type": "UnicodeDecodeError",
  "message": "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
}
```

这里三种信息各有用途：

- error_type：程序定义的类别，供策略分支使用。
- exception_type：实际 Python 异常类型，方便诊断。
- message：错误细节，供人阅读；策略不靠匹配这段文字决定动作。

本课只将具体异常转换成失败结果，不把失败变成成功。对于非 UTF-8 字节，不使用 errors=ignore 丢弃内容，也不自动猜测编码。

## 本次转换规则

| Python 异常 | 结构化 error_type | 本课策略原因 |
| --- | --- | --- |
| FileNotFoundError | file_not_found | required_file_missing |
| PermissionError | permission_denied | file_access_denied |
| IsADirectoryError | is_a_directory | expected_file |
| NotADirectoryError | not_a_directory | invalid_parent_directory |
| UnicodeDecodeError | invalid_encoding | utf8_required |
| 其他 OSError | io_error | io_failure |

这些结果在本课策略下都停止。OSError 的兜底分类不代表已证明是临时故障，也不会自动触发重试。

原有 read_text_file 已经在内部处理 FileNotFoundError 并返回错误字典；这种结果直接通过分发器，保持原格式。只有异常确实传播到分发器并被捕获时，才添加 exception_type 等诊断信息。

具体 OSError 子类写在 except OSError 之前，否则会先被更宽的父类分支接住，失去具体分类。UnicodeDecodeError 不属于 OSError，需要自己的分支。[Python 3.11 异常说明](https://docs.python.org/3.11/library/exceptions.html)

本节没有 except Exception 或 except BaseException。工具内部意外的 TypeError 等编程错误仍会暴露出来，不能假装都是模型参数错误；KeyboardInterrupt 和 SystemExit 也不在本次捕获范围。已知执行异常的恢复与程序 bug 的诊断是不同任务。[Python 3.11 异常继承关系](https://docs.python.org/3.11/library/exceptions.html#exception-hierarchy)

## 运行对照实验

```bat
python -X utf8 -m labs.l13_tool_exceptions
python -X utf8 -m unittest discover -s tests -v
```

脚本使用预设模型响应，不调用模型 API。它创建一个临时演示项目，退出时清理临时夹具；不会改写现有课程文件。

四种情况：

1. UTF-8 文件：正常读取，继续并回答，模型决策 2 次。
2. 目录读取：由实际操作系统产生异常，转换后停止，模型决策 1 次。
3. 非 UTF-8 字节：实际触发 UnicodeDecodeError，转换后停止，模型决策 1 次。
4. 注入 PermissionError：演示工具主动 raise，以稳定验证转换，不改变 Windows ACL，转换后停止，模型决策 1 次。

Direct call 部分为了对照，绕过 call_tool 直接执行一次工具，并在演示层捕获打印；Through dispatcher 部分再通过正式循环调用一次。两部分是两次独立执行，不是同一次异常被重复捕获。

在本机 Windows 实测，目录读取抛出 PermissionError，而不是 IsADirectoryError。脚本按实际类型分类，不据此断言目录一定存在 ACL 配置问题。不同平台的文件操作可能产生不同异常。[Path.read_text 文档](https://docs.python.org/3.11/library/pathlib.html#pathlib.Path.read_text)

AI 首次运行后，学习者已独立运行四个案例，输出符合预期；全部 41 项测试独立通过（0.080 秒），其中新增 6 项。报告位于 reports/l13_tool_exceptions.json；其中临时夹具路径在清理后不再存在，这是预期行为。三层职责的精确解释继续复习，独立修改待验收。

这次修改分发器，因此已有 l11 也具备已知异常转换能力；是否立即停止仍取决于是否传入 tool_policy。l13 显式使用 decide_tool_result，沿用上一课的停止规则。

## 理解检查

一次调用先抛出 UnicodeDecodeError，分发器捕获并返回 status=failed、error_type=invalid_encoding。此时，决定停止的是 except 本身，还是后面的 decide_tool_result？它们分别负责什么？
