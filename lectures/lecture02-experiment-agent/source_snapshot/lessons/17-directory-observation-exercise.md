# 第 17 次动手：用目录观察判断能否继续

学习日期：2026-10-22。预计 15–20 分钟。前置：已独立完成 l14 三个真实任务，能区分目录元数据与文件正文。

本课由学习者亲自实现一个小函数。AI 只准备函数骨架和 8 项行为验收；不预先填写答案，也不调用本地模型。

## 核心概念

工具返回 success 说明这次工具操作成功，不等于已满足用户目标。例如 list_directory 成功返回一部分条目时，truncated=true；只看到一个 .txt，不能证明整个目录只有一个 .txt。不能把“暂时没看到”当作“不存在”。

本题任务要求是“目录中有且只有一个普通 .txt 文件时，使用其路径继续读取”。因此先确认观察成功且完整，再判断候选数。本题遇到不完整结果就返回失败；分页、继续搜索等恢复方式留到后续。

## 你需要实现的函数

文件：exercises/select_text_file.py，函数：select_unique_text_file(directory_result)。

它接收已经获得的目录结果，不调用 list_directory、不读取正文、不请求模型；本题先练习确定性的数据处理。暂不注册成第三个工具，也不改变真实模型循环或全局停止策略。

本题假设输入符合现有目录工具的结构；暂不增加任意畸形输入校验。

输入例子：

```json
{
  "status": "success",
  "entries": [
    {"name": "hello.txt", "type": "file", "relative_path": "labs/fixtures/hello.txt"},
    {"name": "README.md", "type": "file", "relative_path": "labs/fixtures/README.md"}
  ],
  "truncated": false
}
```

期望输出：

```json
{"status": "success", "relative_path": "labs/fixtures/hello.txt"}
```

## 返回契约

按表中顺序判断：

| 观察情况 | 返回 |
| --- | --- |
| 原目录结果 status 不是 success | 原样返回原失败结果，保留原错误类别 |
| 目录结果 truncated=true | {"status": "failed", "error_type": "incomplete_directory_listing"} |
| 完整结果，没有候选文件 | {"status": "failed", "error_type": "no_text_file"} |
| 完整结果，有多个候选文件 | {"status": "failed", "error_type": "multiple_text_files"} |
| 完整结果，只有一个候选文件 | {"status": "success", "relative_path": 候选条目的原 relative_path} |

候选必须同时满足 type 等于 file、name 以 .txt 结尾；扩展名大小写不敏感。目录和符号链接不算本题候选；这不是宣称符号链接一定不可读，而是本题“普通文件”的选择规则。

不要修改输入字典，不要猜路径、拼接项目根目录或去掉合法文件名中的空格。返回已有条目的 relative_path，后续读取工具仍需自己做路径范围检查。

提示：先写提前返回的分支，再遍历 entries 收集候选，最后按候选数量判断。可用字符串 lower 或 casefold 处理扩展名大小写，用 endswith 判断后缀。暂时不提供完整实现。

## 运行验收

在项目根目录的 Anaconda Prompt 中运行：

```bat
conda activate agent-study
python -X utf8 -m unittest discover -s exercises -p test_text_file_selection.py -v
```

初始函数主动抛出 NotImplementedError，8 项会报错。这是待完成练习的起点，不代表昨日 Agent 代码回归。只修改 exercises/select_text_file.py，不修改验收用例。

AI 备课验证：现有 tests/ 50 项通过；本题 8 项均能加载，初始报错全部来自上述待实现占位。学习者尚未提交实现或运行结果。

完成后再次运行同一命令，应 8 项全部通过。必要时再运行已有功能的测试：

```bat
python -X utf8 -m unittest discover -s tests -v
```

本题没有新增真实模型实验或结果报告；不要将测试通过记录成已经接入 Agent。通过后，下一步再讨论如何把判断结果接到读取步骤，并区分固定流程和模型决策。

## 交给我检查

提供你实现的函数和 8 项验收结果，并解释：如果 truncated=true，entries 里恰好只有 hello.txt，为什么不能继续断言“整个目录中有且只有这一个 .txt”？

## 首次提交检查

学习者依据提示补全函数后，AI 用 agent-study 实际运行本题测试：8 项中 5 项通过、3 项失败。未改动学习者函数。问题集中在候选数量判断与成功 return 仍位于 for 循环内部；待学习者将数量判断移至遍历结束之后，再复验。暂未完成验收，也尚未接入 Agent。

## 修正后复验

2026-10-22 学习者自行调整缩进，AI 检查实际代码并重新运行指定验收命令：8 项全部通过。候选筛选先完成遍历，再判断数量；失败传播、截断优先判断、空目录、多文件、大小写、路径空格与输入不变均符合本题契约。本次保留学习者源码，未代改。截断观察的独立解释尚待复述，函数还未接入 Agent 或真实读取流程。
