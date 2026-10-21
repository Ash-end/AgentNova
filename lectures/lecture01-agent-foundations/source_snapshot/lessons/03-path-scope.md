# 第 3 次动手：工具可以读哪些路径

## 起点与本课目标

学习者已在 agent-study 环境中独立运行文件工具演示和两个自动测试，并提供终端输出。函数由 AI 保存，不能据此声称学习者已独立实现。

本课学习：先判断路径是否属于授权项目，再尝试读取；区分“允许读取”和“文件存在”。

## 为什么拼接不等于限制范围

```python
Path("E:/study/agent") / "../outside-demo.txt"
```

解析后是 E:/study/outside-demo.txt。拼接本身没有拒绝 `..`。Windows 上，其他绝对路径输入也可能替代原先的根路径。

project_root 应由可信的运行配置指定，后续工具接口只让模型提供 relative_path；否则模型可自行替换根目录，范围检查就失去意义。

## 两个操作

```python
root = Path(project_root).resolve()
target = (root / relative_path).resolve()
allowed = target.is_relative_to(root)
```

resolve 解析相对段和可解析的链接；is_relative_to 判断解析后路径是否位于根目录下。先解析再比较，避免仅检查字符串前缀。当前只学习本地路径范围，不将此检查等同于完整执行沙箱。

文件不存在也可以计算路径范围：resolve 默认不要求目标存在。范围判断通过后，实际读取仍可能产生 FileNotFoundError。

## 运行示例

在项目根目录、已激活 agent-study 时执行：

```bat
python -X utf8 -m labs.l02_path_scope
```

脚本仅计算和打印路径，不读取示例目标，也不会创建项目外文件。四个输入依次为项目内已有文件、项目内缺失文件、带 .. 的外部路径、外部绝对路径。

## 本轮练习

运行后解释：为什么 missing.txt 尚不存在，但 allowed 仍然是 True？如果加入读取工具，这种情况应返回 file_not_found 还是 path_outside_project？

学习者已正确回答 file_not_found，并提供四种路径的实际演示输出。现已把检查加入文件工具，并增加三项越界回归用例。运行：

```bat
python -X utf8 -m unittest discover -s tests -v
```

AI 已实际验证总计 5 项通过；学习者复跑待完成。新增检查位于 read_text 之前：项目外路径不进行读取，直接返回 path_outside_project；项目内路径继续读取，缺失时返回 file_not_found。

新增用例：带 .. 访问项目外已存在文件、绝对路径访问名称有共同前缀的兄弟目录、项目外不存在文件。用例仅在临时目录内创建自己的练习数据。
