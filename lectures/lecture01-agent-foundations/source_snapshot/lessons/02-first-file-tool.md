# 第 2 次动手：文件读取工具与 Anaconda

## 文件放在哪里

```text
agent/
  experiment_agent/
    __init__.py
    tools/
      __init__.py
      file_tools.py       read_text_file 函数
  labs/
    __init__.py
    l01_read_file.py       打印两种情况的实际返回值
    fixtures/
      hello.txt           已存在的 UTF-8 文本
  tests/
    test_file_tools.py    两种情况的自动检查
```

当前使用项目根目录下的 Python 包，便于从项目根目录直接运行；早期计划中的 src 布局留到学习打包时再考虑。

`file_tools.py` 定义能力，实验脚本负责调用，测试负责核对返回值。函数由 AI 按学习者已经提出的实现思路保存；学习者独立运行与修改仍需另行记录。

## 运行步骤

在 Anaconda Prompt 中执行：

```bat
cd /d E:\study\agent
conda activate agent-study
python -c "import sys; print(sys.executable)"
python -X utf8 -m labs.l01_read_file
```

如果使用 PowerShell，切换目录用 `Set-Location E:/study/agent`。

解释器应来自 `E:\Anaconda3\envs\agent-study\python.exe`。`-X utf8` 让终端输出使用 UTF-8；文件内容的读取编码由函数内的 `encoding="utf-8"` 指定，两者负责不同环节。

`-m labs.l01_read_file` 从项目根目录按模块执行脚本，便于导入同项目下的 `experiment_agent` 包。这里不直接双击 .py 文件。

## 不激活环境的等价方式

```powershell
conda run --no-capture-output -n agent-study python -X utf8 -m labs.l01_read_file
```

## 应观察什么

第一种情况读取 `labs/fixtures/hello.txt`，返回 `status=success` 和文件内容。

第二种情况尝试读取不存在的 `labs/fixtures/missing.txt`，返回 `status=failed`、`error_type=file_not_found` 和实际查找路径。

第二种情况本身是预期行为；异常已由工具转为错误字典，所以演示脚本可以正常结束。要区分“工具返回失败状态”和“整个 Python 进程崩溃”。

演示脚本使用自己的 `__file__` 定位项目根目录，然后将绝对根目录传入工具。

## 自动检查

```powershell
conda run --no-capture-output -n agent-study python -X utf8 -m unittest discover -s tests -v
```

两个测试使用临时目录，分别创建真实 UTF-8 文件和读取不存在的文件；目录由标准库自动清理。只需要 Python 标准库，不安装 pytest 或模型 SDK。

## 学习者下一步

亲自运行演示，比较两个返回字典。然后解释：为什么第二次返回 `status=failed`，自动测试仍然应当通过？尚未回答前不标记该知识点验收完成。
