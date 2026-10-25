# Lecture 02 阅读与复盘

本讲覆盖 2026-10-22 至 2026-10-25 的第 17–27 次小课、l15–l21。与 Lecture 01 一起覆盖目前全部课程；不是 CS2680 官方讲义，也不代表 16 周路线完成。

最终 PDF 共 91 页；固定快照 168 份。桌面编辑器编译验证成功，交付 PDF 由 Tectonic 0.17.0 实际编译单文件 lecture.tex；已检查全部页面缩略图以及封面、正文表格和长代码页面。中文内容检查使用 pdfplumber，元数据检查使用 pypdf。

- lecture.md：详细正文、逐课全文、核心源码、全部资料索引和对话摘录。
- lecture_body.md：可编辑的正文源稿。
- main.tex / content.tex：LaTeX 项目主文件与正文。
- lecture.tex：单文件 LaTeX，便于独立保存。
- lecture02-experiment-agent.pdf：由本套 LaTeX 源码实际编译的最终 PDF。
- source_snapshot/：公开脱敏后的固定学习源码、任务、笔记、测试、报告、证据及选定训练产物。
- manifest.json：快照字节数与 SHA-256。
- quality-check.json：PDF、源码、快照与版面检查结果。
- build_lecture.py / markdown_to_tex.py：重新生成文稿，不执行模型或训练。
- check_quality.py / audit_publication.py：PDF 与公开内容复核；security-review.json 记录补充隐私筛查。

先读正文第 1 节的状态分层，再按第 2–11 节回顾课程；第 12 节复盘错误，第 15 节遮住答案做自测。实现细节和历史失败可在附录全文中核对。

已有 manifest 时，运行 `python build_lecture.py` 保持原快照不变。只有明确需要重新冻结当前项目时才用 --refresh-snapshot。LaTeX 使用 ctexart、Fandol 字体与常用宏包，采用 Tectonic/XeLaTeX 编译；传统 XeLaTeX 需多遍更新目录。最终 PDF 的实际编译和质量检查以 quality-check.json 为准。

运行证据区分 AI 与学习者；G1 核心循环经提示和 AI 修复，不记为独立无提示实现。指标函数为学习者在提示后完成。最近学习者独立运行的指定测试为 l19 8 项、l20 12 项、l21 7 项，全量 122+28 的记录由 AI 提供。

公开副本的 USER 是目录占位符；私人附件路径不公开；模型、版本、耗时、程序 run_id 和教学项目相对路径保留。归档不包含模型权重、Anaconda 环境、凭据或整个本机 runs 目录，只挑选当前训练报告关联的五类 JSON 产物。

原项目 .gitattributes 在快照中保存为 gitattributes.snapshot.txt，避免它在快照目录内重新生效。归档文件保留原换行字节，公开脱敏替换除外；上传前还核对 Git 提交区中的实际 blob 哈希与 manifest 一致。
