# 独立修改练习准备记录

用户明确希望自己动手。AI 仅创建题目与独立验收测试，不修改 registry.py、tool_policy.py 或循环实现，不提供完整实现代码。

目标：工具 TimeoutError → tool_timeout；策略停止理由 tool_timeout_needs_review。普通 OSError 保持 io_error / io_failure。不增加自动重试，不改模型 HTTP 超时处理，不调用模型 API。

基线检查：

- exercises/test_timeout_mapping.py：4 项中 1 项通过、3 项失败。失败分别为独立超时分类、超时策略理由、循环中的工具超时诊断；符合尚未实现的题目要求。
- tests/：原有 41 项全部通过。

练习测试单独放在 exercises/，不改变现有 tests/ 的验收范围。最终需要分别运行两组测试，达到练习 4 项与原有 41 项全部通过。

以上为练习发布时的基线，保留作为前后对照。

## 独立修改验收

学习者报告已修改，AI 读取实际文件确认：registry.py 已在 OSError 前增加 TimeoutError 分支，复用 _exception_result 返回 tool_timeout；tool_policy.py 已新增 tool_timeout_needs_review 映射。验收测试未被修改。

学习者正确解释 TimeoutError 是 OSError 的子类，若将其捕获分支放到 OSError 后面，会先进入 OSError 分支。

AI 在 agent-study 中实际运行：练习 4 项全部通过，原有 41 项全部通过（0.084 秒）。该结果验证独立分类、保留异常细节、策略理由、循环停止和原有 I/O 分类。此处测试由 AI 验收，不额外记为学习者独立运行测试。

首次独立功能修改已验收。格式小建议：TimeoutError 分支的 return 多缩进 4 个空格，Python 当前可运行，建议与相邻分支保持一致。AI 未重写学习者的实现。
