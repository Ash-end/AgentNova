# Agent 学习与构建项目

目标：以 Harvard CS2680 为主线，系统掌握 Agent 的设计、实现、评估和运行，最终独立交付一个可以持续使用的 Agent。

规划日期：2026-10-21。学习者：Python / 深度学习基础很好；每天投入 2–3 小时；已有 Anaconda。

## 从这里开始

本日复盘：[Lecture 01：从文件工具到双工具真实循环](lectures/lecture01-agent-foundations/lecture.md)。同目录提供 LaTeX、PDF 与原始资料快照；作为下一次复习入口。

| 文档 | 用途 |
| --- | --- |
| [16 周学习路线](docs/01-roadmap.md) | 每周学什么、做什么、如何验收 |
| [知识点覆盖矩阵](docs/02-knowledge-map.md) | 必须实现、必须理解和选修拓展的边界 |
| [课程与资料导航](docs/03-resources.md) | CS2680 对应关系、后续课程和已核验来源 |
| [实验任务书](docs/04-labs.md) | 16 个递进实验及失败场景 |
| [代码实验 Agent 设计](docs/05-capstone.md) | 已选项目、架构、评测与版本目标 |
| [学习方法与环境](docs/06-learning-workflow.md) | Anaconda、每日节奏、如何与 AI 一起学 |
| [进度与验收](PROGRESS.md) | 当前状态、掌握程度、下一步 |
| [第 1 周任务](lessons/week01.md) | 可以直接开始的第一周安排 |
| [第 1 课：代码实验 Agent 如何工作](lessons/01-agent-loop.md) | 当前学习入口；概念、案例和第一道练习 |
| [文件工具与 Anaconda 实操](lessons/02-first-file-tool.md) | 当前动手入口；运行文件存在/不存在两种测试 |
| [路径范围检查](lessons/03-path-scope.md) | 下一步：理解路径拼接与授权范围的区别 |
| [工具注册表](lessons/04-tool-registry.md) | 当前小节：按名称查找函数、固定根目录、展开参数 |
| [工具参数契约](lessons/05-tool-arguments.md) | 当前小节：观察错误参数并设计调用前校验 |
| [工具的 JSON Schema](lessons/06-tool-json-schema.md) | 当前小节：向模型描述参数结构和约束 |
| [模型替身反馈循环](lessons/07-mock-agent-loop.md) | 当前小节：根据工具观察提出下一步动作并结束 |
| [真实模型接口选择](lessons/08-model-backend.md) | 当前小节：本地 Ollama 预检，以及与 Codex 集成的区别 |
| [第一次真实模型聊天](lessons/09-first-local-chat.md) | 当前小节：发送 HTTP JSON 请求、读取模型响应 |
| [真实模型的工具请求](lessons/10-real-tool-call.md) | 当前小节：观察原生 tool_calls，区分请求与执行 |
| [执行工具并回传结果](lessons/11-tool-result-reply.md) | 当前小节：执行已保存的请求，让模型根据真实结果回答 |
| [真实模型自动循环](lessons/12-real-agent-loop.md) | 当前小节：自动请求、执行、回传，直到回答或步数耗尽 |
| [工具失败的处理策略](lessons/13-tool-failure-policy.md) | 当前小节：判断何时允许修正、何时停止，限制修正次数 |
| [工具异常转换](lessons/14-tool-exceptions.md) | 当前小节：捕获具体 Python 异常，转换成错误结果交给策略 |
| [独立修改练习：工具超时分类](lessons/15-timeout-mapping-exercise.md) | 当前练习：自己补异常映射与策略理由，用 4 项独立验收测试检查 |
| [目录工具与模型选择](lessons/16-directory-tool-and-selection.md) | 当前小节：给模型两个工具，观察查看、读取及先查看再读取的选择 |
| [学习记录模板](templates/study-note.md) | 概念、实验、错题和复盘 |
| [实验报告模板](templates/experiment-report.md) | 假设、对照、指标和复现信息 |

## 路线和成果

这是一套 **16 周、每周 14–21 小时，约 224–336 小时** 的自学设计，不是学校原定课表。完成度以能力验收为准。

- 第 2 周：自己写出能调用工具、观察结果并结束任务的最小 Agent。
- 第 6 周：有检索、记忆、任务规划的原型。
- 第 8 周：能用固定任务集检验质量、可靠性和权限边界。
- 第 12 周：交付能日常使用的 API 版 Agent。
- 第 16 周：完成系统优化实验、最终评估和毕业演示。

2026-10-21 已由学习者选定：**代码实验 Agent**。项目暂称 **ExperimentAgent**，逐步实现代码库理解、配置实验、受控执行、结果验证、有限修复和报告生成。先从小型、CPU 可运行的实验项目开始，再接入深度学习项目。

技术路线：先用 Python 和模型 SDK 手写核心循环，再学习框架与 MCP；先建单 Agent 基线，再检验多 Agent 是否有价值；先交付 API 版本，再研究自部署模型。

## 课程边界

用户提供的 [leaderboard.cs2680.com](https://leaderboard.cs2680.com/) 是排行榜；正式入口为 [CS2680](https://cs2680.com/)。官网 FAQ 说明课堂不录像，因此主线采用公开讲义、阅读材料和作业方向，视频内容由 Berkeley 等公开课补充。[课程政策](https://cs2680.com/policy)

本项目是独立自学计划，不等同正式选课、评分或排行榜提交。部分作业详情链接在本次访问中回到总览；相关实验明确为自学替代设计，不假定拥有学校 API、GPU、隐藏测试或 starter code。

当前已创建 Anaconda 环境 `agent-study`（Python 3.11.17），学习者已独立完成工具超时分类修改，并完成 l14 查看、读取和先查看再读取三种真实模型任务，正确解释了目录元数据与文件正文的区别。AI 验收 tests/ 50 项与 exercises/ 4 项均通过；本次学习者附件未提供新的 50 项测试输出。今日内容已整理为 43 页讲义，附 PDF、LaTeX、Markdown 与 95 份原始资料快照。
