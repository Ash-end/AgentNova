"""子进程里的真实未捕获异常，不是直接向父工具注入异常。"""


print("异常脚本：准备触发 RuntimeError。", flush=True)
raise RuntimeError("演示用异常：计算未完成。")
