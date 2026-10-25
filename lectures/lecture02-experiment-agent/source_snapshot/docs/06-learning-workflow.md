# 学习方法与环境

## 每天 2–3 小时怎么安排

普通学习日建议：20 分钟回忆上次内容，35 分钟读材料，55 分钟写代码或做实验，10 分钟记录。还有 1 小时则用于更深入实验或论文选读。

一周可按以下方式安排：3 小时概念与阅读、7 小时实现、3 小时测量与排错、1 小时复述和复盘；额外 0–7 小时用于选修或补齐。不要把全部时间用来观看视频。

每个主题用同一个学习闭环：

1. 用自己的话描述要解决的问题。
2. 读最少必要材料，画出机制和数据流。
3. 实现最小版本，看到实际输入输出。
4. 故意制造一个失败，定位发生在哪一层。
5. 与更简单的方法比较。
6. 解释结果，保存证据，隔一段时间重新复述。

## 与 AI 一起学习

本项目默认采用导师式协作：我负责拆解、解释、设计练习、审阅和排错；你需要完成关键推理、核心实现和结果解释。你要求完整示范时可以提供，但会标记哪些部分尚未经过你独立完成。

每次学习可以这样开始：

> 开始第 X 周第 Y 次学习。先读 PROGRESS.md，根据上次未掌握的点问我 3 个诊断问题，再讲本节内容，给一个可验收的小实验。

遇到问题可以这样请求：

> 先提示我问题在哪里，不直接替我写完整代码；等我尝试后再审阅。

每周结束记录：能解释什么、独立写了什么、测到了什么、哪里仍不确定、下周先补什么。学习记录使用 [模板](../templates/study-note.md)。

掌握等级：

- 0：没接触。
- 1：阅读过，能识别术语。
- 2：能不看材料解释机制和边界。
- 3：能独立实现或完成实验分析。
- 4：能诊断失败、设计对照，并迁移到新任务。

“我替你生成了代码”和“你已经掌握了实现”分别记录，不互相替代。

## Anaconda 环境

2026-10-21 只读检查确认：`conda` 可调用，base 位于 `E:/Anaconda3`。与课程无关的环境名称已在公开版移除。当前 shell 的 `python` 指向 WindowsApps 别名，因此执行时应明确激活 Conda 环境或使用 `conda run`。

专用 `agent-study` 环境已于 2026-10-21 创建，Python 3.11.17；当前文件工具使用标准库，不需要安装额外包。可激活现有环境直接运行，详见 [实操](../lessons/02-first-file-tool.md)。下面的创建命令仅供未来重建，后续第三方包按课程需要再安装。

```powershell
conda create -n agent-study python=3.11 pip
conda activate agent-study
python -c "import sys; print(sys.executable); print(sys.version)"
python -m pip install pytest pydantic httpx python-dotenv
```

如果当前 shell 无法激活，可在 Anaconda Prompt 操作，或使用：

```powershell
conda run -n agent-study python -c "import sys; print(sys.executable)"
```

原则：按周添加必要依赖；第二周选一个模型 SDK，第四周才引入检索所需库，第九周才引入框架。第一次成功运行后记录版本和导出环境，后续实验用固定环境，不在 base 里集中安装所有 Agent 框架。

密钥放环境变量或本机不入库的配置文件；日志与评测报告不记录密钥。依赖安装不等于已经接通模型，也不等于拥有付费额度。

GPU 服务阶段另核验驱动、显存、运行平台和引擎兼容性，必要时采用适配的 Linux/WSL2/远程环境。不能仅凭 Windows 上有 Anaconda 就认定 vLLM GPU 服务可运行；实施以[官方安装文档入口](https://docs.vllm.ai/en/latest/)为准。

## 目录演进建议

当前已创建文档、任务、模板，以及项目根目录下的 `experiment_agent/tools/file_tools.py`、`labs/l01_read_file.py` 和 `tests/test_file_tools.py`。初学阶段使用根目录包方便运行，下面的 src 布局为后续演进建议，不代表已经迁移：

```text
agent/
  README.md
  PROGRESS.md
  docs/                 路线、知识地图、资料与任务书
  lessons/              每周学习任务
  templates/            学习与实验模板
  notes/                你实际完成的笔记（后续创建）
  src/experiment_agent/  核心实现（后续创建）
    runtime/
    models/
    tools/
    retrieval/
    memory/
    policy/
  labs/                 可重复运行的实验入口（后续创建）
  tests/                工具与运行时测试（后续创建）
  evals/                开发任务与评分器（后续创建）
  reports/              脱敏实验结果（后续创建）
  data/                 允许使用的资料（后续创建）
```

保留测试集的答案不进入 Agent 的检索库或记忆。为评价泛化而保管的材料，最好与日常开发上下文隔离。

## 成本与无 API 学习模式

第一周观察可以复用现有工具。第二周先用模拟模型验证运行时，再接实际模型。没有 API 时，schema、状态机、工具权限、故障恢复、部分评测器都可继续完成；真实模型能力和费用则标为未测量。

预算估算分输入、输出、缓存、工具服务和 GPU 时间；记录价格日期。先用 3–5 个开发任务探索，再批量评测。预算上限和人工中止应进入运行时，而不是只写在 prompt 中。
