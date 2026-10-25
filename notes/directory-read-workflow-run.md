# 固定目录读取流程运行记录

日期：2026-10-22。以下先记录 AI 备课执行；学习者后续独立运行与解释单独记录在末尾。

学习者已依据提示完成选择函数，并自行修复缩进，8 项验收通过。本次直接导入该函数，未改写其源码。串接与演示由 AI 编写；没有模型 API 调用，尚未改造真实 Agent 循环。

入口：labs/l15_directory_read_workflow.py。运行报告：reports/l15_directory_read_workflow.json。

| 案例 | 实际执行步骤 | 实际结果 |
| --- | --- | --- |
| unique_text_file | list_directory → select_unique_text_file → read_text_file | success，读取项目 hello.txt 的两行正文 |
| multiple_text_files | list_directory → select_unique_text_file | failed / multiple_text_files，没有执行读取 |
| invalid_utf8_file | list_directory → select_unique_text_file → read_text_file | 选择 success，实际读取 failed / invalid_encoding |

后两个案例为真实临时文件，结束后自动清理；非法编码来自实际 b"\\xff\\xfe" 字节，未注入假异常。报告只包含项目相对路径与必要错误，没有本机用户目录或临时根路径。

AI 在 agent-study 执行：tests/ 56 项通过，包含新增 6 项连接测试；指定第 17 课练习 8 项通过。连接测试通过调用观察确认：缺失、空目录、多文件和真实截断时未调用读取，唯一文件时按观察路径读取一次，读取异常仍返回失败。

待学习者运行演示并解释：为什么多个文本文件时只有两个 trace 步骤；哪条 return 跳过了读取；为什么选中唯一文件后仍可能因编码而失败。尚未把这些解释记为已独立掌握。

## 学习者独立运行与解释

学习者已提供 l15 三个案例的完整终端输出：唯一文本文件实际读取成功；多个文本文件时仅列目录和选择两个步骤，multiple_text_files 后停止；非法 UTF-8 文件选择成功但读取返回 invalid_encoding，流程失败。输出与本课预期相符。

学习者正确解释：多个文件使 selection 返回 failed，进入非 success 分支后 return 结束整个函数，因此不会执行后面的 read_text_file。本项控制流理解已验收。非法编码案例中“选择成功不等于读取成功”的独立解释仍待确认；本次未提供新的测试输出，不将 AI 的 56+8 测试结果改记为学习者独立执行。

后续解释已确认：学习者正确指出最终 status 来自 read_result，选中文件成功不代表读取成功。本项已验收；异常抛出与分发器转换的精确措辞已由 AI 补充。原先“待确认”保留为过程记录。
