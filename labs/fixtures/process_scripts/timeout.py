"""真实等待超过父工具固定时限，超时前刷新一次输出。"""

import time


print("超时脚本：开始等待。", flush=True)
time.sleep(10)
print("超时脚本：等待结束。", flush=True)
