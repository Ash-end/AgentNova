# 参数校验实操与反馈

日期：2026-10-21。环境：agent-study，Python 3.11.17。

## 学习者证据

学习者独立运行初版 labs.l04_tool_arguments，观察正常请求成功、缺字段/拼错字段/整数路径三种 TypeError。回答提出先用 isinstance 排除非字符串，再检查 strip 后是否为空；其中“去掉里面所有空格”的理解需纠正，strip 仅移除两端空白。

## 实现与边界

AI 按讨论保存 validate_read_text_arguments：检查字典、必需 relative_path、无额外字段、字符串非空且不全为空白。只用 strip 的结果判断，不改写实际路径。call_tool 在已知名称之后、实际调用之前校验，返回 invalid_arguments 与 message。

没有改变文件工具的路径范围与读取逻辑。文件名中间允许空格，测试使用 my notes.txt。参数错误不会通过捕获任意运行异常来代替校验。

## 实测

先增加参数错误用例，运行观察到 TypeError，以及空白路径进入文件读取后的 PermissionError/OSError。随后实现校验，在相同环境执行：

```bat
python -X utf8 -m labs.l04_tool_arguments
python -X utf8 -m unittest discover -s tests -v
```

六种演示输入中：正常输入 success，其余缺字段、错名、整数、全空白和额外 project_root 均返回 invalid_arguments。全部 15 项测试通过，耗时 0.029 秒。部分测试含多个子用例，15 指 unittest 测试方法数量。

学习者随后提供独立复跑结果：额外 project_root 返回 invalid_arguments，全部 15 项通过（0.028 秒）。独立运行已确认；strip / 短路求值的解释复述和独立修改仍未验证，不标记为独立实现。
