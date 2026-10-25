# 受控 Python 脚本工具备课运行

日期：2026-10-22。先记录 AI 备课实际执行；学习者后续独立运行与解释另记在末尾。

实现 script_tools.run_python_script，固定 normal/error/timeout 三个 ID，执行路径解析后检查项目范围；使用当前 sys.executable、参数列表、shell=False、固定 cwd、关闭交互输入，默认子进程超时 2 秒。注册表仅在 enable_python_scripts=True 时添加工具，l14 默认工具集合保持不变。

实际启动解释器为 agent-study 的 Python 3.11.17；演示三个真实子进程，没有模型 API 调用。结果见 reports/l17_controlled_python_script.json：

| 案例 | 实测结果 | 观测耗时 |
| --- | --- | --- |
| normal | success，exit_code=0；stdout 为计算输出，stderr 为普通诊断 | 约 0.023 秒 |
| error | failed / process_failed，exit_code=1；保留失败前 stdout 和 RuntimeError 堆栈 | 约 0.022 秒 |
| timeout | failed / tool_timeout，timed_out=true，exit_code=null；保留启动输出 | 约 2.013 秒 |

正常和异常来自真实脚本内容；超时来自脚本真实等待。测试中的进程创建失败及 bytes 超时输出明确为注入，不混写为实际环境故障。

新增 12 项脚本工具测试在完整 tests/ 87 项中通过；exercises/ 12 项也通过。报告不写作学习者独立执行证据。尚未运行训练、接入模型执行请求或增加实验指标验收；退出码 0 不证明计算或实验指标正确。

此工具是可信脚本名单与超时控制，不是完整权限或资源沙箱，具体边界见第 21 课。

## 学习者独立运行与解释

学习者提供三个案例的完整终端输出：normal 为 success/0、timed_out=false，即使 stderr 有诊断信息；error 为 failed/process_failed/1，保留失败前输出和真实堆栈；timeout 为 failed/tool_timeout、exit_code=null、timed_out=true，保留启动输出。

学习者观测耗时分别约 0.021、0.020、2.012 秒，并提供本题 12 项工具测试通过结果，耗时 2.138 秒。与 AI 备课数据分开记录，不改记为已独立执行全部 87 项回归测试。

学习者正确解释：stderr 也可以输出诊断，不能按是否为空判断失败；正常案例退出码 0 且没有超时，所以工具 status 为 success。本课独立运行、指定测试与本项理解检查通过；工具实现仍由 AI 编写，尚未交给真实模型选择执行。
