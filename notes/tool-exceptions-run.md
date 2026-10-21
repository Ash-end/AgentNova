# 工具异常转换实测

日期：2026-10-21。代码与首次运行由 AI 完成；学习者已独立复跑，解释细节继续复习，独立修改待验收。

在 registry.call_tool 的实际调用位置新增具体 except 分支：FileNotFoundError、PermissionError、IsADirectoryError、NotADirectoryError、UnicodeDecodeError 以及最后的 OSError 兜底。转换结果包含 status、error_type、tool_name、exception_type 和 message。

名称查找和参数校验仍在执行前完成，原工具返回的字典不改写。read_text_file 原有 FileNotFoundError 处理保持原样。没有捕获普通 TypeError 或所有 Exception，也没有新增自动重试。

tool_policy.py 为新增错误类别给出明确停止原因。未改动循环控制逻辑；异常转换后通过现有消息保存与策略机制处理。

新增 6 项测试；先观察未捕获的文件/解码异常导致行为断言失败，再完成转换与策略映射。最终在 agent-study 中全部 41 项测试通过，包含原有 35 项。新测试验证真实解码错误、目录读取、注入各类 OSError 的具体分类、编程错误不误判为参数错误、参数校验先于执行，以及转换结果进入策略后立即停止。

运行命令：

```bat
python -X utf8 -m labs.l13_tool_exceptions
python -X utf8 -m unittest discover -s tests -v
```

实验不访问模型 API，在临时演示项目中创建 UTF-8 文件、目录及非法 UTF-8 字节。每个案例先绕过分发器对照，再走正式调用链：

| 案例 | 实际情况 | 转换与判断 | 模型决策数 |
| --- | --- | --- | --- |
| UTF-8 文件 | 正常返回内容 | success → continue → 正确回答 | 2 |
| 目录 | Windows 实际抛出 PermissionError | permission_denied → stop / file_access_denied | 1 |
| 非 UTF-8 字节 | 实际抛出 UnicodeDecodeError | invalid_encoding → stop / utf8_required | 1 |
| 权限异常注入 | 演示工具主动抛出 PermissionError | permission_denied → stop / file_access_denied | 1 |

注入权限异常不等于验证实际 ACL 拒绝，未修改文件权限。目录异常按当前平台实际返回记录。临时项目退出时由 TemporaryDirectory 清理，报告中的临时路径随后不存在。

完整证据保存在 reports/l13_tool_exceptions.json。三种失败案例是符合预期的策略终止，演示程序正常退出。

学习者随后独立运行四个案例，结果与上表一致；全部 41 项测试通过，耗时 0.080 秒。学习者正确指出停止由后续策略判断，但将 except 表述为“选择策略”，需要补准：except 捕获并转换异常，策略根据结果返回动作，循环检查动作并 return 实现终止。该细节已解释，独立实现尚未验证。
