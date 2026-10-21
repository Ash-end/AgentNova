# Lecture 01 使用与复盘

本讲为 2026-10-21 阶段归档，覆盖从文件工具到真实双工具循环的学习内容。不是 CS2680 官方讲义，也不代表 16 周路线全部完成。

本目录为公开脱敏版：USER 为用户目录占位符，附件内部路径和无关环境名称已移除；95 份资料的 manifest 哈希对应脱敏后的字节。实验输出的错误类别、结论和耗时未改动。重新收集终端证据时，可先将脱敏文本放入本目录的 learner_evidence_inbox（已排除版本控制）；已有快照不需要此目录。

## 阅读入口

- lecture.md：完整 Markdown，正文、自测题、全部资料索引与关键源码。
- main.tex：LaTeX 主文件，调用同目录 content.tex。
- lecture.tex：同内容的单文件 LaTeX，便于单独保存或导入其他编辑器。
- content.tex：与 Markdown 同内容的生成版 LaTeX 正文。
- lecture01-agent-foundations.pdf：最终 PDF，适合阅读和打印。
- lecture_body.md：可编辑的正文源稿。
- source_snapshot/：95 个固定原始学习文件，包括规划、16 次小课与周任务、14 个实验、实现、测试、笔记、原始 JSON 与学习者终端附件。
- manifest.json：原始文件字节数与 SHA-256，保留快照时刻。
- build_lecture.py：从正文源稿和固定快照重新生成 Markdown 与 LaTeX 正文，不调用模型或执行训练。

## 复盘顺序

1. 先读正文第 1 节的完整闭环，再看第 14 节易错点。
2. 独立回答第 15 节自测题，再对照答案。
3. 打开第 12 节实验总账，核对哪些是模拟、哪些是真实运行、哪些由学习者独立完成。
4. 用附录 B 看实际源码；必要时打开附录 A 对应的原始记录。
5. 下一次学习从第 16 节恢复入口接续，今天无需再运行新实验。

## 重新生成

在本目录执行：

```bat
python build_lecture.py
```

脚本默认复用已存在的 manifest.json 和 source_snapshot，不会把原项目后续变化混入本次快照。

LaTeX 使用 ctexart、Fandol 中文字体及常用宏包，可在 Codex 中打开本目录并编译，或在具备 Tectonic/XeLaTeX 的环境中编译 main.tex。传统 XeLaTeX 通常需执行两遍，以更新目录；Tectonic 自动重跑。首次运行 Tectonic 可能需联网下载排版资源。

最终交付 PDF 由单文件 lecture.tex 使用 Tectonic 实际编译生成，与所附 LaTeX 源码对应。初始化资源期间另生成并检查过离线备用版；render_pdf.py 保留为备用导出脚本，使用文档制作运行时中的 ReportLab，不属于 agent-study 的运行依赖。备用导出和 LaTeX 的分页可能不同。

PDF 生成工具属于讲义制作环境，不是 agent-study 学习代码的新依赖。原有 Python 工具仍仅使用标准库。

## 证据边界

学习者最新 l14 三项结果分别为 51.419、0.856、1.413 秒，工具选择正确。AI 早先较慢运行单独保存在笔记叙述中，不能混作相同条件的性能比较。

原有 41 项测试曾由学习者独立运行；超时功能修改由学习者完成、AI 验收；扩展后项目 50 项与练习 4 项由 AI 验收。本次 l14 附件未提供新的 50 项测试输出。

归档包不含模型权重、Anaconda 环境或密钥。源码快照和测试可以用于复盘，但真实模型实验仍需本机 Ollama 与已安装模型。
