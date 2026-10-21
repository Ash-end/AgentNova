# 课程与资料导航

核验日期：2026-10-21。以下页面已实际访问；“页面可访问”不代表全部视频已观看、实验已复现或账号权益已确认。代码接口与模型可用性在实际实验前再次核验。

## CS2680 主线

正式课程名：Modern AI Systems: Agents and System Optimizations，Fall 2026。[主页](https://cs2680.com/)

| 入口 | 本项目如何使用 | 本次访问状态 |
| --- | --- | --- |
| [课程主页](https://cs2680.com/) | 根据 Agent 设计与模型服务两个部分组织主线；每周从主页进入相应 slide | 页面可读，日程标明可能调整；未逐份审阅讲义 |
| [作业总览](https://cs2680.com/assignments/) | 参考观察、实现、优化、服务、全栈的递进关系 | 页面可读 |
| [Assignment 1](https://cs2680.com/assignments/assignment1) | 理解观察 Agent 行为的练习方向 | 独立页面可读 |
| [Agent evaluation](https://cs2680.com/notes/agent-evaluation) | 第 7 周评测设计选读 | 页面可读，未逐项复现 |
| [Cost-effective agents](https://cs2680.com/notes/cost-effective-agents) | 第 11 周优化实验选读 | 页面可读 |
| [Final project](https://cs2680.com/project) | 参考用实际问题、对照和测量支撑项目的方式 | 页面可读 |
| [Policy / FAQ](https://cs2680.com/policy) | 了解系统基础要求、无录像及校内资源边界 | 页面可读 |
| [排行榜](https://leaderboard.cs2680.com/) | 理解成功率、成本和耗时的权衡 | 页面可读；动态成绩未加载，不据此判断排名 |
| [学生博客](https://blog.cs2680.com/) | 后续寻找案例和失败经验 | 本次工具未能访问；尚未作为内容依据 |

### 作业与本地实验的关系

| 官方方向 | 对应本地实验 | 自学适配 |
| --- | --- | --- |
| A1 Mads-Lens：观察现有 Agent | L01，L12 再做可视化 | 先记录轨迹，完整 Web 界面延后；这不满足原 A1 的全部提交要求 |
| A2 Mads-Loop：实现运行循环 | L02–L03，L05，L07 | 从空白实现，用自己的任务集和模拟工具验收 |
| A3 Mads-Opt：优化 API Agent | L10–L11 | 固定本地 workload，做质量、成本和延迟对照 |
| A4 Mads-Serve：自行服务模型 | L13–L14 | 按个人算力选择实验规模；更小模型属于自学适配 |
| A5 Mads-Stack：跨层优化 | L15 | 至少一项有假设、测量和消融的优化 |
| Final project | L16，且从第 1 周持续积累 | 交付一个自己真正使用的 Agent |

以上作业概述来自[官方总览](https://cs2680.com/assignments/)。本次从主页点击 A2–A5 详情均回到总览，未获得完整独立说明，不声称这些材料确定未发布，也不编造官方数据集、starter code 或隐藏评分规则。需要时重新检查；本地实验可独立完成。

## 补充课程：按缺口使用

| 课程 | 适合解决的问题 | 使用阶段 | 学习范围 |
| --- | --- | --- | --- |
| [Hugging Face Agents Course](https://huggingface.co/learn/agents-course/en/unit0/introduction) | 工具调用、常用框架和 Agentic RAG 的实践入口 | 第 2、4、9 周 | Unit 1、Unit 3 必选读；Unit 2 中只选一种框架，不同时刷完所有框架 |
| [Berkeley LLM Agents，Fall 2024](https://llmagents-learning.org/f24) | 需要视频解释推理、规划、检索、应用和评测 | 第 1–10 周按需 | 从 syllabus 选与本周实验相关的讲座；课程已结束，官网保留视频链接 |
| [Berkeley Advanced LLM Agents，Spring 2025](https://llmagents-learning.org/sp25) | 深入推理、后训练、搜索、代码与多模态 Agent | 第 6、8 周选讲；第 16 周后深化 | 主线先看规划/记忆、安全；后续再看训练、程序验证等专题 |
| [Stanford CS336，Spring 2025 归档](https://cs336.stanford.edu/spring2025/) | 想深入模型本身与训练系统 | 第 16 周后选修 | 本计划有意固定 2025 归档版本，非声称它是最新课程；不作为做出 Agent 的前置条件 |
| [MIT Missing Semester](https://missing.csail.mit.edu/) | shell、Git、调试、profiling、工程工具有缺口 | 随时按需 | 以实际遇到的问题为入口，不重复学习已有基础 |

推荐顺序：**CS2680 作主线 → HF 对应单元补实践 → Berkeley F24 补视频与视野 → Berkeley SP25 深化 → 按方向选 CS336。** 这些是自行组合的后续学习资源，不是 CS2680 官方规定的后续课程。

## 论文与工程资料

| 材料 | 阅读时要回答的问题 | 产出 |
| --- | --- | --- |
| [ReAct](https://arxiv.org/abs/2210.03629) | 观察如何影响下一步行动？实验环境与我们的任务有什么差别？ | 画一个工具交互循环；实现简化版本；不把论文结论当作所有任务通则 |
| [MemGPT](https://arxiv.org/abs/2310.08560) | 哪些状态放在上下文内外？何时读写和淘汰？ | 对比全量历史、摘要和检索记忆；说明丢失信息的代价 |
| [Building effective agents](https://www.anthropic.com/research/building-effective-agents) | 什么时候固定流程更合适？增加复杂度的证据是什么？ | 把自己的任务分别映射为简单调用、workflow 和动态 Agent |
| [MCP 官方介绍](https://modelcontextprotocol.io/docs/getting-started/intro) | 工具能力、数据资源、调用协议与权限检查分别在哪一层？ | 一个自有工具的 MCP 接口；实现时再查当前 SDK 与协议版本 |
| [LangGraph 官方概览](https://docs.langchain.com/oss/python/langgraph/overview) | 框架替我们管理了哪些状态和执行语义？ | 迁移一条已理解的流程，比较代码复杂度与恢复能力 |
| [vLLM 官方文档](https://docs.vllm.ai/en/latest/) | 当前环境支持什么模型、后端和优化功能？ | 在实际安装时锁定版本，记录兼容性和运行参数 |

Anthropic 上述文章的页面提示，部分工具生态描述已随时间变化；本项目主要用它理解架构模式，SDK 用法以实施时的官方文档为准。

每周通常只安排 **1 份主材料 + 1 份补充材料 + 1 个实验**。资料清单是导航，不是要求一次读完的阅读债务。

## 来源记录方式

笔记至少保留：标题、URL、作者/机构、版本或年份、访问日期、实际阅读范围、支撑的观点、尚未验证的部分。只阅读摘要时注明“摘要”；不能写成“论文已复现”。课程原文不大段复制进项目。
