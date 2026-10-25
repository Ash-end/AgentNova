# 第 27 次动手：真实线性回归训练与指标验收

日期：2026-10-25。AI 已实现、运行并测试；学习者已独立运行两组训练及指定 7 项测试，正确区分进程成功与指标未达标。模型配置决策及独立实现尚未验收。

## 这次变化

之前 write_metrics.py 写入固定 mse=0.04，用来验证运行来源和故障分支。本课新增 experiments/linear_regression/train.py，真实更新线性模型的参数，再用验证集计算 MSE。原 l20 故障演示保留。

不需要新依赖：使用当前 Anaconda 解释器、CPU 和 Python 标准库。训练脚本仍由固定 workflow 执行，尚未让模型选择配置。

## 实验规则预先固定

数据由 y=3x+2+噪声生成，x 在 [-1, 1] 均匀采样，噪声标准差为 0.1。128 个训练样本、64 个独立生成的验证样本，分别使用固定随机种子 20261025 和 20261026。

两组配置都从 weight=0、bias=0 出发，执行 100 次全批量梯度下降，只改变学习率：0.1 与 0.01。数据、初始化、预算和验收阈值相同；验证集不参与梯度更新、早停或选择训练步数。此处不是最终保留测试集评测。

## 训练脚本负责什么

模型预测为 prediction = weight * x + bias。对训练集残差求梯度，更新 weight、bias；更新结束后分别计算训练集和验证集 MSE。

```python
model = fit_line(train_data, config["learning_rate"], config["steps"])
validation_mse = mse(validation_data, model["weight"], model["bias"])
```

metrics.json 的 mse 字段等于 validation_mse，保持与学习者 verify_metrics 的接口兼容。mse 由实际预测与标签计算，不能从模型回答、预期答案或阈值反推出一个数值。

额外记录 initial_train_mse、initial_validation_mse 和 baseline_validation_mse。均值基线用训练集标签均值作为常数预测，再在验证集上评估，不使用验证集标签均值拟合基线。

## 运行器与验收器负责什么

experiment_workflow.py 新增两个固定训练 case：linear_regression、linear_regression_slow。它们指向固定训练脚本，脚本只接受本程序生成的 run_id 和固定 case。原执行工具、模型注册表和旧故障 case 不变。

运行仍沿用：

```text
新 run_id / 新目录
  → 真实训练子进程
  → 成功退出后读取本次 metrics.json
  → 解析 JSON
  → check_run_id
  → verify_metrics 检查验证集 MSE 是否不超过 0.1
```

训练脚本计算指标，运行器记录执行和路径，验收器判断任务要求是否满足。进程 success 与指标 passed 仍然分别判断。

## 本次目录保存哪些产物

| 文件 | 内容 |
| --- | --- |
| config.json | 学习率、步数、样本数、种子、初始化及数据生成设置 |
| data.json | 本次实际训练和验证数据 |
| model.json | 训练得到的 weight、bias |
| validation_predictions.json | 验证样本的 x、真实标签和预测值 |
| metrics.json | 本次 run_id、各项 MSE、模型、配置、数据指纹、训练脚本 SHA256、Python 版本及训练耗时 |

这些文件留在 runs/<run_id>/，Git 忽略；精简实验报告保存到 reports/l21_real_linear_regression.json。训练耗时只测参数更新循环，区别于运行器的整个子进程耗时。一次极短 CPU 耗时不用于性能排名。

独立测试从 data.json 的验证集与 model.json 重新计算预测和 MSE，核对预测文件及报告，而不调用训练脚本里的 mse 函数。这提供本实验的数值交叉检查；运行时的通用 verify_metrics 仍只验结构、有限性、非负性与阈值，不是通用防伪裁判。

## 实际测量（AI 首次运行）

| 学习率 | 步数 | 初始训练 MSE | 最终训练 MSE | 最终验证 MSE | 验收 |
| --- | --- | --- | --- | --- | --- |
| 0.1 | 100 | 6.77084887 | 0.01132177 | 0.01207715 | passed |
| 0.01 | 100 | 6.77084887 | 0.89226171 | 0.87744596 | failed / mse_above_threshold |

两组初始验证 MSE 均为 5.57655214，均值基线验证 MSE 均为 3.19075572。学习率 0.1 训练得到 weight≈2.99633、bias≈2.00068。

两组进程都正常退出，run_id 均匹配。低学习率配置在固定预算下未达到目标，不自动重试、不改阈值、不伪造成功。此结论只针对该固定小型合成任务及预算，不表示学习率越大总是越好。

## 在 Anaconda 中运行

```bat
cd /d E:\study\agent
conda activate agent-study
python -X utf8 -m labs.l21_real_linear_regression
python -X utf8 -m unittest discover -s tests -p test_linear_regression_training.py -v
```

演示命令保存两组结果。两组都有有效训练、来源关联和对照条件时，命令正常结束，即使其中一组指标未达标；不要把这个演示命令的退出状态理解为每组任务都 passed。

新增 7 项测试包含真实训练、保存产物独立复算、公平对照、重复运行复现、已知无噪声直线、手算 MSE 以及正常执行但指标未达标。此前 G1 独立迁移仍未验收，不因开始训练自动标记为通过。

## 本次理解检查

linear_regression_slow 的 exit_code 为什么是 0，Workflow status 却是 failed？请说明失败来自哪一层、哪个实际指标，不要将其解释成 Python 异常。
