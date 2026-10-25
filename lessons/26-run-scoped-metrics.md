# 第 26 次动手：执行脚本，只验收本次运行的指标

准备日期：2026-10-23。2026-10-25 学习者已在 agent-study 独立运行五例，指定 12 项测试通过，并正确复述本次目录缺少指标才导致外层失败。运行器独立实现与目录绑定机制的完整复述仍待验收。

## 为什么只读 metrics.json 不够

昨天的实验可能已生成一个合格文件，今天的脚本却没有写文件。如果仍读取共享路径，就会把旧结果当成本次结果。stdout 声称保存成功、文件存在或修改时间较新，都不能单独证明来源。

本次使用新目录和运行编号组合：

```text
Python 创建 run_id 和全新 runs/<run_id>/
  → 固定脚本在此目录作为 cwd 的子进程中执行
  → 脚本写入 metrics.json，正文包含同一个 run_id
  → 确认进程 success，否则立即停止
  → 只在本次目录内读取 metrics.json
  → 解析 JSON
  → 比较文件 run_id 与父进程保存的编号
  → 调用已有 verify_metrics
```

## 一、父进程分配运行上下文

experiment_agent/experiment_workflow.py 中的 run_experiment_workflow 使用 uuid4().hex 生成编号，构造 runs/<run_id>/metrics.json。mkdir(..., exist_ok=False) 拒绝复用旧目录；即使编号碰撞，也报 run_setup_failed，不覆盖旧文件。

路径由可信 Python 程序决定，不接收模型提供的输出位置。runs/ 中的生成物留在本地，并已加入 Git 忽略。

## 二、脚本在哪写文件

只执行固定的 labs/fixtures/experiment_scripts/write_metrics.py，使用当前 sys.executable，shell=False，stdin 禁用、输出捕获、默认超时 2 秒。cwd 设为本次运行目录，而不是改变父进程的当前目录。

脚本收到 --run-id 参数；相对写入 Path("metrics.json")，因此落在 runs/<run_id>/metrics.json：

```json
{"run_id": "父进程生成的编号", "mse": 0.04}
```

mse=0.04 是固定教学值，没有训练发生。本次脚本执行器是可信工作流内部能力，不注册给模型；原 l17/l18 的三个脚本、注册表和参数限制保持原样。

## 三、执行失败时不读取结果

即使异常脚本或超时脚本已写入文件，执行失败也立即返回，不做指标验收。不能只因为有文件，就忽略失败的进程。

## 四、只读本次目录，并检查编号

读取工具的 project_root 缩小为本次目录，输入固定为 metrics.json。因此常规路径解析也不能把本次目录外的旧文件当成目标。

已有 run_metrics_file_workflow 增加可选的 expected_run_id 参数。省略时仍是 l19 的三步流程；传入时，在 JSON 解析成功后、指标验收前，增加 check_run_id。

编号缺失或不一致返回 run_id_mismatch，不能继续验收 mse，也不去其他目录查找替代文件。通过编号检查后，仍需要数值和阈值检查。

这一关联建立在固定可信脚本、没有外部并发篡改运行目录的前提下。run_id 是关联标记，不是签名；它不证明数值来自真实训练，也不阻止恶意脚本主动伪造标记。本课不是完整文件系统或网络隔离沙箱。

## 五个真实运行案例

| 案例 | 执行 | 预期验收 |
| --- | --- | --- |
| normal | 正常写入本次编号和指标 | passed / verified_metrics |
| missing_metrics | 退出码 0，但不写本次文件；上一例文件仍存在 | failed / file_not_found，禁止回退读取旧结果 |
| wrong_run_id | 正常写入合法 mse，但编号故意为 previous_run | failed / run_id_mismatch |
| error | 写入后抛异常 | failed / process_failed，不读取文件 |
| timeout | 写入后长时间等待 | failed / tool_timeout，不读取文件 |

在 Anaconda 中运行：

```bat
cd /d E:\study\agent
conda activate agent-study
python -X utf8 -m labs.l20_run_scoped_metrics
python -X utf8 -m unittest discover -s tests -p test_experiment_workflow.py -v
```

演示保留 runs/ 下的实际产物，报告写到 reports/l20_run_scoped_metrics.json。报告把项目根目录替换为 <demo_project>；运行编号与项目相对路径保留，便于复盘。12 项测试覆盖新目录、旧文件误用、编号错误、进程失败、超时、阈值、碰撞与拒绝非法执行输入。

## 本次理解检查

missing_metrics 的 execution 明明是 success，旧文件也仍然存在，为什么仍然返回 file_not_found？请沿着 metrics_path 和读取工具绑定的根目录解释，而不是只回答“因为策略要求停止”。
